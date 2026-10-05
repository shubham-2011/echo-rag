"""SQLite-backed, tamper-evident audit ledger.

The local hash-chain is an operational development adapter.  It provides
durable auditability immediately, while ``contracts/EcoRAGAudit.sol`` is the
minimal public-chain anchor target.  A local block must never be represented as
a public blockchain transaction.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .canonicalizer import hash_payload, sha256_hex
from .merkle import merkle_proof, merkle_root, verify_merkle_proof


class AuditService:
    """Create and verify immutable-style audit anchors without RAG latency."""

    def __init__(self, database_path: str | Path | None = None):
        default_path = Path(__file__).resolve().parents[2] / "data" / "audit.db"
        configured_path = os.getenv("AUDIT_DATABASE_PATH")
        self.database_path = Path(database_path or configured_path or default_path)
        self._lock = threading.RLock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS audit_records (
                    id TEXT PRIMARY KEY,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    payload_hash TEXT NOT NULL,
                    schema_version TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_audit_entity
                    ON audit_records(entity_type, entity_id, created_at DESC);
                CREATE TABLE IF NOT EXISTS audit_blocks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    anchor_type TEXT NOT NULL,
                    merkle_root TEXT NOT NULL,
                    previous_block_hash TEXT,
                    block_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS audit_block_records (
                    block_id INTEGER NOT NULL REFERENCES audit_blocks(id),
                    audit_record_id TEXT NOT NULL REFERENCES audit_records(id),
                    position INTEGER NOT NULL,
                    PRIMARY KEY(block_id, audit_record_id)
                );
                """
            )

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _validate_identity(entity_type: str, entity_id: str) -> None:
        if not entity_type.strip() or not entity_id.strip():
            raise ValueError("entity_type and entity_id must not be empty.")
        if len(entity_type) > 100 or len(entity_id) > 255:
            raise ValueError("entity_type or entity_id exceeds the supported length.")

    def anchor(self, entity_type: str, entity_id: str, payload: Any, schema_version: str = "1") -> dict[str, Any]:
        """Persist a record and anchor its hash as a one-record Merkle block."""
        return self.anchor_batch([(entity_type, entity_id, payload, schema_version)])[0]

    def anchor_batch(self, records: Iterable[tuple[str, str, Any, str]]) -> list[dict[str, Any]]:
        prepared: list[dict[str, Any]] = []
        for entity_type, entity_id, payload, schema_version in records:
            self._validate_identity(entity_type, entity_id)
            canonical, payload_hash = hash_payload(payload)
            prepared.append({
                "id": str(uuid.uuid4()),
                "entity_type": entity_type.strip(),
                "entity_id": entity_id.strip(),
                "payload_json": canonical,
                "payload_hash": payload_hash,
                "schema_version": str(schema_version),
                "created_at": self._timestamp(),
            })
        if not prepared:
            raise ValueError("At least one audit record is required.")

        root = merkle_root(record["payload_hash"] for record in prepared)
        with self._lock, self._connect() as connection:
            prior = connection.execute(
                "SELECT block_hash FROM audit_blocks ORDER BY id DESC LIMIT 1"
            ).fetchone()
            previous_hash = prior["block_hash"] if prior else None
            created_at = self._timestamp()
            block_material = {
                "anchor_type": "local-hash-chain",
                "created_at": created_at,
                "merkle_root": root,
                "previous_block_hash": previous_hash,
            }
            _, block_hash = hash_payload(block_material)
            cursor = connection.execute(
                """INSERT INTO audit_blocks
                   (anchor_type, merkle_root, previous_block_hash, block_hash, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                ("local-hash-chain", root, previous_hash, block_hash, created_at),
            )
            block_id = cursor.lastrowid
            for position, record in enumerate(prepared):
                connection.execute(
                    """INSERT INTO audit_records
                       (id, entity_type, entity_id, payload_json, payload_hash, schema_version, created_at)
                       VALUES (:id, :entity_type, :entity_id, :payload_json, :payload_hash, :schema_version, :created_at)""",
                    record,
                )
                connection.execute(
                    "INSERT INTO audit_block_records (block_id, audit_record_id, position) VALUES (?, ?, ?)",
                    (block_id, record["id"], position),
                )

        return [
            {
                "audit_record_id": record["id"],
                "entity_type": record["entity_type"],
                "entity_id": record["entity_id"],
                "payload_hash": record["payload_hash"],
                "merkle_root": root,
                "anchor_type": "local-hash-chain",
                "block_number": block_id,
                "block_hash": block_hash,
                "transaction_hash": None,
                "status": "anchored_local",
                "anchored_at": created_at,
            }
            for record in prepared
        ]

    def latest_for_entity(self, entity_id: str, entity_type: str = "experiment") -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                """SELECT r.*, br.position, b.id AS block_number, b.merkle_root, b.block_hash, b.anchor_type
                   FROM audit_records r
                   JOIN audit_block_records br ON br.audit_record_id = r.id
                   JOIN audit_blocks b ON b.id = br.block_id
                   WHERE r.entity_type = ? AND r.entity_id = ?
                   ORDER BY r.created_at DESC LIMIT 1""",
                (entity_type, entity_id),
            ).fetchone()
        return dict(row) if row else None

    def list_records(self, entity_type: str = "experiment", limit: int = 100) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 500))
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT r.id AS audit_record_id, r.entity_type, r.entity_id, r.payload_hash,
                          r.schema_version, r.created_at, b.id AS block_number, b.merkle_root,
                          b.block_hash, b.anchor_type
                   FROM audit_records r
                   JOIN audit_block_records br ON br.audit_record_id = r.id
                   JOIN audit_blocks b ON b.id = br.block_id
                   WHERE r.entity_type = ? ORDER BY r.created_at DESC LIMIT ?""",
                (entity_type, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def verify(self, entity_id: str, payload: Any | None = None, entity_type: str = "experiment") -> dict[str, Any] | None:
        record = self.latest_for_entity(entity_id, entity_type)
        if record is None:
            return None
        local_payload = json.loads(record["payload_json"])
        _, local_hash = hash_payload(local_payload if payload is None else payload)

        with self._connect() as connection:
            rows = connection.execute(
                """SELECT r.id, r.payload_hash, br.position
                   FROM audit_block_records br JOIN audit_records r ON r.id = br.audit_record_id
                   WHERE br.block_id = ? ORDER BY br.position""",
                (record["block_number"],),
            ).fetchall()
            block = connection.execute("SELECT * FROM audit_blocks WHERE id = ?", (record["block_number"],)).fetchone()

        current_hashes = [local_hash if row["id"] == record["id"] else row["payload_hash"] for row in rows]
        calculated_root = merkle_root(current_hashes)
        block_material = {
            "anchor_type": block["anchor_type"],
            "created_at": block["created_at"],
            "merkle_root": block["merkle_root"],
            "previous_block_hash": block["previous_block_hash"],
        }
        _, calculated_block_hash = hash_payload(block_material)
        verified = (
            local_hash == record["payload_hash"]
            and calculated_root == block["merkle_root"]
            and calculated_block_hash == block["block_hash"]
        )
        return {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "database_hash": local_hash,
            "anchored_hash": record["payload_hash"],
            "merkle_root": block["merkle_root"],
            "calculated_merkle_root": calculated_root,
            "block_number": block["id"],
            "anchor_type": block["anchor_type"],
            "verified": verified,
            "status": "verified" if verified else "mismatch",
        }

    def proof(self, entity_id: str, entity_type: str = "experiment") -> dict[str, Any] | None:
        """Export a database-independent Merkle proof for the latest entity record."""
        record = self.latest_for_entity(entity_id, entity_type)
        if record is None:
            return None
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT r.payload_hash, br.position FROM audit_block_records br
                   JOIN audit_records r ON r.id = br.audit_record_id
                   WHERE br.block_id = ? ORDER BY br.position""",
                (record["block_number"],),
            ).fetchall()
        hashes = [row["payload_hash"] for row in rows]
        leaf_index = next(i for i, row in enumerate(rows) if row["position"] == record["position"])
        proof = merkle_proof(hashes, leaf_index)
        return {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "payload_hash": record["payload_hash"],
            "leaf_index": leaf_index,
            "proof": proof,
            "merkle_root": record["merkle_root"],
            "block_number": record["block_number"],
            "anchor_type": record["anchor_type"],
            "verified": verify_merkle_proof(record["payload_hash"], proof, record["merkle_root"]),
        }

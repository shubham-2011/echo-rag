"""Durable experiment lifecycle and provenance manifest service."""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.audit import AuditService
from src.audit.canonicalizer import hash_payload


class ExperimentRunStore:
    """SQLite store that freezes experiment inputs and anchors terminal results."""

    def __init__(self, database_path: str | Path | None = None, audit_service: AuditService | None = None):
        default_path = Path(__file__).resolve().parents[1] / "data" / "experiments.db"
        self.database_path = Path(database_path or os.getenv("EXPERIMENT_DATABASE_PATH") or default_path)
        self.audit_service = audit_service or AuditService()
        self._lock = threading.RLock()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS experiment_runs (
                experiment_id TEXT PRIMARY KEY, name TEXT NOT NULL, status TEXT NOT NULL,
                dataset_json TEXT NOT NULL, configuration_json TEXT NOT NULL,
                result_json TEXT, telemetry_json TEXT, environment_json TEXT,
                manifest_json TEXT, manifest_hash TEXT, audit_json TEXT,
                failure_reason TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            )""")

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _json(value: Any) -> str:
        return hash_payload(value)[0]

    @staticmethod
    def _decode(row: sqlite3.Row) -> dict[str, Any]:
        result = dict(row)
        for key in ("dataset", "configuration", "result", "telemetry", "environment", "manifest", "audit"):
            raw = result.pop(f"{key}_json", None)
            result[key] = json.loads(raw) if raw else None
        return result

    def create(self, name: str, dataset: dict[str, Any], configuration: dict[str, Any]) -> dict[str, Any]:
        experiment_id, now = str(uuid.uuid4()), self._now()
        with self._lock, self._connect() as connection:
            connection.execute("""INSERT INTO experiment_runs
                (experiment_id,name,status,dataset_json,configuration_json,created_at,updated_at)
                VALUES (?,?,?,?,?,?,?)""", (experiment_id, name, "queued", self._json(dataset), self._json(configuration), now, now))
        return self.get(experiment_id)  # type: ignore[return-value]

    def get(self, experiment_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM experiment_runs WHERE experiment_id = ?", (experiment_id,)).fetchone()
        return self._decode(row) if row else None

    def list(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM experiment_runs ORDER BY created_at DESC LIMIT ?", (max(1, min(limit, 500)),)).fetchall()
        return [self._decode(row) for row in rows]

    def cancel(self, experiment_id: str) -> dict[str, Any] | None:
        record = self.get(experiment_id)
        if record is None:
            return None
        if record["status"] not in {"queued", "running"}:
            raise ValueError("Only queued or running experiments can be cancelled.")
        with self._lock, self._connect() as connection:
            connection.execute("UPDATE experiment_runs SET status='cancelled', updated_at=? WHERE experiment_id=?", (self._now(), experiment_id))
        return self.get(experiment_id)

    def complete(self, experiment_id: str, result: dict[str, Any], telemetry: dict[str, Any], environment: dict[str, Any]) -> dict[str, Any] | None:
        record = self.get(experiment_id)
        if record is None:
            return None
        if record["status"] == "cancelled":
            raise ValueError("A cancelled experiment cannot be completed.")
        dataset_hash = hash_payload(record["dataset"])[1]
        configuration_hash = hash_payload(record["configuration"])[1]
        result_hash = hash_payload(result)[1]
        telemetry_hash = hash_payload(telemetry)[1]
        manifest = {
            "schema_version": "1", "experiment_id": experiment_id,
            "dataset": {"sha256": dataset_hash}, "configuration": {"sha256": configuration_hash},
            "result": {"sha256": result_hash}, "telemetry": {"sha256": telemetry_hash},
            "environment": environment, "created_at": self._now(),
        }
        _, manifest_hash = hash_payload(manifest)
        anchor = self.audit_service.anchor("experiment", experiment_id, manifest, schema_version="1")
        with self._lock, self._connect() as connection:
            connection.execute("""UPDATE experiment_runs SET status='completed', result_json=?, telemetry_json=?,
                environment_json=?, manifest_json=?, manifest_hash=?, audit_json=?, updated_at=? WHERE experiment_id=?""",
                (self._json(result), self._json(telemetry), self._json(environment), self._json(manifest), manifest_hash, self._json(anchor), self._now(), experiment_id))
        return self.get(experiment_id)

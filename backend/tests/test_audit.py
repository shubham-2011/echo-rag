import json

from src.audit.canonicalizer import hash_payload
from src.audit.merkle import merkle_root
from src.audit.service import AuditService


def test_canonical_hash_ignores_json_key_order():
    _, first_hash = hash_payload({"latency_ms": 84.2, "model": "MiniLM"})
    _, second_hash = hash_payload({"model": "MiniLM", "latency_ms": 84.2})
    assert first_hash == second_hash


def test_merkle_root_is_deterministic():
    leaves = ["a" * 64, "b" * 64, "c" * 64]
    assert merkle_root(leaves) == merkle_root(leaves)
    assert merkle_root(leaves) != merkle_root(list(reversed(leaves)))


def test_anchor_and_verify_detects_tampering(tmp_path):
    service = AuditService(tmp_path / "audit.db")
    experiment = {
        "dataset_version": "v1",
        "energy_wh": 0.00231,
        "latency_ms": 184.7,
        "model": "all-MiniLM-L6-v2",
    }
    anchor = service.anchor("experiment", "EXP-001", experiment)

    assert anchor["status"] == "anchored_local"
    assert service.verify("EXP-001", experiment)["verified"] is True
    assert service.verify("EXP-001", {**experiment, "energy_wh": 9.9})["verified"] is False


def test_batch_uses_one_merkle_block(tmp_path):
    service = AuditService(tmp_path / "audit.db")
    anchored = service.anchor_batch([
        ("experiment", "EXP-001", {"score": 0.8}, "1"),
        ("experiment", "EXP-002", {"score": 0.9}, "1"),
    ])

    assert len(anchored) == 2
    assert anchored[0]["block_number"] == anchored[1]["block_number"]
    assert anchored[0]["merkle_root"] == anchored[1]["merkle_root"]

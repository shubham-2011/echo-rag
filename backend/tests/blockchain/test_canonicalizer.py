"""BC-UNIT-* and BC-HASH-* canonicalization and hashing tests."""

import json
import pytest

from src.audit.canonicalizer import canonical_json, hash_payload

pytestmark = pytest.mark.unit


def test_bc_unit_001_same_object_twice():
    payload = {"energy": 0.5, "latency": 200}
    assert canonical_json(payload) == canonical_json(payload)


def test_bc_unit_002_key_order_independent():
    _, hash_a = hash_payload({"energy": 0.5, "latency": 200})
    _, hash_b = hash_payload({"latency": 200, "energy": 0.5})
    assert hash_a == hash_b


def test_bc_unit_003_one_field_change_changes_hash():
    _, base = hash_payload({"top_k": 5, "mode": "dense"})
    _, changed = hash_payload({"top_k": 10, "mode": "dense"})
    assert base != changed


def test_bc_unit_005_unicode_stable():
    _, h1 = hash_payload({"text": "café — 日本語"})
    _, h2 = hash_payload({"text": "café — 日本語"})
    assert h1 == h2


def test_bc_unit_006_float_deterministic():
    _, h1 = hash_payload({"energy_wh": 0.00231})
    _, h2 = hash_payload({"energy_wh": 0.00231})
    assert h1 == h2


def test_bc_hash_001_same_record_twice():
    record = {"experiment_id": "EXP-001", "energy_wh": 0.00231}
    assert hash_payload(record)[1] == hash_payload(record)[1]


def test_bc_hash_002_modify_energy_changes_hash():
    base = {"energy_wh": 0.00231, "latency_ms": 184.7}
    tampered = {"energy_wh": 0.00031, "latency_ms": 184.7}
    assert hash_payload(base)[1] != hash_payload(tampered)[1]


def test_bc_hash_004_config_top_k_change():
    assert hash_payload({"top_k": 5})[1] != hash_payload({"top_k": 10})[1]


def test_bc_hash_007_empty_object_allowed():
    _, digest = hash_payload({})
    assert len(digest) == 64


def test_bc_hash_008_nan_rejected():
    with pytest.raises(ValueError):
        hash_payload({"x": float("nan")})

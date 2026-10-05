"""BC-API-* and BC-VERIFY-* HTTP tests for /api/audit."""

import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.audit.service import AuditService

pytestmark = [pytest.mark.integration]


@pytest.fixture
def audit_client(tmp_path, monkeypatch):
    service = AuditService(tmp_path / "audit.db")
    monkeypatch.setattr("src.api.routes.audit.audit_service", service)
    return TestClient(app), service


def test_bc_api_001_anchor_valid_experiment(audit_client):
    client, _ = audit_client
    payload = {
        "entity_type": "experiment",
        "entity_id": "EXP-API-001",
        "payload": {"dataset_version": "dataset-v1", "energy_wh": 0.00231},
    }
    response = client.post("/api/audit/anchor", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["entity_id"] == "EXP-API-001"
    assert body["status"] == "anchored_local"
    assert len(body["payload_hash"]) == 64


def test_bc_api_002_missing_entity_id(audit_client):
    client, _ = audit_client
    response = client.post(
        "/api/audit/anchor",
        json={"entity_type": "experiment", "entity_id": "", "payload": {"x": 1}},
    )
    assert response.status_code == 422


def test_bc_verify_001_untouched_record(audit_client):
    client, _ = audit_client
    record = {
        "experiment_id": "EXP-001",
        "dataset_version": "dataset-v1",
        "git_commit": "abc123",
        "top_k": 5,
        "energy_wh": 0.00231,
        "latency_ms": 184.7,
    }
    client.post(
        "/api/audit/anchor",
        json={"entity_type": "experiment", "entity_id": "EXP-001", "payload": record},
    )
    verify = client.post(
        "/api/audit/EXP-001/verify",
        json={"entity_type": "experiment", "payload": record},
    )
    assert verify.status_code == 200
    assert verify.json()["verified"] is True


def test_bc_verify_002_energy_tamper(audit_client):
    """Primary tamper demo: energy_wh change must fail verification."""
    client, _ = audit_client
    original = {"energy_wh": 0.00231, "latency_ms": 184.7, "top_k": 5}
    client.post(
        "/api/audit/anchor",
        json={"entity_type": "experiment", "entity_id": "EXP-TAMPER", "payload": original},
    )
    tampered = {**original, "energy_wh": 0.00001}
    verify = client.post(
        "/api/audit/EXP-TAMPER/verify",
        json={"entity_type": "experiment", "payload": tampered},
    )
    body = verify.json()
    assert body["verified"] is False
    assert body["status"] == "mismatch"


def test_bc_verify_004_config_top_k(audit_client):
    client, _ = audit_client
    anchored = {"top_k": 5, "mode": "dense"}
    client.post(
        "/api/audit/anchor",
        json={"entity_type": "experiment", "entity_id": "EXP-CFG", "payload": anchored},
    )
    verify = client.post(
        "/api/audit/EXP-CFG/verify",
        json={"entity_type": "experiment", "payload": {"top_k": 10, "mode": "dense"}},
    )
    assert verify.json()["verified"] is False

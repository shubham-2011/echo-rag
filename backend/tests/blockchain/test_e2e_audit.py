"""E2E-001 / E2E-002 / E2E-005 experiment → anchor → verify → restart."""

import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.audit.service import AuditService
from src.experiment_runs import ExperimentRunStore

pytestmark = [pytest.mark.e2e, pytest.mark.integration]


@pytest.fixture
def e2e_stores(tmp_path, monkeypatch):
    audit = AuditService(tmp_path / "audit.db")
    store = ExperimentRunStore(tmp_path / "experiments.db", audit_service=audit)
    monkeypatch.setattr("src.api.routes.audit.audit_service", audit)
    monkeypatch.setattr("src.api.routes.experiments.experiment_store", store)
    return TestClient(app), audit, store, tmp_path


def test_e2e_001_full_flow(e2e_stores):
    client, audit, store, _ = e2e_stores
    created = store.create(
        "E2E-001",
        {"name": "dataset-v1", "version": "1"},
        {"chunk_size": 512, "top_k": 5, "embedding_model": "all-MiniLM-L6-v2"},
    )
    exp_id = created["experiment_id"]
    completed = store.complete(
        exp_id,
        {"answer_correct": True, "recall_at_k": 0.91},
        {"energy_wh": 0.00231, "latency_ms": 184.7, "input_tokens": 512, "output_tokens": 183},
        {"git_commit": "abc123"},
    )
    assert completed["audit"]["status"] == "anchored_local"

    get_resp = client.get(f"/api/audit/{exp_id}")
    assert get_resp.status_code == 200

    verify_resp = client.post(
        f"/api/audit/{exp_id}/verify",
        json={"entity_type": "experiment", "payload": completed["manifest"]},
    )
    assert verify_resp.json()["verified"] is True
    proof = audit.proof(exp_id)
    assert proof is not None and proof["verified"] is True


def test_e2e_002_tamper_after_anchor(e2e_stores):
    client, _, store, _ = e2e_stores
    created = store.create("tamper", {"v": 1}, {"top_k": 5})
    exp_id = created["experiment_id"]
    completed = store.complete(exp_id, {"accuracy": 0.9}, {"energy_wh": 0.00231}, {"git": "x"})
    manifest = completed["manifest"]
    verify_ok = client.post(
        f"/api/audit/{exp_id}/verify",
        json={"entity_type": "experiment", "payload": manifest},
    )
    assert verify_ok.json()["verified"] is True

    bad_manifest = dict(manifest)
    bad_manifest["environment"] = {"git": "edited-after-publication"}
    verify_bad = client.post(
        f"/api/audit/{exp_id}/verify",
        json={"entity_type": "experiment", "payload": bad_manifest},
    )
    assert verify_bad.json()["verified"] is False


def test_e2e_005_restart_recovery(tmp_path):
    """BC-AUDIT-010 / E2E-005: audit DB survives process-style reload."""
    db = tmp_path / "audit.db"
    first = AuditService(db)
    first.anchor("experiment", "EXP-RESTART", {"energy_wh": 0.01})
    second = AuditService(db)
    assert second.verify("EXP-RESTART", {"energy_wh": 0.01})["verified"] is True

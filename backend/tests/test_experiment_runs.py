from src.audit.service import AuditService
from src.audit.merkle import verify_merkle_proof
from src.experiment_runs import ExperimentRunStore


def test_completed_run_is_anchored_and_has_a_verifiable_proof(tmp_path):
    audit = AuditService(tmp_path / "audit.db")
    store = ExperimentRunStore(tmp_path / "experiments.db", audit_service=audit)
    created = store.create("baseline", {"id": "qa", "version": "1"}, {"mode": "adaptive", "top_k": 3})

    completed = store.complete(
        created["experiment_id"],
        {"eco_score": 8.8, "recall_at_k": 0.9},
        {"estimated_wh": 0.0012, "p95_latency_ms": 124},
        {"git_commit": "abc123", "models": ["MiniLM"]},
    )

    assert completed["status"] == "completed"
    assert completed["manifest_hash"]
    assert completed["audit"]["status"] == "anchored_local"
    proof = audit.proof(created["experiment_id"])
    assert proof["verified"] is True
    assert verify_merkle_proof(proof["payload_hash"], proof["proof"], proof["merkle_root"])


def test_cancelled_run_cannot_be_completed(tmp_path):
    store = ExperimentRunStore(tmp_path / "experiments.db", audit_service=AuditService(tmp_path / "audit.db"))
    created = store.create("cancel-me", {"id": "qa"}, {"mode": "sparse"})
    store.cancel(created["experiment_id"])
    try:
        store.complete(created["experiment_id"], {}, {}, {})
    except ValueError as error:
        assert "cancelled" in str(error)
    else:
        raise AssertionError("Expected completion of a cancelled run to fail")

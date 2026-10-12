import json

from fastapi.testclient import TestClient

from src.api.app import app
from src.api.dependencies import app_state
from src.ingestion import ParentDocumentStore
def test_user_documents_retrieval_and_exact_cache_are_tenant_isolated(monkeypatch):
    alice_key = "alice-only-test-api-key-at-least-32-characters"
    bob_key = "bob-only-test-api-key-at-least-32-characters"
    records = [
        {"api_key": alice_key, "subject": "alice", "scopes": ["read", "write"]},
        {"api_key": bob_key, "subject": "bob", "scopes": ["read", "write"]},
    ]
    monkeypatch.delenv("ECORAG_API_KEY", raising=False)
    monkeypatch.delenv("ECORAG_API_SCOPES", raising=False)
    monkeypatch.setenv("ECORAG_API_KEYS_JSON", json.dumps(records))
    alice = TestClient(app, headers={"Authorization": f"Bearer {alice_key}"})
    bob = TestClient(app, headers={"Authorization": f"Bearer {bob_key}"})
    document_text = (
        "alphauniquemarker is a private record owned by Alice. "
        "It must not be visible to other authenticated users."
    )

    ingest_response = alice.post(
        "/api/ingest/text",
        json={
            "text": document_text,
            "doc_id": "same-document-id",
            "chunk_size": 50,
            "chunk_overlap": 0,
        },
    )
    assert ingest_response.status_code == 200
    bob_document = "bobuniquemarker belongs to Bob and remains private to Bob."
    bob_ingest = bob.post(
        "/api/ingest/text",
        json={
            "text": bob_document,
            "doc_id": "same-document-id",
            "chunk_size": 50,
            "chunk_overlap": 0,
        },
    )
    assert bob_ingest.status_code == 200

    alice_first = alice.post(
        "/api/search",
        json={"query": "alphauniquemarker", "mode": "adaptive", "enable_rerank": False},
    )
    alice_cached = alice.post(
        "/api/search",
        json={"query": "alphauniquemarker", "mode": "adaptive", "enable_rerank": False},
    )
    bob_search = bob.post(
        "/api/search",
        json={"query": "alphauniquemarker", "mode": "adaptive", "enable_rerank": False},
    )

    assert alice_first.status_code == 200
    assert alice_first.json()["hits"]
    assert alice_cached.json()["adaptive_telemetry"]["cache_tier"] == "L1_EXACT"
    assert bob_search.status_code == 200
    assert bob_search.json()["hits"] == []
    assert bob_search.json()["adaptive_telemetry"]["cache_tier"] == "MISS"
    for mode in ("dense", "sparse", "hybrid"):
        response = bob.post(
            "/api/search",
            json={"query": "alphauniquemarker", "mode": mode, "enable_rerank": False},
        )
        assert response.status_code == 200
        assert all("alphauniquemarker" not in hit["text"] for hit in response.json()["hits"])

    alice_chunk = next(
        chunk
        for chunk in app_state.tenant_indexes["alice"].chunks
        if chunk.doc_id == "same-document-id"
    )
    assert alice_chunk.metadata["owner"] == "alice"
    parent_key = alice_chunk.metadata["parent_doc_id"]
    assert parent_key != "same-document-id"
    assert ParentDocumentStore.get_instance().get_document(parent_key) == document_text
    bob_chunk = next(
        chunk
        for chunk in app_state.tenant_indexes["bob"].chunks
        if chunk.doc_id == "same-document-id"
    )
    assert bob_chunk.metadata["parent_doc_id"] != parent_key
    assert ParentDocumentStore.get_instance().get_document(bob_chunk.metadata["parent_doc_id"]) == bob_document

    health = bob.get("/api/health")
    assert health.status_code == 200
    assert health.json()["total_indexed_chunks"] is None


def test_unknown_or_duplicate_tenant_credentials_fail_closed(monkeypatch):
    record = {
        "api_key": "alice-only-test-api-key-at-least-32-characters",
        "subject": "alice",
        "scopes": ["read"],
    }
    monkeypatch.delenv("ECORAG_API_KEY", raising=False)
    monkeypatch.setenv("ECORAG_API_KEYS_JSON", json.dumps([record, record]))

    response = TestClient(app).post(
        "/api/search",
        headers={"Authorization": f"Bearer {record['api_key']}"},
        json={"query": "secret"},
    )

    assert response.status_code == 503

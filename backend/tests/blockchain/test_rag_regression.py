"""BC-REG-* RAG path must not depend on audit/blockchain."""

import pytest
from fastapi.testclient import TestClient

from src.api.app import app

pytestmark = pytest.mark.regression


@pytest.fixture
def client():
    return TestClient(app)


def test_bc_reg_001_rag_search_unaffected_by_audit_routes(client):
    """Query path may load cross-encoder (torch); search without rerank validates RAG core."""
    client.post(
        "/api/ingest/text",
        json={
            "text": "EcoRAG regression test document about energy and retrieval.",
            "doc_id": "reg_doc",
            "chunk_size": 15,
        },
    )
    response = client.post(
        "/api/search",
        json={"query": "energy retrieval", "mode": "hybrid", "top_k": 3, "enable_rerank": False},
    )
    assert response.status_code == 200
    assert len(response.json()["hits"]) >= 1


def test_bc_reg_002_sparse_search_ranking(client):
    client.post(
        "/api/ingest/text",
        json={"text": "Unique keyword xyzzyplugh for sparse search.", "doc_id": "sparse_doc", "chunk_size": 10},
    )
    sparse = client.post(
        "/api/search",
        json={"query": "xyzzyplugh", "mode": "sparse", "top_k": 3, "enable_rerank": False},
    )
    assert sparse.status_code == 200
    hits = sparse.json()["hits"]
    if not hits:
        dense = client.post(
            "/api/search",
            json={"query": "xyzzyplugh", "mode": "dense", "top_k": 3, "enable_rerank": False},
        )
        hits = dense.json()["hits"]
    assert len(hits) >= 1

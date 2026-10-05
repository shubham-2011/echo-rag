import json
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.api.dependencies import AppState
from src.embeddings import HashEmbeddingService
from src.ingestion import Chunk
from src.persistence import IndexStore, compute_dataset_hash


@pytest.fixture
def tmp_index_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("ECORAG_INDEX_DIR", str(tmp_path))
    monkeypatch.setenv("ECORAG_INDEX_PERSIST", "true")
    return tmp_path


def test_dataset_hash_is_stable():
    chunks = [
        Chunk(text="alpha", chunk_id="a", doc_id="d", chunk_index=0, char_length=5, token_count_approx=1),
        Chunk(text="beta", chunk_id="b", doc_id="d", chunk_index=1, char_length=4, token_count_approx=1),
    ]
    assert compute_dataset_hash(chunks) == compute_dataset_hash(list(reversed(chunks)))


def test_save_and_load_round_trip(tmp_index_dir):
    store = IndexStore(tmp_index_dir)
    state = AppState.__new__(AppState)
    state.embedder = HashEmbeddingService()
    state.vector_store = __import__("src.vector_store", fromlist=["FAISSVectorStore"]).FAISSVectorStore(
        state.embedder.dimension
    )
    state.chunks = []
    state.bm25_retriever = None
    state.exact_cache = __import__("src.retrieval", fromlist=["ExactQueryCache"]).ExactQueryCache()
    state.semantic_cache = __import__("src.retrieval", fromlist=["SemanticQueryCache"]).SemanticQueryCache(
        threshold=0.90
    )
    state.classifier = __import__("src.retrieval", fromlist=["QueryClassifier"]).QueryClassifier()
    state.context_filter = __import__("src.retrieval", fromlist=["DynamicContextFilter"]).DynamicContextFilter()
    state.reranker = __import__("src.reranker", fromlist=["ThresholdGatedReranker"]).ThresholdGatedReranker()
    state._gemini_client = None
    state.index_store = store
    state.index_manifest = None
    state.index_loaded_from_disk = False

    chunk = Chunk(
        text="EcoRAG persists FAISS to disk.",
        chunk_id="c1",
        doc_id="doc",
        chunk_index=0,
        char_length=10,
        token_count_approx=5,
    )
    embedding = state.embedder.embed_batch([chunk.text])[0]
    state.vector_store.add_chunks([chunk], [embedding])
    state.chunks = [chunk]
    from src.retrieval import BM25Retriever

    state.bm25_retriever = BM25Retriever(state.chunks)

    manifest = store.save(state)
    assert manifest is not None
    assert manifest["chunk_count"] == 1
    assert (tmp_index_dir / "index_manifest.json").is_file()

    fresh = AppState.__new__(AppState)
    fresh.embedder = HashEmbeddingService()
    fresh.vector_store = __import__("src.vector_store", fromlist=["FAISSVectorStore"]).FAISSVectorStore(
        fresh.embedder.dimension
    )
    fresh.chunks = []
    fresh.bm25_retriever = None
    fresh.index_store = IndexStore(tmp_index_dir)
    loaded = fresh.index_store.load(fresh)
    assert loaded is not None
    assert fresh.vector_store.total_vectors == 1
    assert fresh.chunks[0].text.startswith("EcoRAG persists")
    assert json.loads((tmp_index_dir / "index_manifest.json").read_text())["dataset_hash"] == manifest["dataset_hash"]

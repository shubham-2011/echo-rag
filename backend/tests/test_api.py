import unittest
import sys
import os

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from src.api.app import app


class TestEcoRAGComprehensiveAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    # --- 1. System Health & Metadata Tests ---
    def test_01_root_endpoint(self):
        """Test GET / returns welcome message and documentation links."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("docs_url", data)
        self.assertIn("health_url", data)

    def test_02_health_endpoint(self):
        """Test GET /api/health returns healthy system status and model specs."""
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("total_indexed_chunks", data)
        self.assertIn("active_embedding_dimension", data)
        self.assertIn("embedding_provider", data)
        self.assertIn("reranker_model", data)
        self.assertIn("reranker_bypass_rate", data)

    # --- 2. Ingestion & Deduplication Tests ---
    def test_03_ingest_empty_text_error(self):
        """Test POST /api/ingest/text returns 400 Bad Request on empty text."""
        payload = {"text": "   ", "doc_id": "empty_doc"}
        response = self.client.post("/api/ingest/text", json=payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("cannot be empty", response.json()["detail"])

    def test_04_ingest_text_with_deduplication(self):
        """Test document ingestion with automatic paragraph deduplication."""
        text_content = (
            "EcoRAG optimizes energy consumption in Retrieval-Augmented Generation. "
            "By reducing prompt context length, it avoids quadratic attention costs in Transformers. "
            "EcoRAG optimizes energy consumption in Retrieval-Augmented Generation. "
            "By reducing prompt context length, it avoids quadratic attention costs in Transformers. "
            "FAISS provides in-memory vector indexing with zero background daemon overhead."
        )
        payload = {
            "text": text_content,
            "doc_id": "arch_doc_001",
            "chunk_size": 19,
            "chunk_overlap": 0,
            "enable_dedup": True
        }
        response = self.client.post("/api/ingest/text", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["doc_id"], "arch_doc_001")
        self.assertEqual(data["total_chunks_produced"], 3)
        self.assertEqual(data["unique_chunks_indexed"], 2)
        self.assertEqual(data["deduplicated_count"], 1)
        self.assertGreaterEqual(data["total_vectors_in_store"], 2)

    # --- 3. Modular Search Tests ---
    def test_05_search_empty_query_error(self):
        """Test POST /api/search returns 400 on empty query."""
        payload = {"query": "  ", "mode": "hybrid"}
        response = self.client.post("/api/search", json=payload)
        self.assertEqual(response.status_code, 400)

    def test_06_search_invalid_mode_error(self):
        """Test POST /api/search returns 400 on unsupported search mode."""
        payload = {"query": "energy", "mode": "quantum_search"}
        response = self.client.post("/api/search", json=payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Unsupported retrieval mode", response.json()["detail"])

    def test_07_search_sparse_bm25(self):
        """Test pure lexical BM25 search mode (zero neural compute)."""
        payload = {
            "query": "zero background daemon overhead FAISS",
            "mode": "sparse",
            "top_k": 2,
            "enable_rerank": False
        }
        response = self.client.post("/api/search", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["mode"], "sparse")
        self.assertGreater(len(data["hits"]), 0)
        self.assertIn("FAISS", data["hits"][0]["text"])

    def test_08_search_dense_faiss(self):
        """Test pure dense semantic search mode via FAISS."""
        payload = {
            "query": "How does context size affect quadratic attention?",
            "mode": "dense",
            "top_k": 2,
            "enable_rerank": False
        }
        response = self.client.post("/api/search", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["mode"], "dense")
        self.assertGreater(len(data["hits"]), 0)

    def test_09_search_hybrid_rrf_with_rerank_telemetry(self):
        """Test hybrid RRF search with threshold-gated reranker telemetry."""
        payload = {
            "query": "energy consumption in Retrieval-Augmented Generation",
            "mode": "hybrid",
            "top_k": 2,
            "enable_rerank": True
        }
        response = self.client.post("/api/search", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["mode"], "hybrid")
        self.assertGreater(len(data["hits"]), 0)
        self.assertIsNotNone(data["rerank_telemetry"])
        self.assertIn("bypassed", data["rerank_telemetry"])
        self.assertIn("reason", data["rerank_telemetry"])
        self.assertGreater(data["latency_ms"], 0.0)

    # --- 4. End-to-End Query & Telemetry Tests ---
    def test_10_query_empty_error(self):
        """Test POST /api/query returns 422 (or 400) on empty query string."""
        payload = {"query": ""}
        response = self.client.post("/api/query", json=payload)
        self.assertIn(response.status_code, [400, 422])

    def test_11_query_end_to_end_adaptive_rag(self):
        """Test end-to-end question answering with citations and live physical telemetry."""
        payload = {
            "query": "How does EcoRAG avoid quadratic attention costs?",
            "retrieval_mode": "hybrid",
            "top_k": 2,
            "max_tokens": 60
        }
        response = self.client.post("/api/query", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("answer", data)
        self.assertGreater(len(data["answer"]), 0)
        self.assertGreater(len(data["citations"]), 0)

        # Validate Telemetry card
        telemetry = data["telemetry"]
        self.assertGreater(telemetry["latency_ms"], 0.0)
        self.assertGreater(telemetry["peak_ram_mb"], 0.0)
        self.assertGreater(telemetry["estimated_wh"], 0.0)
        self.assertGreater(telemetry["eco_score"], 0.0)
        self.assertIsInstance(telemetry["rerank_bypassed"], bool)

    # --- 5. Adversarial Boundary & Validation Tests ---
    def test_12_search_boundary_top_k_zero(self):
        """Test POST /api/search with top_k=0 returns 422 Unprocessable Entity instead of 500."""
        payload = {"query": "energy", "top_k": 0}
        response = self.client.post("/api/search", json=payload)
        self.assertEqual(response.status_code, 422)

    def test_13_search_boundary_top_k_negative(self):
        """Test POST /api/search with top_k=-5 returns 422 Unprocessable Entity instead of 500."""
        payload = {"query": "energy", "top_k": -5}
        response = self.client.post("/api/search", json=payload)
        self.assertEqual(response.status_code, 422)

    def test_14_ingest_boundary_negative_chunk_size(self):
        """Test POST /api/ingest/text with chunk_size=-10 returns 422 Unprocessable Entity instead of 500."""
        payload = {"text": "Valid content to chunk", "chunk_size": -10}
        response = self.client.post("/api/ingest/text", json=payload)
        self.assertEqual(response.status_code, 422)

    def test_15_ingest_boundary_overlap_exceeds_size(self):
        """Test POST /api/ingest/text with chunk_overlap >= chunk_size returns 422 Unprocessable Entity."""
        payload = {"text": "Valid content to chunk", "chunk_size": 50, "chunk_overlap": 50}
        response = self.client.post("/api/ingest/text", json=payload)
        self.assertEqual(response.status_code, 422)

    def test_16_search_top_k_exceeds_max(self):
        """Test POST /api/search with top_k=101 returns 422 Unprocessable Entity."""
        payload = {"query": "energy", "top_k": 101}
        response = self.client.post("/api/search", json=payload)
        self.assertEqual(response.status_code, 422)

    def test_17_cors_trusted_origin(self):
        """Test OPTIONS / GET with trusted Origin header returns proper CORS headers."""
        response = self.client.get(
            "/api/health",
            headers={"Origin": "http://localhost:3000"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("access-control-allow-origin"), "http://localhost:3000")
        self.assertEqual(response.headers.get("access-control-allow-credentials"), "true")


if __name__ == "__main__":
    unittest.main()

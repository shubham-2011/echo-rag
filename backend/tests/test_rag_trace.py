"""Part 26 — log-based end-to-end RAG trace acceptance test."""

import io
import logging
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient

from src.api.app import app


class RagTraceLogCapture(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record.getMessage())


class TestRagPipelineTrace(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.handler = RagTraceLogCapture()
        logging.getLogger("ecorag.trace").addHandler(cls.handler)
        logging.getLogger("ecorag.trace").setLevel(logging.DEBUG)

    def setUp(self):
        self.handler.records.clear()
        os.environ["ECORAG_EXPOSE_TRACE"] = "true"

    def _ingest_internship_doc(self) -> str:
        text = (
            "Company: Synoptek India Private Limited. "
            "Headquarters: Pune, Maharashtra. "
            "Internship Details. Stipend: ₹10,000 per month. "
            "Work location: Pune office. ITSM tool: ServiceNow."
        )
        doc_id = "internship_eoc_pdf"
        res = self.client.post(
            "/api/ingest/text",
            json={
                "text": text,
                "doc_id": doc_id,
                "chunk_size": 25,
                "chunk_overlap": 0,
                "enable_dedup": False,
                "strategy": "standard",
            },
        )
        self.assertEqual(res.status_code, 200, res.text)
        return doc_id

    def _stage_present(self, tag: str) -> bool:
        return any(f"[{tag}]" in line for line in self.handler.records)

    def test_internship_stipend_full_trace(self):
        doc_id = self._ingest_internship_doc()
        query = "What is the internship stipend?"

        with patch("src.api.routes.query.app_state.get_gemini_client", return_value=None):
            response = self.client.post(
                "/api/query",
                json={
                    "query": query,
                    "retrieval_mode": "sparse",
                    "top_k": 3,
                    "max_tokens": 120,
                    "doc_ids": [doc_id],
                    "session_id": "test_session",
                    "turn": 2,
                },
            )

        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        request_id = data["request_id"]
        self.assertTrue(request_id.startswith("rag_"))
        self.assertEqual(data["telemetry"]["request_id"], request_id)

        logs = "\n".join(self.handler.records)
        self.assertIn(f"request_id={request_id}", logs)

        failures: list[str] = []
        if not self._stage_present("QUERY"):
            failures.append("QUERY")
        if doc_id not in logs and "internship" not in logs.lower():
            failures.append("DOCUMENT_SCOPE")
        if not self._stage_present("FAISS"):
            failures.append("FAISS")
        if not self._stage_present("RERANK"):
            failures.append("RERANK")
        if not self._stage_present("RELEVANCE_GATE"):
            failures.append("RELEVANCE_GATE")
        if not self._stage_present("CONTEXT"):
            failures.append("CONTEXT")
        if not self._stage_present("PROMPT"):
            failures.append("PROMPT")
        if not self._stage_present("LLM"):
            failures.append("LLM")
        if not self._stage_present("GROUNDING"):
            failures.append("GROUNDING")
        if not self._stage_present("TELEMETRY"):
            failures.append("TELEMETRY")
        if not self._stage_present("API_RESPONSE"):
            failures.append("API_RESPONSE")

        if "₹10,000" not in data["answer"] and "10,000" not in data["answer"]:
            failures.append("ANSWER_CONTENT")
        if "₹10,000" not in logs and "10,000" not in logs:
            failures.append("CONTEXT_CONTENT")

        trace = data.get("trace") or {}
        rewritten = (trace.get("rewritten_query") or "").strip()
        if not rewritten or "stipend" not in rewritten.lower():
            failures.append("REWRITE")
        if trace.get("request_id") != request_id:
            failures.append("TRACE_REQUEST_ID")

        self.assertFalse(failures, f"Failed stages: {', '.join(failures)}")

    def test_company_name_uses_document_not_architecture(self):
        text = (
            "About Us: Synoptek is a Global Systems Integrator (SI) and Managed IT Services Provider "
            "offering comprehensive IT management. The company was incorporated in 2001 and is "
            "headquartered in Irvine, CA. Internship Details. Stipend: ₹10,000 per month. Work location: Pune."
        )
        res = self.client.post(
            "/api/ingest/text",
            json={
                "text": text,
                "doc_id": "Pre Placement Paid Internship -EOC Engineer(1).pdf",
                "chunk_size": 40,
                "chunk_overlap": 0,
                "enable_dedup": False,
                "strategy": "standard",
            },
        )
        self.assertEqual(res.status_code, 200, res.text)
        with patch("src.api.routes.query.app_state.get_gemini_client", return_value=None):
            response = self.client.post(
                "/api/query",
                json={
                    "query": "What is the company name?",
                    "retrieval_mode": "adaptive",
                    "top_k": 5,
                    "doc_ids": ["Pre Placement Paid Internship -EOC Engineer(1).pdf"],
                },
            )
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        answer = data["answer"]
        self.assertIn("Synoptek", answer)
        self.assertNotIn("FAISS", answer)
        self.assertNotIn("energy-optimized pipeline", answer)
        self.assertGreater(len(data["citations"]), 0)
        self.assertTrue(any("Synoptek" in (c.get("text") or "") for c in data["citations"]))
        self.assertEqual(data["request_id"], data["telemetry"]["request_id"])


if __name__ == "__main__":
    unittest.main()

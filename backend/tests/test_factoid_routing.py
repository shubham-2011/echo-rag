import unittest
from src.retrieval import QueryClassifier, QueryComplexity
from src.observability.trace import extractive_answer
from src.ingestion import Chunk


class TestFactoidRouting(unittest.TestCase):
    def test_company_name_is_simple(self):
        c = QueryClassifier()
        self.assertEqual(c.classify("What is the company name?"), QueryComplexity.SIMPLE)
        self.assertEqual(c.classify("Where is it headquartered?"), QueryComplexity.SIMPLE)
        self.assertEqual(c.classify("What is the internship stipend?"), QueryComplexity.SIMPLE)

    def test_extractive_uses_about_us_not_pipeline(self):
        chunk = Chunk(
            text="About Us: Synoptek is a Global Systems Integrator (SI) and Managed IT Services Provider.",
            chunk_id="c1",
            doc_id="doc.pdf",
            chunk_index=0,
            char_length=90,
            token_count_approx=14,
            metadata={"filename": "doc.pdf", "page": 1, "section": "About Us"},
        )
        answer = extractive_answer("What is the company name?", [(chunk, 1.0)])
        self.assertIn("Synoptek", answer)
        self.assertNotIn("FAISS", answer)

    def test_ceo_abstains(self):
        chunk = Chunk(
            text="About Us: Synoptek is a Global Systems Integrator. Headquartered in Irvine, CA.",
            chunk_id="c1",
            doc_id="doc.pdf",
            chunk_index=0,
            char_length=80,
            token_count_approx=12,
            metadata={},
        )
        answer = extractive_answer("Who is the CEO?", [(chunk, 1.0)])
        self.assertIn("couldn't find", answer.lower())

import unittest

from src.ingestion import Chunk
from src.observability.trace import RequestTrace, compact_factoid_answer, extractive_answer, normalize_query


class TestQueryNormalization(unittest.TestCase):
    def test_stiphan_maps_to_stipend(self):
        trace = RequestTrace("how much stiphan")
        normalized = normalize_query("how much stiphan", trace)
        self.assertIn("stipend", normalized.lower())
        self.assertNotIn("10000", normalized)
        self.assertNotIn("3.5", normalized)

    def test_internship_pay_paraphrase(self):
        trace = RequestTrace("how much does the internship pay?")
        normalized = normalize_query("how much does the internship pay?", trace)
        self.assertIn("stipend", normalized.lower())

    def test_does_not_rewrite_unrelated_words(self):
        trace = RequestTrace("What is Round 2?")
        normalized = normalize_query("What is Round 2?", trace)
        self.assertEqual(normalized.lower(), "what is round 2")

    def test_does_not_change_headquartered(self):
        trace = RequestTrace("Where is it headquartered?")
        normalized = normalize_query("Where is it headquartered?", trace)
        self.assertIn("headquartered", normalized.lower())
        self.assertNotEqual(normalized.lower(), "where is it headquarters")


class TestFactoidBrevity(unittest.TestCase):
    def test_headquarters_is_short_span(self):
        chunk = Chunk(
            text="Who are we: Incorporated in 2001; Headquartered in Irvine, CA. About Us: Synoptek is a Global Systems Integrator.",
            chunk_id="c1",
            doc_id="doc.pdf",
            chunk_index=0,
            char_length=120,
            token_count_approx=20,
            metadata={"section": "Who are we"},
        )
        answer = extractive_answer("Where is it headquartered?", [(chunk, 1.0)])
        self.assertIn("Irvine", answer)
        self.assertNotIn("1100", answer)
        self.assertLess(len(answer.split()), 16)

    def test_stipend_compact_uses_context_amount(self):
        chunk = Chunk(
            text="Internship Details / Stipend: ₹10,000 per month.",
            chunk_id="c1",
            doc_id="doc.pdf",
            chunk_index=0,
            char_length=48,
            token_count_approx=8,
            metadata={"section": "Internship Details", "subsection": "Stipend"},
        )
        compact = compact_factoid_answer(
            "What is the stipend?",
            "Internship Details / Stipend: ₹10,000 per month. Shift 7.30AM to 4.30PM",
            [(chunk, 1.0)],
        )
        self.assertIn("10,000", compact)
        self.assertIn("per month", compact.lower())
        self.assertNotIn("7.30", compact)

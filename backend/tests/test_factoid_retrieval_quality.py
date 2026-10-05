import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from synoptek_smoke_benchmark import normalize_money_text

from src.ingestion import Document, HeadingAwareChunker
from src.observability.trace import extractive_answer, validate_grounding
from src.retrieval import BM25Retriever, DynamicContextFilter, apply_section_boost, classify_query_profile


JD_TEXT = """
About Us
Synoptek is a Global Systems Integrator. Headquartered in Irvine, CA.

Job Specification & Employment Details
This role is for an EOC Engineer internship converting to FTE.

Required Technical Skillset
Windows/Linux knowledge
Networking
TCP/IP
DNS
DHCP
IT troubleshooting

Work Location
Pune

Eligibility Criteria
Degree Requirement
B.E./B.Tech in Computer Science, Information Technology / EC, M.Sc. IT, MCA
Academic Performance
minimum aggregate 65%

Internship Details
Stipend
₹10,000 per month
Shift
7.30AM to 4.30PM OR 10.30PM to 7.30AM

Full-Time Employment Terms
Annual Compensation
₹3.5 lakhs per annum
Commitment Period
2-year service agreement
Bond Clause
₹2 lakh

Interview Selection Process
Be prepared to discuss yourself and why Synoptek.

Round 1
Aptitude Test and Group Discussion
"""


def _index_jd():
    doc = Document(doc_id="synoptek.pdf", content=JD_TEXT, metadata={"filename": "synoptek.pdf", "page": 1})
    chunks = HeadingAwareChunker().chunk_document(doc)
    retriever = BM25Retriever(chunks)
    return chunks, retriever


def _retrieve(query: str):
    _chunks, retriever = _index_jd()
    profile = classify_query_profile(query)
    rewritten = query
    if profile.preferred_sections:
        rewritten = query + " " + " ".join(profile.preferred_sections)
    hits = apply_section_boost(query, retriever.search(rewritten, top_k=5))
    return hits, profile


class TestFactoidRetrievalQuality(unittest.TestCase):
    def test_a_degrees_eligibility(self):
        hits, _ = _retrieve("What degrees are eligible?")
        blob = " ".join(c.text for c, _ in hits)
        self.assertIn("Degree Requirement", blob)
        self.assertRegex(blob, r"B\.E\./B\.Tech")
        self.assertIn("M.Sc. IT", blob)
        self.assertIn("MCA", blob)
        answer = extractive_answer("What degrees are eligible?", hits)
        self.assertRegex(answer, r"B\.E\.|B\.Tech|MCA")
        self.assertNotIn("why Synoptek", answer)

    def test_b_fte_compensation(self):
        hits, _ = _retrieve("What is the FTE compensation?")
        blob = " ".join(c.text for c, _ in hits)
        self.assertIn("Annual Compensation", blob)
        self.assertIn("₹3.5 lakhs per annum", blob)
        answer = extractive_answer("What is the FTE compensation?", hits)
        self.assertIn("3.5", answer)
        self.assertNotRegex(answer, r"7\.30AM")

    def test_c_technical_requirements(self):
        hits, _ = _retrieve("What are the technical requirements?")
        blob = " ".join(c.text for c, _ in hits)
        self.assertIn("Required Technical Skillset", blob)
        for term in ("Windows/Linux", "TCP/IP", "DNS", "DHCP", "IT troubleshooting"):
            self.assertIn(term, blob)
        answer = extractive_answer("What are the technical requirements?", hits)
        self.assertRegex(answer, r"Windows|Linux|TCP|DNS|DHCP")
        self.assertNotIn("converting to FTE", answer)

    def test_d_internship_stipend(self):
        hits, _ = _retrieve("What is the internship stipend?")
        blob = " ".join(c.text for c, _ in hits)
        self.assertIn("₹10,000 per month", blob)
        answer = extractive_answer("What is the internship stipend?", hits)
        self.assertIn("10,000", answer)

    def test_e_ceo_abstain(self):
        hits, _ = _retrieve("Who is the CEO?")
        answer = extractive_answer("Who is the CEO?", hits)
        self.assertIn("couldn't find", answer.lower())

    def test_f_headquarters(self):
        hits, _ = _retrieve("Where is the company headquartered?")
        blob = " ".join(c.text for c, _ in hits)
        self.assertIn("Irvine, CA", blob)
        answer = extractive_answer("Where is the company headquartered?", hits)
        self.assertIn("Irvine", answer)

    def test_compression_keeps_compensation_bullet(self):
        hits, _ = _retrieve("What is the FTE compensation?")
        compressed = DynamicContextFilter.compress_chunk_sentences(hits[0][0], "What is the FTE compensation?", max_sentences=3)
        self.assertIn("Annual Compensation", compressed)
        self.assertIn("3.5", compressed)

    def test_grounding_requires_answer_in_context(self):
        hits, _ = _retrieve("What is the FTE compensation?")
        ok, _ = validate_grounding("Annual Compensation: ₹3.5 lakhs per annum", hits)
        self.assertTrue(ok)
        fail, _ = validate_grounding("The CEO is Alice Example", hits)
        self.assertFalse(fail)

    def test_money_normalization(self):
        self.assertIn("50000", normalize_money_text("₹50 Thousand"))
        self.assertIn("50000", normalize_money_text("₹50,000"))
        self.assertIn("50000", normalize_money_text("INR 50,000"))
        self.assertNotEqual(normalize_money_text("₹50,000"), normalize_money_text("₹5,000"))
        self.assertIn("5000", normalize_money_text("₹5,000"))
        self.assertNotIn("50000", normalize_money_text("₹5,000"))


if __name__ == "__main__":
    unittest.main()

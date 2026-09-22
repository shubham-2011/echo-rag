import pytest
import io
import fitz
from src.ingestion import extract_text_from_bytes, DocumentIngestionPipeline
from fastapi.testclient import TestClient
from src.api.app import app

client = TestClient(app)


def test_pdf_text_extraction():
    """Verify clean text extraction from PDF without bytecode corruption."""
    doc = fitz.open()
    page = doc.new_page()
    sample_text = "Shubham Kumar is a Machine Learning Engineer specializing in EcoRAG and green AI."
    page.insert_text((50, 50), sample_text)
    pdf_bytes = doc.write()

    extracted = extract_text_from_bytes(pdf_bytes, "shubham_resume.pdf")
    assert "Shubham Kumar" in extracted
    assert "%PDF-" not in extracted.split("--- Page 1 ---")[1]


def test_txt_and_md_text_extraction():
    """Verify UTF-8 decoding for markdown and plain text."""
    txt_bytes = "EcoRAG optimization techniques.".encode("utf-8")
    extracted = extract_text_from_bytes(txt_bytes, "notes.txt")
    assert extracted == "EcoRAG optimization techniques."


def test_api_ingest_file_pdf():
    """Test POST /api/ingest/file with a real generated PDF."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Shubham Kumar built the EcoRAG platform using FAISS and FastAPI.")
    pdf_bytes = doc.write()

    files = {"file": ("test_shubham_resume.pdf", pdf_bytes, "application/pdf")}
    data = {
        "chunk_size": "100",
        "chunk_overlap": "20",
        "enable_dedup": "true",
        "strategy": "sentence_window"
    }

    resp = client.post("/api/ingest/file", files=files, data=data)
    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data["doc_id"] == "test_shubham_resume.pdf"
    assert res_data["unique_chunks_indexed"] >= 1

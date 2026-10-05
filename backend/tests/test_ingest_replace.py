import io

import fitz
from fastapi.testclient import TestClient

from src.api.app import app
from src.api.dependencies import app_state


def _pdf_bytes(text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), text)
    return doc.write()


def test_file_ingest_replaces_previous_document():
    client = TestClient(app)
    first = _pdf_bytes("AlphaCorp is headquartered in Oslo.")
    second = _pdf_bytes("BetaLabs makes industrial sensors in Pune.")

    r1 = client.post(
        "/api/ingest/file",
        files={"file": ("alpha.pdf", first, "application/pdf")},
        data={"strategy": "sentence_window", "replace_index": "true"},
    )
    assert r1.status_code == 200
    r2 = client.post(
        "/api/ingest/file",
        files={"file": ("beta.pdf", second, "application/pdf")},
        data={"strategy": "sentence_window", "replace_index": "true"},
    )
    assert r2.status_code == 200
    docs = {c.doc_id for c in app_state.chunks}
    assert docs == {"beta.pdf"}
    listed = client.get("/api/documents").json()
    assert [d["fileName"] for d in listed] == ["beta.pdf"]

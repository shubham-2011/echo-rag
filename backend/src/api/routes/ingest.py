import hashlib
import logging
import os

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from src.ingestion import Document
from src.api.schemas import IngestTextRequest, IngestResponse
from src.api.dependencies import app_state, security_gateway
from src.ingestion import DocumentIngestionPipeline
from src.security.config import SECURITY_CONFIG
from src.security.auth import ApiScope, AuthenticatedPrincipal, require_access
from src.security.parser import extract_text_with_limits

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ingest", tags=["Ingestion"])


@router.post("/text", response_model=IngestResponse)
def ingest_text(
    payload: IngestTextRequest,
    principal: AuthenticatedPrincipal = Depends(require_access(ApiScope.WRITE, "ingestion")),
):
    """
    Ingest raw text, apply configurable chunking and deduplication,
    compute embeddings, and update the FAISS vector store and BM25 index.
    """
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="Document text cannot be empty.")

    security_decision, document_security = security_gateway.inspect_document(
        payload.text,
        document_id=payload.doc_id,
        source="api_text",
        owner=principal.subject,
    )
    if not security_decision.allowed or document_security is None:
        raise HTTPException(status_code=400, detail=security_decision.reason)

    pipeline = DocumentIngestionPipeline(
        chunk_size=payload.chunk_size,
        chunk_overlap=payload.chunk_overlap,
        enable_dedup=payload.enable_dedup,
        strategy=payload.strategy
    )

    # Ingest with deduplication
    unique_chunks = pipeline.ingest_text(
        payload.text,
        doc_id=payload.doc_id,
        metadata={
            **document_security.model_dump(mode="json"),
            "parent_doc_id": _tenant_document_key(principal.subject, payload.doc_id),
        },
    )

    # Compute total produced chunks without dedup for stats
    raw_chunker = pipeline.chunker
    raw_chunks = raw_chunker.chunk_document(Document(doc_id=payload.doc_id, content=payload.text))
    dedup_count = len(raw_chunks) - len(unique_chunks)

    if unique_chunks:
        embeddings = app_state.embedder.embed_batch([c.text for c in unique_chunks])
        app_state.update_corpus(unique_chunks, embeddings)

    return IngestResponse(
        doc_id=payload.doc_id,
        total_chunks_produced=len(raw_chunks),
        unique_chunks_indexed=len(unique_chunks),
        deduplicated_count=dedup_count,
        total_vectors_in_store=app_state.get_tenant_vector_count(principal.subject)
    )


@router.post("/file", response_model=IngestResponse)
async def ingest_file_upload(
    file: UploadFile = File(...),
    principal: AuthenticatedPrincipal = Depends(require_access(ApiScope.WRITE, "ingestion")),
    chunk_size: int = Form(256),
    chunk_overlap: int = Form(30),
    enable_dedup: bool = Form(True),
    strategy: str = Form("sentence_window"),
    replace_index: bool = Form(True),
):
    """
    Ingest a binary or text document file (.pdf, .docx, .txt, .md),
    extract readable text, chunk, deduplicate, compute embeddings,
    and index into the FAISS vector database.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename missing.")

    content_bytes = await file.read(SECURITY_CONFIG.max_upload_bytes + 1)
    security_decision = security_gateway.inspect_upload(
        filename=file.filename,
        content=content_bytes,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        content_type=file.content_type,
    )
    if not security_decision.allowed:
        raise HTTPException(status_code=400, detail=security_decision.reason)

    extracted_text = await extract_text_with_limits(content_bytes, file.filename)
    if not extracted_text.strip():
        raise HTTPException(status_code=400, detail="Could not extract readable text from document.")
    security_decision, document_security = security_gateway.inspect_document(
        extracted_text,
        document_id=file.filename,
        source="file_upload",
        owner=principal.subject,
        raw_content=content_bytes,
    )
    if not security_decision.allowed or document_security is None:
        raise HTTPException(status_code=400, detail=security_decision.reason)

    doc_id = file.filename
    is_md = file.filename.lower().endswith(".md")

    pipeline = DocumentIngestionPipeline(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        enable_dedup=enable_dedup,
        strategy=strategy
    )

    ext = os.path.splitext(file.filename)[1].lstrip(".").lower()
    unique_chunks = pipeline.ingest_text(
        extracted_text,
        doc_id=doc_id,
        metadata={
            **document_security.model_dump(mode="json"),
            "filename": file.filename,
            "file_type": ext,
            "source": file.filename,
            "parent_doc_id": _tenant_document_key(principal.subject, doc_id),
        },
        is_markdown=is_md,
    )

    raw_chunks = pipeline.chunker.chunk_document(Document(doc_id=doc_id, content=extracted_text))
    dedup_count = len(raw_chunks) - len(unique_chunks)

    if unique_chunks:
        embeddings = app_state.embedder.embed_batch([c.text for c in unique_chunks])
        previous: list[str] = []
        if replace_index:
            previous = app_state.replace_tenant_corpus(
                principal.subject,
                unique_chunks,
                embeddings,
            )
        else:
            app_state.update_corpus(unique_chunks, embeddings)
        logger.info(
            "[INGEST] doc_id=%s replace_index=%s previous_docs=%s chunks=%s vectors=%s",
            doc_id,
            replace_index,
            ",".join(previous) or "none",
            len(unique_chunks),
            app_state.get_tenant_vector_count(principal.subject),
        )

    return IngestResponse(
        doc_id=doc_id,
        total_chunks_produced=len(raw_chunks),
        unique_chunks_indexed=len(unique_chunks),
        deduplicated_count=dedup_count,
        total_vectors_in_store=app_state.get_tenant_vector_count(principal.subject)
    )


def _tenant_document_key(owner: str, document_id: str) -> str:
    value = f"{owner}\0{document_id}".encode("utf-8")
    return f"tenant-document-{hashlib.sha256(value).hexdigest()}"

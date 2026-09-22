from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from src.ingestion import extract_text_from_bytes, Document
from src.api.schemas import IngestTextRequest, IngestResponse
from src.api.dependencies import app_state
from src.ingestion import DocumentIngestionPipeline

router = APIRouter(prefix="/api/ingest", tags=["Ingestion"])


@router.post("/text", response_model=IngestResponse)
def ingest_text(payload: IngestTextRequest):
    """
    Ingest raw text, apply configurable chunking and deduplication,
    compute embeddings, and update the FAISS vector store and BM25 index.
    """
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="Document text cannot be empty.")

    pipeline = DocumentIngestionPipeline(
        chunk_size=payload.chunk_size,
        chunk_overlap=payload.chunk_overlap,
        enable_dedup=payload.enable_dedup,
        strategy=payload.strategy
    )

    # Ingest with deduplication
    unique_chunks = pipeline.ingest_text(payload.text, doc_id=payload.doc_id)

    # Compute total produced chunks without dedup for stats
    raw_chunker = pipeline.chunker
    from src.ingestion import Document
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
        total_vectors_in_store=app_state.vector_store.total_vectors
    )


@router.post("/file", response_model=IngestResponse)
async def ingest_file_upload(
    file: UploadFile = File(...),
    chunk_size: int = Form(256),
    chunk_overlap: int = Form(30),
    enable_dedup: bool = Form(True),
    strategy: str = Form("sentence_window")
):
    """
    Ingest a binary or text document file (.pdf, .docx, .txt, .md),
    extract readable text, chunk, deduplicate, compute embeddings,
    and index into the FAISS vector database.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename missing.")

    content_bytes = await file.read()
    if not content_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    extracted_text = extract_text_from_bytes(content_bytes, file.filename)
    if not extracted_text.strip():
        raise HTTPException(status_code=400, detail="Could not extract readable text from document.")

    doc_id = file.filename
    is_md = file.filename.lower().endswith(".md")

    pipeline = DocumentIngestionPipeline(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        enable_dedup=enable_dedup,
        strategy=strategy
    )

    unique_chunks = pipeline.ingest_text(extracted_text, doc_id=doc_id, is_markdown=is_md)

    raw_chunks = pipeline.chunker.chunk_document(Document(doc_id=doc_id, content=extracted_text))
    dedup_count = len(raw_chunks) - len(unique_chunks)

    if unique_chunks:
        embeddings = app_state.embedder.embed_batch([c.text for c in unique_chunks])
        app_state.update_corpus(unique_chunks, embeddings)

    return IngestResponse(
        doc_id=doc_id,
        total_chunks_produced=len(raw_chunks),
        unique_chunks_indexed=len(unique_chunks),
        deduplicated_count=dedup_count,
        total_vectors_in_store=app_state.vector_store.total_vectors
    )

# Technical Audit: EcoRAG Backend Project (`d:\Program\Python\Echo Rag`)

> **Audited Target**: `d:\Program\Python\Echo Rag`  
> **Audited By**: Antigravity Architect  
> **Backend Framework**: Python 3.14 + FastAPI + FAISS + PyTorch / HuggingFace SentenceTransformers  
> **Test Suite Status**: **31 passed (100%)** in `tests/` (API, retrieval, and benchmark tests)  
> **Target Consumer**: EcoRAG Windows Desktop Application (`d:\Program\C#\ECORAG desktop application`)

---

## 1. Executive Summary & Verification

The backend repository at `d:\Program\Python\Echo Rag` is a verified, fully-functional **Energy-Efficient Retrieval-Augmented Generation (EcoRAG)** research and production platform.

All **31 automated test cases** were executed and passed cleanly:
- `tests/test_api.py` (17 tests): Health, text ingestion, deduplication, sparse BM25, dense FAISS, hybrid RRF, adaptive query, and parameter boundary validations.
- `tests/test_experiments.py` (3 tests): QA dataset loading, Pareto frontier calculation, and experiment manager.
- `tests/test_retrieval_overhaul.py` (11 tests): Markdown hierarchy chunker, query classification (simple/normal/complex), L1/L2 semantic caching, and dynamic sentence compression.

---

## 2. API Endpoint Inventory & Contracts

The FastAPI application is mounted in `src/api/app.py` with the following active endpoints:

| Method | Endpoint | Purpose | Request Payload | Response Model |
|---|---|---|---|---|
| `GET` | `/` | API Welcome & links | None | `{ "message", "docs_url", "health_url" }` |
| `GET` | `/api/health` | System health & telemetry | None | `HealthResponse` |
| `POST` | `/api/ingest/text` | Ingest raw text & deduplicate | `IngestTextRequest` | `IngestResponse` |
| `POST` | `/api/search` | Multi-mode candidate search | `SearchRequest` | `SearchResponse` |
| `POST` | `/api/query` | End-to-end adaptive RAG query | `QueryRequest` | `QueryResponse` |

### Detailed Endpoint Specifications

#### 1. `GET /api/health`
Returns active vector counts, embedding dimension, provider, and reranker bypass statistics:
```json
{
  "status": "healthy",
  "total_indexed_chunks": 420,
  "active_embedding_dimension": 384,
  "embedding_provider": "sentence-transformers",
  "reranker_model": "BAAI/bge-reranker-large",
  "reranker_bypass_rate": 42.5
}
```

#### 2. `POST /api/ingest/text`
Accepts text content with configurable chunking and deduplication:
```json
{
  "text": "Full document text string...",
  "doc_id": "research_doc_01",
  "chunk_size": 50,
  "chunk_overlap": 10,
  "enable_dedup": true
}
```
**Response**:
```json
{
  "doc_id": "research_doc_01",
  "total_chunks_produced": 45,
  "unique_chunks_indexed": 38,
  "deduplicated_count": 7,
  "total_vectors_in_store": 458
}
```

#### 3. `POST /api/search`
Retrieves candidate chunks using one of four modes: `"adaptive"`, `"hybrid"`, `"dense"`, or `"sparse"`:
```json
{
  "query": "What are the primary sources of energy waste in RAG?",
  "mode": "adaptive",
  "top_k": 5,
  "enable_rerank": true
}
```

#### 4. `POST /api/query`
The primary inference endpoint used by the desktop app. Runs query classification, cache check, retrieval, sentence-level context compression, and generation (via Gemini 2.5 Flash with fallback extractive synthesis):
```json
{
  "query": "Explain how EcoRAG reduces token generation overhead.",
  "retrieval_mode": "adaptive",
  "top_k": 3,
  "max_tokens": 200
}
```
**Response**:
```json
{
  "query": "Explain how EcoRAG reduces token generation overhead.",
  "answer": "EcoRAG minimizes token generation overhead by applying sentence-level context compression...",
  "citations": [
    {
      "chunk_id": "doc1_c12_a3f8",
      "doc_id": "doc1",
      "text": "Sentence extracted from relevant chunk...",
      "score": 0.9412,
      "rank": 1
    }
  ],
  "telemetry": {
    "latency_ms": 412.5,
    "peak_ram_mb": 312.4,
    "estimated_wh": 0.0051,
    "rerank_bypassed": false,
    "eco_score": 8.45,
    "cache_tier": "MISS",
    "complexity": "NORMAL"
  }
}
```

---

## 3. Core Architectural Modules in `src/`

### A. Document Ingestion & Deduplication (`src/ingestion.py`)
- **`TextChunker`**: Token-approximated sliding window chunker.
- **`MarkdownHierarchyChunker`**: Preserves header hierarchies (`#`, `##`, `###`) and breadcrumbs (`# Arch > ## Ingestion`).
- **`Deduplicator`**: Jaccard / MinHash similarity detection preventing redundant embeddings from consuming vector space.

### B. Vector Store (`src/vector_store.py`)
- Uses **FAISS `IndexFlatIP`** with normalized L2 embeddings for exact inner-product cosine similarity search.
- Thread-safe serialization (`save_index`, `load_index`).

### C. Embeddings (`src/embeddings.py`)
- Supports local HuggingFace models (`sentence-transformers/all-MiniLM-L6-v2`, `BAAI/bge-small-en-v1.5`) and cloud Google Gemini Embeddings.

### D. Reranking (`src/reranker.py`)
- **Threshold-Gated Cross-Encoder**: If the gap between top candidate scores exceeds a threshold, the reranker **bypasses computation** to save inference FLOPs.

### E. Adaptive Retrieval & Caching (`src/retrieval.py`)
- **Query Complexity Classifier**: Simple queries bypass reranking; complex queries activate hybrid search.
- **Two-Tier Caching**:
  - **L1 Cache**: Exact query match.
  - **L2 Semantic Cache**: Vector cosine match on previous queries (`similarity > 0.96`). Hits yield an **80% energy discount**.
- **Dynamic Context Compression**: Uses sentence similarity to filter out non-essential sentences before LLM prompt assembly.

---

## 4. Integration Alignment with the Desktop Application

### Current Alignment Status:

| Dimension | Backend Implementation | Desktop Client Implementation | Status / Action Needed |
|---|---|---|---|
| **Health Check** | `GET /api/health` | Was checking `GET /health` | **Action**: Update Desktop client URL to `/api/health`. |
| **RAG Query** | `POST /api/query` | Structured `QueryRequest` | **Aligned**: Map C# DTOs to `QueryResponse.telemetry`. |
| **Telemetry** | `estimated_wh`, `latency_ms`, `eco_score`, `cache_tier` | Display in `EnergyTelemetry` pill | **Aligned**: Convert `estimated_wh` to Joules (`Wh * 3600`). |
| **Citations** | `SearchHit` with `chunk_id`, `text`, `score` | Expandable citation badges in `ChatView` | **Aligned**: Render directly in UI. |
| **File Upload** | Accepts raw text (`POST /api/ingest/text`) | Desktop uploads `.pdf`, `.docx` | **Enhancement**: Add multipart upload or local text extractor. |

---

## 5. Recommended Backend Enhancements for Desktop Clients

1. **Add Multipart File Ingestion Route**:
   Add `POST /api/ingest/file` in `src/api/routes/ingest.py` accepting `UploadFile` (using `pypdf` / `python-docx`) so desktop users can upload binary files directly without client-side text pre-extraction.
2. **Add SSE Token Streaming**:
   Create `GET /api/query/stream` using FastAPI `StreamingResponse` for true token-by-token generation in the desktop chat interface.
3. **Running the Backend Server**:
   To start the backend for desktop client access:
   ```bash
   uvicorn src.api.app:app --host 127.0.0.1 --port 8000 --reload
   ```

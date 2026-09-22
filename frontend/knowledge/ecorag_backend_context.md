# EcoRAG Backend Context & Client Integration

This document outlines the **EcoRAG Backend API**, energy telemetry model, and data structures that the **EcoRAG Desktop Application** interfaces with.

---

## 1. Backend Core Overview

- **Framework**: Python FastAPI
- **Vector Search Engine**: FAISS (Facebook AI Similarity Search)
- **Reranker Model**: BGE Reranker (`BAAI/bge-reranker-large` / `base`)
- **Embedding Models**: HuggingFace Sentence Transformers (e.g., `all-MiniLM-L6-v2` or `bge-small-en-v1.5`)
- **Primary Innovation**: **Energy-Efficient RAG (EcoRAG)**
  - Dynamic telemetry tracking compute energy consumption (Joules / Watt-hours).
  - Energy-aware retrieval strategies: Dynamic chunk selection, embedding deduplication, tiered retrieval, and threshold-based reranking.

---

## 2. Telemetry Model (`@measure_energy`)

The backend tracks execution energy per query and ingestion task using hardware counters or proxy formulas:

```json
{
  "query_id": "q_8f93a1c2",
  "prompt_tokens": 128,
  "completion_tokens": 254,
  "total_tokens": 382,
  "retrieval_latency_ms": 42.5,
  "rerank_latency_ms": 118.2,
  "llm_latency_ms": 850.1,
  "total_latency_ms": 1010.8,
  "energy_joules": 142.35,
  "energy_kwh": 0.0000395,
  "energy_saved_percentage": 34.2,
  "baseline_comparison": {
    "standard_rag_joules": 216.4,
    "ecorag_joules": 142.35,
    "difference_joules": 74.05
  }
}
```

### Desktop Display Requirement:
The WinUI 3 Desktop client must render an **Energy Badge / Telemetry Pill** on each chat message and provide dedicated analytics dashboards plotting:
1. **Joules per Query** over time.
2. **Standard RAG vs. EcoRAG Energy Savings (%)**.
3. **Retrieval Latency Breakdown**: Search vs. Rerank vs. LLM Generation.

---

## 3. Anticipated API Endpoints for Desktop Client

### A. System & Health
- `GET /health` or `GET /api/v1/health`
  - Returns backend health status, active GPU/CPU, and vector store stats.

### B. Ingestion & Documents
- `POST /api/v1/documents/upload` (Multipart Form)
  - Accepts PDF, DOCX, TXT, MD files.
  - Returns `document_id` and initial processing job ID.
- `GET /api/v1/documents`
  - Returns paginated list of ingested documents, chunk counts, and indexing timestamps.
- `GET /api/v1/documents/{id}/chunks`
  - Allows desktop users to inspect chunking strategies and preview extracted text.
- `DELETE /api/v1/documents/{id}`
  - Removes document from relational metadata and purges vector index entries.

### C. RAG Query & Chat
- `POST /api/v1/rag/query` (Standard HTTP REST)
  - JSON payload with query string, top_k, rerank enable/disable flag.
  - Returns generated answer, citations array, and energy telemetry.
- `POST /api/v1/rag/stream` (Server-Sent Events / SSE)
  - Streams response tokens in real-time.
  - Emits final metadata packet containing citations and energy summary.

### D. Benchmarking & Analytics
- `GET /api/v1/benchmarks/summary`
  - Aggregated historical metrics: Total queries, total Joules consumed, total Joules saved.
- `POST /api/v1/benchmarks/run-comparison`
  - Executes test prompt across both Standard RAG and Eco-optimized RAG to generate side-by-side benchmark data.

---

## 4. Desktop Client Contract Best Practices

1. **Keep Secrets Out of Client**: LLM API keys (OpenAI, Anthropic, HuggingFace) and database passwords are kept exclusively on the FastAPI server. The desktop client only sends user requests and receives processed answers.
2. **Resilience & Polling**: Document ingestion should be monitored via job ID polling or WebSocket to prevent UI freezes on large PDF uploads.
3. **Local Caching**: The desktop client should cache query history and document lists locally using SQLite to enable rapid navigation even during backend latency spikes.

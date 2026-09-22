# EcoRAG Backend Service

High-performance, energy-efficient Retrieval-Augmented Generation (RAG) backend API engine built with **FastAPI**, **FAISS**, **BM25+**, and **Sentence-Transformers**.

---

## 🌟 Key Features

- ⚡ **Adaptive Multi-Stage Retrieval**: Dynamically routes queries between exact cache, semantic cache, BM25 keyword search, dense vector retrieval, and RRF hybrid search based on query classification.
- 🎯 **Green-Computing Conditional Reranker**: Threshold-gated Cross-Encoder reranker (`cross-encoder/ms-marco-MiniLM-L-6-v2`) that bypasses compute when confidence margins are clear (achieving up to 70%+ energy savings).
- 🧩 **Smart Ingestion Pipeline**: Ingestion for PDF, DOCX, Markdown, Text, and CSV with SHA-256 chunk deduplication, hierarchical parent document storage, and sentence-window expansion.
- 🐳 **Docker-Ready**: Optimized container build with CPU-specialized PyTorch, pre-cached embedding weights, and sub-second healthcheck probes.
- 📊 **Comprehensive Telemetry**: Granular token accounting, TTFT latency tracking, and Eco Score computation on every query.

---

## 🚀 Quick Start

### Running with Docker
```bash
docker build -t ecorag-backend .
docker run -p 8000:8000 --env-file .env ecorag-backend
```

### Running Locally with Python
```bash
# 1. Create and activate virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start development server
uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload
```

Interactive API documentation will be available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Healthcheck: `http://localhost:8000/api/health`

---

## 🧪 Running Tests & Benchmarks
```bash
# Run complete test suite (39 tests)
python -m pytest

# Run Chunk Attention quadratic compute benchmark
python src/benchmarks/chunk_attention_benchmark.py
```

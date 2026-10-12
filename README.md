# EcoRAG: Energy-Efficient Retrieval-Augmented Generation Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![.NET 10.0](https://img.shields.io/badge/.NET-10.0%20%2F%20WPF-purple.svg)](https://dotnet.microsoft.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)

**EcoRAG** is a systems-level experimental research platform and production architecture designed to minimize computational, latency, and energy overhead in Retrieval-Augmented Generation (RAG).

While standard RAG implementations indiscriminately retrieve large document chunks and pump thousands of tokens into large language models (resulting in quadratic prefill self-attention compute, high latency, and high energy consumption), **EcoRAG frames RAG as an adaptive multi-objective optimization problem**: minimizing Watt-hours, latency, and token waste while strictly maintaining retrieval accuracy and answer correctness.

---

## 🏛️ Architecture Overview

```
                          ┌──────────────────────────┐
                          │   User Query / Request   │
                          └─────────────┬────────────┘
                                        │
                                        ▼
                          ┌──────────────────────────┐
                          │     Query Classifier     │
                          │ (Keyword, Semantic, etc) │
                          └───────┬──────────┬───────┘
                                  │          │
                     Exact/Cached │          │ Cache Miss
                                  ▼          ▼
                        ┌───────────┐  ┌──────────────────────────┐
                        │ Fast Path │  │    Adaptive Retrieval    │
                        │  (0 Wh)   │  │ (Dense + BM25 Lexical)   │
                        └───────────┘  └─────────────┬────────────┘
                                                     │
                                                     ▼
                                       ┌──────────────────────────┐
                                       │   Reciprocal Rank Fusion │
                                       │       (RRF k=60)         │
                                       └─────────────┬────────────┘
                                                     │
                                                     ▼
                                       ┌──────────────────────────┐
                                       │ Conditional Reranker     │
                                       │ (Bypasses Cross-Encoder  │
                                       │  when margin > threshold)│
                                       └─────────────┬────────────┘
                                                     │
                                                     ▼
                                       ┌──────────────────────────┐
                                       │ Dynamic Context Filter   │
                                       │ (Strips irrelevant tokens│
                                       └─────────────┬────────────┘
                                                     │
                                                     ▼
                                       ┌──────────────────────────┐
                                       │ LLM Generation / Stream  │
                                       └──────────────────────────┘
```

The repository is organized as a clean, unified monorepo:

- **`backend/`**: FastAPI backend service containerized with Docker.
  - **Adaptive Retrieval**: Dense (FAISS bi-encoder with `all-MiniLM-L6-v2` or Google Gemini) + Lexical (BM25+) fused with Reciprocal Rank Fusion (RRF).
  - **Conditional Reranking**: Threshold-gated reranker (`cross-encoder/ms-marco-MiniLM-L-6-v2`) that bypasses compute when confidence margins are clear (saving up to 70%+ reranking energy).
  - **Multi-Tier Caching**: In-memory Exact Hash cache & FAISS Semantic vector cache.
  - **Dynamic Context Sizing**: Slices context tokens based on relevance thresholds rather than fixed K.
  - **Telemetry Engine**: Real-time energy estimations (Joules), RAM tracking, TTFT, and Eco Score computation.
- **`frontend/`**: Modern Windows desktop frontend built with **C# (.NET 10 / WPF)** following the **MVVM** pattern.
  - **Dashboard**: Live system health, active embedding model, and reranker bypass telemetry.
  - **Documents Manager**: Drag-and-drop file ingestion supporting PDF, DOCX, Markdown, CSV, and Text.
  - **Interactive Chat**: Streaming chat interface with citations and per-query energy footprint meters.
  - **Telemetry View**: Real-time energy metrics, latency breakdowns, and caching efficiency gauges.
- **`docs/`**: Comprehensive research findings, academic benchmarks, and system specifications.

---

## 🚀 Quick Start Guide

### 1. Run the Backend with Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/shubham-2011/echo-rag.git
cd echo-rag

# Start the backend via Docker Compose
docker-compose up --build -d
```

The backend will start and become available at:
- API Base: `http://localhost:8000`
- Swagger UI Documentation: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/api/health`

### 2. Run the Backend Locally (Python 3.11+)

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate

pip install -r requirements.txt
uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Launch the Desktop Frontend (WPF / .NET 10)

```powershell
cd frontend/src/EcoRag.Desktop
dotnet run
```
Or simply run `frontend/Run-EcoRag-Desktop.bat`.

---

## 🧪 Testing & Evaluation

Run the automated backend test suite (39 tests):
```bash
cd backend
python -m pytest
```

Run the quadratic attention benchmark:
```bash
python backend/src/benchmarks/chunk_attention_benchmark.py
```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

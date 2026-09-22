# EcoRAG: Energy-Efficient Retrieval-Augmented Generation Platform

EcoRAG is a systems-level experimental research platform and production architecture designed to minimize computational and energy overhead in Retrieval-Augmented Generation (RAG). 

While standard RAG implementations blindly retrieve large contexts and pump thousands of tokens into large language models (resulting in high (N^2)$ prefill compute, high latency, and high financial cost), **EcoRAG frames RAG as an adaptive multi-objective optimization problem**: minimizing Joules, latency, and token waste while preserving retrieval accuracy and answer correctness.

---

## Architecture Overview

EcoRAG is composed of two primary modules within this monorepo:

1. **ackend/**: High-efficiency FastAPI service containerized with Docker, featuring:
   - **Hybrid Retrieval**: Dense (FAISS bi-encoder with ll-MiniLM-L6-v2 / ge-small-en-v1.5) + Lexical (BM25) fused with Reciprocal Rank Fusion (RRF).
   - **Conditional Reranking**: Threshold-gated reranker that bypasses cross-encoder forward passes when confidence margins are clear (saving up to 80% reranking energy).
   - **Hierarchical Caching**: Exact hash caching and vector semantic query caching.
   - **Dynamic Context Sizing**: Slices context window dynamically based on relevance thresholds.
   - **Real-Time Telemetry**: Tracks CPU energy estimations (Joules), RAM usage, TTFT, and token usage per query.

2. **desktop/**: Modern C# .NET WPF Desktop Application featuring:
   - **Dashboard**: Live system health, active embedding model, vector dimensions, and reranker bypass statistics.
   - **Documents**: Document ingestion manager supporting PDF, DOCX, and text file uploads.
   - **Chat**: Streaming interactive chat interface with citations and per-turn energy footprint metrics.
   - **Telemetry**: Real-time energy telemetry, query latency breakdowns, and caching efficiency meters.

---

## Quickstart Guide

### Option A: Run Backend with Docker (Recommended)

1. Navigate to the repository root:
   `ash
   cd EcoRAG
   `

2. Copy the environment configuration:
   `ash
   cp backend/.env.example backend/.env
   # Edit backend/.env if using Google Gemini API key
   `

3. Build and launch the containerized backend:
   `ash
   docker compose up --build -d
   `

4. Verify health at http://localhost:8000/api/health or view Swagger API docs at http://localhost:8000/docs.

---

### Option B: Run Backend Locally (Python)

1. Navigate to the backend directory:
   `ash
   cd backend
   `

2. Install dependencies:
   `ash
   pip install -r requirements.txt
   `

3. Start the FastAPI server:
   `ash
   uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload
   `

---

### Launch Desktop Frontend (C# .NET)

1. Navigate to desktop/:
   `ash
   cd desktop
   `

2. Build and run via .NET CLI:
   `ash
   dotnet run --project src/EcoRag.Desktop/EcoRag.Desktop.csproj
   `

   *Or simply double-click Run-EcoRag-Desktop.bat.*

---

## Monorepo Layout

`
EcoRAG/
+-- backend/                       # Python EcoRAG FastAPI Backend
¦   +-- src/                       # API routes, retrieval, embeddings, vector store
¦   +-- tests/                     # Automated pytest suites
¦   +-- benchmarks/                # Energy and attention benchmarks
¦   +-- data/                      # Sample documents & vector indices
¦   +-- Dockerfile                 # Container definition with pre-cached weights
¦   +-- docker-compose.yml         # Backend docker compose configuration
¦   +-- requirements.txt           # CPU-optimized Python dependencies
+-- desktop/                       # C# .NET WPF Desktop Client
¦   +-- src/EcoRag.Desktop/        # MVVM Views, ViewModels, Services, Models
¦   +-- Run-EcoRag-Desktop.bat     # Windows desktop launcher
¦   +-- EcoRag.Desktop.csproj      # .NET 10.0 WPF project
+-- docker-compose.yml             # Monorepo compose file
+-- .gitignore                     # Unified ignore rules
+-- README.md                      # Documentation & architecture
`

## License
MIT License

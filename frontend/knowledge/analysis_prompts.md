# Master Analysis & Architecture Prompts

This document contains the complete collection of prompts designed during the architectural audit of the **EcoRAG Desktop Application**. Use these prompts with AI coding and reasoning models (Antigravity, Claude 3.7 Sonnet, Gemini 2.0/3.0, ChatGPT o3) to audit technical decisions, backend contracts, and software design before coding.

---

## Prompt 1: Complete Desktop Technology & Architecture Audit (20 Phases)

```markdown
# Desktop Application — Complete Technology, Architecture & Feature Audit

Act as a **Senior Software Architect, Desktop Application Architect, UI/UX Architect, Security Engineer, DevOps Engineer, Database Architect, API Architect, and Technical Product Manager**.

I am planning to build a **professional production-grade desktop application**.

Before writing any application code, perform a complete technical audit and recommend the most suitable technology stack and architecture.

Do not blindly recommend a technology based on popularity. Evaluate the requirements, constraints, maintainability, security, performance, UI/UX, API integration, deployment, and future scalability.

---

### Phase 1 — Application Profile & Requirements Discovery
Identify:
- Target operating systems (Windows 10/11, macOS, Linux)
- Target users and deployment scale
- Connectivity model: Online-only, Offline-capable, or Hybrid
- Authentication and Role-Based Access Control (RBAC) needs
- Backend communication needs (REST, WebSocket, gRPC, SSE)
- Local storage and filesystem interaction
- Hardware acceleration and native OS integrations (notifications, credential vault)
- Automatic update and distribution requirements

### Phase 2 — Multi-Technology Matrix Comparison
Compare candidate technologies:
- C# + WinUI 3 (Windows App SDK)
- C# + WPF
- Tauri + React / TypeScript
- Electron + React
- .NET MAUI / Flutter Desktop
- Qt + C++ / Qt + Python

Evaluate across:
1. UI quality & Modern design system support (Fluent, dark/light mode, mica)
2. Performance: Startup time, memory footprint (RAM), CPU idle vs load
3. Security: Token storage, IPC isolation, binary attack surface
4. API Integration: HTTP/2, streaming responses, connection pooling
5. Installer & Packaging: MSIX, EXE, code signing, automatic updates
6. Developer ergonomics & long-term maintainability

### Phase 3 — UI/UX Component & Design System Audit
Audit component requirements:
- Navigation Shell (NavigationView, tabs, breadcrumbs)
- Responsive layout across standard desktop resolutions and DPI scaling
- Data grids, virtualized lists, and search filters
- Asynchronous loading states: Skeleton loaders, progress rings, error banners
- Dialogs, context menus, tooltips, and toast notifications
- Keyboard accessibility and shortcut mapping

### Phase 4 — Client-Server Boundary & API Contract
Establish strict boundaries:
- Treat desktop client as an UNTRUSTED consumer
- Inventory all REST/SSE/WebSocket endpoints
- Define request/response validation (OpenAPI/DTOs)
- Error schema, retry policies, and timeout handling
- Token refresh lifecycle and session revocation

### Phase 5 — Security Threat Modeling
- Secure credential storage (Windows Credential Manager / DPAPI)
- Local file validation (mime-type checking, path traversal guards)
- Prevention of sensitive secrets (API keys, DB credentials) leaking into client binaries

### Phase 6 — Deliverables
Produce:
1. Executive Technology Recommendation with explicit trade-offs.
2. High-Level Component & Layered Architecture Diagram.
3. API Contract & Integration Strategy.
4. Pre-Development Risk Matrix.
```

---

## Prompt 2: Existing Project & Backend Conversation Audit

```markdown
# Existing Project & Backend Architecture Audit

Act as a:
- Senior Software Architect
- Desktop Application Architect
- API & Backend Architect
- Security & Performance Engineer

I am providing you with the complete previous project discussion, documentation, and API specifications.

Your job is to deeply analyze the ENTIRE provided conversation and extract the actual requirements, decisions, APIs, features, workflows, UI expectations, backend architecture, data flow, and technical constraints.

DO NOT immediately start coding.
First perform a complete architecture and desktop-application audit.

==================================================
PHASE 1 — UNDERSTAND THE EXISTING SYSTEM
==================================================
Extract:
1. Project purpose & Core problem solved
2. Existing backend framework & programming language
3. Confirmed APIs and endpoints
4. Authentication & Authorization mechanisms
5. Document processing & RAG pipeline (chunking, embeddings, vector DB, reranking)
6. Real-time telemetry, energy measurement, and benchmarking requirements
7. Existing test cases and known limitations
8. Unresolved assumptions or missing requirements

==================================================
PHASE 2 — API INVENTORY & CLIENT CONTRACT
==================================================
For every endpoint identify:
- METHOD & PATH
- PURPOSE
- AUTHENTICATION REQUIRED
- REQUEST PAYLOAD SCHEMA
- RESPONSE SCHEMA & STATUS CODES
- ERROR CODES & RECOVERY ACTIONS
- DESKTOP CLIENT USAGE (Screen / Feature)

==================================================
PHASE 3 — DESKTOP INTEGRATION SPECIFICATION
==================================================
Determine:
- How the desktop client handles file uploads and status tracking
- How streaming LLM responses and real-time energy telemetry are consumed
- What data belongs in local desktop cache vs backend database
- Offline fallback behavior
```

---

## Prompt 3: The 37-Point Master Software Design Audit Blueprint

```markdown
# Complete 37-Point Master Software Design Blueprint

Perform a comprehensive software design audit across all 37 foundational engineering dimensions before writing production code:

1. Product Design (Problem statement, target personas, MVP scope)
2. Requirements Classification (Functional, non-functional, operational)
3. Use-Case Workflows (Actor -> Action -> System -> Persistence -> Output)
4. System Architecture (Monolith vs. Modular vs. Client-Server)
5. Component Architecture (UI, Navigation, State, API Client, Storage)
6. Data Flow Architecture (Step-by-step trace for every key action)
7. Desktop Layer Architecture (MVVM, Views, ViewModels, Application Services)
8. UI/UX Global Layout (Shell, Sidebar, Main Content, Status bar)
9. Design System Tokens (Color palettes, Typography, Spacing, Controls)
10. API Specification (REST, SSE, WebSockets)
11. API Contract-First Mindset (OpenAPI DTO schemas)
12. Authentication Architecture (JWT, Refresh tokens, Lockouts)
13. Authorization Architecture (RBAC, Backend validation)
14. Database Design (PostgreSQL / SQLite schema)
15. Data Ownership Boundary (Local client vs. Server data)
16. RAG Pipeline Architecture (Ingestion, Chunking, Embedding, Vector DB, Reranker, LLM)
17. Asynchronous Job Processing (Background workers, task status)
18. Real-Time Streaming Architecture (SSE / WebSocket progress updates)
19. Unified Error Handling Architecture (Error codes, user messages, log IDs)
20. Security Threat Model (OWASP Desktop & API threat vectors)
21. Performance & Latency Measurement (Startup, RAM, FPS, RAG breakdown)
22. Caching Strategy (Local UI preferences, temporary caches)
23. Offline & Sync Architecture (Conflict resolution, offline queues)
24. File Handling & Ingestion Safety (Size limits, mime check, hashing)
25. Three-Tier Observability (Client telemetry, API logs, RAG/LLM metrics)
26. Multi-Level Testing Architecture (Unit, Integration, E2E, UI, Benchmarks)
27. Build & Release Pipeline (CI/CD, code signing, packaging)
28. Automatic Update Architecture (Manifest checking, rollback capability)
29. Configuration Management (Public configs vs. Secrets)
30. Scalability & Graceful Degradation (Concurrency limits, rate limits)
31. Reliability & Fault Tolerance (Retry mechanisms, circuit breakers)
32. Backup & Disaster Recovery (Database restore, RTO/RPO)
33. Licensing & Compliance (Third-party SDK and open-source licenses)
34. Continuous Integration Pipeline (PR linting, automated test gates)
35. Living Documentation Structure (/docs architecture, ADRs)
36. Architecture Decision Records (ADRs for framework, auth, storage, RAG)
37. Implementation Roadmap & Milestones (Phase 1 MVP through Production)
```

---

## Prompt 4: EcoRAG Research, Benchmarking, QA Test Suite & Implementation Master Prompt

```markdown
# EcoRAG: Research, Benchmarking, Comprehensive QA Testing & Implementation Blueprint

Act as a **Senior AI/ML Systems Researcher, Principal RAG Architect, Performance Engineering Lead, and Senior Software QA Automation Engineer**.

I am researching, benchmarking, and developing **EcoRAG**, an Energy-Efficient Retrieval-Augmented Generation platform consisting of:
1. **Python Backend**: FastAPI + FAISS Vector Store + HuggingFace SentenceTransformers (local `all-MiniLM-L6-v2`, 384d) + Cloud Gemini (`gemini-embedding-001`, 3072d) + BGE Reranker + Sentence-Window Expansion + Dynamic Context Compression + Physical Energy Telemetry.
2. **Desktop Client**: C# .NET 10 WPF Application (Fluent Dark UI, MVVM, WPF-UI, live streaming chat, source citations, hardware energy telemetry badge).

Your mission is to perform a rigorous scientific research analysis, construct comprehensive automated test cases across 5 RAG quality categories, evaluate hardware and algorithmic energy trade-offs, and guide production implementation.

---

### Phase 1: Algorithmic & Scientific Energy Research

1. **Quadratic Self-Attention ($\mathcal{O}(N^2)$) vs. Chunk Size vs. Context Tokens**:
   - Analyze the mathematical distinction between chunk size (indexing parameter) and prompt context tokens (causal driver of LLM prefill energy).
   - Evaluate the theoretical attention score component ratio:
     $$\text{Attention Work Ratio} = \left(\frac{N_{\text{context}}}{1024}\right)^2$$
   - Explain why reducing chunk size from 1024 to 256 reduces attention work by 93.75% *only* if Top-K is kept constant, and how compensating Top-K ($K=5 \to 20$) negates this gain.
   - Establish the full experimental chain:
     $$\text{Chunk Size} \to \text{Number of Chunks} \to \text{Index Size} \to \text{Recall@K} \to \text{Retrieved Tokens} \to \text{Prompt Tokens} \to \text{LLM Energy} \to \text{Answer Correctness}$$

2. **Semantic Fragmentation & Context Expansion Strategies**:
   - Analyze empirical fragmentation risks at 128 and 256 tokens (loss of coreferences, demonstrative pronouns like "This threshold...").
   - Compare three architectural mitigations:
     a. **Parent-Document Retrieval** (small vector chunks mapping to full parent docs).
     b. **Sentence-Window Expansion** ($\pm W$ sentences around retrieved matches where $W \in \{1, 2, 3\}$).
     c. **Dynamic Sentence Compression** (filtering low-importance sentences before LLM prefill).

3. **Multi-Model Embedding & Vector Distance Trade-Offs**:
   - Compare Cloud Gemini (3072d, 117.19 MiB / 10k vectors) vs. Local MiniLM (384d, 14.65 MiB / 10k vectors, 8x smaller).
   - Evaluate distance arithmetic operations $\mathcal{O}(N_{\text{chunks}} \times D)$. Under what vector count ($10\text{k}, 100\text{k}, 1\text{M}$) does vector search energy become measurable relative to LLM prefill?
   - Formulate the Cloud vs. Local energy boundary:
     $$E_{\text{Gemini}} = E_{\text{client HTTP}} + E_{\text{network transit}} + E_{\text{cloud datacenter compute}}$$
     $$E_{\text{MiniLM}} = E_{\text{local CPU/GPU compute}}$$

4. **Deduplication Net Energy Equation**:
   - Formulate and benchmark:
     $$\text{NetEnergySaved} = E_{\text{downstream saved (search + rerank + LLM)}} - E_{\text{deduplication overhead (hash/shingle)}}$$
   - Compare exact SHA-256 vs. 3-gram Jaccard Shingling vs. SimHash vs. MinHash LSH.

---

### Phase 2: Complete QA Test Suite (5 RAG Quality Categories + Non-Functional)

Construct concrete test cases with explicit inputs, expected outputs, status criteria, and assertions:

1. **Type A — Direct Single-Chunk Factoid**:
   - Query answer exists verbatim within a single 256-token chunk.
   - Assert: Recall@1 = 100%, exact numerical/factual entity in answer.

2. **Type B — Cross-Chunk Sentence-Window Coherence**:
   - Query requires connecting two consecutive sentences separated by a chunk boundary.
   - Assert: Sentence-Window Expansion ($W=2$) captures both sentences, resolves coreferent pronouns without hallucination.

3. **Type C — Multi-Hop Cross-Document Synthesis**:
   - Query requires combining facts across two distinct documents (e.g., compute scaling + database replication).
   - Assert: Retrieved citations contain both documents; synthesis accurately correlates them.

4. **Type D — Out-of-Domain Abstention**:
   - Query on topic completely absent from the indexed corpus.
   - Assert: Similarity scores < 0.60; system abstains cleanly ("The provided context does not contain...") without hallucinating facts.

5. **Type E — Adversarial Distractor Filtering**:
   - Corpus contains a distractor document with fake/deprecated parameters (e.g., 10% threshold vs. 70% production threshold).
   - Assert: Production context ranks higher; reranker suppresses distractor; LLM outputs valid production value.

6. **Document Parser & Bytecode Resilience**:
   - Ingest valid PDF, multi-page PDF, PDF with tables, DOCX, Markdown, plain text, empty file, corrupted binary.
   - Assert: Page text extracted cleanly; zero `%PDF-` bytecode in vector store chunks.

7. **Boundary & Concurrency Stress Testing**:
   - Boundaries: $K=0, K=1, K=50, K=100$, empty query, whitespace query, 5,000-word query.
   - Concurrency: 10, 50, 100 simultaneous requests. Verify thread safety of FAISS index, absence of event-loop blocking in async endpoints.

---

### Phase 3: Hardware & Telemetry Attribution Protocol

Classify every reported measurement strictly into one of four categories:
1. **Measured**: Real physical hardware counters (Intel/AMD RAPL, NVIDIA NVML).
2. **Estimated**: Token/FLOPs proxy models (e.g., $(N/1024)^2$ attention scaling).
3. **Calculated**: Mathematical conversion (e.g., $\text{Joules} = \text{Watt-hours} \times 3600$).
4. **Unavailable**: Metrics that cannot be measured directly (e.g., physical power of proprietary cloud APIs).

---

### Phase 4: Implementation Deliverables

Provide:
1. **The Executive Benchmark Summary**: A clean Markdown table summarizing Chunk Size $\times$ Top-K metrics, attention savings, latency, and Joules.
2. **Automated Pytest Script**: Complete test code with fixtures and assertions for Types A through E.
3. **FastAPI Route Implementations**: Clean Pydantic schemas and async endpoints.
4. **Desktop UI Integration Blueprint**: C# WPF MVVM service code connecting live endpoints to the UI with telemetry visualization.
```

# 11. EcoRAG FastAPI — Comprehensive Testing & GPT Audit Prompt Toolkit

This document provides ready-to-use, production-grade prompts designed to be run in **ChatGPT (GPT-4o)** to test, analyze, and stress-test every feature of the EcoRAG FastAPI platform.

---

## 🎯 Prompt 1: Test All APIs & All Features (Generation Prompt)

Copy and paste this prompt into ChatGPT to generate a complete end-to-end test suite for every endpoint:

```markdown
Act as a Senior QA Automation Engineer and FastAPI Specialist.
I have built the EcoRAG (Energy-Efficient Retrieval-Augmented Generation) FastAPI application with the following endpoints:
1. `GET /api/health` -> System status, active embedding dimension, reranker bypass stats.
2. `POST /api/ingest/text` -> Accepts `{text, doc_id, chunk_size, chunk_overlap, enable_dedup}`, produces chunks, deduplicates, and updates FAISS + BM25 indexes.
3. `POST /api/search` -> Accepts `{query, mode: 'dense'|'sparse'|'hybrid', top_k, enable_rerank}`, returns ranked hits and reranker bypass telemetry.
4. `POST /api/query` -> Accepts `{query, retrieval_mode, top_k, max_tokens}`, performs hybrid search, gated reranking, generates an answer via Gemini API, and returns live telemetry (latency_ms, peak_ram_mb, estimated_wh, eco_score).

Write a comprehensive, production-grade Python `unittest` test suite using `fastapi.testclient.TestClient` that covers:
- Happy paths with various chunk sizes (128, 256, 512) and retrieval modes ('sparse', 'dense', 'hybrid').
- Paragraph deduplication verification (verifying duplicate chunks are pruned).
- Negative input validation: empty text, whitespace-only, negative chunk_size, chunk_overlap >= chunk_size, top_k <= 0, invalid mode.
- Threshold-gated reranker telemetry: high-confidence bypass vs ambiguous cross-encoder trigger.
- End-to-end question answering and telemetry assertions (positive latency, valid Eco Score).
- Ensure no tests throw unhandled 500 exceptions on invalid inputs; assert proper 400 or 422 HTTP status codes.
```

---

## 🔍 Prompt 2: Analyze All Test Cases & Results via GPT (Analysis Prompt)

Copy and paste this prompt into ChatGPT along with your test run output to perform a senior-level audit:

```markdown
Act as a Lead Systems Architect, FastAPI Security Auditor, and Green AI Performance Engineer.
Below are the implementation details and actual test execution logs from our EcoRAG FastAPI platform:

[PASTE YOUR TEST SUITE CODE OR TERMINAL OUTPUT HERE]

Please perform a rigorous, critical audit of these test cases and results:
1. Test Quality Audit:
   - Identify weak assertions (e.g., tests that only assert HTTP 200 without validating business logic or payload schemas).
   - Identify brittle or flaky tests that could fail due to network variance or model downloading.
   - What critical edge cases (boundary values, empty indexes, unicode, concurrency) are completely untested?

2. Concurrency & Event Loop Audit:
   - Check whether CPU-bound calls (FAISS search, BM25, SentenceTransformers) or blocking network calls (Gemini API) inside `async def` route handlers will block FastAPI's event loop under concurrent load.
   - How should we refactor them using `anyio.to_thread.run_sync` or threadpool workers?

3. Green Computing & Telemetry Audit:
   - Critically evaluate our energy accounting: Are we distinguishing between *measured* physical energy (Joules from RAPL/NVML) and *estimated* energy (TDP formulas)?
   - Does our composite Eco Score mathematically reflect true efficiency?

4. Produce a prioritized defect list categorized as CRITICAL, HIGH, MEDIUM, or LOW, with exact code snippets for the recommended fixes.
```

---

## ⚡ Prompt 3: Automated Load & Concurrency Stress-Testing Prompt

Copy and paste this prompt into ChatGPT to generate a load-testing script:

```markdown
Act as a Performance Engineer.
I need a Python asynchronous load-testing script using `httpx` (or Locust) to stress-test our EcoRAG FastAPI backend (`http://127.0.0.1:8000`).

Requirements:
1. Simulate concurrent user workloads across 3 tiers:
   - 10 concurrent requests (Low load)
   - 50 concurrent requests (Medium load)
   - 100 concurrent requests (High load)
2. Mix traffic across:
   - 60% `POST /api/search` (Hybrid RRF search)
   - 30% `POST /api/query` (End-to-end generation)
   - 10% `POST /api/ingest/text` (Document ingestion)
3. Measure and output a formatted markdown table containing:
   - Concurrency level, total requests, success count, error count.
   - P50, P95, and P99 latency (milliseconds).
   - Average requests per second (RPS / Throughput).
   - Identify any HTTP 500 errors or event-loop starvation bottlenecks.
```

---

## 🛡️ Prompt 4: API Security, Boundary & Injection Audit Prompt

Copy and paste this prompt into ChatGPT to audit the security posture of the FastAPI application:

```markdown
Act as an API Security Engineer and Penetration Tester.
Review our EcoRAG FastAPI schemas, CORS configuration, and route handlers:

Schemas:
- `IngestTextRequest(text: str, doc_id: str, chunk_size: int = 50, chunk_overlap: int = 10, enable_dedup: bool = True)`
- `SearchRequest(query: str, mode: str = "hybrid", top_k: int = 5, enable_rerank: bool = True)`
- `QueryRequest(query: str, retrieval_mode: str = "hybrid", top_k: int = 3, max_tokens: int = 200)`

Evaluate our application against:
1. Denial of Service (DoS): Lack of string length / payload size limits on ingestion.
2. CORS Misconfigurations: Wildcard `allow_origins=["*"]` combined with `allow_credentials=True`.
3. Input Boundary Crashes: Passing `top_k <= 0`, negative `chunk_size`, or empty text.
4. Error & Stack Trace Leakage: Does the API leak internal exception traces to clients in production?
5. Prompt Injection: What guards should be added to `POST /api/query` to prevent user queries from escaping context bounds?

Provide concrete, hardened Pydantic validators and security middleware code to patch every vulnerability.
```

# Live bug investigation (company name / sources / 97.5 vs 46.0 J)

Date: 2026-10-03

## Phase 1 live capture (before code change)

`GET /api/health`: 43 chunks, `embedding_provider=fallback-hash` (PyTorch blocked).

`POST /api/query` "What is the company name?" on the **then-running** process:

- No `request_id` / `X-Request-ID` (old process without observability).
- Adaptive **dense** path. Top hits were HR/legal chunks, not About Us.
- Answer: extractive dump of unrelated interview text.

Screenshot answer was **not** that API text. It matched `GenerateContextualAnswer` in `EcoRagApiService.cs`.

## Root causes

### 1. Wrong answer

Three stacked failures:

1. **Desktop stub** (`GenerateContextualAnswer`) ran when `/api/query` failed (5s HttpClient timeout and/or swallowed exceptions). That text is the screenshot.
2. **Even a successful API call used hash embeddings + NORMAL→dense FAISS**, so "What is the company name?" missed About Us. Sparse BM25 **does** retrieve Synoptek About Us.
3. Extractive fallback dumped the first 200 characters instead of answering the question.

No hardcoded "Synoptek" was added. Retrieval + extractive scoring now use the document.

### 2. Missing sources

- `SearchHit` had no filename/page; UI always set `PageNumber = 1`.
- Sources lived in a **collapsed Expander**, so the header showed with no visible rows.
- Demo citations were EcoRAG paper snippets, not the intern PDF.

### 3. 97.5 J vs 46.0 J

- **97.5 J**: chat bubble bound to **fallback** `EnergyTelemetry` (old formula `80 + (query.Length % 20) * 3.5` and similar), not the API.
- **46.0 J**: **static XAML** in `ChatView.xaml` (Energy header, ACTUAL panel, COMPARE EcoRAG). Stage bars 8.2+2.1+6.7+3.4+25.6 were also hardcoded and happen to sum to 46.
- These were **different objects**. Dashboard was never bound to `CurrentQueryTelemetry`.

## Fixes (files)

Backend: `query.py`, `schemas.py`, `retrieval.py`, `ingestion.py`, `ingest.py`, `observability/trace.py`  
Desktop: `EcoRagApiService.cs`, `ChatViewModel.cs`, `ChatView.xaml`, `EnergyTelemetry.cs`, `Citation.cs`, `App.xaml.cs`  
Tests: `test_rag_trace.py`, `test_factoid_routing.py`

## After (API, request `rag_20261003_110223_90ac`)

Question: What is the company name?  
Answer: About Us: Synoptek is a Global Systems Integrator…  
Source filename: Pre Placement Paid Internship -EOC Engineer(1).pdf  
No FAISS/architecture contamination. Telemetry `request_id` matches.

## Desktop

Rebuild is blocked while `EcoRag.Desktop` PID 20724 holds the exe. **Close the running app and rebuild/restart** so the bound dashboard and expanded sources load.

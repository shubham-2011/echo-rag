# EcoRAG RAG Observability & Logging (Parts 25–28)

This document captures the **structured, request-level tracing** specification for EcoRAG and how it is implemented in this repository.

## Correlation ID

Every `/api/query` request receives:

- `request_id` format: `rag_YYYYMMDD_HHMMSS_xxxx`
- Response body: `QueryResponse.request_id`
- Header: `X-Request-ID`
- Telemetry: `telemetry.request_id`
- Logs: every line includes `request_id=...`

Implementation: `backend/src/observability/trace.py` (`RequestTrace`).

## Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `ECORAG_LOG_LEVEL` | `INFO` | `ERROR` / `WARNING` / `INFO` / `DEBUG` |
| `LOG_FULL_PROMPT` | `false` | When `true`, log full prompt (dev only) |
| `ECORAG_EXPOSE_TRACE` | `false` | When `true`, include `trace` object in `QueryResponse` |
| `ECORAG_RELEVANCE_THRESHOLD` | `0.12` | Dense/sparse relevance gate |
| `ECORAG_RRF_RELEVANCE_THRESHOLD` | `0.015` | Hybrid/adaptive RRF gate |
| `ECORAG_DEMO_FALLBACK` | unset | WPF: `true` enables synthetic demo answers (logged `[FALLBACK]`) |

## Log categories (Part 25)

| Tag | When | Module |
|-----|------|--------|
| `[QUERY]` | Intent, rewrite, session | `query.py` |
| `[DOCUMENT_SCOPE]` | Indexed / filtered corpus | `query.py` |
| `[EMBEDDING]` | Model, dim, latency | `query.py` |
| `[FAISS]` | Top-K candidates (DEBUG details) | `query.py` |
| `[FUSION]` | RRF dense/sparse ranks (DEBUG) | `retrieval.py` |
| `[RERANK]` | Before/after ranks | `query.py` |
| `[RELEVANCE_GATE]` | Threshold decision | `query.py` |
| `[CONTEXT]` | Compression stats | `query.py` |
| `[PROMPT]` / `[CONTEXT_CHUNKS]` | Pre-LLM structure | `query.py` |
| `[LLM]` | Model, tokens, latency | `query.py` |
| `[GROUNDING]` | Heuristic faithfulness | `query.py` |
| `[ANSWER]` | Final status | `query.py` |
| `[TELEMETRY]` | One record per request | `query.py` |
| `[API_RESPONSE]` | Values sent to client | `query.py` |
| `[FALLBACK]` | Explicit substitute paths | `query.py`, WPF `EcoRagApiService.cs` |
| `[ERROR]` | Failures with component | `query.py` |
| `[PERFORMANCE]` | Stage timings | `query.py` |
| `[UI_UPDATE]` / `[UI_STATE]` | WPF correlation | `ChatViewModel.cs`, `EcoRagApiService.cs` |

DEBUG mode emits FAISS candidate previews, fusion ranks, rerank deltas, and safe context previews. Full document text is not logged in production-style INFO runs.

## End-to-end trace block

When a query completes, an **EcoRAG TRACE** summary block is written at INFO (see spec Part 25.22).

## Part 26 — automated trace test

`backend/tests/test_rag_trace.py`:

- Ingests internship text containing `Stipend: ₹10,000 per month`
- Queries with `retrieval_mode=sparse`, `doc_ids` filter, Gemini disabled
- Asserts log stages and answer/trace fields; reports failed **stage name** on failure

Run:

```powershell
cd backend
..\venv\Scripts\python.exe -m pytest tests/test_rag_trace.py -q
```

## Part 27 — no silent fallback (audit)

### Backend

- Gemini failure → `[FALLBACK] component=LLM reason=...` then extractive synthesis or abstain
- No bare `except: pass` in query pipeline

### Desktop (critical for “wrong answer” symptoms)

Previously `EcoRagApiService.cs`:

- Synthetic `GenerateContextualAnswer` (generic EcoRAG marketing text)
- Hardcoded `38.5` J when telemetry missing
- Fake citations when backend failed

Now:

- Default: **abstain message** + `[FALLBACK] component=UI reason=backend_unavailable_or_empty_answer`
- Demo path only if `ECORAG_DEMO_FALLBACK=true` (logged)
- Telemetry `QueryId` = backend `request_id`; no fabricated joules default
- `ChatViewModel` ignores stale telemetry when `QueryId` ≠ active request

### Remaining demo seeds

Welcome message telemetry in `ChatViewModel` is static UI chrome (not live query metrics). Dashboard XAML may still show placeholder values unless bound to ViewModel — bind live `EnergyTelemetry` where needed.

## Part 28 — manual acceptance queries

With backend on `127.0.0.1:8000`, ingest your PDF/text, then run:

1. What is the company name?
2. Where is it headquartered?
3. What does the company do?
4. What is the internship stipend?
5. What is the work location?
6. What ITSM tool is mentioned?

For each response, copy `request_id` from JSON or `X-Request-ID`, then grep backend logs:

```powershell
Select-String -Path backend.log -Pattern "rag_20261003_"
```

Failure localization: find the last successful stage tag before missing/wrong data (QUERY → … → UI).

## API schema changes

- `QueryRequest`: optional `session_id`, `turn`, `doc_ids`
- `QueryResponse`: `request_id`, optional `trace`
- `TelemetryMetrics`: `request_id`, token counts, `stage_timings_ms`, `grounding_passed`, `measurement_type`

## Related files

- `backend/src/api/routes/query.py` — pipeline orchestration
- `backend/src/observability/` — trace helpers
- `frontend/src/EcoRag.Desktop/Services/EcoRagApiService.cs`
- `frontend/src/EcoRag.Desktop/ViewModels/ChatViewModel.cs`

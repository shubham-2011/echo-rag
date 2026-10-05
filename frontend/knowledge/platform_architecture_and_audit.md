# Platform Architecture, Features Added, and Audit

**Date:** 2026-10-03  
**Authoritative architecture:** [../../docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md)  
**Implementation roadmap:** [../../docs/12_implementation_plan.md](../../docs/12_implementation_plan.md)

---

## What was added in this session

### 1. Index persistence (`backend/src/persistence/`)

| Item | Detail |
|---|---|
| **Module** | `IndexStore` — save/load FAISS + chunk metadata + manifest |
| **Env** | `ECORAG_INDEX_DIR` (default `backend/data/index`), `ECORAG_INDEX_PERSIST` (`true`/`false`) |
| **When** | Save after every successful `update_corpus`; load when `AppState` starts |
| **Safety** | Skip load if saved embedding provider or dimension ≠ active embedder |
| **Manifest** | `dataset_hash` = canonical SHA-256 over sorted chunk text hashes |
| **Health API** | `index_persisted`, `index_loaded_from_disk`, `dataset_hash` on `GET /api/health` |
| **Tests** | `backend/tests/test_index_persistence.py` |

### 2. Telemetry label (`energy_source`)

| Item | Detail |
|---|---|
| **Schema** | `TelemetryMetrics.energy_source` default `ESTIMATED` |
| **Query** | `/api/query` sets `energy_source="ESTIMATED"` explicitly |
| **Meaning** | Energy is still the 45 W × latency formula until hardware measurement is added |

### 3. Documentation

| File | Role |
|---|---|
| `docs/ARCHITECTURE.md` | Single source of truth for live stack |
| This file | Audit matrix + session changelog |

---

## Architecture (short)

```
WPF Desktop  →  FastAPI  →  RAG (FAISS + BM25 + rerank + cache + LLM)
                │              ↓
                │         data/index (persist)
                ├── experiments.db
                └── audit.db (SHA-256 + Merkle + local blocks)
```

Blockchain audits **experiments**, not chat latency. Contract file exists; RPC adapter not enabled.

---

## Feature audit matrix (documented vs implemented)

| Feature | Documented in research | In code | On critical path | Tested |
|---|---|:---:|:---:|:---:|
| FAISS dense retrieval | Yes | Yes | `/search`, `/query` | Yes |
| BM25 sparse | Yes | Yes | Yes | Yes |
| Hybrid RRF | Yes | Yes | Yes | Yes |
| Adaptive routing + caches | Yes | Yes | `/query` adaptive | Yes |
| Gated reranker | Yes | Yes | Yes | Yes |
| Context compression | Yes | Yes | `/query` | Partial |
| Gemini generation | Yes | Yes | If `GEMINI_API_KEY` | Partial |
| Local MiniLM embeddings | Yes | Yes* | Yes | Yes |
| Index survive restart | Plan Phase 1 | **Yes (new)** | Ingest + startup | **Yes (new)** |
| `dataset_hash` on health | Plan Phase 1 | **Yes (new)** | Health | Via persistence test |
| `energy_source` label | Plan Phase 2 | **Yes (new)** | `/query` | OpenAPI |
| Experiment lifecycle | Chat + plan | Yes | `/api/experiments` | Yes |
| Auto-anchor on complete | Chat + plan | Yes | complete → audit | Yes |
| Local verify / mismatch | Chat + plan | Yes | `/api/audit/.../verify` | Yes |
| Merkle batch anchor | Chat + plan | Yes | `/api/audit/batch/anchor` | Yes |
| Public chain tx | Chat + plan | Contract only | No | No |
| Redis / Chroma | Old README | No | — | — |
| Measured joules (NVML/RAPL) | Research | No | — | — |
| WPF Audit / Experiments UI | Chat + plan | No | — | — |
| `/experiments/{id}/run` auto RAG | Plan Phase 3 | No | — | — |

\* Falls back to `HashEmbeddingService` if PyTorch/sentence-transformers blocked on host.

---

## How to run (demo)

From repo root (with `venv` and dependencies):

```powershell
cd backend
..\venv\Scripts\python.exe -m uvicorn src.api.app:app --host 127.0.0.1 --port 8000
```

Desktop:

```powershell
frontend\src\EcoRag.Desktop\bin\Debug\net10.0-windows\EcoRag.Desktop.exe
```

**Smoke demo (PowerShell):**

```powershell
$base = "http://127.0.0.1:8000"
Invoke-RestMethod "$base/api/health"
Invoke-RestMethod -Method Post -Uri "$base/api/ingest/text" -ContentType "application/json" -Body '{"text":"EcoRAG index persistence demo.","doc_id":"demo1","chunk_size":20}'
Invoke-RestMethod -Method Post -Uri "$base/api/search" -ContentType "application/json" -Body '{"query":"persistence","mode":"hybrid","top_k":3}'
```

Restart the API and call `/api/health` again — `total_indexed_chunks` and `dataset_hash` should match if persistence is enabled.

**Audit demo:**

```powershell
$exp = Invoke-RestMethod -Method Post -Uri "$base/api/experiments" -ContentType "application/json" -Body '{"name":"demo","dataset":{"v":1},"configuration":{"top_k":3}}'
$id = $exp.experiment_id
Invoke-RestMethod -Method Post -Uri "$base/api/experiments/$id/complete" -ContentType "application/json" -Body '{"result":{"accuracy":0.9},"telemetry":{"energy_wh":0.01},"environment":{"git":"local"}}'
Invoke-RestMethod -Method Post -Uri "$base/api/audit/$id/verify" -ContentType "application/json" -Body "{`"entity_type`":`"experiment`",`"payload`":$(Get-Content ...)}" 
```

Use the manifest returned from `GET /api/experiments/$id` as the verify payload.

---

## Gaps to implement next (from plan)

1. Desktop **Experiments** + **Audit** views wired to API  
2. `POST /api/experiments/{id}/run` — real RAG evaluation, not hand-entered metrics  
3. Optional `blockchain/` adapter + `AUDIT_CHAIN_ENABLED`  
4. Measured energy when sensors available; desktop shows label from `energy_source`

### Blockchain test suite (2026-10-03)

- Plan: [blockchain_audit_test_plan.md](blockchain_audit_test_plan.md)  
- Traceability: [blockchain_test_traceability.md](blockchain_test_traceability.md)  
- Run: `cd backend && ..\venv\Scripts\python.exe -m pytest tests/blockchain -q` → **27 passed, 1 skipped** (on-chain anchor)

---

## Research positioning (allowed claim)

> EcoRAG runs an adaptive, energy-labeled RAG pipeline, persists its vector index, and anchors completed experiment manifests with a tamper-evident local audit chain (with optional public anchoring later).

Not allowed:

> Blockchain makes RAG use less energy.

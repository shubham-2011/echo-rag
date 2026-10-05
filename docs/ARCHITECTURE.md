# EcoRAG — System Architecture (Authoritative)

**Last updated:** 2026-10-03  
**Scope:** What this repository actually runs today. Older notes that mention Redis, Chroma, Prometheus, or WinUI 3 are research or planning unless this file says otherwise.

---

## 1. Purpose

EcoRAG is an **energy-aware RAG platform**: retrieve from a document index, compress context, generate an answer, and report latency, RAM, and **estimated** energy. A separate **audit layer** hashes experiment manifests so results can be checked for tampering (local hash-chain today; optional public chain later).

Blockchain does **not** run inside retrieval or generation.

---

## 2. Runtime topology

```
┌─────────────────────────────────────────────────────────────┐
│  EcoRag.Desktop (WPF / .NET 10, MVVM, Iris UI)              │
│  Overview | Documents | Assistant | Telemetry | Settings    │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTP JSON
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  FastAPI (Uvicorn) — backend/src/api/app.py                 │
│  /api/health  /api/ingest/*  /api/search  /api/query        │
│  /api/experiments  /api/audit/*                             │
└───────────────────────────┬─────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
   AppState            SQLite stores        Optional Gemini
   (in-memory RAG)     audit.db             (embed + generate)
                       experiments.db
        │
        ├── FAISS IndexFlatIP (+ normalized cosine)
        ├── BM25Okapi corpus
        ├── Threshold-gated cross-encoder reranker
        ├── L1 exact + L2 semantic query cache
        ├── Query classifier + adaptive / hybrid / dense / sparse
        └── Dynamic context / sentence compression
        │
        ▼
   data/index/  (FAISS .bin + chunk meta + manifest)  ← persistence
```

---

## 3. Request flows

### 3.1 Ingest

`POST /api/ingest/text` or `POST /api/ingest/file` → chunk → dedupe → embed batch → `AppState.update_corpus` → **persist index** to `ECORAG_INDEX_DIR` (default `backend/data/index`).

On API startup, `AppState` **loads** the index if manifest matches active embedding provider and dimension.

### 3.2 Search

`POST /api/search` → mode `sparse` | `dense` | `hybrid` | `adaptive` → optional gated rerank → ranked hits.

### 3.3 Query (chat)

`POST /api/query` → cache → retrieve → rerank gate → compress → Gemini or extractive fallback → telemetry with `energy_source=ESTIMATED` (45 W × duration proxy, not hardware RAPL/NVML yet).

### 3.4 Experiment + audit

1. `POST /api/experiments` — queue run with dataset + configuration JSON.  
2. `POST /api/experiments/{id}/complete` — supply result + telemetry + environment; builds manifest with separate SHA-256 hashes for dataset, config, result, telemetry; **auto-anchors** via `AuditService`.  
3. `POST /api/audit/{id}/verify` — rehash payload; `verified=true` if unchanged.  
4. Public chain: **not wired** (`AUDIT_CHAIN_ENABLED=false`, `transaction_hash` null).

---

## 4. Data stores

| Store | Path | Contents |
|---|---|---|
| FAISS index | `data/index/faiss_index.bin` | Vectors |
| Chunk meta | `data/index/faiss_index_meta.json` | Chunk text + ids |
| Index manifest | `data/index/index_manifest.json` | `dataset_hash`, provider, dimension |
| Audit | `data/audit.db` | Records, Merkle blocks, local hash-chain |
| Experiments | `data/experiments.db` | Run lifecycle + manifest + anchor JSON |

---

## 5. Energy telemetry honesty

| Field | Meaning |
|---|---|
| `estimated_wh` | Calculated proxy (45 W × seconds, with cache/rerank discounts) |
| `energy_source` | `ESTIMATED` until measured sensors are integrated |
| Future | `MEASURED` via CodeCarbon / NVML when available |

Do not describe `estimated_wh` as measured joules in papers or UI without checking `energy_source`.

---

## 6. Smart contract

`backend/contracts/EcoRAGAudit.sol` — minimal anchor (`entityKey`, `payloadHash`, `merkleRoot`). Deployed only when Phase 5 of `docs/12_implementation_plan.md` is implemented.

---

## 7. Related docs

- Implementation roadmap: `docs/12_implementation_plan.md`
- Research spec: `docs/01`–`06`, `ecorag_complete_findings.md`
- Desktop Iris UI: `frontend/knowledge/ui_ux_iris_redesign.md`
- Platform audit (this release): `frontend/knowledge/platform_architecture_and_audit.md`

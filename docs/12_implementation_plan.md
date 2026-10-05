# 12. Implementation Plan — Fix the Platform, Then Prove Experiments

**Date:** 2026-10-03  
**Source:** Live code in this repo plus ChatGPT share `6ac0c2a1-ddb4-83ec-97a6-50f38613db48`  
**Rule that does not change:** Blockchain audits EcoRAG. It does not retrieve, compress, generate, or save energy. A RAG answer must never wait on a chain transaction.

This plan is ordered so later work has something honest to hash. Do not skip to a public chain while the index still dies on restart and energy is still a 45 W formula.

---

## Current truth (code, not docs)

| Capability | Status |
|---|---|
| FastAPI ingest / search / query | Working |
| FAISS + BM25 + hybrid RRF + gated rerank + L1/L2 cache | Working in process memory |
| FAISS `save` / `load` | Written, **not called** on ingest or startup |
| Energy on `/api/query` | **Estimated**: `45 W × seconds`, with cache/rerank discounts |
| Experiment lifecycle | Working: create → complete → local SHA-256 + Merkle block |
| Audit API | Working: anchor, batch, get, verify, proof |
| `EcoRAGAudit.sol` | File only. `AUDIT_CHAIN_ENABLED=false`. `transaction_hash` always `null` |
| Desktop | WPF Iris UI. No Experiments screen. No Audit screen |
| Redis / Chroma / Prometheus / WinUI 3 / Ollama cascade | Named in older notes. **Not** the live stack |

---

## Research claim we are allowed to make

After the plan is done:

> EcoRAG measures (or clearly labels) energy-aware RAG experiments, stores the full record off-chain, and publishes a cryptographic proof so a later copy of that record can be shown as unchanged.

We will **not** claim that blockchain reduces joules, latency, or token count. Energy of the chain, if any, is reported separately from RAG energy.

---

## Non-goals (explicit)

- Do not put PDFs, chunk text, embeddings, prompts, or answers on a chain.
- Do not hash every chat query by default.
- Do not add Redis or Chroma just because old READMEs mention them.
- Do not wait for RPC confirmation inside `/api/query`.
- Do not treat a local SQLite hash-chain as a public blockchain in the UI or papers.

---

## Architecture after the plan

```
WPF (Overview, Documents, Assistant, Telemetry, Experiments, Audit, Settings)
        │
        ▼
FastAPI  /ingest  /search  /query  /experiments  /audit
        │                              │
        ▼                              ▼
   RAG engine                    Experiment store
   FAISS + BM25                  (SQLite, full JSON)
   Cache + rerank                       │
   Compression + LLM                    ▼
        │                         Audit engine
        ▼                         canonicalize → SHA-256 → Merkle
   Telemetry                      local hash-chain (always)
   energy_source =                optional async chain adapter
   MEASURED | ESTIMATED           (hashes + merkle root only)
```

---

## Phase 0 — Canonical docs (1 session)

**Why first:** The ChatGPT thread already flagged documentation drift. New work must not copy Redis/Chroma/WinUI as if they were live.

**Do:**

1. Add one short `docs/ARCHITECTURE.md` that lists only what the code does today, plus “planned” with this file as the source.
2. Point `docs/README.md`, `backend/README.md`, and `frontend/README.md` at that file.
3. Add `energy_source` language: `MEASURED`, `ESTIMATED`, `CALCULATED`, `UNAVAILABLE`.

**Done when:** A new reader cannot confuse `anchored_local` with a public transaction.

---

## Phase 1 — Persistence (index survives restart)

**Problem:** `AppState` keeps chunks and FAISS in RAM. `FAISSVectorStore.save` / `load` exist and are unused. Restart empties the knowledge base.

**Do:**

1. On ingest success, persist FAISS binary + chunk metadata (and BM25 corpus) under `backend/data/index/`.
2. On API startup, load if files exist and dimensions match the active embedder.
3. Record a `dataset_hash` (canonical hash of sorted chunk hashes) on each persist. Store it next to the index.
4. Rebuild BM25 from loaded chunks.

**Files:** `backend/src/api/dependencies.py`, `backend/src/vector_store.py`, ingest routes, tests that restart the store from disk.

**Done when:** Ingest → kill process → start → `/api/health` still reports the same chunk count and a search still hits.

**Not in this phase:** PostgreSQL. SQLite + FAISS files are enough.

---

## Phase 2 — Honest telemetry

**Problem:** `/api/query` reports `estimated_wh` from a 45 W proxy. Desktop energy gauges look measured.

**Do:**

1. Add `energy_source` to `TelemetryMetrics` (`ESTIMATED` today).
2. Keep the 45 W formula as `CALCULATED` / `ESTIMATED` only, with the formula documented in one comment and in OpenAPI.
3. Optional hook: if `pynvml` or CodeCarbon is available, fill `measured_wh` and set `energy_source=MEASURED`. If not, leave measured fields null. Never add NVML on top of CodeCarbon for the same GPU.
4. Stage timings: retrieval_ms, rerank_ms, generate_ms. Do not invent joules per stage unless measured.
5. Desktop: show “Estimated” on energy chips unless `energy_source` is `MEASURED`.

**Files:** `schemas.py`, `query.py`, `experiments.py` (same formula), Chat / Telemetry XAML + DTOs, tests that assert the label.

**Done when:** No API field implies hardware joules unless a sensor ran.

---

## Phase 3 — Experiment engine that actually runs RAG

**Problem:** `POST /api/experiments/{id}/complete` accepts any JSON result. The demo we ran was hand-written telemetry, not a real pipeline run.

**Do:**

1. Add `POST /api/experiments/{id}/run` that:
   - loads dataset files or already-indexed `doc_id`s
   - applies the frozen `configuration` (chunk size, mode, top_k, rerank, cache)
   - executes the evaluation questions through the same retrieval + query path
   - writes result + telemetry + environment (`git_commit` if available, embedding model, dimension)
   - calls existing `complete()`, which already hashes and anchors
2. Keep create / cancel / complete for interrupted or external runs.
3. Refuse complete if configuration was mutated (compare stored canonical JSON).

**Files:** `experiment_runs.py`, `routes/experiments.py`, `tests/test_experiment_runs.py`.

**Done when:** One fixture corpus + three questions produces a completed experiment whose `manifest.dataset.sha256` matches the persisted index hash from Phase 1.

---

## Phase 4 — Tighten the local audit layer (already mostly done)

**Keep:** canonicalizer, Merkle, SQLite blocks, verify mismatch, proof export.

**Do:**

1. Align the contract comment and API docs: local adapter name is `local-hash-chain`.
2. Store `verification_records` (who verified, when, match/mismatch) so the desktop can show history.
3. On ingest, optionally `anchor(entity_type="document", ...)` with `{doc_id, document_hash, chunk_count}` — hashes only.
4. Never change `/api/query` to call the chain. Optional: after a completed **experiment run**, not after each chat.

**Done when:** Existing `test_audit.py` still passes; a tampered complete-payload still returns `verified=false`.

---

## Phase 5 — Optional public-chain adapter (off the hot path)

**Default:** `AUDIT_CHAIN_ENABLED=false`. Local chain remains the source of operational truth.

**Do only when RPC + key exist:**

1. Adapter `backend/src/blockchain/adapter.py`:
   - input: `entity_key`, `payload_hash`, `merkle_root`
   - output: `transaction_hash`, `block_number`, `network`, `contract_address`
   - write to new table `blockchain_anchors` (do not overwrite local blocks)
2. Run submit in a background thread / queue after `complete()`. Query path stays untouched.
3. Status machine: `anchored_local` → `submitted` → `confirmed` | `failed`.
4. Deploy `contracts/EcoRAGAudit.sol` to a **test** network first (Sepolia or a local Anvil). Keep the contract small: payload hash + merkle root + timestamp.
5. Verify endpoint: compare local hash to on-chain `getAnchor`. If RPC is down, return `local_verified` + `chain_status=unavailable`.

**Env:**

```
AUDIT_CHAIN_ENABLED=false
AUDIT_RPC_URL=
AUDIT_CONTRACT_ADDRESS=
AUDIT_SIGNER_KEY=          # server only, never in WPF
```

**Done when:** With the flag off, behavior is identical to today. With the flag on in a local Anvil test, `transaction_hash` is non-null and verify still works if the JSON is unchanged.

---

## Phase 6 — Desktop: Experiments + Audit (Iris)

**Do:**

1. Nav items: **Experiments** and **Audit** (same selected-state pattern as Overview).
2. Experiments view: list runs, status, create from named config, show quality vs estimated/measured energy. Do not show chain jargon here.
3. Audit view: experiment id, payload hash, merkle root, block number, `anchor_type`, integrity `VERIFIED` / `MISMATCH`, optional tx hash if confirmed. Copy hash buttons.
4. Client calls existing `/api/experiments` and `/api/audit/*`. Secrets stay on the server.
5. Energy copy uses `energy_source`.

**Files:** `MainViewModel.cs`, new view-models/views, `EcoRagApiService.cs`, `MainWindow.xaml`.

**Done when:** Completing a run in the UI shows VERIFIED; editing the payload in a verify box shows MISMATCH.

---

## Phase 7 — Research comparison (after 1–6)

Run four labeled configurations on the same dataset:

1. Baseline RAG (dense, no cache, always rerank, large context)
2. Optimized EcoRAG (hybrid, gated rerank, compression)
3. Adaptive EcoRAG (classifier + cache)
4. Same as 3, plus experiment anchor (local, and chain only if Phase 5 is on)

Report **separately**: quality, latency, energy (with source), RAM, cost, auditability (`verified` rate). Do not fold auditability into Eco Score.

---

## Suggested build order for the next coding sessions

| Session | Deliverable |
|---|---|
| 1 | Phase 0 docs + Phase 1 persist/load + tests |
| 2 | Phase 2 `energy_source` API + desktop labels |
| 3 | Phase 3 `/experiments/{id}/run` |
| 4 | Phase 4 verification history + document hash anchors |
| 5 | Phase 6 Experiments + Audit screens |
| 6 | Phase 5 only if you have a test RPC (otherwise skip) |
| 7 | Phase 7 benchmark table for the paper/demo |

---

## Test matrix (must stay green)

- Persist/load round-trip
- Query telemetry includes `energy_source`
- Experiment run produces matching dataset hash
- Anchor + verify true; tamper verify false (already exists)
- Batch Merkle: two records, one `block_number`
- Desktop: never displays `transaction_hash` as a public proof when it is null
- Chain adapter tests use a fake RPC; no live mainnet in CI

---

## What you already do not need to rebuild

Canonical JSON, SHA-256, Merkle root/proof, SQLite audit blocks, experiment complete → auto-anchor, FastAPI audit routes, and the Solidity stub. Phase 4–5 extend those; they do not replace them.

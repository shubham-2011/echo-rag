# EcoRAG Blockchain Audit Layer — Test Plan, Test Cases, and Validation Strategy

**Saved:** 2026-10-03 (project knowledge copy)  
**Automation map:** [blockchain_test_traceability.md](blockchain_test_traceability.md)  
**Pytest location:** `backend/tests/blockchain/`

---

## 1. Test objective

Verify that adding blockchain to EcoRAG:

1. Creates a tamper-evident record of experiments.
2. Correctly hashes experiment configuration, datasets, results, and telemetry.
3. Anchors hashes to the blockchain without modifying RAG behavior.
4. Detects any modification to previously recorded experiment data.
5. Provides reliable verification through the API and desktop client.
6. Handles blockchain failures without breaking the RAG pipeline.
7. Does not significantly distort EcoRAG latency, energy, memory, or answer-quality measurements.

The blockchain layer is an **audit/provenance system**, not part of the RAG inference path.

---

## 2. Scope

**In scope:** canonicalization, SHA-256, Merkle trees, audit records, blockchain client, smart contract, anchoring, transaction tracking, verification, audit API, DB consistency, WPF audit screen, failure recovery, security, performance, regression.

**Out of scope:** retrieval/embedding quality, FAISS/BM25/reranker logic changes, LLM training, consensus optimization.

---

## 3. Test architecture

```text
EcoRAG RAG Query → Experiment Runner → Telemetry → Audit Canonicalizer
→ SHA-256 → Audit Database → Blockchain Adapter → Smart Contract
→ Transaction/Event → Verification Engine
```

**Current implementation:** local hash-chain + Merkle in SQLite (`audit.db`); `EcoRAGAudit.sol` on disk; public adapter **not enabled**.

---

## 4–5. Environment and fixtures

- Python 3.12+, FastAPI, pytest, SQLite test DBs.
- Local EVM for contract tests (future); public testnet after local pass.
- Fixture experiment `EXP-001` with `energy_wh`, `latency_ms`, `top_k`, etc.
- Tamper: change `energy_wh` or `top_k` → verification must fail.

---

## 6–12. Unit, hash, Merkle, contract, audit service, API tables

All **BC-UNIT-***, **BC-HASH-***, **BC-MERKLE-***, **BC-CONTRACT-***, **BC-AUDIT-***, **BC-API-***, **BC-VERIFY-*** IDs are defined in the original specification (sections 6–12 of the submitted plan).

**Automated today:** see traceability matrix for pytest function names.

---

## 13. Most important test — tamper detection (E2E demo)

1. Create `EXP-001` and anchor → hash `H1`.
2. Verify with original payload → **PASS**.
3. Change `energy_wh` (or DB result) → rehash `H2`.
4. `H2 != H1` → **VERIFICATION FAILED**.

Implemented: `test_bc_verify_002_energy_tamper`, `test_e2e_002_tamper_after_anchor`.

---

## 14–20. Regression, energy separation, performance, failures, security, WPF, E2E

- **BC-REG-***: RAG search/ingest unchanged (`test_rag_regression.py`).
- **§15 Critical energy test:** blockchain overhead must not be labeled as RAG `estimated_wh`; use separate metrics when chain is enabled.
- **BC-PERF-***, **BC-SEC-***, **BC-UI-***: planned; UI and chain adapter pending.

**E2E IDs:** E2E-001 (full flow), E2E-002 (tamper), E2E-005 (restart) — automated in `test_e2e_audit.py`.

---

## 21. Scientific validation

Compare **Baseline RAG** vs **EcoRAG optimized** vs **EcoRAG + audit** separately:

- A vs B → optimization effect  
- B vs C → audit overhead  
- C → auditability (verify API)

---

## 22. Test directory (as implemented)

```text
backend/tests/
├── blockchain/
│   ├── test_canonicalizer.py
│   ├── test_merkle.py
│   ├── test_audit_api.py
│   ├── test_e2e_audit.py
│   ├── test_rag_regression.py
│   └── test_contract.py
├── test_audit.py
├── test_experiment_runs.py
└── test_index_persistence.py
```

---

## 23–24. Pytest markers and execution order

Markers in `backend/pytest.ini`: `unit`, `blockchain`, `integration`, `security`, `performance`, `regression`, `e2e`.

Suggested order: baseline freeze → unit → contract (local EVM) → API → integration → tamper → failure → performance → regression → research runs.

---

## 25. Release acceptance criteria

Use checklist in traceability file; on-chain anchor, transaction persistence, WPF Audit, and full SEC/PERF suites remain open.

---

## 26. Priority ten tests

| # | ID | Automated |
|---:|---|:---:|
| 1 | BC-UNIT-001 | Yes |
| 2 | BC-HASH-002 | Yes |
| 3 | BC-CONTRACT-010 | Skipped |
| 4 | BC-CONTRACT-016 | No |
| 5 | BC-API-001 | Yes |
| 6 | BC-VERIFY-001 | Yes |
| 7 | BC-VERIFY-002 | Yes |
| 8 | BC-AUDIT-010 | Yes |
| 9 | BC-REG-001 | Yes |
| 10 | E2E-001 | Yes |

---

## Final demo flow

```text
USER RUNS EXPERIMENT → EcoRAG → Metrics → Experiment Record → SHA-256
→ Blockchain (local today) → ANCHORED ✓ → User modifies record → VERIFY → MISMATCH ✗
```

That demonstrates the core purpose: experiment records are not silently mutable.

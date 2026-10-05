# EcoRAG Blockchain Audit Layer — Test Plan

**Status:** Active specification for validation  
**Companion:** [blockchain_test_traceability.md](blockchain_test_traceability.md) maps test IDs to pytest in `backend/tests/blockchain/`  
**Architecture:** [ARCHITECTURE.md](ARCHITECTURE.md)

---

## 1. Test objective

Verify that the blockchain audit layer:

1. Creates a tamper-evident record of experiments.
2. Correctly hashes configuration, datasets, results, and telemetry.
3. Anchors hashes without modifying RAG behavior.
4. Detects modification to recorded experiment data.
5. Exposes reliable verification via API (and desktop when implemented).
6. Survives blockchain/RPC failures without breaking RAG.
7. Does not conflate blockchain overhead with RAG energy metrics.

The audit layer is **provenance**, not inference.

---

## 2. Scope

**In scope:** canonicalization, SHA-256, Merkle trees, audit records, smart contract, anchoring, verification, API, DB consistency, failure recovery, security, performance, regression.

**Out of scope:** retrieval quality, embedding training, FAISS/BM25/reranker logic changes, consensus optimization.

---

## 3–26. Full case catalog

The complete numbered catalog (BC-UNIT through E2E, acceptance checklist, execution order, and demo flow) is maintained in the project knowledge copy:

- [../frontend/knowledge/blockchain_audit_test_plan.md](../frontend/knowledge/blockchain_audit_test_plan.md) — full text as provided for audit/research.

---

## 4. Implementation status (summary)

| Area | Automated today | Notes |
|---|---|---|
| BC-UNIT / BC-HASH | Yes | `tests/blockchain/test_canonicalizer.py` |
| BC-MERKLE | Yes | `tests/blockchain/test_merkle.py` |
| BC-API / BC-VERIFY | Yes | `tests/blockchain/test_audit_api.py` |
| E2E-001, E2E-002, E2E-005 | Yes | `tests/blockchain/test_e2e_audit.py` |
| BC-REG | Yes | `tests/blockchain/test_rag_regression.py` |
| BC-CONTRACT (on-chain) | Partial | Source check only; anchor skipped until adapter |
| BC-UI (WPF Audit) | No | Planned Phase 6 |
| BC-PERF / BC-SEC (full) | No | Add incrementally |

---

## 5. How to run

From `backend/`:

```bash
..\venv\Scripts\python.exe -m pytest -m unit
..\venv\Scripts\python.exe -m pytest -m integration
..\venv\Scripts\python.exe -m pytest -m e2e
..\venv\Scripts\python.exe -m pytest -m regression
..\venv\Scripts\python.exe -m pytest tests/blockchain
..\venv\Scripts\python.exe -m pytest
```

Priority ten (from plan §26): covered by the blockchain test package except on-chain anchor and UI.

---

## 6. Release acceptance

Use the checklist in §25 of the full plan. Items marked implemented in [blockchain_test_traceability.md](blockchain_test_traceability.md).

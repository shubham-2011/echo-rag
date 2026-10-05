# Blockchain audit test traceability

Maps **test plan IDs** to pytest in `backend/tests/`.  
Full plan narrative: [blockchain_audit_test_plan.md](blockchain_audit_test_plan.md)  
Summary index: [../../docs/blockchain_audit_test_plan.md](../../docs/blockchain_audit_test_plan.md)

---

## Priority ten (plan §26)

| ID | Description | pytest | Status |
|---|---|---|:---:|
| BC-UNIT-001 | Canonical determinism | `test_canonicalizer.py::test_bc_unit_001_*` | Pass |
| BC-HASH-002 | Hash changes after modification | `test_canonicalizer.py::test_bc_hash_002_*` | Pass |
| BC-CONTRACT-010 | Successful on-chain anchor | `test_contract.py::test_bc_contract_010_*` | **Skipped** (no adapter) |
| BC-CONTRACT-016 | Event emission | — | **Not implemented** |
| BC-API-001 | Anchor API | `test_audit_api.py::test_bc_api_001_*` | Pass |
| BC-VERIFY-001 | Valid verification | `test_audit_api.py::test_bc_verify_001_*` | Pass |
| BC-VERIFY-002 | Tamper detection (energy) | `test_audit_api.py::test_bc_verify_002_*` | Pass |
| BC-AUDIT-010 | Restart recovery | `test_e2e_audit.py::test_e2e_005_restart_recovery` | Pass |
| BC-REG-001 | RAG regression | `test_rag_regression.py::test_bc_reg_001_*` | Pass |
| E2E-001 | Full experiment flow | `test_e2e_audit.py::test_e2e_001_full_flow` | Pass |

---

## Unit / hash / Merkle

| ID | pytest |
|---|---|
| BC-UNIT-002 | `test_bc_unit_002_key_order_independent` |
| BC-UNIT-003 | `test_bc_unit_003_one_field_change_changes_hash` |
| BC-UNIT-005 | `test_bc_unit_005_unicode_stable` |
| BC-UNIT-006 | `test_bc_unit_006_float_deterministic` |
| BC-HASH-001 | `test_bc_hash_001_same_record_twice` |
| BC-HASH-004 | `test_bc_hash_004_config_top_k_change` |
| BC-HASH-007 | `test_bc_hash_007_empty_object_allowed` |
| BC-HASH-008 | `test_bc_hash_008_nan_rejected` |
| BC-MERKLE-001–008 | `test_merkle.py` (001, 002, 004, 007, 008 + empty) |
| Legacy | `tests/test_audit.py` (anchor tamper, batch block) |

---

## API / verify / E2E

| ID | pytest |
|---|---|
| BC-API-002 | `test_bc_api_002_missing_entity_id` |
| BC-VERIFY-004 | `test_bc_verify_004_config_top_k` |
| E2E-002 | `test_e2e_002_tamper_after_anchor` |
| E2E-005 | `test_e2e_005_restart_recovery` |
| Experiment store | `tests/test_experiment_runs.py` |

---

## Not automated yet

| Area | IDs | Blocker |
|---|---|---|
| On-chain anchor / events | BC-CONTRACT-010–023 | `blockchain/` adapter + local EVM |
| Auth on audit routes | BC-API-009 | No auth middleware |
| RPC timeout / retry | BC-API-007–008, §17 | Adapter |
| Performance load | BC-PERF-* | Benchmark harness |
| Security scan | BC-SEC-* (partial) | Manual + future tests |
| WPF Audit UI | BC-UI-* | Desktop view not built |
| Measured vs chain energy | §15 | Separate metrics not wired |

---

## Release checklist (plan §25) — honest status

| Criterion | Done |
|---|:---:|
| Canonical hash deterministic | Yes |
| One-field change changes hash | Yes |
| Merkle proof verifies | Yes |
| Smart contract stores anchors on-chain | No |
| Transaction IDs persisted | No |
| Verification API works | Yes |
| Tampering detected | Yes |
| Blockchain outage does not break RAG | Partial (no chain yet) |
| Backend restart preserves audit state | Yes |
| Private keys not in frontend/logs | Yes (no keys in repo) |
| RAG search regression | Yes |
| Energy excludes chain overhead | Yes (no chain) |
| `energy_source` distinguished | Yes |
| No fake chain status in UI | N/A (no Audit UI) |
| Desktop audit history | No |
| Docs match API | In progress |

---

## Commands

```powershell
cd backend
..\venv\Scripts\python.exe -m pytest -m unit
..\venv\Scripts\python.exe -m pytest -m integration
..\venv\Scripts\python.exe -m pytest -m e2e
..\venv\Scripts\python.exe -m pytest tests/blockchain -q
```

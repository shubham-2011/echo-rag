# Phase 2 — Security Foundation Report

**Completed:** 2026-10-11
**Baseline:** [`PHASE_1_BASELINE.md`](./PHASE_1_BASELINE.md)

## Files added or changed

| Path | Purpose |
|---|---|
| `backend/src/security/__init__.py` | Public exports for the security module. |
| `backend/src/security/config.py` | Central configurable limits and supported upload extensions. |
| `backend/src/security/models.py` | Typed decisions, events, context, violations, and document metadata. |
| `backend/src/security/input_guard.py` | Query, document, upload, filename, content-type, and chunk-parameter validation. |
| `backend/src/security/injection_detector.py` | Source-aware heuristic detection for instruction override, secret disclosure, command execution, exfiltration, and security bypass. |
| `backend/src/security/document_guard.py` | SHA-256, untrusted trust label, findings, and non-destructive review status. |
| `backend/src/security/security_gateway.py` | Central orchestration and content-free structured security-event logging. |
| `backend/src/api/dependencies.py` | Shared gateway instance. |
| `backend/src/api/schemas.py` | Query and ingestion schema limits sourced from centralized security configuration. |
| `backend/src/api/routes/query.py` | Query guard and separate Gemini system instruction; retrieved chunks are JSON-encoded untrusted context. |
| `backend/src/api/routes/search.py` | Search-query guard. |
| `backend/src/api/routes/ingest.py` | Text/file guards, bounded upload read, and document metadata propagation. |
| `backend/.env.example` | Optional environment variables for security limits. |
| `backend/tests/security/` | 17 security unit and integration tests. |
| `docs/security/PHASE_0_REPOSITORY_AUDIT.md` | Pre-change repository audit. |
| `docs/security/PHASE_1_BASELINE.md` | Observed test and benchmark baseline. |

## Components and responsibilities

- `InputGuard`: rejects invalid, oversized, unsupported, or path-like inputs.
- `InjectionDetector`: distinguishes direct user input, retrieved documents, and system instructions; returns explainable decisions.
- `DocumentGuard`: hashes and classifies documents, marks every document `UNTRUSTED`, and flags suspicious documents for review without editing or deleting them.
- `SecurityGateway`: routes checks, returns typed decisions, and logs event identifiers and rule outcomes without logging user/document text.
- Generation boundary: retrieved context is serialized as JSON and sent separately from Gemini's `system_instruction`; the instruction explicitly treats context as untrusted data.

## Validation results

- Security tests: **17 passed**, 0 failed.
- Full backend suite: **56 passed**, 0 failed, 0 skipped.
- Existing test baseline: **39 passed**; all remain passing, with no observed regression.
- Warnings: existing Starlette `TestClient` deprecation and a Google GenAI/Python deprecation warning.
- `git diff --check`: passed.
- Workspace diagnostics: no errors reported for changed Python source/tests.

The unchanged retrieval experiment suite was also rerun: all four configurations retained 100% Recall@K and 100% accuracy proxy on the existing 5-query dataset. The harness reported 94.1% latency reduction and 94.7% estimated energy reduction for EcoRAG Adaptive versus Baseline Heavy in that run. These latency/energy figures are estimated and run-dependent, not physical measurements.

## Security limitations

- Injection detection is heuristic and must not be treated as a complete prompt-injection or malware detector.
- Separate system-instruction channels and JSON data encoding improve the trust boundary but cannot guarantee that a generative model will always ignore hostile content.
- No authentication, authorization, rate limiting, SSRF policy, tool policy, secret-output scanner, anomaly detection, or approval workflow is implemented.
- Upload validation checks configured size, filename, extension, and declared content type; it does not perform file-signature validation or antivirus scanning.
- Security metadata is attached to in-memory indexed chunks; a durable document registry and tamper-resistant audit store are not implemented.
- No production security certification is claimed.

## Next phase

The Phase 2 acceptance checks pass, so development can proceed to **Phase 3 — Authentication, Authorization, and Tool Security**. Treat the current gateway as a foundation only; EcoRAG is not production-secure until the limitations above are addressed and independently tested.

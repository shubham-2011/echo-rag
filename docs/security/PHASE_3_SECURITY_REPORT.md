# Phase 3 — Authentication, Authorization, and Resource Security

**Status:** Implemented; measured results and limitations below.

## Implemented controls

### Authentication and tenant authorization

- Protected query and search routes require `read`; text and file ingestion require `write`.
- Local single-user deployments can use `ECORAG_API_KEY`. Multi-user deployments can configure up to 100 distinct identities with `ECORAG_API_KEYS_JSON`; each identity has a validated subject and explicit scopes.
- Keys must be at least 32 characters, are compared with `hmac.compare_digest`, and are never written to logs. Invalid authentication configuration fails closed with `503`, invalid/missing credentials with `401`, and insufficient scopes with `403`.
- Invalid-credential attempts are rate-limited per remote client address. Authenticated requests have per-subject request and concurrency limits.
- FAISS indexes, BM25 indexes, exact/semantic caches, and ingestion counts are tenant-scoped. Retrieval methods require an owner; there is no unscoped application-level retriever or aggregate document index. Parent-document IDs are namespaced by tenant.
- Public health remains available for liveness but omits aggregate indexed-document counts.
- No audit or experiment HTTP endpoints exist in the current API. Any future endpoints must add explicit scopes and tenant authorization before being exposed.

### Resource and content controls

- ASGI middleware caps declared and streamed request-body bytes. Upload reads are bounded; file size, filename, type, extension, text size, and chunk parameters are validated.
- Parser work has a concurrency cap and timeout. A timed-out parser thread is not forcibly killed; its slot remains occupied until it exits, and any late parser exception is logged by type.
- Query, search, ingestion, unauthenticated-auth attempts, operation concurrency, and model calls are bounded by configurable limits. Gemini generation and embeddings use the configured network timeout; provider errors are surfaced rather than returned as success-shaped fallback answers.
- Suspicious documents are retained as `UNTRUSTED` and marked for review. Generation keeps retrieved data JSON-encoded and separate from the system instruction.
- Tool policy remains default-deny and authorizes names only; no tools or commands are executed.
- The WPF client attaches its configured bearer key and surfaces HTTP errors. Both Compose configurations pass through multi-user credentials and Phase 3 security limits.

## Validation results

- Security suite: **37 passed**, with two dependency deprecation warnings.
- Full backend suite: **76 passed**, with the same two warnings.
- The command-execution detector now catches “execute the script” while a regression test confirms benign discussion of running a command remains allowed.
- Cross-tenant tests exercise adaptive, dense, sparse, and hybrid retrieval, exact-cache isolation, namespaced parent expansion, and the public health response.
- The PDF integration test verifies an embedded injection is retained as untrusted and flagged for review.
- Unchanged five-query retrieval benchmark, run from `backend/`: all four configurations retained 100% Recall@K and accuracy proxy. EcoRAG Adaptive measured 55.1 ms and estimated 0.613 mWh/query versus Baseline Heavy at 1521.9 ms and 19.023 mWh/query (96.4% latency and 96.8% estimated-energy reduction). These figures are small-dataset, run-dependent estimates, not physical energy measurements.
- Security-overhead microbenchmark (`--iterations 100`): 4,000 checks across 34 direct inputs and 6 retrieved-document samples. Mean incremental gateway time was **0.028447 ms/check** against a no-op baseline, with an observed process RSS increase of **0.102 MB**. It rejected 1,900/3,400 direct inputs (**55.88%**) and flagged 500/600 retrieved documents (**83.33%**) for review. Incremental energy was estimated at **0.00142235 Wh** using an assumed 45 W; this is not a physical measurement.
- A dependency vulnerability scan was **not completed**: `pip-audit` is not installed in the available Python environments. No claim is made that the dependency set is vulnerability-free.

## Residual risks and operational limits

- Injection scanning is heuristic and is not a malware scanner or a guarantee against direct, indirect, encoded, multilingual, or model-mediated attacks.
- Parsing is bounded by a thread/semaphore timeout, not an isolated worker process. A wedged native parser can keep a slot occupied until it exits.
- Tenant indexes, document content, parent-document storage, concurrency counters, and rate-limit windows are in-process memory. They are neither durable nor coordinated across workers; multi-worker deployment can cause inconsistent retrieval and per-process quota multiplication.
- API keys are configured through environment variables, without a secret manager, rotation endpoint, expiry, or revocation service. Key changes require updating deployment configuration; keep the API on loopback or behind trusted TLS.
- The public liveness endpoint exposes basic model metadata, but not cross-tenant document counts. Security events are application logs, not a durable, tamper-resistant audit ledger.
- The adversarial set is a small regression fixture, not a broad red-team evaluation. The five-query retrieval benchmark is also only a smoke test.
- The gateway-overhead figure is an in-process microbenchmark on short fixture strings, not end-to-end API latency; its 45 W energy value is an estimate, not a physical measurement.
- No production-readiness or security-certification claim is made.

## Incident handling

See [Incident response procedure](./INCIDENT_RESPONSE.md) for containment, evidence handling, key revocation, recovery, and follow-up steps.

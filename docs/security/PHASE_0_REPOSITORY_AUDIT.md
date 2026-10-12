# Phase 0 — Repository Security Audit

**Captured:** 2026-10-11
**Repository revision:** `fc55e7169ae6adfd9e8eb3c24704e46f0764c129`
**Scope:** This EcoRAG checkout, with focus on `backend/src/` and `backend/tests/`.

## Repository facts

- Backend: FastAPI/Pydantic application under `backend/src/api/`.
- Query and search routes are `POST /api/query` and `POST /api/search`.
- Text and multipart document ingestion are `POST /api/ingest/text` and `POST /api/ingest/file`.
- The query pipeline retrieves chunks and passes their text to answer generation.
- `Chunk.metadata` and the ingestion pipeline already support document metadata propagation.
- Pydantic request schemas already constrain some text, chunk, top-K, and generation parameters.
- File upload previously read the complete upload without an application-level size limit or filename/extension validation.
- No `backend/src/security/` module, security gateway, injection detector, or security-specific test directory existed at this revision.

## Existing boundary controls

- Pydantic returns validation errors for malformed JSON fields and constrained request parameters.
- Text ingestion had a 5,000,000-character maximum.
- Search/query modes and empty inputs have route-level checks.
- CORS origins are configured separately from the security work.

## Security gaps observed

1. No unified typed security decision, event, or context model.
2. No shared configurable guard for query/document lengths, file sizes, filenames, or ingestion parameters.
3. Retrieved text was interpolated into a generation prompt without explicit untrusted-data boundaries.
4. No prompt-injection signal or source distinction for direct input, retrieved documents, and system instructions.
5. Documents had no content hash, trust label, scan status, or scan findings.
6. No security-focused unit or API tests.

## Scope and preservation

This phase adds a small gateway at the existing API boundaries. Retrieval, ranking, embedding, chunking algorithms, reranking, context compression, and experiment scoring are intentionally unchanged. The current `backend/benchmarks/data/qa_benchmark.json` is a five-query JSON benchmark; the shared-chat reference to a missing 22-question PDF does not describe a missing fixture in this checkout.

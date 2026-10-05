# EcoRAG Desktop Application — Knowledge Base

This folder serves as the permanent knowledge base for the **EcoRAG Desktop Application** project. It contains research links, complete verbatim conversation transcripts, architecture decisions, backend audits, and audit prompts.

---

## Knowledge Index

| Document | Purpose |
|---|---|
| [backend_audit.md](file:///d:/Program/C%23/ECORAG%20desktop%20application/knowledge/backend_audit.md) | **Technical Audit of the Python EcoRAG Backend** (`d:\Program\Python\Echo Rag`), API endpoints, test suite results, and integration mapping. |
| [links.md](file:///d:/Program/C%23/ECORAG%20desktop%20application/knowledge/links.md) | Archived research links, source conversation URLs, and references. |
| [chatgpt_conversation_transcript.md](file:///d:/Program/C%23/ECORAG%20desktop%20application/knowledge/chatgpt_conversation_transcript.md) | Complete Verbatim Transcript of the Desktop App Audit chat ([`chatgpt.com/share/6ab1985a...`](https://chatgpt.com/share/6ab1985a-c41c-83e9-b51b-8be4562768a9)). |
| [ecorag_backend_transcript.md](file:///d:/Program/C%23/ECORAG%20desktop%20application/knowledge/ecorag_backend_transcript.md) | Complete Verbatim Transcript of the EcoRAG Backend chat ([`chatgpt.com/share/6ab18f6d...`](https://chatgpt.com/share/6ab18f6d-8e1c-83ee-9c04-d77ac8f0e36b)). |
| [desktop_app_architecture_audit.md](file:///d:/Program/C%23/ECORAG%20desktop%20application/knowledge/desktop_app_architecture_audit.md) | Comprehensive software design audit, WinUI 3 rationale, client-server boundary, MVVM layout, and pre-development checklist. |
| [analysis_prompts.md](file:///d:/Program/C%23/ECORAG%20desktop%20application/knowledge/analysis_prompts.md) | Ready-to-use prompts for AI coding agents to audit desktop technology, existing conversations, and complete software design. |
| [ecorag_backend_context.md](file:///d:/Program/C%23/ECORAG%20desktop%20application/knowledge/ecorag_backend_context.md) | Technical overview of the EcoRAG FastAPI backend, `@measure_energy` telemetry, and API contract. |
| [ui_ux_iris_redesign.md](ui_ux_iris_redesign.md) | UI/UX audit of the WPF client and the Iris color persona, layout, and files changed on 2026-10-03. |
| [../docs/12_implementation_plan.md](../../docs/12_implementation_plan.md) | Backend + desktop plan to persist the index, label estimated energy, run experiments, and finish the audit layer. |
| [../../docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md) | Authoritative live architecture (FastAPI, FAISS persistence, audit, desktop). |
| [platform_architecture_and_audit.md](platform_architecture_and_audit.md) | Feature audit matrix, run/demo commands, and changelog for persistence + telemetry labels. |
| [blockchain_audit_test_plan.md](blockchain_audit_test_plan.md) | Full blockchain audit test plan (objectives, BC-* cases, acceptance criteria). |
| [blockchain_test_traceability.md](blockchain_test_traceability.md) | Maps plan IDs to pytest; release checklist status. |
| [rag_observability_logging_spec.md](rag_observability_logging_spec.md) | Parts 25–28: request_id tracing, log tags, fallback audit, trace test, acceptance queries. |
| [ecorag_audit_solidity_security_audit.md](ecorag_audit_solidity_security_audit.md) | Pre-deploy Solidity audit for `EcoRAGAudit.sol` (commitments, access control, verification). |
| [live_bug_company_name_investigation.md](live_bug_company_name_investigation.md) | Live UI: wrong architecture answer, empty sources, 97.5 J vs 46.0 J. |
| [synoptek_pdf_smoke_benchmark.md](synoptek_pdf_smoke_benchmark.md) | 20-question smoke test vs the Synoptek intern PDF (18/22 live). |

---

## Core Project Summary
- **Client**: Native C# / .NET 10 Desktop Application built with WPF Fluent Design and MVVM (`d:\Program\C#\ECORAG desktop application`).
- **Backend**: EcoRAG Python FastAPI backend (`d:\Program\Python\Echo Rag`) with FAISS vector store, BM25 sparse index, BGE reranker, and two-tier semantic caching.
- **Test Status**: Backend verified with 31/31 passing tests (100%).

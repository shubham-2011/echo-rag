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

---

## Core Project Summary
- **Client**: Native C# / .NET 10 Desktop Application built with WPF Fluent Design and MVVM (`d:\Program\C#\ECORAG desktop application`).
- **Backend**: EcoRAG Python FastAPI backend (`d:\Program\Python\Echo Rag`) with FAISS vector store, BM25 sparse index, BGE reranker, and two-tier semantic caching.
- **Test Status**: Backend verified with 31/31 passing tests (100%).

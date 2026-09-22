# Research Links & References

This file archives the foundational project discussions, shared chat sessions, and architectural references for the **EcoRAG Desktop Application**.

---

## Primary Shared Conversations

### 1. Desktop Application Architecture, Technology Audit & Software Design
- **URL**: [https://chatgpt.com/share/6ab1985a-c41c-83e9-b51b-8be4562768a9](https://chatgpt.com/share/6ab1985a-c41c-83e9-b51b-8be4562768a9)
- **Title**: Audit Desktop App Languages & Complete Software Design
- **Key Focus Areas**:
  - Comparison of desktop frameworks: **C# (.NET / WinUI 3 / WPF)**, **Tauri + React**, **Electron + React**, **JavaFX**, **Python + PySide6**, **Qt + C++**.
  - Visual Studio 2022 setup: Selecting **Blank App, Packaged (WinUI 3 in Desktop)** under Windows App SDK.
  - Software Design & System Architecture: Client-Server boundaries, treating desktop as an untrusted client, MVVM design pattern, API contracts, local storage vs. server database.
  - 20-Phase & 37-Point Software Design Framework for enterprise desktop applications.

---

### 2. EcoRAG Platform, FastAPI Backend & Energy Telemetry
- **URL**: [https://chatgpt.com/share/6ab18f6d-8e1c-83ee-9c04-d77ac8f0e36b](https://chatgpt.com/share/6ab18f6d-8e1c-83ee-9c04-d77ac8f0e36b)
- **Title**: EcoRAG Platform Architecture, Energy Optimization & FastAPI Backend
- **Key Focus Areas**:
  - EcoRAG Core: Energy-Efficient Retrieval-Augmented Generation experimentation & benchmarking platform.
  - Telemetry & Measurements: `@measure_energy` decorator, Joules/Wh estimation for local and cloud models, token efficiency, latency, and FLOPs proxy calculations.
  - Ingestion & Vector Pipeline: Document parsing, cleaning, chunking, deduplication, FAISS vector search, and BGE reranking.
  - FastAPI backend endpoints, testing strategies, and API test prompts.

### 3. EcoRAG Systems Research, Benchmarking & QA Evaluation Blueprint
- **URL**: [https://chatgpt.com/share/6ab1a7c5-9a44-83ee-9a18-c9a1ec5fd285](https://chatgpt.com/share/6ab1a7c5-9a44-83ee-9a18-c9a1ec5fd285)
- **Title**: Systems Research, Benchmarking, QA Test Suite & Implementation Blueprint
- **Key Focus Areas**:
  - Critical scientific corrections: Chunk size vs. prompt context tokens, quadratic attention ratio ($\mathcal{O}(N^2)$), and Top-K compensation analysis.
  - Empirically calibrated out-of-domain abstention thresholds (avoiding arbitrary hardcoded cutoffs).
  - Strict 4-tier energy classification: `MEASURED`, `ESTIMATED`, `CALCULATED`, and `UNAVAILABLE`.
  - Comprehensive 5-Category RAG quality evaluation dataset and execution verification.

---

## Local Knowledge & Artifact References

- `knowledge/desktop_app_architecture_audit.md`: Full architectural analysis and synthesis of the conversation.
- `knowledge/analysis_prompts.md`: Reusable prompts for AI coding agents (Antigravity, Claude, ChatGPT) to audit technology, APIs, and features.
- `knowledge/ecorag_backend_context.md`: Technical summary of the EcoRAG backend services that the desktop app connects to.
- `knowledge/ecorag_research_qa_transcript.md`: Complete verbatim transcript of the research and QA blueprint conversation.


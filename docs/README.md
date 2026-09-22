# EcoRAG: Energy-Efficient Retrieval-Augmented Generation Knowledge Base

Welcome to the **EcoRAG Knowledge Base**. This repository of documentation captures the architectural principles, optimization strategies, benchmarking methodologies, and system designs gathered from the comprehensive EcoRAG research specification and audit.

---

## 🎯 Executive Summary & Mission

Standard Retrieval-Augmented Generation (RAG) pipelines follow a brute-force pattern: **retrieve $K$ large document chunks, stuff them into an LLM context window, and generate an answer**. While this often achieves high answer quality, it incurs massive penalties in:
- **Compute and GPU Wattage** (dominated by quadratic LLM attention over thousands of irrelevant context tokens)
- **Latency and Throughput Bottlenecks**
- **RAM / VRAM Memory Footprints**
- **Financial Cost per Successful Answer**

**EcoRAG** frames RAG as a **multi-objective optimization problem**:
> **Core Objective:** *Minimize energy, compute, latency, memory, and financial cost while maintaining an acceptable, verifiable threshold of retrieval quality and answer correctness.*

Instead of a static pipeline, EcoRAG introduces an **adaptive, energy-aware architecture**:
```
User Query ──► Query Classifier ──► Adaptive Retrieval ──► Context Compression ──► Model Cascade ──► Telemetry & Feedback
```

---

## 📚 Knowledge Base Structure

| Document | Title | Description |
| :--- | :--- | :--- |
| [ecorag_complete_findings.md](file:///d:/Program/Python/Echo%20Rag/knowledge/ecorag_complete_findings.md) | **Master Research Findings & Spec** | **Complete All-in-One Master Guide:** All architectural findings, formulas, 5-layer optimizations, and metrics. |
| [01_ecorag_foundations.md](file:///d:/Program/Python/Echo%20Rag/knowledge/01_ecorag_foundations.md) | **EcoRAG Foundations** | Contrast with standard RAG, core philosophy, and the 7 experimental dimensions. |
| [02_energy_resource_audit.md](file:///d:/Program/Python/Echo%20Rag/knowledge/02_energy_resource_audit.md) | **Energy & Resource Audit** | Detailed breakdown of where power, compute, and memory are consumed across offline and online phases. |
| [03_optimization_strategies.md](file:///d:/Program/Python/Echo%20Rag/knowledge/03_optimization_strategies.md) | **Optimization Strategies** | In-depth audit of context compression, dynamic context, multi-tier caching, selective reranking, and query routing. |
| [04_system_architecture.md](file:///d:/Program/Python/Echo%20Rag/knowledge/04_system_architecture.md) | **System Architecture** | Component diagrams, adaptive query flow, ingestion pipelines, and the Experiment Manager harness. |
| [05_evaluation_metrics_and_eco_score.md](file:///d:/Program/Python/Echo%20Rag/knowledge/05_evaluation_metrics_and_eco_score.md) | **Evaluation Metrics & Eco Score** | Retrieval recall, generation quality (faithfulness/relevance), latency, RAM, energy measurement (Wh), cost, and composite Eco Score formulations. |
| [06_experiment_matrix_and_tech_stack.md](file:///d:/Program/Python/Echo%20Rag/knowledge/06_experiment_matrix_and_tech_stack.md) | **Experiment Matrix & Tech Stack** | Combinatorial matrix pruning, recommended Python/FastAPI/FAISS/Ollama stack, telemetry tools, and development roadmap. |
| [07_raw_conversation_transcript.md](file:///d:/Program/Python/Echo%20Rag/knowledge/07_raw_conversation_transcript.md) | **Raw Conversation Transcript** | Verbatim transcript of the original ChatGPT shared session (`6ab17960-c178-83e8-b557-3b4bc476942e`). |
| [08_further_research_and_prompts.md](file:///d:/Program/Python/Echo%20Rag/knowledge/08_further_research_and_prompts.md) | **Further Research & Prompts Guide** | Saved research link, project audit checklist, and 6 ready-to-use prompt templates for coding and evaluation. |
| [09_gemini_embedding_integration.md](file:///d:/Program/Python/Echo%20Rag/knowledge/09_gemini_embedding_integration.md) | **Gemini Embeddings Integration** | Implementation guide for Gemini embeddings (3072d), API key security, and trade-off analysis vs local models. |
| [10_gpt_research_prompts_and_audit.md](file:///d:/Program/Python/Echo%20Rag/knowledge/10_gpt_research_prompts_and_audit.md) | **GPT Research & Investigation Guide** | 5 targeted, deep-dive academic and architectural prompt suites designed specifically to run in ChatGPT. |
| [11_fastapi_testing_and_gpt_prompts.md](file:///d:/Program/Python/Echo%20Rag/knowledge/11_fastapi_testing_and_gpt_prompts.md) | **FastAPI Testing & GPT Audit Prompts** | Master prompt suites to generate test cases, analyze test logs, stress-test concurrency, and audit API security via GPT. |
| [fastapi_audit_report.md](file:///d:/Program/Python/Echo%20Rag/knowledge/fastapi_audit_report.md) | **EcoRAG FastAPI Technical Audit Report** | Complete 15-section senior engineer audit report with empirical metrics, bug analyses, and ranked action items. |

---

## 🔬 Core Research Question

> **"How can RAG systems dynamically select retrieval, context, model, and caching strategies to minimize energy and resource consumption while maintaining answer quality?"**

### Normal RAG vs. EcoRAG

* **Normal RAG:** `User Query ──► Retrieve Top-K Chunks ──► Concatenate All ──► Giant LLM ──► Output`
* **EcoRAG:** `User Query ──► Analyze Query Complexity ──► Choose Cheapest Sufficient Strategy ──► Filter/Compress Context ──► Right-Sized Model ──► Measure Energy/Tokens ──► Continuous Telemetry`

---

## ⚡ Quick Metrics Checklist

For every experimental run or query served, EcoRAG tracks:
1. **Retrieval Quality**: Hit Rate@K, Recall@K, MRR@K
2. **Answer Correctness**: Semantic Similarity, Faithfulness / Hallucination Rate, RAGAS/BERTScore
3. **Latency**: Time-to-First-Token (TTFT), End-to-End Latency (seconds)
4. **RAM & VRAM**: Peak process memory footprint (GB)
5. **Energy Consumption**: Active Watt-hours (Wh) via CodeCarbon, PyJoules, Intel RAPL, or NVIDIA NVML
6. **Cost per Successful Answer**: Currency ($ / ₹) factoring in compute watts and API token pricing

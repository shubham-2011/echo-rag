# 03. Comprehensive EcoRAG Optimization Strategies

This document provides a systematic guide to the optimization strategies that transform standard RAG into an energy-efficient, adaptive architecture. These strategies are structured into **5 distinct Optimization Layers**.

---

## The 5 Optimization Layers Overview

```
┌────────────────────────────────────────────────────────────────────────┐
│                        THE 5 OPTIMIZATION LAYERS                       │
├────────────────────┬───────────────────────────────────────────────────┤
│ Layer 1: Retrieval │ Selective hybrid, thresholding, deduplication     │
│ Layer 2: Context   │ Compression, dynamic sizing, sentence extraction  │
│ Layer 3: Compute   │ Model cascading, quantization, local execution    │
│ Layer 4: Reuse     │ Exact hash, semantic, embedding & retrieval cache │
│ Layer 5: Telemetry │ Per-query Joules/Wh, TTFT, multi-objective score  │
└────────────────────┴───────────────────────────────────────────────────┘
```

---

## Layer 1: Retrieval Efficiency

### 1.1. Optimize Retrieval Before Invoking a Reranker
- Standard pipelines pull Top-20 chunks and feed all 20 to a heavy cross-encoder.
- **EcoRAG Solution:** Improve the quality of the first-stage retriever (e.g., hybrid dense + BM25) and reduce the candidate pool to Top-5 or Top-8 before reranking.
- **Conditional / Threshold-Based Reranking:**
  - If the top vector similarity score exceeds a high confidence threshold (e.g., $\text{Score}_{\text{top1}} \ge 0.88$ and $\text{Score}_{\text{top1}} - \text{Score}_{\text{top2}} \ge 0.15$), **bypass the reranker entirely**.
  - Only fire the computationally expensive cross-encoder when retriever confidence is ambiguous or spread evenly across multiple documents.

### 1.2. Chunk Deduplication
- Multiple documents or versions often share identical or nearly identical paragraphs.
- Indexing duplicate chunks wastes vector memory and results in redundant context chunks occupying valuable LLM prompt slots.
- **Strategy:** Calculate MinHash / LSH or exact SHA-256 hashes of text chunks during ingestion; suppress near-duplicate embeddings.

### 1.3. Selective Hybrid Retrieval (Adaptive Retrieval)
- Keyword-specific queries (e.g., exact part numbers, function names, error codes, dates) achieve 100% recall with **pure BM25**.
- BM25 requires **zero GPU/neural compute** at runtime!
- Only invoke dense vector embeddings when the query exhibits conceptual, semantic, or conversational phrasing.

---

## Layer 2: Context Efficiency (The Highest Leverage Area)

Since prompt tokens scale LLM prefill energy quadratically ($O(N^2)$), minimizing unnecessary context delivered to the generator is the single most effective optimization.

### 2.1. Dynamic Context Sizing (Cutoff Thresholds vs. Static Top-K)
- **Standard RAG:** Always sends static $K=5$ chunks (e.g., $5 \times 400 = 2,000$ tokens).
- **EcoRAG Dynamic Context:**
  - Retrieve chunks above an absolute relevance score $\theta_{\text{min}}$.
  - If only 1 chunk exceeds $\theta_{\text{min}}$, pass **only that single chunk** (400 tokens).
  - Energy saved: $\approx 75\%$ reduction in prefill compute.

### 2.2. Context Compression & Sentence Filtering
- A 500-token chunk often contains only 1 or 2 sentences directly answering the user's question; the remaining 400+ tokens are filler narrative.
- **Techniques:**
  - **Sentence-Level Scoring:** Split retrieved chunks into individual sentences and retain only the top 3–5 most similar sentences to the query.
  - **Extractive Compression (e.g., LLMLingua / Compact Prompting):** Strip low-perplexity tokens and non-informative filler before LLM ingestion.

---

## Layer 3: Computation & Model Efficiency

### 3.1. Query Routing & Model Cascades (Small LLM vs. Large LLM)
Not all user requests require a massive 70B parameter model.
- **Tier 1 (Trivial / Factoid Queries):** Route to a lightweight, quantized local model (e.g., 3B or 7B parameter model like Llama-3-8B-Instruct or Qwen2.5-3B).
- **Tier 2 (Complex / Multi-Hop Reasoning):** Route to a larger model (e.g., 70B or frontier cloud API) only when the query analyzer flags multi-step reasoning or high synthesis requirements.

```
                           Incoming Query
                                 │
                                 ▼
                         Query Classifier
                                 │
                 ┌───────────────┴───────────────┐
                 ▼                               ▼
       Low/Medium Complexity             High Complexity
                 │                               │
                 ▼                               ▼
         Lightweight LLM                    Frontier LLM
         (3B / 7B Model)                 (70B+ / Cloud API)
     [~0.5 Wh, 200ms TTFT]             [~4.5 Wh, 1500ms TTFT]
```

### 3.2. Model Quantization
- **Weights Quantization:** Run local LLMs and cross-encoders using 4-bit or 8-bit precision (AWQ, GPTQ, or GGUF Q4_K_M).
- **Benefits:**
  - 50%–75% reduction in VRAM / RAM consumption.
  - Memory bandwidth reduction directly translates to lower active wattage during autoregressive decoding.
- **Vector Quantization:** Use Scalar Quantization (SQ8) or Product Quantization (PQ) in FAISS to cut index memory footprint by 4× with negligible drop in recall.

### 3.3. Constrained Token Generation
- Direct the system prompt to enforce concise, information-dense answers:
  > *"Answer directly and concisely in 2–3 sentences. Avoid preamble, repetition, or conversational filler."*
- Set a strict `max_new_tokens` ceiling (e.g., 150 tokens instead of 2048 tokens).
- Autoregressive generation consumes energy linearly with every single generated token.

---

## Layer 4: Reuse & Multi-Tier Caching

Caching turns recurring computation into near-zero-energy memory lookups.

```
Incoming Query
     │
     ▼
[ Exact Hash Cache ] ──────────────► Hit: Return Answer (0.001 Wh, < 2ms)
     │ Miss
     ▼
[ Semantic Cache (Cosine >= 0.92) ] ► Hit: Return Answer (0.02 Wh, < 20ms)
     │ Miss
     ▼
[ Embedding Cache ] ───────────────► Hit: Reuse Query Vector (Skip Encoder)
     │ Miss: Generate Vector
     ▼
[ Retrieval Cache ] ───────────────► Hit: Reuse Chunk IDs (Skip Vector DB)
     │ Miss: Search DB
     ▼
[ LLM Generation Pipeline ]
```

1. **Exact Query Cache (Tier 1):**
   - Key: `hash(user_query + system_prompt)`
   - Value: Generated answer + citations
   - Latency: < 1ms | Energy: ~0.0001 Wh
2. **Semantic Cache (Tier 2):**
   - Compares the query embedding against a cache vector index of past queries.
   - If cosine similarity $\ge 0.92$, return the cached response.
   - Saves 100% of LLM prefill and generation energy.
3. **Embedding Cache (Tier 3):**
   - Caches query vectors for common phrases or repetitive sub-queries.
4. **Retrieval Cache (Tier 4):**
   - If the exact or near-identical question was asked, reuse the retrieved document set without re-executing search or reranking.

---

## Layer 5: Telemetry & Measurement Loop

Optimization cannot happen without continuous measurement:
- Track active Joules and Watt-hours for every pipeline stage.
- Relate energy spent directly to answer correctness.
- Compute the **Energy-to-Correctness Efficiency Ratio**.

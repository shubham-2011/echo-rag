# 02. Energy & Resource Audit for RAG Systems

To optimize RAG for environmental sustainability and cost-efficiency, we must conduct a granular physical audit of where computational cycles, memory bandwidth, and electrical wattage are expended.

---

## 1. The Energy Consumption Breakdown

In a standard RAG pipeline serving user queries, energy consumption is distributed across distinct stages:

```
┌────────────────────────────────────────────────────────────────────────┐
│               TYPICAL RAG QUERY ENERGY DISTRIBUTION                    │
├──────────────────────────────────────┬─────────────────────────────────┤
│ Stage                                │ % of Total Query Energy         │
├──────────────────────────────────────┼─────────────────────────────────┤
│ 1. LLM Generation (Autoregressive)   │ 60% – 75%                       │
│ 2. LLM Prompt Processing (Prefill)   │ 15% – 25%                       │
│ 3. Cross-Encoder Reranking           │ 5% – 15%                        │
│ 4. Query Embedding Inference         │ 2% – 5%                         │
│ 5. Vector Index Search               │ < 1%                            │
│ 6. App Logic, Parsing & Network      │ < 1%                            │
└──────────────────────────────────────┴─────────────────────────────────┘
```

> [!IMPORTANT]
> **Key Takeaway:** The **LLM is the overwhelming energy sink** (80%–95% of total query power when combining prompt processing and generation). Any architectural decision that reduces the **number of prompt tokens**, the **number of generated tokens**, or **bypasses the LLM entirely** yields exponential energy savings.

---

## 2. Granular Stage-by-Stage Resource Profile

### 2.1. The LLM Stage: Quadratic Attention & Token Costs
The computational complexity of Transformer-based LLMs manifests in two phases:
1. **Prefill (Prompt Processing):**
   - The LLM processes all tokens in the system prompt, retrieved context chunks, and user question simultaneously.
   - Attention computational complexity scales with the context length $N$ as $\mathcal{O}(N^2)$.
   - Doubling the retrieved context from 2,000 tokens to 4,000 tokens roughly **quadruples** the self-attention matrix operations during prefill!
2. **Decode (Autoregressive Generation):**
   - The model generates one token at a time.
   - Memory bandwidth bound: At each new token, the model must read all parameters from VRAM (or RAM) and maintain the Key-Value (KV) cache.
   - A verbose response (e.g., 500 tokens) consumes 5× the energy of a concise, dense response (e.g., 100 tokens).

### 2.2. Cross-Encoder Reranking
While standard bi-encoder retrieval independently embeds the query and compares vectors via dot-product, a **cross-encoder reranker** feeds `(Query, Chunk)` concatenated pairs through a transformer model.
- If the vector retriever retrieves $K = 20$ candidate chunks, the cross-encoder must perform **20 full forward passes** of a multi-layer transformer!
- On a CPU or lower-tier GPU, reranking 20 chunks can draw 50–150 Watts for several seconds, completely negating the speed of fast vector search.

### 2.3. Query Embedding Generation
- Before searching the vector database, the incoming query string must be transformed into a dense vector using the embedding model (e.g., BGE-small, E5).
- A 384-dimensional model (`bge-small-en-v1.5`) takes ~5–15ms and draws minimal power.
- A 1024-dimensional model (`bge-large-en-v1.5`) requires roughly 8× more FLOPs and substantial VRAM allocation.

### 2.4. Vector Index Similarity Search
- Modern vector indexes (like FAISS HNSW or FlatIP) are extremely fast and efficient (often sub-millisecond to 5ms for tens of thousands of chunks).
- While CPU/RAM intensive, vector search itself contributes less than 1% to the overall per-query energy consumption.

---

## 3. Offline vs. Online Energy Footprints

A rigorous EcoRAG audit separates the lifecycle into two operational regimes:

```
               ┌──────────────────────────────────────────────┐
               │              RAG ENERGY LIFECYCLE            │
               └──────────────────────┬───────────────────────┘
                                      │
            ┌─────────────────────────┴─────────────────────────┐
            ▼                                                   ▼
   ┌──────────────────┐                                ┌──────────────────┐
   │  OFFLINE PHASE   │                                │   ONLINE PHASE   │
   │ (Ingestion/Build)│                                │ (Per User Query) │
   └────────┬─────────┘                                └────────┬─────────┘
            │                                                   │
  • Document parsing & OCR                            • Query embedding
  • Text chunking                                     • Vector similarity search
  • Embedding model inference                         • Cross-encoder rerank
  • Vector index construction                         • LLM prompt prefill (O(N²))
  • Index quantization / clustering                   • LLM autoregressive decode
```

### Offline Ingestion: The Fixed Sunk Cost
- Computing embeddings for 100,000 document chunks using a heavy model can consume hours of sustained 250W GPU compute (kilowatt-hours of energy).
- **Optimization Strategy:**
  - Chunk deduplication: Avoid embedding duplicate paragraphs or boilerplates.
  - Chunk size trade-off: Larger chunks produce fewer vectors, reducing total embedding forward passes.
  - Model selection: A lighter embedding model saves massive energy during large-scale re-indexing.

### Online Query Serving: The Recurring Operational Burden
- Runs for every single query over the lifetime of the application.
- In high-throughput production systems serving millions of queries, online energy rapidly surpasses offline indexing energy by orders of magnitude.
- **Optimization Strategy:**
  - Zero-compute query routing (skip retrieval if LLM internal knowledge or cache suffices).
  - Semantic caching to completely skip computation for similar intents.
  - Aggressive context compression to minimize LLM prefill tokens.

---

## 4. Hardware Telemetry & Measurement Points

To accurately quantify resources, an EcoRAG system must tap into physical hardware counters:

| Metric | Measurement Tool / API | Unit |
| :--- | :--- | :--- |
| **System Wall Energy** | CodeCarbon / PyJoules / Scaphandre | Watt-hours (Wh) / Joules (J) |
| **CPU Energy** | Intel Running Average Power Limit (RAPL) | Joules (J) |
| **GPU Power & Energy** | NVIDIA NVML (`pynvml` / `nvidia-smi`) | Watts (W) & Joules (J) |
| **RAM Footprint** | `psutil.Process().memory_info().rss` | Megabytes / Gigabytes (MB / GB) |
| **GPU VRAM** | `torch.cuda.memory_allocated()` | Megabytes / Gigabytes (MB / GB) |
| **Latency / TTFT** | High-precision timers (`time.perf_counter`) | Milliseconds / Seconds (ms / s) |
| **Token Volumes** | Tokenizer count (Input / Output / Context) | Integer token counts |

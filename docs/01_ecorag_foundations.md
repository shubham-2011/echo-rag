# 01. EcoRAG Foundations & Experimental Dimensions

## 1. What is Normal RAG?

Standard Retrieval-Augmented Generation (RAG) follows a standard sequence:

```
[ Documents ] ──► [ Fixed Chunker ] ──► [ Large Embedding Model ] ──► [ Vector Store ]
                                                                             │
[ User Query ] ─────────► [ Query Embedding ] ───────────────────────────────┘
                                   │
                                   ▼
                           [ Top-K Chunks ]
                                   │
                                   ▼
                [ LLM Prompt: System + Context + Query ]
                                   │
                                   ▼
                            [ Answer Text ]
```

In typical implementations, engineers prioritize **accuracy at all costs**:
- Oversized chunk windows (1024–2048 tokens).
- Top-$K$ values set high ($K=10$ or $K=20$) "just in case".
- Heavy cross-encoder rerankers invoked on every single request.
- Huge LLMs (70B+ parameters or expensive commercial API models).
- Zero query discrimination: a trivial greeting or direct factoid query executes the exact same compute-heavy retrieval and generation pipeline as a multi-step analytical synthesis.

---

## 2. What Makes EcoRAG Different?

**EcoRAG** is an **experimental, benchmarking, and adaptive architectural paradigm** where RAG configurations are treated as an engineering optimization space:

> **Core Axiom:** Find the point of **diminishing returns** where a dramatic decrease in computational resource consumption (compute, memory, wattage, latency, dollars) yields virtually identical or acceptable retrieval and answer accuracy.

Instead of asking *"What pipeline produces the highest accuracy?"*, EcoRAG asks:
> *"What pipeline delivers acceptable accuracy with the minimum physical resources, and how can the system dynamically adapt per query?"*

---

## 3. The Seven Core Experimental Dimensions

EcoRAG investigates 7 key pipeline knobs and measures their direct impact on both quality and energy consumption:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        THE 7 ECORAG DIMENSIONS                         │
├────────────────────┬───────────────────────────────────────────────────┤
│ 1. Chunk Size      │ 128 / 256 / 512 / 1024 / 2048 tokens              │
│ 2. Embeddings      │ Compact (384d) vs Medium (768d) vs Large (1536d+) │
│ 3. Vector DBs      │ In-Memory (FAISS) vs Embedded vs Standalone Server│
│ 4. Retrieval Mode  │ Sparse (BM25) vs Dense (Vector) vs Hybrid         │
│ 5. Rerankers       │ None vs Fast-Rank (Tiny) vs Cross-Encoder         │
│ 6. Cache Layers    │ No Cache vs Exact Query vs Embedding vs Semantic  │
│ 7. Context Window  │ Dynamic Context vs 1K / 2K / 4K / 8K / 16K        │
└────────────────────┴───────────────────────────────────────────────────┘
```

### 3.1. Chunk Size
- **Small Chunks (128 – 256 tokens):**
  - *Pros:* High semantic specificity; minimal irrelevant noise passed to LLM; lower LLM prompt token consumption; faster generation.
  - *Cons:* More total vectors to index, store, and search; potential loss of wider context/continuity across paragraph boundaries.
- **Medium Chunks (512 tokens):**
  - The industry default; provides reasonable balance for general expository prose.
- **Large Chunks (1024 – 2048 tokens):**
  - *Pros:* Preserves document narrative and complex structural context; fewer embeddings to compute during indexing.
  - *Cons:* Injects significant irrelevant filler into the LLM context; scales LLM quadratic attention overhead quadratically; increases TTFT (Time-to-First-Token) and wattage.

---

### 3.2. Embedding Models
The choice of embedding model dictates offline indexing energy, vector database memory, and online query embedding latency:
- **Compact Models (e.g., `all-MiniLM-L6-v2`, `bge-small-en-v1.5`):**
  - Dimensions: 384
  - Speed: Ultra-fast CPU/GPU inference (~10–20ms)
  - Memory: ~1.5 KB per vector
  - Energy: Negligible energy footprint per query
- **Medium Models (e.g., `bge-base-en-v1.5`, `e5-base-v2`):**
  - Dimensions: 768
  - Accuracy: Noticeably improved semantic nuance
  - Memory: ~3.0 KB per vector
- **Large Models (e.g., `bge-large-en-v1.5`, OpenAI `text-embedding-3-large`):**
  - Dimensions: 1024 to 3072
  - Accuracy: State-of-the-art semantic separation
  - Drawback: 4× to 8× vector memory footprint, higher compute per similarity check.

---

### 3.3. Vector Databases & Indexing Engines
How vectors are stored, indexed, and retrieved directly governs RAM and query latency:
- **In-Memory Flat/HNSW (e.g., FAISS IndexFlatIP, FAISS HNSW):**
  - High speed, zero network serialization latency, zero database daemon overhead.
  - Consumes active host RAM.
- **Embedded Document/Vector DBs (e.g., Chroma, DuckDB-vss, SQLite-vec):**
  - File-backed, lightweight, easy local lifecycle.
- **Dedicated Vector Servers (e.g., Qdrant, Milvus):**
  - Scales to millions of records, advanced filtering and payload management.
  - Background daemon consumes standing baseline idle memory and CPU cycles.

---

### 3.4. Retrieval Methods
- **Dense Retrieval (Bi-Encoder Vector Search):**
  - Excels at conceptual and semantic matching (paraphrases, high-level intent).
  - Requires embedding generation for every user query.
- **Sparse Retrieval (e.g., BM25, TF-IDF):**
  - Pure keyword inverted index.
  - Requires **zero neural embedding computation** at query time. Extremely fast, minimal CPU cost, highly effective for exact keyword lookups, part numbers, names, and error codes.
- **Hybrid Retrieval (Dense + Sparse Fusion, e.g., Reciprocal Rank Fusion / RRF):**
  - Combines semantic understanding with exact lexical matching.
  - Slightly more CPU compute to merge and score rank lists, but often achieves superior Recall@K.

---

### 3.5. Rerankers
- **No Reranker:** Top-$K$ items from the vector index are fed directly to the context. Minimal latency and lowest energy.
- **Cross-Encoder Rerankers (e.g., `bge-reranker-base`, `ms-marco-MiniLM-L-6-v2`):**
  - Deep attention between `(Query, Candidate_Document)` pairs.
  - Substantially boosts accuracy and relevance ranking.
  - **Major Energy Penalty:** Running a cross-encoder over 10–20 candidate chunks can take 200–800ms and consume more energy than the retrieval step itself!
- **Fast / Distilled Rerankers (e.g., FlashRank):**
  - Quantized, pruned models designed to deliver 80% of cross-encoder ranking gains with 10% of the compute.

---

### 3.6. Caching Strategies
Caching is the single highest-leverage green computing mechanism in RAG:
1. **No Cache:** Every request computes embeddings, searches index, reranks, and prompts the LLM from scratch.
2. **Exact Query / Response Cache:** Direct hash lookup (`SHA-256(query)`). Instant response (sub-millisecond), zero LLM invocation.
3. **Embedding Cache:** Reuses previously computed embeddings for frequent queries or terms.
4. **Retrieval Cache:** Reuses the retrieved chunk ID list for identical/similar query intents.
5. **Semantic Cache (e.g., GPTCache, Redis Vector Cache):**
   - Matches incoming queries based on cosine similarity to past queries ($\text{similarity} \ge 0.92$).
   - Completely bypasses downstream retrieval, reranking, and generation for repeated or near-identical questions.

---

### 3.7. Context-Window Sizes & Token Packing
The number of tokens delivered into the LLM prompt is the **primary cost and energy driver** of the entire system:
- **Fixed Large Windows (4K – 16K tokens):**
  - Increases prompt processing time; triggers quadratic self-attention FLOPs ($O(N^2)$); increases energy consumption linearly or super-linearly.
- **Dynamic Context Sizing:**
  - Injects only chunks that exceed a strict similarity/confidence threshold.
  - If 1 chunk is sufficient, pass only 1 chunk (~300 tokens) instead of blindly packing 5 chunks (~2000 tokens).

# 09. Gemini Embeddings Integration in EcoRAG

This document outlines the integration of Google's Gemini Embedding models into the EcoRAG platform using the modern `google.genai` SDK and the provided API credentials.

---

## 1. Integration Overview

The Gemini embedding service is implemented in [`src/embeddings.py`](file:///d:/Program/Python/Echo%20Rag/src/embeddings.py) and verified via [`examples/demo_gemini_embedding.py`](file:///d:/Program/Python/Echo%20Rag/examples/demo_gemini_embedding.py).

### Verified Available Models
Through direct API inspection with your key, the following embedding models are active:
- **`gemini-embedding-001`** (Default, 3072 dimensions): High semantic nuance and multilingual capability.
- **`gemini-embedding-2`** (Latest preview, 3072 dimensions): State-of-the-art representation model.

---

## 2. Security & Environment Configuration

To adhere to the Safe Credentials Protocol:
1. **Never Hardcoded:** The key is stored in [`.env`](file:///d:/Program/Python/Echo%20Rag/.env) as `GEMINI_API_KEY`.
2. **Git Ignored:** [`.gitignore`](file:///d:/Program/Python/Echo%20Rag/.gitignore) ensures `.env` is never committed to source control.
3. **Auto-Loaded:** `GeminiEmbeddingService` automatically parses `.env` on initialization using `python-dotenv`.

---

## 3. How to Use in Code

```python
from src.embeddings import GeminiEmbeddingService

# Initialize the service (loads GEMINI_API_KEY from .env)
service = GeminiEmbeddingService(model_name="gemini-embedding-001")

# 1. Embed a single string
query_vector = service.embed_text("How does EcoRAG optimize retrieval energy?")
print(f"Dimension: {len(query_vector)}")  # 3072

# 2. Embed a batch of document chunks
corpus = [
    "Chunk 1 text...",
    "Chunk 2 text...",
]
corpus_vectors = service.embed_batch(corpus)

# 3. Calculate Cosine Similarity
similarity = service.cosine_similarity(query_vector, corpus_vectors[0])
print(f"Similarity: {similarity:.4f}")
```

---

## 4. Role of Gemini Embeddings in the EcoRAG Trade-Off Matrix

In the EcoRAG experiment matrix, Gemini embeddings represent the **Cloud Frontier / High-Dimensional Baseline**:

```
┌─────────────────────────┬──────────────┬──────────────┬────────────────────────┐
│ Model                   │ Dimensions   │ Host Memory  │ Energy Trade-off       │
├─────────────────────────┼──────────────┼──────────────┼────────────────────────┤
│ `all-MiniLM-L6-v2`      │ 384          │ ~1.5 KB/vec  │ Zero network, low CPU  │
│ `bge-small-en-v1.5`     │ 384          │ ~1.5 KB/vec  │ Local GPU/CPU (< 15ms) │
│ `bge-base-en-v1.5`      │ 768          │ ~3.0 KB/vec  │ Moderate local compute │
│ `gemini-embedding-001`  │ 3072         │ ~12.3 KB/vec │ Offloads compute to    │
│                         │              │              │ cloud; adds HTTP round-│
│                         │              │              │ trip latency & network │
└─────────────────────────┴──────────────┴──────────────┴────────────────────────┘
```

### Research Insight for EcoRAG
- **When to use Gemini:** For high-complexity queries requiring fine-grained semantic separation across multi-concept documents.
- **When to use Local MiniLM/BGE:** For simple, high-frequency, or on-premise deployments where minimizing host RAM and eliminating cloud API dependencies is the priority.

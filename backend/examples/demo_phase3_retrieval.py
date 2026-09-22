import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ingestion import DocumentIngestionPipeline
from src.embeddings import LocalEmbeddingService
from src.vector_store import FAISSVectorStore
from src.retrieval import BM25Retriever, DenseRetriever, HybridRetriever
from src.reranker import ThresholdGatedReranker


def main():
    print("=== Phase 3 Verification: FAISS Vector Store, Hybrid Retrieval & Gated Reranker ===")

    corpus_text = """
    Document 1: EcoRAG Platform Architecture.
    EcoRAG is an adaptive benchmarking framework that minimizes energy, latency, and RAM in RAG.
    It introduces multi-tier query routing and context compression to save GPU wattage.

    Document 2: Quadratic Attention Bottleneck in Transformer Models.
    During the prompt prefill phase, Transformer self-attention complexity scales with context length squared O(N^2).
    Passing unnecessary context tokens into the prompt causes exponential energy spikes.

    Document 3: Vector Databases and FAISS Indexing.
    FAISS provides low-latency in-memory vector similarity search using inner-product IndexFlatIP and HNSW.
    It eliminates background daemon overhead compared to standalone vector servers.

    Document 4: Cross-Encoder vs Bi-Encoder Trade-offs.
    While bi-encoders generate separate embeddings for queries and chunks, cross-encoders compute deep joint attention.
    Cross-encoders achieve higher ranking precision but draw significant GPU wattage for every candidate chunk.

    Document 5: BM25 Sparse Lexical Retrieval.
    BM25 requires zero neural network computation at query time. For exact keyword searches, error codes, and IDs,
    BM25 provides 100% recall with negligible CPU cycles.
    """

    # 1. Ingest & Chunk Corpus
    print("\n1. Ingesting and chunking corpus...")
    pipeline = DocumentIngestionPipeline(chunk_size=40, chunk_overlap=5)
    chunks = pipeline.ingest_text(corpus_text, doc_id="ecorag_corpus")
    print(f"Total chunks created: {len(chunks)}")

    # 2. Build In-Memory FAISS Vector Store
    print("\n2. Initializing LocalEmbeddingService & FAISS Vector Store...")
    embedder = LocalEmbeddingService(model_name="all-MiniLM-L6-v2")
    vector_store = FAISSVectorStore(dimension=embedder.dimension)

    chunk_embeddings = embedder.embed_batch([c.text for c in chunks])
    vector_store.add_chunks(chunks, chunk_embeddings)
    print(f"FAISS index loaded with {vector_store.total_vectors} vectors (dimension={vector_store.dimension}).")

    # 3. Setup Retrievers (Sparse, Dense, Hybrid)
    bm25 = BM25Retriever(chunks)
    dense = DenseRetriever(vector_store, embedder)
    hybrid = HybridRetriever(dense, bm25, rrf_k=60)
    reranker = ThresholdGatedReranker(confidence_threshold=0.60, margin_threshold=0.10)

    # Test Query 1: Exact keyword search
    q1 = "BM25 zero neural network computation keyword searches"
    print(f"\n--- Test 1: Lexical Query --- '{q1}'")
    bm25_hits = bm25.search(q1, top_k=2)
    hybrid_hits = hybrid.search(q1, top_k=2)
    print(f"  [BM25 Top Hit]: {bm25_hits[0][0].text[:80]}... (Score: {bm25_hits[0][1]:.2f})")
    print(f"  [Hybrid Top Hit]: {hybrid_hits[0][0].text[:80]}... (RRF Score: {hybrid_hits[0][1]:.4f})")

    # Test Query 2: High confidence query (Should bypass Cross-Encoder)
    q2 = "Why does self-attention complexity scale with O(N^2) in Transformers?"
    print(f"\n--- Test 2: High Confidence Query (Check Gated Bypass) --- '{q2}'")
    dense_hits_q2 = dense.search(q2, top_k=5)
    rerank_result_q2 = reranker.rerank(q2, dense_hits_q2, top_k=2)
    print(f"  Bypassed Cross-Encoder: {rerank_result_q2.bypassed}")
    print(f"  Reason: {rerank_result_q2.reason}")
    print(f"  Top Candidate: {rerank_result_q2.ranked_chunks[0][0].text[:80]}...")

    # Test Query 3: Ambiguous query (Should trigger Cross-Encoder reranking)
    q3 = "framework trade-offs in search and deep attention"
    print(f"\n--- Test 3: Ambiguous Query (Check Cross-Encoder Trigger) --- '{q3}'")
    dense_hits_q3 = dense.search(q3, top_k=5)
    rerank_result_q3 = reranker.rerank(q3, dense_hits_q3, top_k=2)
    print(f"  Bypassed Cross-Encoder: {rerank_result_q3.bypassed}")
    print(f"  Reason: {rerank_result_q3.reason}")
    print(f"  Top Candidate: {rerank_result_q3.ranked_chunks[0][0].text[:80]}...")

    # Summary of Reranker Telemetry
    print(f"\n--- Reranker Green Telemetry ---")
    print(f"  Total Queries: {reranker.total_queries}")
    print(f"  Bypassed Queries: {reranker.bypassed_queries}")
    print(f"  Bypass Rate: {reranker.bypass_rate:.1f}% (Energy saved by avoiding Cross-Encoder inference!)")

    print("\n Phase 3 Hybrid Retrieval & Threshold-Gated Reranker verification COMPLETE!")


if __name__ == "__main__":
    main()

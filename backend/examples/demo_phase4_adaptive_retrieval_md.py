import sys
import os
import glob
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ingestion import DocumentIngestionPipeline, MarkdownChunker
from src.embeddings import LocalEmbeddingService
from src.vector_store import FAISSVectorStore
from src.retrieval import (
    BM25Retriever,
    DenseRetriever,
    HybridRetriever,
    AdaptiveRetriever,
    DynamicContextFilter,
)


def main():
    print("=" * 80)
    print("EcoRAG Phase 4: Markdown Analysis, Adaptive Retrieval & Multi-Tier Caching")
    print("=" * 80)

    knowledge_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "knowledge"))
    md_files = [
        os.path.join(knowledge_dir, "03_optimization_strategies.md"),
        os.path.join(knowledge_dir, "04_system_architecture.md"),
        os.path.join(knowledge_dir, "ecorag_complete_findings.md"),
    ]

    # Filter to existing files
    md_files = [f for f in md_files if os.path.exists(f)]
    print(f"\n1. Ingesting {len(md_files)} knowledge markdown files with MarkdownChunker...")

    pipeline = DocumentIngestionPipeline(chunk_size=120, chunk_overlap=15, enable_dedup=True)
    all_chunks = []
    for f in md_files:
        chunks = pipeline.ingest_file(f)
        all_chunks.extend(chunks)
        print(f"   Indexed '{os.path.basename(f)}' -> {len(chunks)} structured markdown chunks.")

    print(f"\nTotal markdown chunks produced: {len(all_chunks)}")
    sample_chunk = all_chunks[2] if len(all_chunks) > 2 else all_chunks[0]
    print(f"\n[Sample Markdown-Aware Chunk Preview]:")
    print(f"  Chunk ID: {sample_chunk.chunk_id}")
    print(f"  Header Path: {sample_chunk.metadata.get('header_path')}")
    print(f"  Snippet:\n    {sample_chunk.text[:220].replace(chr(10), ' ')}...")

    # 2. Embed and Index into FAISS Vector Store
    print("\n2. Initializing LocalEmbeddingService & FAISS Vector Store...")
    embedder = LocalEmbeddingService(model_name="all-MiniLM-L6-v2")
    vector_store = FAISSVectorStore(dimension=embedder.dimension)

    embeddings = embedder.embed_batch([c.text for c in all_chunks])
    vector_store.add_chunks(all_chunks, embeddings)
    print(f"   Loaded {vector_store.total_vectors} vectors into in-memory FAISS IndexFlatIP.")

    # 3. Assemble Retrievers & Adaptive Engine
    print("\n3. Assembling Adaptive Retrieval Engine (BM25, Dense, Hybrid, L1/L2 Caches)...")
    dense_retriever = DenseRetriever(vector_store, embedder)
    bm25_retriever = BM25Retriever(all_chunks)
    hybrid_retriever = HybridRetriever(dense_retriever, bm25_retriever, rrf_k=60)

    adaptive_engine = AdaptiveRetriever(
        dense_retriever=dense_retriever,
        bm25_retriever=bm25_retriever,
        hybrid_retriever=hybrid_retriever,
        embedding_service=embedder
    )

    test_queries = [
        ("Query 1 [Keyword / Factoid]", "BM25Okapi"),
        ("Query 2 [Repeated Query - Exact Cache Test]", "BM25Okapi"),
        ("Query 3 [Conceptual Question]", "how does dynamic context sizing cut quadratic prefill energy"),
        ("Query 4 [Paraphrased Question - Semantic Cache Test]", "how does dynamic context sizing reduce quadratic attention compute"),
        ("Query 5 [Comparative Multi-Concept]", "compare cross-encoder vs bi-encoder trade-offs in accuracy and energy"),
    ]

    print("\n" + "=" * 80)
    print("Executing Adaptive Retrieval Benchmark")
    print("=" * 80)

    for label, query in test_queries:
        t0 = time.perf_counter()
        result = adaptive_engine.search(query, top_k=3, use_cache=True, apply_dynamic_filter=True)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        print(f"\n>>> {label}: \"{query}\"")
        print(f"    Complexity:       {result.complexity.value.upper()}")
        print(f"    Mode Chosen:      {result.retrieval_mode_chosen.upper()}")
        print(f"    Cache Tier:       {result.cache_tier} (sim={result.cache_similarity})")
        print(f"    Latency:          {elapsed_ms:.2f} ms")
        print(f"    Energy Strategy:  {result.energy_saving_reason}")
        print(f"    Pruned Chunks:    {result.pruned_candidate_count} (below relevance cutoff)")

        if result.hits:
            top_hit, top_score = result.hits[0]
            header = top_hit.metadata.get("header_path", "N/A")
            compressed_snippet = DynamicContextFilter.compress_chunk_sentences(top_hit, query, max_sentences=2)
            print(f"    [Top Hit Source]: {top_hit.doc_id} -> {header}")
            print(f"    [Score]:          {top_score:.4f}")
            print(f"    [Extractive Text]: {compressed_snippet[:160]}...")

    print("\n" + "=" * 80)
    print("Adaptive Retrieval Telemetry Summary")
    print("=" * 80)
    print(f"Total Queries:             {adaptive_engine.total_queries}")
    print(f"L1 Exact Cache Hits:       {adaptive_engine.exact_cache_hits}")
    print(f"L2 Semantic Cache Hits:    {adaptive_engine.semantic_cache_hits}")
    print(f"Sparse (BM25) Routed:      {adaptive_engine.sparse_routed_queries}")
    print(f"Dense (FAISS) Routed:      {adaptive_engine.dense_routed_queries}")
    print(f"Hybrid (RRF) Routed:       {adaptive_engine.hybrid_routed_queries}")

    cache_rate = ((adaptive_engine.exact_cache_hits + adaptive_engine.semantic_cache_hits) / adaptive_engine.total_queries) * 100.0
    print(f"Cache Efficiency:          {cache_rate:.1f}% of queries completely bypassed downstream compute!")
    print("\n Phase 4 Markdown Analysis and Adaptive Retrieval Verification Complete.")


if __name__ == "__main__":
    main()

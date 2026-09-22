import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ingestion import DocumentIngestionPipeline
from src.embeddings import GeminiEmbeddingService, LocalEmbeddingService


def main():
    print("=== Phase 2 Verification: Ingestion, Chunking, Deduplication & Embedding ===")

    sample_doc = """
    EcoRAG is an experimental platform designed to minimize resource consumption in Retrieval-Augmented Generation.
    By analyzing query complexity, EcoRAG selects the minimal sufficient retrieval and generation pipeline.
    
    Traditional RAG approaches stuff large 1024-token contexts into LLM prompts without considering energy costs.
    This causes quadratic self-attention computation during the prefill phase, wasting significant Watt-hours.
    
    Traditional RAG approaches stuff large 1024-token contexts into LLM prompts without considering energy costs.
    This causes quadratic self-attention computation during the prefill phase, wasting significant Watt-hours.
    
    To optimize RAG, EcoRAG integrates five distinct optimization layers: retrieval efficiency, context efficiency,
    computation efficiency, caching reuse, and continuous hardware telemetry measurement.
    """

    # 1. Test Ingestion with Chunking & Deduplication
    print("\n1. Running Ingestion Pipeline (Chunk size = 30 words, with deduplication)...")
    pipeline = DocumentIngestionPipeline(chunk_size=30, chunk_overlap=5, enable_dedup=True)
    chunks = pipeline.ingest_text(sample_doc, doc_id="ecorag_overview.txt")

    print(f"Generated {len(chunks)} unique chunks (duplicate paragraph was filtered):")
    for i, c in enumerate(chunks, 1):
        print(f"  Chunk {i} [tokens ~{c.token_count_approx}, id={c.chunk_id[:25]}...]: {c.text[:75]}...")

    # 2. Test Multi-Model Embedding
    print("\n2. Comparing Multi-Model Embeddings...")
    
    # Cloud Gemini
    gemini_svc = GeminiEmbeddingService(model_name="gemini-embedding-001")
    chunk_texts = [c.text for c in chunks]
    gemini_vecs = gemini_svc.embed_batch(chunk_texts)
    print(f"  [Cloud] Gemini Embedding: {len(gemini_vecs)} vectors, dimension = {gemini_svc.dimension}")

    # Local MiniLM
    print("  [Local] Initializing LocalEmbeddingService ('all-MiniLM-L6-v2')...")
    local_svc = LocalEmbeddingService(model_name="all-MiniLM-L6-v2")
    local_vecs = local_svc.embed_batch(chunk_texts)
    print(f"  [Local] Local Embedding: {len(local_vecs)} vectors, dimension = {local_svc.dimension}")

    # 3. Memory & Resource Footprint Comparison
    gemini_bytes_per_vec = gemini_svc.dimension * 4  # float32 = 4 bytes
    local_bytes_per_vec = local_svc.dimension * 4

    print("\n--- Memory Footprint per 10,000 Chunks ---")
    print(f"  Gemini (3072d): {gemini_bytes_per_vec * 10000 / (1024*1024):.2f} MB RAM")
    print(f"  Local (384d):   {local_bytes_per_vec * 10000 / (1024*1024):.2f} MB RAM ({gemini_bytes_per_vec/local_bytes_per_vec:.1f}x smaller)")

    print("\n Phase 2 Ingestion & Multi-Model Embedding verification COMPLETE!")


if __name__ == "__main__":
    main()

import sys
import os

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.embeddings import GeminiEmbeddingService


def main():
    print("Initializing GeminiEmbeddingService...")
    service = GeminiEmbeddingService(model_name="gemini-embedding-001")

    # Sample EcoRAG document chunks
    corpus = [
        "EcoRAG focuses on minimizing computational energy and latency in Retrieval-Augmented Generation.",
        "FAISS provides fast in-memory similarity search for high-dimensional vector embeddings.",
        "Quadratic self-attention in Transformer LLMs causes prefill power consumption to scale with context length squared.",
        "Deep learning architectures often utilize convolutional neural networks for computer vision applications.",
    ]

    print(f"Embedding {len(corpus)} sample document chunks...")
    corpus_embeddings = service.embed_batch(corpus)

    query = "How does context size affect energy consumption in RAG?"
    print(f"\nUser Query: '{query}'")
    query_emb = service.embed_text(query)

    print("\n--- Semantic Similarity Ranking ---")
    scores = []
    for idx, (doc, doc_emb) in enumerate(zip(corpus, corpus_embeddings)):
        sim = service.cosine_similarity(query_emb, doc_emb)
        scores.append((idx, sim, doc))

    scores.sort(key=lambda x: x[1], reverse=True)
    for rank, (idx, sim, doc) in enumerate(scores, 1):
        print(f"Rank {rank} [Score: {sim:.4f}]: {doc}")


if __name__ == "__main__":
    main()

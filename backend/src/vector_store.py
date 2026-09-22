import os
import json
from typing import List, Tuple, Dict, Any, Optional
import numpy as np
import faiss

from src.ingestion import Chunk


class FAISSVectorStore:
    """
    In-Memory FAISS Vector Database for EcoRAG.
    Uses IndexFlatIP with normalized vectors for exact Cosine Similarity.
    Supports dynamic vector dimensions (e.g. 384d for MiniLM, 3072d for Gemini).
    """

    def __init__(self, dimension: int):
        self.dimension = dimension
        self.index = faiss.IndexFlatIP(dimension)
        self.chunks: List[Chunk] = []
        self.chunk_id_map: Dict[str, int] = {}

    def add_chunks(self, chunks: List[Chunk], embeddings: List[List[float]]) -> None:
        """Add chunks and their corresponding embedding vectors to the index."""
        if len(chunks) != len(embeddings):
            raise ValueError(f"Mismatched counts: {len(chunks)} chunks vs {len(embeddings)} vectors.")

        if not chunks:
            return

        vectors = np.array(embeddings, dtype=np.float32)
        # Normalize for Inner Product -> Cosine Similarity
        faiss.normalize_L2(vectors)

        start_idx = len(self.chunks)
        self.index.add(vectors)

        for i, chunk in enumerate(chunks):
            self.chunks.append(chunk)
            self.chunk_id_map[chunk.chunk_id] = start_idx + i

    def search(
        self,
        query_vector: List[float],
        top_k: int = 5,
        score_threshold: Optional[float] = None
    ) -> List[Tuple[Chunk, float]]:
        """
        Search for top_k most similar chunks.
        Returns a list of (Chunk, similarity_score) tuples sorted in descending order.
        """
        if top_k <= 0 or self.index.ntotal == 0:
            return []

        q_vec = np.array([query_vector], dtype=np.float32)
        faiss.normalize_L2(q_vec)

        k = min(top_k, self.index.ntotal)
        if k <= 0:
            return []

        scores, indices = self.index.search(q_vec, k)

        results: List[Tuple[Chunk, float]] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self.chunks):
                continue
            sim = float(score)
            if score_threshold is not None and sim < score_threshold:
                continue
            results.append((self.chunks[idx], sim))

        return results

    @property
    def total_vectors(self) -> int:
        return self.index.ntotal

    def save(self, directory: str, index_name: str = "faiss_index") -> None:
        """Save FAISS index and chunk metadata to disk."""
        os.makedirs(directory, exist_ok=True)
        index_file = os.path.join(directory, f"{index_name}.bin")
        meta_file = os.path.join(directory, f"{index_name}_meta.json")

        faiss.write_index(self.index, index_file)

        meta = [
            {
                "text": c.text,
                "chunk_id": c.chunk_id,
                "doc_id": c.doc_id,
                "chunk_index": c.chunk_index,
                "char_length": c.char_length,
                "token_count_approx": c.token_count_approx,
                "metadata": c.metadata,
            }
            for c in self.chunks
        ]
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump({"dimension": self.dimension, "chunks": meta}, f, indent=2)

    @classmethod
    def load(cls, directory: str, index_name: str = "faiss_index") -> "FAISSVectorStore":
        """Load FAISS index and chunk metadata from disk."""
        index_file = os.path.join(directory, f"{index_name}.bin")
        meta_file = os.path.join(directory, f"{index_name}_meta.json")

        if not os.path.exists(index_file) or not os.path.exists(meta_file):
            raise FileNotFoundError(f"FAISS index files not found in {directory}")

        with open(meta_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        store = cls(dimension=data["dimension"])
        store.index = faiss.read_index(index_file)

        store.chunks = [
            Chunk(
                text=c["text"],
                chunk_id=c["chunk_id"],
                doc_id=c["doc_id"],
                chunk_index=c["chunk_index"],
                char_length=c["char_length"],
                token_count_approx=c["token_count_approx"],
                metadata=c["metadata"],
            )
            for c in data["chunks"]
        ]
        store.chunk_id_map = {c.chunk_id: i for i, c in enumerate(store.chunks)}
        return store

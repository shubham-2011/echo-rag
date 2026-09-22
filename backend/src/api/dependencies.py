import os
from typing import List, Optional
from src.embeddings import BaseEmbeddingService, LocalEmbeddingService, GeminiEmbeddingService
from src.vector_store import FAISSVectorStore
from src.retrieval import (
    BM25Retriever,
    DenseRetriever,
    HybridRetriever,
    AdaptiveRetriever,
    ExactQueryCache,
    SemanticQueryCache,
    QueryClassifier,
    DynamicContextFilter,
)
from src.reranker import ThresholdGatedReranker
from src.ingestion import Chunk


class AppState:
    """
    Singleton service container managing stateful vector stores, models, caches, and retrievers.
    """

    def __init__(self):
        self.embedder: BaseEmbeddingService = LocalEmbeddingService(model_name="all-MiniLM-L6-v2")
        self.vector_store: FAISSVectorStore = FAISSVectorStore(dimension=self.embedder.dimension)
        self.chunks: List[Chunk] = []
        self.bm25_retriever: Optional[BM25Retriever] = None
        self.reranker: ThresholdGatedReranker = ThresholdGatedReranker(
            confidence_threshold=0.60,
            margin_threshold=0.10
        )
        self.exact_cache: ExactQueryCache = ExactQueryCache()
        self.semantic_cache: SemanticQueryCache = SemanticQueryCache(threshold=0.90)
        self.classifier: QueryClassifier = QueryClassifier()
        self.context_filter: DynamicContextFilter = DynamicContextFilter()

        # Optional Gemini client for answer generation
        self._gemini_client = None

    def get_gemini_client(self):
        if self._gemini_client is None:
            api_key = os.getenv("GEMINI_API_KEY")
            if api_key:
                from google import genai
                self._gemini_client = genai.Client(api_key=api_key)
        return self._gemini_client

    def update_corpus(self, new_chunks: List[Chunk], new_embeddings: List[List[float]]) -> None:
        """Add new chunks to FAISS and rebuild the BM25 lexical index, clearing query caches."""
        self.vector_store.add_chunks(new_chunks, new_embeddings)
        self.chunks.extend(new_chunks)
        self.bm25_retriever = BM25Retriever(self.chunks)
        self.exact_cache.clear()
        self.semantic_cache.clear()

    def get_dense_retriever(self) -> DenseRetriever:
        return DenseRetriever(self.vector_store, self.embedder)

    def get_bm25_retriever(self) -> BM25Retriever:
        if self.bm25_retriever is None:
            self.bm25_retriever = BM25Retriever(self.chunks)
        return self.bm25_retriever

    def get_hybrid_retriever(self) -> HybridRetriever:
        return HybridRetriever(
            dense_retriever=self.get_dense_retriever(),
            bm25_retriever=self.get_bm25_retriever(),
            rrf_k=60
        )

    def get_adaptive_retriever(self) -> AdaptiveRetriever:
        return AdaptiveRetriever(
            dense_retriever=self.get_dense_retriever(),
            bm25_retriever=self.get_bm25_retriever(),
            hybrid_retriever=self.get_hybrid_retriever(),
            embedding_service=self.embedder,
            exact_cache=self.exact_cache,
            semantic_cache=self.semantic_cache,
            classifier=self.classifier,
            context_filter=self.context_filter,
        )


# Global application state instance
app_state = AppState()


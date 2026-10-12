import logging
import os
import threading
from typing import List, Optional
from src.embeddings import BaseEmbeddingService, HashEmbeddingService, LocalEmbeddingService, GeminiEmbeddingService
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
from src.persistence import IndexStore

logger = logging.getLogger(__name__)
from src.security.security_gateway import SecurityGateway
from src.security.config import SECURITY_CONFIG


class AppState:
    """
    Singleton service container managing stateful vector stores, models, caches, and retrievers.
    """

    def __init__(self):
        try:
            self.embedder: BaseEmbeddingService = LocalEmbeddingService(model_name="all-MiniLM-L6-v2")
        except (ImportError, OSError, RuntimeError) as error:
            logger.warning("Local embeddings unavailable; using deterministic fallback: %s", error)
            self.embedder = HashEmbeddingService()
        self.vector_store: FAISSVectorStore = FAISSVectorStore(dimension=self.embedder.dimension)
        self.chunks: List[Chunk] = []
        self.bm25_retriever: Optional[BM25Retriever] = None
        self.tenant_indexes: dict[str, TenantIndex] = {}
        self._corpus_lock = threading.RLock()
        self.exact_cache: ExactQueryCache = ExactQueryCache()
        self.semantic_cache: SemanticQueryCache = SemanticQueryCache(threshold=0.90)
        self.reranker: ThresholdGatedReranker = ThresholdGatedReranker(
            confidence_threshold=0.60,
            margin_threshold=0.10
        )
        self.classifier: QueryClassifier = QueryClassifier()
        self.context_filter: DynamicContextFilter = DynamicContextFilter()

        # Optional Gemini client for answer generation
        self._gemini_client = None

        self.index_store = IndexStore()
        self.index_manifest: dict | None = None
        self.index_loaded_from_disk = False
        self.active_doc_ids: List[str] = []
        loaded = self.index_store.load(self)
        if loaded is not None:
            self.index_manifest = loaded
            self.index_loaded_from_disk = True
            self.active_doc_ids = sorted({c.doc_id for c in self.chunks})
            tenant_chunks: dict[str, list[Chunk]] = {}
            multi_user_configured = bool(os.getenv("ECORAG_API_KEYS_JSON", "").strip())
            for chunk in self.chunks:
                owner = (chunk.metadata or {}).get("owner")
                if not isinstance(owner, str) or not owner:
                    if multi_user_configured:
                        continue
                    owner = os.getenv("ECORAG_API_USER_ID", "local-user")
                    chunk.metadata = {**(chunk.metadata or {}), "owner": owner}
                tenant_chunks.setdefault(owner, []).append(chunk)
            for owner, chunks in tenant_chunks.items():
                tenant_index = self._get_tenant_index(owner)
                embeddings = self.embedder.embed_batch([chunk.text for chunk in chunks])
                tenant_index.vector_store.add_chunks(chunks, embeddings)
                tenant_index.chunks.extend(chunks)
                tenant_index.bm25_retriever = BM25Retriever(tenant_index.chunks)

    def get_gemini_client(self):
        if self._gemini_client is None:
            api_key = os.getenv("GEMINI_API_KEY")
            if api_key:
                from google import genai
                from google.genai import types

                self._gemini_client = genai.Client(
                    api_key=api_key,
                    http_options=types.HttpOptions(
                        timeout=int(SECURITY_CONFIG.model_timeout_seconds * 1000)
                    ),
                )
        return self._gemini_client

    def reset_index(self) -> list[str]:
        previous = sorted({c.doc_id for c in self.chunks})
        self.vector_store.reset()
        self.chunks = []
        self.bm25_retriever = None
        self.exact_cache.clear()
        self.semantic_cache.clear()
        self.active_doc_ids = []
        self.index_manifest = None
        self.index_loaded_from_disk = False
        self.index_store.clear()
        self.tenant_indexes.clear()
        logger.info("[INGEST] reset_index previous_docs=%s", ",".join(previous) or "none")
        return previous

    def update_corpus(self, new_chunks: List[Chunk], new_embeddings: List[List[float]]) -> None:
        """Add chunks only to their owning tenant's indexes and caches."""
        if len(new_chunks) != len(new_embeddings):
            raise ValueError("Each chunk must have exactly one embedding.")
        if not new_chunks:
            return

        tenant_chunks: dict[str, list[Chunk]] = {}
        tenant_embeddings: dict[str, list[List[float]]] = {}
        for chunk, embedding in zip(new_chunks, new_embeddings):
            owner = chunk.metadata.get("owner")
            if not isinstance(owner, str) or not owner:
                raise ValueError("Every indexed chunk must have a tenant owner.")
            tenant_chunks.setdefault(owner, []).append(chunk)
            tenant_embeddings.setdefault(owner, []).append(embedding)

        with self._corpus_lock:
            for owner, chunks in tenant_chunks.items():
                tenant_index = self._get_tenant_index(owner)
                tenant_index.vector_store.add_chunks(chunks, tenant_embeddings[owner])
                tenant_index.chunks.extend(chunks)
                tenant_index.bm25_retriever = BM25Retriever(tenant_index.chunks)
                tenant_index.exact_cache.clear()
                tenant_index.semantic_cache.clear()
            self.exact_cache.clear()
            self.semantic_cache.clear()

            # The legacy on-disk index remains available for single-user deployments.
            # A shared index is not persisted when multiple principals are configured.
            if not os.getenv("ECORAG_API_KEYS_JSON", "").strip():
                self.vector_store.add_chunks(new_chunks, new_embeddings)
                self.chunks.extend(new_chunks)
                self.bm25_retriever = BM25Retriever(self.chunks)
                self.active_doc_ids = sorted({chunk.doc_id for chunk in self.chunks})
                manifest = self.index_store.save(self)
                if manifest is not None:
                    self.index_manifest = manifest
                    self.index_loaded_from_disk = True

    def replace_tenant_corpus(
        self,
        owner: str,
        new_chunks: List[Chunk],
        new_embeddings: List[List[float]],
    ) -> list[str]:
        tenant_index = self._get_tenant_index(owner)
        previous = sorted({chunk.doc_id for chunk in tenant_index.chunks})
        tenant_index.vector_store.reset()
        tenant_index.chunks.clear()
        tenant_index.bm25_retriever = None
        tenant_index.exact_cache.clear()
        tenant_index.semantic_cache.clear()
        if not os.getenv("ECORAG_API_KEYS_JSON", "").strip():
            remaining_chunks = [
                chunk
                for chunk in self.chunks
                if (chunk.metadata or {}).get("owner") != owner
            ]
            self.vector_store.reset()
            self.chunks = remaining_chunks
            self.bm25_retriever = BM25Retriever(remaining_chunks) if remaining_chunks else None
            if remaining_chunks:
                remaining_embeddings = self.embedder.embed_batch(
                    [chunk.text for chunk in remaining_chunks]
                )
                self.vector_store.add_chunks(remaining_chunks, remaining_embeddings)
                self.active_doc_ids = sorted({chunk.doc_id for chunk in remaining_chunks})
            else:
                self.active_doc_ids = []
                self.index_manifest = None
                self.index_loaded_from_disk = False
                self.index_store.clear()
        if new_chunks:
            self.update_corpus(new_chunks, new_embeddings)
        return previous

    def replace_corpus(self, new_chunks: List[Chunk], new_embeddings: List[List[float]]) -> list[str]:
        owners = {
            str(chunk.metadata.get("owner"))
            for chunk in new_chunks
            if isinstance(chunk.metadata, dict) and chunk.metadata.get("owner")
        }
        if len(owners) != 1:
            raise ValueError("Replacing a corpus requires chunks for exactly one tenant.")
        return self.replace_tenant_corpus(owners.pop(), new_chunks, new_embeddings)

    def get_dense_retriever(self, owner: str) -> DenseRetriever:
        return DenseRetriever(self._get_tenant_index(owner).vector_store, self.embedder)

    def get_bm25_retriever(self, owner: str) -> BM25Retriever:
        tenant_index = self._get_tenant_index(owner)
        if tenant_index.bm25_retriever is None:
            tenant_index.bm25_retriever = BM25Retriever(tenant_index.chunks)
        return tenant_index.bm25_retriever

    def get_hybrid_retriever(self, owner: str) -> HybridRetriever:
        return HybridRetriever(
            dense_retriever=self.get_dense_retriever(owner),
            bm25_retriever=self.get_bm25_retriever(owner),
            rrf_k=60
        )

    def get_adaptive_retriever(self, owner: str) -> AdaptiveRetriever:
        tenant_index = self._get_tenant_index(owner)
        return AdaptiveRetriever(
            dense_retriever=self.get_dense_retriever(owner),
            bm25_retriever=self.get_bm25_retriever(owner),
            hybrid_retriever=self.get_hybrid_retriever(owner),
            embedding_service=self.embedder,
            exact_cache=tenant_index.exact_cache,
            semantic_cache=tenant_index.semantic_cache,
            classifier=self.classifier,
            context_filter=self.context_filter,
        )

    def get_tenant_vector_count(self, owner: str) -> int:
        return self._get_tenant_index(owner).vector_store.total_vectors

    def get_tenant_chunks(self, owner: str) -> list[Chunk]:
        return list(self._get_tenant_index(owner).chunks)

    def _get_tenant_index(self, owner: str) -> "TenantIndex":
        if not owner:
            raise ValueError("A tenant owner is required for tenant-scoped retrieval.")
        with self._corpus_lock:
            if owner not in self.tenant_indexes:
                self.tenant_indexes[owner] = TenantIndex(self.embedder.dimension)
            return self.tenant_indexes[owner]


class TenantIndex:
    def __init__(self, dimension: int):
        self.vector_store = FAISSVectorStore(dimension=dimension)
        self.chunks: List[Chunk] = []
        self.bm25_retriever: Optional[BM25Retriever] = None
        self.exact_cache: ExactQueryCache = ExactQueryCache()
        self.semantic_cache: SemanticQueryCache = SemanticQueryCache(threshold=0.90)


# Global application state instance
app_state = AppState()
security_gateway = SecurityGateway()

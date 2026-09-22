import re
import hashlib
from enum import Enum
from typing import List, Tuple, Dict, Optional, Any
from dataclasses import dataclass, field
import numpy as np
from rank_bm25 import BM25Plus

from src.ingestion import Chunk, ParentDocumentStore
from src.embeddings import BaseEmbeddingService
from src.vector_store import FAISSVectorStore


class QueryComplexity(str, Enum):
    SIMPLE = "simple"      # Keyword / factoid / exact error or formula -> BM25
    NORMAL = "normal"      # Standard conceptual explanation -> Dense FAISS
    COMPLEX = "complex"    # Comparative / multi-hop synthesis -> Hybrid RRF


class QueryClassifier:
    """
    Zero-compute heuristic query classifier.
    Categorizes incoming queries into SIMPLE, NORMAL, or COMPLEX without running
    an expensive forward pass through a large language model.
    """

    COMPLEX_PATTERNS = [
        re.compile(r"\bcompare\b", re.I),
        re.compile(r"\bvs\.?\b", re.I),
        re.compile(r"\bversus\b", re.I),
        re.compile(r"\bdifference(s)?\b", re.I),
        re.compile(r"\btrade-?offs?\b", re.I),
        re.compile(r"\bpros and cons\b", re.I),
        re.compile(r"\brelationship between\b", re.I),
        re.compile(r"\bsynthesize\b", re.I),
        re.compile(r"\bmulti-hop\b", re.I),
    ]

    SIMPLE_PATTERNS = [
        re.compile(r"^[A-Za-z0-9_\-\.]{1,25}$"),       # Single token / ID / code
        re.compile(r"^(what is|define|formula for)\s+[\w\s]{1,25}$", re.I),
        re.compile(r"^\d+([A-Za-z]+)?$"),              # Pure numbers or metrics
    ]

    def classify(self, query: str) -> QueryComplexity:
        q = query.strip().lower()
        words = re.findall(r"\w+", q)
        num_words = len(words)

        if not q or num_words == 0:
            return QueryComplexity.SIMPLE

        # 1. Exact / Short Factoid -> SIMPLE
        if num_words <= 3:
            for pattern in self.SIMPLE_PATTERNS:
                if pattern.match(q):
                    return QueryComplexity.SIMPLE

        # 2. Multi-hop / Comparison / Multi-concept -> COMPLEX
        has_complex_pattern = any(p.search(q) for p in self.COMPLEX_PATTERNS)
        has_multi_conjunction = (" and " in q or " with " in q) and num_words >= 15
        if has_complex_pattern or has_multi_conjunction or num_words >= 20:
            return QueryComplexity.COMPLEX

        # 3. Default to NORMAL (Dense Semantic Search)
        return QueryComplexity.NORMAL


class ExactQueryCache:
    """
    L1 In-Memory Exact Query Cache.
    Sub-millisecond lookup via SHA-256 hash of normalized query.
    Bypasses vector embedding, retrieval, and reranking entirely (zero downstream energy).
    """

    def __init__(self, max_entries: int = 1000):
        self.max_entries = max_entries
        self._cache: Dict[str, List[Tuple[Chunk, float]]] = {}

    @staticmethod
    def _hash_key(query: str) -> str:
        norm = " ".join(query.strip().lower().split())
        return hashlib.sha256(norm.encode("utf-8")).hexdigest()

    def get(self, query: str) -> Optional[List[Tuple[Chunk, float]]]:
        key = self._hash_key(query)
        return self._cache.get(key)

    def set(self, query: str, results: List[Tuple[Chunk, float]]) -> None:
        if len(self._cache) >= self.max_entries:
            # Evict oldest key
            first_key = next(iter(self._cache))
            del self._cache[first_key]
        key = self._hash_key(query)
        self._cache[key] = results

    def clear(self) -> None:
        self._cache.clear()

    @property
    def size(self) -> int:
        return len(self._cache)


class SemanticQueryCache:
    """
    L2 Vector Semantic Cache.
    Stores past query embeddings and returns cached chunk results if cosine similarity
    exceeds the threshold (default >= 0.90 per research recommendation).
    """

    def __init__(self, threshold: float = 0.90, max_entries: int = 500):
        self.threshold = threshold
        self.max_entries = max_entries
        self.entries: List[Dict[str, Any]] = []

    def get(
        self,
        query_vector: List[float],
        threshold: Optional[float] = None
    ) -> Optional[Tuple[List[Tuple[Chunk, float]], float]]:
        """
        Check if any cached query vector matches within the similarity threshold.
        Returns (results, similarity_score) on hit, or None on miss.
        """
        if not self.entries:
            return None

        thresh = threshold or self.threshold
        q_vec = np.array(query_vector, dtype=np.float32)
        norm_q = np.linalg.norm(q_vec)
        if norm_q > 0:
            q_vec = q_vec / norm_q

        best_score = -1.0
        best_entry = None

        for entry in self.entries:
            c_vec = entry["vector"]
            # Cosine similarity (vectors are unit normalized)
            sim = float(np.dot(q_vec, c_vec))
            if sim > best_score:
                best_score = sim
                best_entry = entry

        if best_entry is not None and best_score >= thresh:
            best_entry["hit_count"] += 1
            return best_entry["results"], best_score

        return None

    def set(self, query: str, query_vector: List[float], results: List[Tuple[Chunk, float]]) -> None:
        if len(self.entries) >= self.max_entries:
            # Evict least recently / least frequently used
            self.entries.sort(key=lambda x: x["hit_count"])
            self.entries.pop(0)

        v = np.array(query_vector, dtype=np.float32)
        norm_v = np.linalg.norm(v)
        if norm_v > 0:
            v = v / norm_v

        self.entries.append({
            "query": query,
            "vector": v,
            "results": results,
            "hit_count": 0,
        })

    def clear(self) -> None:
        self.entries.clear()

    @property
    def size(self) -> int:
        return len(self.entries)


class DynamicContextFilter:
    """
    Layer 2 Context Efficiency Engine:
    1. Dynamic Relevance Sizing: Discards chunks falling below a relevance threshold (tau_min)
       or dropping sharply relative to the top chunk's score, curbing quadratic prefill compute.
    2. Extractive Sentence Compression: Extracts only high-salience sentences from retrieved chunks.
    """

    def __init__(self, min_absolute_score: float = 0.20, relative_drop_ratio: float = 0.50):
        self.min_absolute_score = min_absolute_score
        self.relative_drop_ratio = relative_drop_ratio

    def filter_chunks(
        self,
        hits: List[Tuple[Chunk, float]],
        min_score: Optional[float] = None,
        relative_ratio: Optional[float] = None
    ) -> List[Tuple[Chunk, float]]:
        """Filter chunks that fail minimum or relative relevance cutoffs."""
        if not hits:
            return []

        tau_abs = min_score if min_score is not None else self.min_absolute_score
        tau_rel = relative_ratio if relative_ratio is not None else self.relative_drop_ratio

        top_score = hits[0][1]
        filtered: List[Tuple[Chunk, float]] = []

        for chunk, score in hits:
            # Must satisfy absolute threshold
            if score < tau_abs:
                continue
            # Must satisfy relative threshold compared to top candidate
            if top_score > 0 and (score / top_score) < tau_rel:
                continue
            filtered.append((chunk, score))

        # Always return at least the top chunk if hits existed
        if not filtered and hits:
            filtered.append(hits[0])

        return filtered

    @staticmethod
    def compress_chunk_sentences(chunk: Chunk, query: str, max_sentences: int = 3) -> str:
        """Extract top most relevant sentences from a chunk based on lexical term overlap."""
        text = chunk.text
        # Split by sentence boundaries
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
        if len(sentences) <= max_sentences:
            return text

        query_tokens = set(re.findall(r"\w+", query.lower()))
        if not query_tokens:
            return " ".join(sentences[:max_sentences])

        scored_sentences = []
        for idx, sentence in enumerate(sentences):
            sent_tokens = set(re.findall(r"\w+", sentence.lower()))
            overlap = len(query_tokens.intersection(sent_tokens))
            scored_sentences.append((overlap, idx, sentence))

        # Sort by overlap descending, then preserve original order
        top_sentences = sorted(scored_sentences, key=lambda x: x[0], reverse=True)[:max_sentences]
        top_sentences_ordered = sorted(top_sentences, key=lambda x: x[1])

        return " ".join([s[2] for s in top_sentences_ordered])


class SentenceWindowExpander:
    """
    Expands retrieved chunk context by +/- W sentences from the parent document.
    Eliminates semantic fragmentation for small chunk sizes (128/256 tokens) without
    stuffing arbitrary full documents into LLM prompts.
    """

    def __init__(self, default_window: int = 2):
        self.default_window = default_window

    def expand_hits(
        self,
        hits: List[Tuple[Chunk, float]],
        window_size: Optional[int] = None
    ) -> List[Tuple[Chunk, float]]:
        w = self.default_window if window_size is None else window_size
        if w <= 0:
            return hits

        store = ParentDocumentStore.get_instance()
        expanded_hits = []
        for c, score in hits:
            meta = c.metadata
            parent_id = meta.get("parent_doc_id", c.doc_id)
            start_idx = meta.get("sentence_start_idx")
            end_idx = meta.get("sentence_end_idx")

            if start_idx is not None and end_idx is not None:
                expanded_text = store.expand_window(parent_id, start_idx, end_idx, window=w)
                if expanded_text:
                    exp_chunk = Chunk(
                        text=expanded_text,
                        chunk_id=c.chunk_id,
                        doc_id=c.doc_id,
                        chunk_index=c.chunk_index,
                        char_length=len(expanded_text),
                        token_count_approx=len(expanded_text.split()),
                        metadata={**meta, "expanded_window": w, "is_sentence_expanded": True}
                    )
                    expanded_hits.append((exp_chunk, score))
                    continue

            expanded_hits.append((c, score))
        return expanded_hits

    @staticmethod
    def calculate_attention_work_ratio(context_tokens: int, baseline_tokens: int = 1024) -> float:
        """
        Theoretical self-attention computational FLOPs ratio O(N^2) relative to a 1024-token baseline.
        e.g., 256 tokens -> (256/1024)^2 = 0.0625 (93.75% reduction).
        """
        if baseline_tokens <= 0:
            return 1.0
        return round((context_tokens / baseline_tokens) ** 2, 4)


@dataclass
class AdaptiveRetrievalResult:
    """Telemetry and results for an adaptive retrieval query."""
    hits: List[Tuple[Chunk, float]]
    complexity: QueryComplexity
    cache_tier: str  # "L1_EXACT", "L2_SEMANTIC", "MISS"
    cache_similarity: Optional[float]
    retrieval_mode_chosen: str  # "cached", "sparse", "dense", "hybrid"
    energy_saving_reason: str
    original_candidate_count: int
    pruned_candidate_count: int
    attention_work_ratio: float = 1.0
    context_tokens_approx: int = 0


class BM25Retriever:
    """
    Sparse Lexical Retriever using BM25Plus.
    BM25Plus prevents the Robertson zero-IDF penalty on small corpora.
    Zero GPU computation at runtime; instant keyword lookup.
    """

    def __init__(self, chunks: List[Chunk]):
        self.chunks = chunks
        self.tokenized_corpus = [self._tokenize(c.text) for c in chunks]
        has_tokens = any(len(tokens) > 0 for tokens in self.tokenized_corpus)
        self.bm25 = BM25Plus(self.tokenized_corpus) if (chunks and has_tokens) else None

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return re.findall(r"\w+", text.lower())

    def search(self, query: str, top_k: int = 5) -> List[Tuple[Chunk, float]]:
        """Retrieve top_k chunks using lexical BM25."""
        if not self.bm25 or not self.chunks or top_k <= 0:
            return []

        tokenized_query = self._tokenize(query)
        if not tokenized_query:
            return []

        scores = self.bm25.get_scores(tokenized_query)
        ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)

        results: List[Tuple[Chunk, float]] = []
        for idx in ranked_indices[:top_k]:
            if scores[idx] > 0.0:  # only return relevant hits
                results.append((self.chunks[idx], float(scores[idx])))
        return results


class DenseRetriever:
    """
    Dense Semantic Retriever utilizing an embedding service and FAISS Vector Store.
    """

    def __init__(self, vector_store: FAISSVectorStore, embedding_service: BaseEmbeddingService):
        self.vector_store = vector_store
        self.embedding_service = embedding_service

    def search(
        self,
        query: str,
        top_k: int = 5,
        score_threshold: Optional[float] = None
    ) -> List[Tuple[Chunk, float]]:
        """Embed query and search FAISS index."""
        query_vector = self.embedding_service.embed_text(query)
        return self.vector_store.search(
            query_vector=query_vector,
            top_k=top_k,
            score_threshold=score_threshold
        )


class HybridRetriever:
    """
    Hybrid Retriever combining Dense Semantic Search and Sparse BM25 Search.
    Fuses rankings using Reciprocal Rank Fusion (RRF):
        RRF_Score(d) = sum_{m in {dense, bm25}} (1 / (rrf_k + Rank_m(d)))
    """

    def __init__(
        self,
        dense_retriever: DenseRetriever,
        bm25_retriever: BM25Retriever,
        rrf_k: int = 60,
        dense_weight: float = 1.0,
        sparse_weight: float = 1.0,
    ):
        self.dense_retriever = dense_retriever
        self.bm25_retriever = bm25_retriever
        self.rrf_k = rrf_k
        self.dense_weight = dense_weight
        self.sparse_weight = sparse_weight

    def search(
        self,
        query: str,
        top_k: int = 5,
        candidate_multiplier: int = 3
    ) -> List[Tuple[Chunk, float]]:
        """
        Execute both retrievers, pool candidates, and compute fused RRF score.
        """
        fetch_k = top_k * candidate_multiplier

        dense_hits = self.dense_retriever.search(query, top_k=fetch_k)
        sparse_hits = self.bm25_retriever.search(query, top_k=fetch_k)

        # Map chunk_id to Chunk object and RRF score
        chunk_map: Dict[str, Chunk] = {}
        rrf_scores: Dict[str, float] = {}

        # 1. Score Dense Ranks
        for rank, (chunk, _) in enumerate(dense_hits, 1):
            chunk_map[chunk.chunk_id] = chunk
            score = self.dense_weight * (1.0 / (self.rrf_k + rank))
            rrf_scores[chunk.chunk_id] = rrf_scores.get(chunk.chunk_id, 0.0) + score

        # 2. Score Sparse Ranks
        for rank, (chunk, _) in enumerate(sparse_hits, 1):
            chunk_map[chunk.chunk_id] = chunk
            score = self.sparse_weight * (1.0 / (self.rrf_k + rank))
            rrf_scores[chunk.chunk_id] = rrf_scores.get(chunk.chunk_id, 0.0) + score

        # 3. Sort by combined RRF score
        sorted_chunk_ids = sorted(rrf_scores.keys(), key=lambda cid: rrf_scores[cid], reverse=True)

        results: List[Tuple[Chunk, float]] = [
            (chunk_map[cid], rrf_scores[cid])
            for cid in sorted_chunk_ids[:top_k]
        ]
        return results


class AdaptiveRetriever:
    """
    Unified Adaptive Retrieval Engine (EcoRAG Layer 1 + Layer 2 + Layer 4).
    Dynamically routes queries based on complexity, checks L1/L2 caches,
    and applies dynamic context filtering.
    """

    def __init__(
        self,
        dense_retriever: DenseRetriever,
        bm25_retriever: BM25Retriever,
        hybrid_retriever: HybridRetriever,
        embedding_service: BaseEmbeddingService,
        exact_cache: Optional[ExactQueryCache] = None,
        semantic_cache: Optional[SemanticQueryCache] = None,
        classifier: Optional[QueryClassifier] = None,
        context_filter: Optional[DynamicContextFilter] = None,
    ):
        self.dense_retriever = dense_retriever
        self.bm25_retriever = bm25_retriever
        self.hybrid_retriever = hybrid_retriever
        self.embedding_service = embedding_service
        self.exact_cache = exact_cache or ExactQueryCache()
        self.semantic_cache = semantic_cache or SemanticQueryCache(threshold=0.90)
        self.classifier = classifier or QueryClassifier()
        self.context_filter = context_filter or DynamicContextFilter()

        # Telemetry stats
        self.total_queries = 0
        self.exact_cache_hits = 0
        self.semantic_cache_hits = 0
        self.sparse_routed_queries = 0
        self.dense_routed_queries = 0
        self.hybrid_routed_queries = 0

    def search(
        self,
        query: str,
        top_k: int = 5,
        use_cache: bool = True,
        apply_dynamic_filter: bool = True,
        force_mode: Optional[str] = None,
        window_size: int = 0
    ) -> AdaptiveRetrievalResult:
        """
        Adaptive retrieval workflow:
        1. Check L1 Exact Hash Cache.
        2. Check L2 Semantic Vector Cache (threshold >= 0.92).
        3. Classify Query Complexity (SIMPLE, NORMAL, COMPLEX).
        4. Route to minimal sufficient retriever (BM25, Dense FAISS, or Hybrid RRF).
        5. Apply Dynamic Context Filtering (tau_min cutoff).
        6. Store into caches for future queries.
        """
        self.total_queries += 1

        # 1. L1 Exact Cache Check
        if use_cache:
            l1_hit = self.exact_cache.get(query)
            if l1_hit is not None:
                self.exact_cache_hits += 1
                hits = l1_hit[:top_k]
                tokens = sum(c.token_count_approx for c, _ in hits)
                return AdaptiveRetrievalResult(
                    hits=hits,
                    complexity=QueryComplexity.SIMPLE,
                    cache_tier="L1_EXACT",
                    cache_similarity=1.0,
                    retrieval_mode_chosen="cached",
                    energy_saving_reason="L1 Exact Query Hash Match: 100% downstream compute bypassed.",
                    original_candidate_count=len(l1_hit),
                    pruned_candidate_count=0,
                    attention_work_ratio=SentenceWindowExpander.calculate_attention_work_ratio(tokens),
                    context_tokens_approx=tokens
                )

        # 2. Query Classification
        complexity = self.classifier.classify(query)

        # If simple query, BM25 needs no query vector -> execute BM25 directly to save embedding compute!
        mode = force_mode or ("sparse" if complexity == QueryComplexity.SIMPLE else None)

        query_vector: Optional[List[float]] = None

        # Check L2 Semantic Cache if mode not forced to sparse
        if use_cache and mode != "sparse":
            query_vector = self.embedding_service.embed_text(query)
            l2_res = self.semantic_cache.get(query_vector)
            if l2_res is not None:
                hits, sim = l2_res
                self.semantic_cache_hits += 1
                l2_hits = hits[:top_k]
                tokens = sum(c.token_count_approx for c, _ in l2_hits)
                return AdaptiveRetrievalResult(
                    hits=l2_hits,
                    complexity=complexity,
                    cache_tier="L2_SEMANTIC",
                    cache_similarity=round(sim, 4),
                    retrieval_mode_chosen="cached",
                    energy_saving_reason=f"L2 Semantic Cache Match ({sim:.2f} >= 0.92): Bypassed index search & reranker.",
                    original_candidate_count=len(hits),
                    pruned_candidate_count=0,
                    attention_work_ratio=SentenceWindowExpander.calculate_attention_work_ratio(tokens),
                    context_tokens_approx=tokens
                )

        # 3. Dynamic Routing
        if mode == "sparse" or complexity == QueryComplexity.SIMPLE:
            self.sparse_routed_queries += 1
            mode_used = "sparse"
            reason = "Simple factoid / keyword query routed to BM25 (Zero GPU/embedding compute)."
            candidates = self.bm25_retriever.search(query, top_k=top_k * 2)

        elif mode == "dense" or complexity == QueryComplexity.NORMAL:
            self.dense_routed_queries += 1
            mode_used = "dense"
            reason = "Normal conceptual query routed to Dense FAISS (Single bi-encoder pass)."
            if query_vector is None:
                query_vector = self.embedding_service.embed_text(query)
            candidates = self.dense_retriever.search(query, top_k=top_k * 2)

        else:  # mode == "hybrid" or complexity == QueryComplexity.COMPLEX:
            self.hybrid_routed_queries += 1
            mode_used = "hybrid"
            reason = "Complex comparative query routed to Hybrid RRF (BM25 + Dense fusion)."
            candidates = self.hybrid_retriever.search(query, top_k=top_k * 2)

        orig_count = len(candidates)

        # 4. Dynamic Context Filtering (tau_min threshold)
        if apply_dynamic_filter and candidates:
            filtered_candidates = self.context_filter.filter_chunks(candidates)
            pruned_count = orig_count - len(filtered_candidates)
        else:
            filtered_candidates = candidates
            pruned_count = 0

        final_hits = filtered_candidates[:top_k]

        # 5. Optional Sentence-Window Expansion
        if window_size > 0 and final_hits:
            final_hits = SentenceWindowExpander(default_window=window_size).expand_hits(final_hits, window_size=window_size)

        # 6. Populate Caches
        if use_cache and final_hits:
            self.exact_cache.set(query, final_hits)
            if query_vector is not None:
                self.semantic_cache.set(query, query_vector, final_hits)

        tokens = sum(c.token_count_approx for c, _ in final_hits)
        return AdaptiveRetrievalResult(
            hits=final_hits,
            complexity=complexity,
            cache_tier="MISS",
            cache_similarity=None,
            retrieval_mode_chosen=mode_used,
            energy_saving_reason=reason,
            original_candidate_count=orig_count,
            pruned_candidate_count=pruned_count,
            attention_work_ratio=SentenceWindowExpander.calculate_attention_work_ratio(tokens),
            context_tokens_approx=tokens
        )


import json
import os
import time
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

from src.ingestion import Document, Chunk, TextChunker, ChunkDeduplicator
from src.embeddings import LocalEmbeddingService, BaseEmbeddingService
from src.vector_store import FAISSVectorStore
from src.reranker import ThresholdGatedReranker, RerankResult
from src.retrieval import (
    BM25Retriever,
    DenseRetriever,
    HybridRetriever,
    ExactQueryCache,
    SemanticQueryCache,
    DynamicContextFilter,
    AdaptiveRetriever,
    AdaptiveRetrievalResult
)

logger = logging.getLogger(__name__)


@dataclass
class ExperimentConfig:
    """Configuration parameters defining a specific RAG pipeline variation."""
    name: str
    chunk_size: int = 512
    chunk_overlap: int = 50
    retrieval_mode: str = "adaptive"  # "dense", "sparse", "hybrid", "adaptive"
    use_reranker: bool = True
    reranker_bypass_threshold: float = 0.85
    use_cache: bool = True
    compress_context: bool = True
    top_k: int = 3


@dataclass
class BenchmarkItem:
    """A single evaluation query with ground-truth labels."""
    query_id: str
    query: str
    expected_doc_ids: List[str]
    expected_answer_keywords: List[str]
    complexity: str = "normal"


@dataclass
class BenchmarkDataset:
    """Evaluation dataset containing documents and labeled queries."""
    dataset_name: str
    version: str
    documents: List[Document]
    queries: List[BenchmarkItem]

    @classmethod
    def load_from_json(cls, json_path: str) -> "BenchmarkDataset":
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        docs = [
            Document(doc_id=d["doc_id"], content=d["content"])
            for d in data.get("documents", [])
        ]
        queries = [
            BenchmarkItem(
                query_id=q["query_id"],
                query=q["query"],
                expected_doc_ids=q["expected_doc_ids"],
                expected_answer_keywords=q.get("expected_answer_keywords", []),
                complexity=q.get("complexity", "normal")
            )
            for q in data.get("queries", [])
        ]
        return cls(
            dataset_name=data.get("dataset_name", "Benchmark"),
            version=data.get("version", "1.0"),
            documents=docs,
            queries=queries
        )


@dataclass
class QueryResultMetrics:
    """Metrics captured for a single benchmark query execution."""
    query_id: str
    recall_at_k: float
    precision_at_k: float
    reciprocal_rank: float
    keyword_coverage: float
    latency_ms: float
    ram_mb: float
    estimated_wh: float
    cache_hit: bool
    rerank_bypassed: bool
    retrieved_doc_ids: List[str]


@dataclass
class ExperimentResult:
    """Summary of benchmark execution for an entire pipeline configuration."""
    config: ExperimentConfig
    mean_recall: float
    mean_precision: float
    mrr: float
    accuracy_proxy: float
    mean_latency_ms: float
    peak_ram_mb: float
    total_wh: float
    wh_per_query: float
    cost_per_successful_answer: float
    cache_hit_rate: float
    rerank_bypass_rate: float
    eco_score: float
    query_metrics: List[QueryResultMetrics] = field(default_factory=list)


class ExperimentManager:
    """
    Automated evaluation and benchmarking harness for EcoRAG.
    Systematically executes experiment configurations across benchmark datasets,
    captures physical and algorithmic telemetry, and computes the Pareto Frontier.
    """

    def __init__(
        self,
        embedding_service: Optional[BaseEmbeddingService] = None,
        reranker: Optional[ThresholdGatedReranker] = None
    ):
        self.embedding_service = embedding_service or LocalEmbeddingService()
        self.reranker = reranker or ThresholdGatedReranker()
        self.context_filter = DynamicContextFilter()

    def run_experiment(
        self,
        config: ExperimentConfig,
        dataset: BenchmarkDataset
    ) -> ExperimentResult:
        """Execute a single experiment configuration across the dataset."""
        logger.info("Executing experiment '%s' (chunk=%d, mode=%s, reranker=%s, cache=%s)",
                    config.name, config.chunk_size, config.retrieval_mode, config.use_reranker, config.use_cache)

        # 1. Chunk and Ingest documents with configured chunk size
        chunker = TextChunker(chunk_size=config.chunk_size, chunk_overlap=config.chunk_overlap)
        deduplicator = ChunkDeduplicator()
        all_chunks: List[Chunk] = []

        for doc in dataset.documents:
            raw_chunks = chunker.chunk_document(doc)
            unique_chunks = deduplicator.deduplicate_chunks(raw_chunks)
            all_chunks.extend(unique_chunks)

        if not all_chunks:
            raise ValueError(f"No chunks generated for dataset with chunk_size={config.chunk_size}")

        # 2. Embed and build vector store
        chunk_texts = [c.text for c in all_chunks]
        embeddings = self.embedding_service.embed_batch(chunk_texts)
        vector_store = FAISSVectorStore(dimension=self.embedding_service.dimension)
        vector_store.add_chunks(all_chunks, embeddings)

        # 3. Setup retrieval components
        bm25_retriever = BM25Retriever(all_chunks)
        dense_retriever = DenseRetriever(vector_store, self.embedding_service)
        hybrid_retriever = HybridRetriever(dense_retriever, bm25_retriever)
        
        exact_cache = ExactQueryCache() if config.use_cache else None
        semantic_cache = SemanticQueryCache(threshold=0.92) if config.use_cache else None

        adaptive_retriever = AdaptiveRetriever(
            dense_retriever=dense_retriever,
            bm25_retriever=bm25_retriever,
            hybrid_retriever=hybrid_retriever,
            embedding_service=self.embedding_service,
            exact_cache=exact_cache,
            semantic_cache=semantic_cache,
            context_filter=self.context_filter
        )

        query_metrics: List[QueryResultMetrics] = []
        ram_measurements: List[float] = []

        # Run queries
        for item in dataset.queries:
            q_start = time.perf_counter()
            ram_start = (psutil.Process().memory_info().rss / (1024 * 1024)) if HAS_PSUTIL else 256.0

            cache_tier = "MISS"
            rerank_bypassed = not config.use_reranker
            final_hits: List[Tuple[Chunk, float]] = []

            mode = config.retrieval_mode.lower()

            if mode == "adaptive":
                adaptive_res = adaptive_retriever.search(
                    query=item.query,
                    top_k=config.top_k,
                    use_cache=config.use_cache,
                    apply_dynamic_filter=config.compress_context
                )
                candidates = adaptive_res.hits
                cache_tier = adaptive_res.cache_tier

                if cache_tier != "MISS":
                    final_hits = candidates[:config.top_k]
                    rerank_bypassed = True
                elif config.use_reranker:
                    self.reranker.confidence_threshold = config.reranker_bypass_threshold
                    rerank_res = self.reranker.rerank(
                        query=item.query,
                        candidates=candidates,
                        top_k=config.top_k
                    )
                    final_hits = rerank_res.ranked_chunks
                    rerank_bypassed = rerank_res.bypassed
                else:
                    final_hits = candidates[:config.top_k]
            elif mode == "sparse":
                candidates = bm25_retriever.search(item.query, top_k=config.top_k * 2)
                if config.use_reranker:
                    self.reranker.confidence_threshold = config.reranker_bypass_threshold
                    rerank_res = self.reranker.rerank(query=item.query, candidates=candidates, top_k=config.top_k)
                    final_hits = rerank_res.ranked_chunks
                    rerank_bypassed = rerank_res.bypassed
                else:
                    final_hits = candidates[:config.top_k]
            elif mode == "dense":
                candidates = dense_retriever.search(item.query, top_k=config.top_k * 2)
                if config.use_reranker:
                    self.reranker.confidence_threshold = config.reranker_bypass_threshold
                    rerank_res = self.reranker.rerank(query=item.query, candidates=candidates, top_k=config.top_k)
                    final_hits = rerank_res.ranked_chunks
                    rerank_bypassed = rerank_res.bypassed
                else:
                    final_hits = candidates[:config.top_k]
            elif mode == "hybrid":
                candidates = hybrid_retriever.search(item.query, top_k=config.top_k * 2)
                if config.use_reranker:
                    self.reranker.confidence_threshold = config.reranker_bypass_threshold
                    rerank_res = self.reranker.rerank(query=item.query, candidates=candidates, top_k=config.top_k)
                    final_hits = rerank_res.ranked_chunks
                    rerank_bypassed = rerank_res.bypassed
                else:
                    final_hits = candidates[:config.top_k]
            else:
                raise ValueError(f"Unsupported retrieval mode: {config.retrieval_mode}")

            # Optional context compression if not already done by adaptive
            if config.compress_context and mode != "adaptive":
                compressed_hits = []
                for c, score in final_hits:
                    comp_text = self.context_filter.compress_chunk_sentences(c, item.query, max_sentences=3)
                    comp_chunk = Chunk(
                        text=comp_text,
                        chunk_id=c.chunk_id,
                        doc_id=c.doc_id,
                        chunk_index=c.chunk_index,
                        char_length=len(comp_text),
                        token_count_approx=len(comp_text.split()),
                        metadata=c.metadata
                    )
                    compressed_hits.append((comp_chunk, score))
                final_hits = compressed_hits

            latency_sec = time.perf_counter() - q_start
            latency_ms = latency_sec * 1000.0

            ram_end = (psutil.Process().memory_info().rss / (1024 * 1024)) if HAS_PSUTIL else 260.0
            ram_measurements.append(max(ram_start, ram_end))

            # Energy estimation in Watt-hours (45W nominal baseline * execution hours)
            estimated_wh = 45.0 * (latency_sec / 3600.0)
            if cache_tier != "MISS":
                estimated_wh *= 0.20  # 80% reduction for cache hit
            elif rerank_bypassed:
                estimated_wh *= 0.65  # 35% discount for bypassing cross-encoder

            # Retrieval Quality Metrics
            retrieved_doc_ids = [c.doc_id for c, _ in final_hits]
            expected_set = set(item.expected_doc_ids)

            # Recall@K: proportion of expected docs retrieved in top_k
            matched_docs = [did for did in retrieved_doc_ids if did in expected_set]
            recall_at_k = len(matched_docs) / len(expected_set) if expected_set else 1.0

            # Precision@K: proportion of retrieved docs that are relevant
            precision_at_k = len(matched_docs) / len(retrieved_doc_ids) if retrieved_doc_ids else 0.0

            # MRR: Reciprocal rank of the first relevant document
            reciprocal_rank = 0.0
            for rank, did in enumerate(retrieved_doc_ids, start=1):
                if did in expected_set:
                    reciprocal_rank = 1.0 / rank
                    break

            # Keyword Coverage proxy
            retrieved_combined_text = " ".join([c.text.lower() for c, _ in final_hits])
            matched_keywords = sum(
                1 for kw in item.expected_answer_keywords
                if kw.lower() in retrieved_combined_text
            )
            kw_coverage = matched_keywords / len(item.expected_answer_keywords) if item.expected_answer_keywords else 1.0

            query_metrics.append(QueryResultMetrics(
                query_id=item.query_id,
                recall_at_k=round(recall_at_k, 4),
                precision_at_k=round(precision_at_k, 4),
                reciprocal_rank=round(reciprocal_rank, 4),
                keyword_coverage=round(kw_coverage, 4),
                latency_ms=round(latency_ms, 2),
                ram_mb=round(max(ram_start, ram_end), 1),
                estimated_wh=round(estimated_wh, 6),
                cache_hit=(cache_tier != "MISS"),
                rerank_bypassed=rerank_bypassed,
                retrieved_doc_ids=retrieved_doc_ids
            ))

        # Aggregate metrics
        n_queries = len(query_metrics)
        mean_recall = sum(m.recall_at_k for m in query_metrics) / n_queries if n_queries else 0.0
        mean_precision = sum(m.precision_at_k for m in query_metrics) / n_queries if n_queries else 0.0
        mean_mrr = sum(m.reciprocal_rank for m in query_metrics) / n_queries if n_queries else 0.0
        mean_kw_cov = sum(m.keyword_coverage for m in query_metrics) / n_queries if n_queries else 0.0

        # Accuracy proxy = 0.6 * Recall + 0.4 * Keyword Coverage
        accuracy_proxy = round((0.6 * mean_recall) + (0.4 * mean_kw_cov), 4)

        mean_latency = sum(m.latency_ms for m in query_metrics) / n_queries if n_queries else 0.0
        peak_ram = max(ram_measurements) if ram_measurements else 256.0
        total_wh = sum(m.estimated_wh for m in query_metrics)
        wh_per_query = total_wh / n_queries if n_queries else 0.0

        cache_hits = sum(1 for m in query_metrics if m.cache_hit)
        cache_hit_rate = round(cache_hits / n_queries, 4) if n_queries else 0.0

        rerank_bypasses = sum(1 for m in query_metrics if m.rerank_bypassed)
        rerank_bypass_rate = round(rerank_bypasses / n_queries, 4) if n_queries else 0.0

        # Cost per successful answer: Assume standard nominal cost of $0.001 per non-cache query
        successful_queries = sum(1 for m in query_metrics if m.recall_at_k >= 0.5)
        total_cost = sum(0.0002 if m.cache_hit else 0.0010 for m in query_metrics)
        cost_per_success = round(total_cost / max(1, successful_queries), 6)

        # Composite Eco Score = Accuracy / Resource Penalty
        mean_sec = mean_latency / 1000.0
        resource_penalty = 1.0 + (mean_sec * 0.5) + (wh_per_query * 150.0)
        eco_score = round(max(0.1, (accuracy_proxy * 10.0) / resource_penalty), 2)

        return ExperimentResult(
            config=config,
            mean_recall=round(mean_recall, 4),
            mean_precision=round(mean_precision, 4),
            mrr=round(mean_mrr, 4),
            accuracy_proxy=accuracy_proxy,
            mean_latency_ms=round(mean_latency, 2),
            peak_ram_mb=round(peak_ram, 1),
            total_wh=round(total_wh, 5),
            wh_per_query=round(wh_per_query, 6),
            cost_per_successful_answer=cost_per_success,
            cache_hit_rate=cache_hit_rate,
            rerank_bypass_rate=rerank_bypass_rate,
            eco_score=eco_score,
            query_metrics=query_metrics
        )

    def run_suite(
        self,
        configs: List[ExperimentConfig],
        dataset: BenchmarkDataset
    ) -> List[ExperimentResult]:
        """Run multiple experiment configurations sequentially."""
        results = []
        for config in configs:
            res = self.run_experiment(config, dataset)
            results.append(res)
        return results

    @staticmethod
    def compute_pareto_frontier(results: List[ExperimentResult]) -> List[ExperimentResult]:
        """
        Identify the Pareto Frontier configurations.
        A configuration A dominates B if:
        - Accuracy Proxy(A) >= Accuracy Proxy(B) AND
        - Total Resource Cost(A) <= Total Resource Cost(B)
        with at least one strict inequality.
        """
        frontier: List[ExperimentResult] = []

        for candidate in results:
            is_dominated = False
            for other in results:
                if other is candidate:
                    continue
                higher_or_eq_acc = other.accuracy_proxy >= candidate.accuracy_proxy
                lower_or_eq_wh = other.wh_per_query <= candidate.wh_per_query
                lower_or_eq_lat = other.mean_latency_ms <= candidate.mean_latency_ms

                strict_acc = other.accuracy_proxy > candidate.accuracy_proxy
                strict_wh = other.wh_per_query < candidate.wh_per_query
                strict_lat = other.mean_latency_ms < candidate.mean_latency_ms

                if higher_or_eq_acc and lower_or_eq_wh and lower_or_eq_lat and (strict_acc or strict_wh or strict_lat):
                    is_dominated = True
                    break

            if not is_dominated:
                frontier.append(candidate)

        return frontier

    @staticmethod
    def format_comparison_table(results: List[ExperimentResult]) -> str:
        """Format a list of experiment results into a clean markdown table."""
        header = (
            "| Configuration | Chunk | Mode | Recall@K | MRR | Acc Proxy | Latency | Wh/Query | Cost/Ans | Eco Score |\n"
            "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |"
        )
        rows = []
        for r in results:
            cfg = r.config
            row = (
                f"| **{cfg.name}** | {cfg.chunk_size} | {cfg.retrieval_mode} | "
                f"{r.mean_recall * 100:.1f}% | {r.mrr:.3f} | {r.accuracy_proxy * 100:.1f}% | "
                f"{r.mean_latency_ms:.1f} ms | {r.wh_per_query * 1000:.3f} mWh | "
                f"${r.cost_per_successful_answer:.4f} | **{r.eco_score:.2f}** |"
            )
            rows.append(row)
        return header + "\n" + "\n".join(rows)

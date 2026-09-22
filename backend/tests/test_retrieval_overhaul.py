import pytest
import numpy as np
from src.ingestion import Document, MarkdownChunker, DocumentIngestionPipeline, Chunk
from src.embeddings import LocalEmbeddingService
from src.vector_store import FAISSVectorStore
from src.retrieval import (
    QueryComplexity,
    QueryClassifier,
    ExactQueryCache,
    SemanticQueryCache,
    DynamicContextFilter,
    BM25Retriever,
    DenseRetriever,
    HybridRetriever,
    AdaptiveRetriever,
)


class TestMarkdownChunker:
    def test_markdown_header_hierarchy_preservation(self):
        md_text = """# EcoRAG Framework
Intro paragraph about EcoRAG.

## Layer 1: Retrieval Efficiency
Selective hybrid and threshold-gated reranking details.

### 1.1 Sparse BM25
Zero neural compute at runtime.

## Layer 2: Context Efficiency
Dynamic context sizing and sentence extraction.
"""
        doc = Document(doc_id="test_doc.md", content=md_text)
        chunker = MarkdownChunker(max_chunk_size=100, chunk_overlap=10)
        chunks = chunker.chunk_document(doc)

        assert len(chunks) == 4
        # Verify first chunk header
        assert chunks[0].metadata["headers"] == ["EcoRAG Framework"]
        assert "Intro paragraph" in chunks[0].text

        # Verify hierarchical header path in sub-section
        assert chunks[2].metadata["headers"] == ["EcoRAG Framework", "Layer 1: Retrieval Efficiency", "1.1 Sparse BM25"]
        assert "[EcoRAG Framework > Layer 1: Retrieval Efficiency > 1.1 Sparse BM25]" in chunks[2].text
        assert "Zero neural compute" in chunks[2].text

    def test_markdown_long_section_subchunking(self):
        long_body = "word " * 300
        md_text = f"# Big Section\n{long_body}"
        doc = Document(doc_id="big.md", content=md_text)
        chunker = MarkdownChunker(max_chunk_size=100, chunk_overlap=20)
        chunks = chunker.chunk_document(doc)

        assert len(chunks) > 1
        for c in chunks:
            assert "Big Section" in c.text

    def test_pipeline_markdown_autodetection(self, tmp_path):
        md_file = tmp_path / "sample.md"
        md_file.write_text("# Title\nContent under title.\n## Subtitle\nMore text.", encoding="utf-8")

        pipeline = DocumentIngestionPipeline()
        chunks = pipeline.ingest_file(str(md_file))

        assert len(chunks) == 2
        assert chunks[0].metadata.get("is_markdown") is True


class TestQueryClassifier:
    def setup_method(self):
        self.classifier = QueryClassifier()

    def test_classify_simple_query(self):
        assert self.classifier.classify("API-009") == QueryComplexity.SIMPLE
        assert self.classifier.classify("BM25") == QueryComplexity.SIMPLE
        assert self.classifier.classify("what is FAISS") == QueryComplexity.SIMPLE
        assert self.classifier.classify("formula for eco_score") == QueryComplexity.SIMPLE

    def test_classify_normal_query(self):
        assert self.classifier.classify("how does selective hybrid retrieval reduce energy consumption") == QueryComplexity.NORMAL
        assert self.classifier.classify("explain the purpose of document deduplication") == QueryComplexity.NORMAL

    def test_classify_complex_query(self):
        assert self.classifier.classify("compare cross-encoder vs bi-encoder trade-offs in RAG pipelines") == QueryComplexity.COMPLEX
        assert self.classifier.classify("what is the difference between exact cache and semantic cache in energy saving") == QueryComplexity.COMPLEX
        assert self.classifier.classify("analyze the relationship between quadratic prefill attention and context compression") == QueryComplexity.COMPLEX


class TestQueryCaches:
    def test_exact_query_cache(self):
        cache = ExactQueryCache(max_entries=2)
        dummy_chunk = Chunk(text="dummy", chunk_id="c1", doc_id="d1", chunk_index=0, char_length=5, token_count_approx=1)
        results = [(dummy_chunk, 0.95)]

        cache.set("what is ecorag?", results)
        assert cache.get("WHAT is EcoRAG?  ") is not None  # Normalized match
        assert cache.get("something else") is None

        # Test eviction
        cache.set("q2", results)
        cache.set("q3", results)
        assert cache.size == 2

    def test_semantic_query_cache(self):
        cache = SemanticQueryCache(threshold=0.92)
        dummy_chunk = Chunk(text="dummy", chunk_id="c1", doc_id="d1", chunk_index=0, char_length=5, token_count_approx=1)
        results = [(dummy_chunk, 0.99)]

        v1 = [1.0, 0.0, 0.0]
        cache.set("query 1", v1, results)

        # High similarity vector (cosine ~ 0.99)
        v_similar = [0.99, 0.05, 0.0]
        hit = cache.get(v_similar)
        assert hit is not None
        assert hit[1] >= 0.92

        # Low similarity vector (cosine = 0.0)
        v_different = [0.0, 1.0, 0.0]
        assert cache.get(v_different) is None


class TestDynamicContextFilter:
    def test_filter_chunks_thresholds(self):
        c1 = Chunk(text="best chunk", chunk_id="1", doc_id="d", chunk_index=0, char_length=10, token_count_approx=2)
        c2 = Chunk(text="good chunk", chunk_id="2", doc_id="d", chunk_index=1, char_length=10, token_count_approx=2)
        c3 = Chunk(text="irrelevant chunk", chunk_id="3", doc_id="d", chunk_index=2, char_length=10, token_count_approx=2)

        hits = [(c1, 0.90), (c2, 0.70), (c3, 0.15)]
        flt = DynamicContextFilter(min_absolute_score=0.20, relative_drop_ratio=0.50)

        filtered = flt.filter_chunks(hits)
        assert len(filtered) == 2
        assert filtered[0][0].chunk_id == "1"
        assert filtered[1][0].chunk_id == "2"

    def test_compress_chunk_sentences(self):
        chunk = Chunk(
            text="Sentence one is introductory. Sentence two discusses FAISS vector indexing in detail. Sentence three is unrelated.",
            chunk_id="1",
            doc_id="d",
            chunk_index=0,
            char_length=100,
            token_count_approx=20
        )
        compressed = DynamicContextFilter.compress_chunk_sentences(chunk, "FAISS vector indexing", max_sentences=1)
        assert "FAISS vector indexing in detail" in compressed
        assert "Sentence one is introductory" not in compressed


class TestAdaptiveRetrieverEndToEnd:
    def test_adaptive_routing_and_caching(self):
        pipeline = DocumentIngestionPipeline(chunk_size=30, chunk_overlap=5)
        text = """# Hardware Energy
Intel RAPL and NVIDIA NVML monitor Watt-hours directly.
## BM25 Details
BM25 requires zero neural network computation.
## Trade-offs
Comparing bi-encoder vs cross-encoder accuracy and energy consumption.
"""
        chunks = pipeline.ingest_text(text, doc_id="test_md", is_markdown=True)
        embedder = LocalEmbeddingService("all-MiniLM-L6-v2")
        vstore = FAISSVectorStore(dimension=embedder.dimension)
        embeddings = embedder.embed_batch([c.text for c in chunks])
        vstore.add_chunks(chunks, embeddings)

        dense = DenseRetriever(vstore, embedder)
        bm25 = BM25Retriever(chunks)
        hybrid = HybridRetriever(dense, bm25)

        adaptive = AdaptiveRetriever(
            dense_retriever=dense,
            bm25_retriever=bm25,
            hybrid_retriever=hybrid,
            embedding_service=embedder
        )

        # 1. Simple query -> BM25
        res1 = adaptive.search("BM25", top_k=2)
        assert res1.complexity == QueryComplexity.SIMPLE
        assert res1.retrieval_mode_chosen == "sparse"
        assert res1.cache_tier == "MISS"

        # 2. Same query again -> L1 Exact Cache hit!
        res1_cached = adaptive.search("BM25", top_k=2)
        assert res1_cached.cache_tier == "L1_EXACT"
        assert res1_cached.retrieval_mode_chosen == "cached"

        # 3. Normal query -> Dense
        res2 = adaptive.search("how does Intel RAPL monitor energy", top_k=2)
        assert res2.complexity == QueryComplexity.NORMAL
        assert res2.retrieval_mode_chosen == "dense"

        # 4. Paraphrased query -> L2 Semantic Cache hit!
        res2_semantic = adaptive.search("how does Intel RAPL track energy usage", top_k=2)
        assert res2_semantic.cache_tier in ("L1_EXACT", "L2_SEMANTIC")

        # 5. Complex query -> Hybrid
        res3 = adaptive.search("compare bi-encoder vs cross-encoder trade-offs in accuracy and energy", top_k=2)
        assert res3.complexity == QueryComplexity.COMPLEX
        assert res3.retrieval_mode_chosen == "hybrid"

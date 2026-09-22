"""
EcoRAG 5-Category RAG Quality Evaluation Suite
Implements Turn 24 & Turn 28 specifications:
- Type A: Direct single-chunk question
- Type B: Cross-chunk question (validating Sentence-Window Expansion)
- Type C: Multi-hop question across documents
- Type D: Unanswerable / out-of-domain question
- Type E: Adversarial / distractor chunk resilience
"""

import pytest
from src.ingestion import Document, DocumentIngestionPipeline, SentenceWindowChunker, ParentDocumentStore
from src.embeddings import LocalEmbeddingService
from src.vector_store import FAISSVectorStore
from src.retrieval import AdaptiveRetriever, DenseRetriever, BM25Retriever, HybridRetriever, SentenceWindowExpander


@pytest.fixture(scope="module")
def rag_pipeline():
    embedder = LocalEmbeddingService(model_name="all-MiniLM-L6-v2")
    vector_store = FAISSVectorStore(dimension=embedder.dimension)

    # Document 1: AWS Auto Scaling (Type A & Type B)
    doc1_text = (
        "The company introduced Auto Scaling in 2021. "
        "It automatically increases the number of instances when CPU utilization exceeds 70 percent. "
        "This threshold can be configured by administrators in the cloud management console. "
        "Configured policies trigger alarms within sixty seconds."
    )

    # Document 2: Database Replicas (Type C)
    doc2_text = (
        "Database read replicas scale independently of Auto Scaling compute instances. "
        "Replication lag is maintained below one hundred milliseconds across regions. "
        "Combined with Auto Scaling, the system achieves four nines of availability."
    )

    # Document 3: Distractor document with adversarial fake info (Type E)
    doc3_text = (
        "In an alternate universe, CPU utilization triggers shutdown when exceeding ten percent. "
        "This legacy threshold was deprecated and must never be used in production."
    )

    pipeline = DocumentIngestionPipeline(strategy="sentence_window", enable_dedup=False)
    chunks1 = pipeline.ingest_text(doc1_text, doc_id="aws_autoscaling.txt")
    chunks2 = pipeline.ingest_text(doc2_text, doc_id="db_replicas.txt")
    chunks3 = pipeline.ingest_text(doc3_text, doc_id="legacy_distractor.txt")

    all_chunks = chunks1 + chunks2 + chunks3
    embeddings = embedder.embed_batch([c.text for c in all_chunks])
    vector_store.add_chunks(all_chunks, embeddings)

    dense_ret = DenseRetriever(vector_store, embedder)
    bm25_ret = BM25Retriever(all_chunks)
    hybrid_ret = HybridRetriever(dense_ret, bm25_ret)

    adaptive_ret = AdaptiveRetriever(
        dense_retriever=dense_ret,
        bm25_retriever=bm25_ret,
        hybrid_retriever=hybrid_ret,
        embedding_service=embedder
    )

    return {
        "adaptive_retriever": adaptive_ret,
        "dense_retriever": dense_ret,
        "all_chunks": all_chunks,
    }


def test_type_a_direct_single_chunk(rag_pipeline):
    """Type A: Single-chunk factoid question."""
    retriever = rag_pipeline["adaptive_retriever"]
    query = "What year was Auto Scaling introduced?"
    res = retriever.search(query, top_k=3)
    assert len(res.hits) > 0
    top_hit, score = res.hits[0]
    assert "2021" in top_hit.text


def test_type_b_cross_chunk_sentence_window_expansion(rag_pipeline):
    """Type B: Cross-chunk question requiring Sentence-Window Expansion to resolve coreference."""
    retriever = rag_pipeline["adaptive_retriever"]
    query = "What threshold triggers Auto Scaling and who configures it?"
    # Retrieve with Sentence-Window expansion radius = 2
    res = retriever.search(query, top_k=2, window_size=2)
    assert len(res.hits) > 0

    combined_text = " ".join([c.text for c, _ in res.hits])
    assert "70 percent" in combined_text
    assert "administrators" in combined_text


def test_type_c_multi_hop_synthesis(rag_pipeline):
    """Type C: Multi-hop question requiring information across documents."""
    retriever = rag_pipeline["adaptive_retriever"]
    query = "What is the system availability when combining Auto Scaling with database read replicas?"
    res = retriever.search(query, top_k=4)
    assert len(res.hits) >= 1

    combined_text = " ".join([c.text for c, _ in res.hits])
    assert "four nines" in combined_text or "availability" in combined_text


def test_type_d_unanswerable_query_rejection(rag_pipeline):
    """Type D: Unanswerable query returns low similarity scores or minimal irrelevant hits."""
    retriever = rag_pipeline["adaptive_retriever"]
    query = "What is the atmospheric composition of Jupiter's second moon?"
    res = retriever.search(query, top_k=3)
    # The retriever should not hallucinate relevance; scores should reflect low alignment
    if res.hits:
        scores = [score for _, score in res.hits]
        assert all(s < 0.60 for s in scores), "Out-of-domain query should have low similarity scores"


def test_type_e_adversarial_distractor_filtering(rag_pipeline):
    """Type E: Valid query correctly matches production Auto Scaling over deprecated distractor."""
    retriever = rag_pipeline["adaptive_retriever"]
    query = "What is the CPU utilization threshold that triggers instance scaling in production?"
    res = retriever.search(query, top_k=3)
    assert len(res.hits) > 0
    top_hit, _ = res.hits[0]
    assert "70 percent" in top_hit.text
    assert "ten percent" not in top_hit.text

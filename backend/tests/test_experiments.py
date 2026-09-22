import os
import pytest
from src.experiments import (
    ExperimentConfig,
    BenchmarkItem,
    BenchmarkDataset,
    ExperimentManager,
    ExperimentResult,
    QueryResultMetrics
)
from src.ingestion import Document


def test_benchmark_dataset_loading():
    benchmark_path = os.path.join(os.path.dirname(__file__), "..", "benchmarks", "data", "qa_benchmark.json")
    dataset = BenchmarkDataset.load_from_json(benchmark_path)
    assert len(dataset.documents) >= 5
    assert len(dataset.queries) >= 5
    for q in dataset.queries:
        assert q.query_id
        assert q.query
        assert len(q.expected_doc_ids) > 0


def test_pareto_frontier_logic():
    # Setup 3 dummy results
    cfg1 = ExperimentConfig(name="Heavy")
    res1 = ExperimentResult(
        config=cfg1,
        mean_recall=0.95,
        mean_precision=0.8,
        mrr=0.9,
        accuracy_proxy=0.95,
        mean_latency_ms=200.0,
        peak_ram_mb=300.0,
        total_wh=0.01,
        wh_per_query=0.002,
        cost_per_successful_answer=0.001,
        cache_hit_rate=0.0,
        rerank_bypass_rate=0.0,
        eco_score=5.0
    )

    # Clearly dominated by res3 (lower accuracy, higher latency and higher wh)
    cfg2 = ExperimentConfig(name="Inefficient")
    res2 = ExperimentResult(
        config=cfg2,
        mean_recall=0.80,
        mean_precision=0.7,
        mrr=0.75,
        accuracy_proxy=0.80,
        mean_latency_ms=180.0,
        peak_ram_mb=300.0,
        total_wh=0.009,
        wh_per_query=0.0018,
        cost_per_successful_answer=0.001,
        cache_hit_rate=0.0,
        rerank_bypass_rate=0.0,
        eco_score=4.5
    )

    # Highly efficient: equal or better accuracy with vastly lower energy & latency
    cfg3 = ExperimentConfig(name="EcoRAG")
    res3 = ExperimentResult(
        config=cfg3,
        mean_recall=0.94,
        mean_precision=0.85,
        mrr=0.92,
        accuracy_proxy=0.94,
        mean_latency_ms=40.0,
        peak_ram_mb=250.0,
        total_wh=0.002,
        wh_per_query=0.0004,
        cost_per_successful_answer=0.0003,
        cache_hit_rate=0.4,
        rerank_bypass_rate=0.6,
        eco_score=9.2
    )

    frontier = ExperimentManager.compute_pareto_frontier([res1, res2, res3])
    names = [f.config.name for f in frontier]
    assert "EcoRAG" in names
    assert "Heavy" in names
    assert "Inefficient" not in names  # Dominated by EcoRAG


def test_experiment_manager_run_single():
    # Mini dataset
    dataset = BenchmarkDataset(
        dataset_name="MiniTest",
        version="0.1",
        documents=[
            Document(doc_id="d1", content="Amazon Elastic Compute Cloud EC2 provides resizable compute capacity in AWS."),
            Document(doc_id="d2", content="Kubernetes CrashLoopBackOff happens when containers exit unexpectedly.")
        ],
        queries=[
            BenchmarkItem(
                query_id="q1",
                query="What is Amazon EC2 compute?",
                expected_doc_ids=["d1"],
                expected_answer_keywords=["EC2", "compute", "AWS"],
                complexity="simple"
            )
        ]
    )

    manager = ExperimentManager()
    cfg = ExperimentConfig(
        name="TestAdaptive",
        chunk_size=128,
        chunk_overlap=20,
        retrieval_mode="adaptive",
        use_reranker=False,
        use_cache=True,
        compress_context=True,
        top_k=2
    )

    result = manager.run_experiment(cfg, dataset)
    assert result.mean_recall == 1.0
    assert result.accuracy_proxy > 0.0
    assert result.mean_latency_ms > 0.0
    assert result.eco_score > 0.0
    assert len(result.query_metrics) == 1

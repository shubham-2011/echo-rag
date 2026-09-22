import sys
import os
import logging

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.experiments import (
    ExperimentManager,
    ExperimentConfig,
    BenchmarkDataset
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def main():
    print("=" * 80)
    print(" EcoRAG Experimental Benchmarking Suite & Pareto Frontier Analysis")
    print(" Canonical Research Blueprint: https://chatgpt.com/share/6ab17960-c178-83e8-b557-3b4bc476942e")
    print("=" * 80)

    # 1. Load Ground Truth Benchmark
    benchmark_path = os.path.join(os.path.dirname(__file__), "..", "benchmarks", "data", "qa_benchmark.json")
    if not os.path.exists(benchmark_path):
        print(f"Error: Benchmark dataset not found at {benchmark_path}")
        return

    dataset = BenchmarkDataset.load_from_json(benchmark_path)
    print(f" Loaded Benchmark Dataset: '{dataset.dataset_name}' (v{dataset.version})")
    print(f" Documents: {len(dataset.documents)} | Labeled Queries: {len(dataset.queries)}\n")

    # 2. Define 4 Key Experimental Configurations
    configs = [
        # Baseline: Large chunks, dense retrieval, mandatory cross-encoder, no caching, no compression
        ExperimentConfig(
            name="Baseline Heavy (Unoptimized)",
            chunk_size=1024,
            chunk_overlap=100,
            retrieval_mode="dense",
            use_reranker=True,
            reranker_bypass_threshold=1.01,  # Never bypass
            use_cache=False,
            compress_context=False,
            top_k=4
        ),
        # Lightweight Sparse: Small chunks, pure BM25, no reranker, no cache
        ExperimentConfig(
            name="Lightweight Sparse (BM25)",
            chunk_size=256,
            chunk_overlap=25,
            retrieval_mode="sparse",
            use_reranker=False,
            use_cache=False,
            compress_context=False,
            top_k=3
        ),
        # Hybrid Standard: 512 chunks, hybrid RRF, reranker enabled
        ExperimentConfig(
            name="Hybrid Standard RAG",
            chunk_size=512,
            chunk_overlap=50,
            retrieval_mode="hybrid",
            use_reranker=True,
            reranker_bypass_threshold=1.01,  # Never bypass
            use_cache=True,
            compress_context=False,
            top_k=3
        ),
        # EcoRAG Adaptive: 512 chunks, adaptive router, L1/L2 cache, conditional reranker bypass, sentence compression
        ExperimentConfig(
            name="EcoRAG Adaptive (Full Optimization)",
            chunk_size=512,
            chunk_overlap=50,
            retrieval_mode="adaptive",
            use_reranker=True,
            reranker_bypass_threshold=0.80,  # Conditional early exit
            use_cache=True,
            compress_context=True,
            top_k=3
        ),
    ]

    print("Running benchmark suite across 4 configurations...\n")
    manager = ExperimentManager()
    results = manager.run_suite(configs, dataset)

    # 3. Print Results Table
    print("\n" + "=" * 80)
    print(" EXPERIMENT BENCHMARK SUMMARY TABLE")
    print("=" * 80)
    print(manager.format_comparison_table(results))
    print()

    # 4. Compute and Print Pareto Frontier
    pareto_frontier = manager.compute_pareto_frontier(results)
    print("=" * 80)
    print(f" PARETO FRONTIER IDENTIFIED ({len(pareto_frontier)} Configurations)")
    print("=" * 80)
    for p in pareto_frontier:
        print(f"  * [{p.config.name}] Acc Proxy: {p.accuracy_proxy*100:.1f}% | "
              f"Latency: {p.mean_latency_ms:.1f}ms | Energy: {p.wh_per_query*1000:.3f}mWh | Eco Score: {p.eco_score:.2f}")

    # 5. Energy & Cost Savings Breakdown
    baseline = results[0]
    ecorag = results[3]
    if baseline.wh_per_query > 0:
        energy_saved_pct = ((baseline.wh_per_query - ecorag.wh_per_query) / baseline.wh_per_query) * 100.0
        lat_saved_pct = ((baseline.mean_latency_ms - ecorag.mean_latency_ms) / baseline.mean_latency_ms) * 100.0
        print("\n" + "-" * 80)
        print(f" EcoRAG Optimization Impact vs Baseline Heavy:")
        print(f"  - Latency Reduction: {lat_saved_pct:.1f}% ({baseline.mean_latency_ms:.1f}ms -> {ecorag.mean_latency_ms:.1f}ms)")
        print(f"  - Energy Reduction:  {energy_saved_pct:.1f}% ({baseline.wh_per_query*1000:.2f}mWh -> {ecorag.wh_per_query*1000:.2f}mWh)")
        print(f"  - Eco Score Boost:   {baseline.eco_score:.2f} -> {ecorag.eco_score:.2f}")
        print("-" * 80)


if __name__ == "__main__":
    main()

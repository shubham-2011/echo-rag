# Phase 1 — Existing Test and Benchmark Baseline

**Captured:** 2026-10-11
**Repository revision:** `fc55e7169ae6adfd9e8eb3c24704e46f0764c129`
**Purpose:** Preserve the observed pre-security state; these results are not claims about a different checkout or benchmark.

## Environment

| Item | Observed value |
|---|---|
| Python | 3.14.6, 64-bit |
| OS | Windows 11, build 10.0.26300 |
| Virtual environment | No; system interpreter at `C:\Python314\python.exe` |
| pytest | 9.1.1 |
| Dependency source | Installed Python environment; `backend/requirements.txt` declares dependencies |

## Test baseline

Command: `python -m pytest tests -q` from `backend/`

| Result | Count |
|---|---:|
| Passed | 39 |
| Failed | 0 |
| Skipped | 0 |
| Errors | 0 |
| Warnings | 1 Starlette deprecation warning for `httpx` use by `TestClient` |

## EcoRAG retrieval benchmark baseline

Command: `python examples/run_benchmark_suite.py` from `backend/`

Dataset: `backend/benchmarks/data/qa_benchmark.json`, “EcoRAG Standard Infrastructure QA Benchmark” v1.0, **5 documents / 5 labeled queries**. The suite ran all four existing configurations unchanged.

| Configuration | Recall@K | MRR | Accuracy proxy | Mean latency | Estimated Wh/query | Eco Score |
|---|---:|---:|---:|---:|---:|---:|
| Baseline Heavy (Unoptimized) | 100% | 1.000 | 100% | 1631.5 ms | 20.393 mWh | 2.05 |
| Lightweight Sparse (BM25) | 100% | 1.000 | 100% | 0.1 ms | 0.001 mWh | 10.00 |
| Hybrid Standard RAG | 100% | 1.000 | 100% | 172.7 ms | 2.159 mWh | 7.09 |
| EcoRAG Adaptive (Full Optimization) | 100% | 1.000 | 100% | 62.0 ms | 0.682 mWh | 8.82 |

The harness reported one Pareto configuration (Lightweight Sparse) and a 96.2% latency / 96.7% estimated energy reduction for EcoRAG Adaptive versus Baseline Heavy. These are results on this small synthetic/in-repository QA dataset; energy is an estimate, not a direct wall-power measurement.

## Metrics not captured by the baseline

- TTFT and generated-token counts: not measured by this retrieval benchmark.
- Peak RAM: not included in the printed configuration summary.
- Direct physical energy: not measured; `Wh/query` is estimated by the harness.
- The shared-chat value of 92 passed / 3 failed / 2 skipped and its 22/22 PDF benchmark are not this checkout's baseline. Do not substitute those numbers or alter the current benchmark to match them.

## Reproduction notes

- The benchmark loaded the embedding model from Hugging Face; the run emitted the unauthenticated Hub warning.
- Running the baseline suite from the project root with `pytest tests` fails because tests are located in `backend/tests`; run from `backend/`.
- TestClient emitted one Starlette deprecation warning. No test failures were observed.

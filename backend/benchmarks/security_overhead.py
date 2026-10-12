import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    import psutil
except ImportError:
    psutil = None

from src.security.security_gateway import SecurityGateway

DATASET_PATH = Path(__file__).resolve().parents[1] / "tests" / "security" / "data" / "adversarial_cases.json"


def run_benchmark(iterations: int) -> dict[str, Any]:
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    cases = [
        case for case in dataset["cases"]
        if case["kind"] in {"direct_input", "retrieved_document"}
    ]
    direct_case_count = sum(case["kind"] == "direct_input" for case in cases)
    document_case_count = sum(case["kind"] == "retrieved_document" for case in cases)
    if direct_case_count == 0 or document_case_count == 0:
        raise ValueError("Benchmark dataset must contain direct-input and document cases.")
    gateway = SecurityGateway()
    texts = [(case["content"], case["kind"]) for case in cases]
    process = psutil.Process() if psutil is not None else None
    ram_before = process.memory_info().rss if process else None
    cpu_before = time.process_time()

    baseline_started = time.perf_counter()
    for _ in range(iterations):
        for text, _ in texts:
            len(text)
    baseline_seconds = time.perf_counter() - baseline_started

    guarded_started = time.perf_counter()
    denied = 0
    flagged = 0
    for _ in range(iterations):
        for text, kind in texts:
            if kind == "retrieved_document":
                decision, metadata = gateway.inspect_document(
                    text,
                    document_id="benchmark-document",
                    source="security_benchmark",
                )
                flagged += int(bool(metadata and metadata.findings))
            else:
                decision = gateway.inspect_query(text)
            denied += int(not decision.allowed)
    guarded_seconds = time.perf_counter() - guarded_started

    cpu_seconds = time.process_time() - cpu_before
    ram_after = process.memory_info().rss if process else None
    operations = iterations * len(texts)
    direct_operations = iterations * direct_case_count
    document_operations = iterations * document_case_count
    additional_seconds = max(0.0, guarded_seconds - baseline_seconds)
    return {
        "dataset_version": dataset["version"],
        "cases_per_iteration": len(texts),
        "iterations": iterations,
        "operations": operations,
        "direct_input_checks": direct_operations,
        "document_checks": document_operations,
        "baseline_noop_mean_latency_ms": round(baseline_seconds * 1000 / operations, 6),
        "guarded_mean_latency_ms": round(guarded_seconds * 1000 / operations, 6),
        "incremental_mean_latency_ms": round(additional_seconds * 1000 / operations, 6),
        "cpu_time_ms": round(cpu_seconds * 1000, 3),
        "rss_before_mb": round(ram_before / (1024 * 1024), 3) if ram_before is not None else None,
        "rss_after_mb": round(ram_after / (1024 * 1024), 3) if ram_after is not None else None,
        "rss_delta_mb": round((ram_after - ram_before) / (1024 * 1024), 3)
        if ram_before is not None and ram_after is not None else None,
        "estimated_incremental_wh_at_45w": round(additional_seconds * 45 / 3600, 9),
        "rejections": denied,
        "rejection_rate": round(denied / direct_operations, 4),
        "documents_flagged_for_review": flagged,
        "document_flag_rate": round(flagged / document_operations, 4),
        "energy_note": "Estimated at 45 W from incremental wall time; not a physical power measurement.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Measure injection detector overhead on the versioned security dataset.")
    parser.add_argument("--iterations", type=int, default=1000)
    args = parser.parse_args()
    if args.iterations < 1:
        parser.error("--iterations must be positive.")
    print(json.dumps(run_benchmark(args.iterations), indent=2))


if __name__ == "__main__":
    main()

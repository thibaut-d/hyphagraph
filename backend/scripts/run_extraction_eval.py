"""
Run the gold extraction benchmark against the current batch extraction pipeline.

This is developer tooling for measuring extraction quality over time. It uses
the live batch extractor plus the curated benchmark cases defined in
`app.services.extraction_evaluation`.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.batch_extraction_orchestrator import BatchExtractionOrchestrator
from app.services.extraction_evaluation import (
    EXTRACTION_GOLD_BENCHMARK_CASES,
    ExtractionBenchmarkCase,
    ExtractionBenchmarkReport,
    ExtractionEvaluationService,
    render_extraction_benchmark_report,
)


async def run_eval(
    *,
    selected_cases: list[ExtractionBenchmarkCase],
    min_confidence: str | None,
    validation_level: str,
) -> ExtractionBenchmarkReport:
    orchestrator = BatchExtractionOrchestrator(
        enable_validation=True,
        validation_level=validation_level,
    )
    evaluation_service = ExtractionEvaluationService(validation_level=validation_level)

    case_results = []
    for case in selected_cases:
        print(f"Running case {case.case_id}: {case.title}")
        entities, relations = await orchestrator.extract_batch(
            case.source_text,
            min_confidence=min_confidence,
        )
        case_results.append(
            evaluation_service.evaluate_case(case, entities, relations)
        )

    return evaluation_service.evaluate_cases(case_results)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the gold extraction benchmark.")
    parser.add_argument(
        "--case",
        action="append",
        dest="case_ids",
        help="Benchmark case id to run. Repeat to select multiple cases.",
    )
    parser.add_argument(
        "--min-confidence",
        choices=("low", "medium", "high"),
        default=None,
        help="Optional confidence filter passed to the extractor.",
    )
    parser.add_argument(
        "--validation-level",
        choices=("lenient", "moderate", "strict"),
        default="moderate",
        help="Validation level used by extraction and semantic scoring.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the report as JSON instead of plain text.",
    )
    return parser.parse_args()


def select_cases(case_ids: list[str] | None) -> list[ExtractionBenchmarkCase]:
    if not case_ids:
        return list(EXTRACTION_GOLD_BENCHMARK_CASES)

    selected = []
    known_case_ids = {case.case_id for case in EXTRACTION_GOLD_BENCHMARK_CASES}
    unknown_case_ids = sorted(set(case_ids) - known_case_ids)
    if unknown_case_ids:
        raise SystemExit(f"Unknown benchmark case ids: {', '.join(unknown_case_ids)}")

    requested_ids = set(case_ids)
    for case in EXTRACTION_GOLD_BENCHMARK_CASES:
        if case.case_id in requested_ids:
            selected.append(case)
    return selected


def main() -> None:
    args = parse_args()
    report = asyncio.run(
        run_eval(
            selected_cases=select_cases(args.case_ids),
            min_confidence=args.min_confidence,
            validation_level=args.validation_level,
        )
    )

    if args.json:
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
        return

    print(render_extraction_benchmark_report(report))


if __name__ == "__main__":
    main()

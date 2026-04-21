"""
Gold-benchmark scoring utilities for extraction quality.

These helpers let HyphaGraph score extraction outputs against a curated,
source-grounded benchmark without introducing a second extraction contract.
The benchmark reuses the runtime extraction schemas and relation validator so
prompt/model changes can be measured against the same semantic expectations.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from typing import Iterable

from app.llm.schemas import ExtractedEntity, ExtractedRelation
from app.services.extraction_text_span_validator import (
    TextSpanValidator,
    ValidationLevel,
)


@dataclass(frozen=True, order=True)
class RelationSignature:
    """Semantic relation fingerprint used for gold-benchmark comparison."""

    relation_type: str
    roles: tuple[tuple[str, str], ...]
    statement_kind: str | None = None
    finding_polarity: str | None = None

    def to_display_string(self) -> str:
        role_text = ", ".join(f"{role_type}={slug}" for role_type, slug in self.roles)
        qualifiers: list[str] = []
        if self.statement_kind:
            qualifiers.append(f"statement_kind={self.statement_kind}")
        if self.finding_polarity:
            qualifiers.append(f"finding_polarity={self.finding_polarity}")
        qualifier_text = f" [{', '.join(qualifiers)}]" if qualifiers else ""
        return f"{self.relation_type}({role_text}){qualifier_text}"


@dataclass(frozen=True)
class ExtractionBenchmarkCase:
    """Single curated extraction benchmark case."""

    case_id: str
    title: str
    source_text: str
    expected_entity_slugs: tuple[str, ...]
    expected_relations: tuple[RelationSignature, ...]


@dataclass(frozen=True)
class MatchMetrics:
    """Precision/recall/F1 counts for one extraction dimension."""

    true_positives: int
    false_positives: int
    false_negatives: int

    @property
    def precision(self) -> float:
        denominator = self.true_positives + self.false_positives
        if denominator:
            return self.true_positives / denominator
        return 1.0 if self.false_negatives == 0 else 0.0

    @property
    def recall(self) -> float:
        denominator = self.true_positives + self.false_negatives
        if denominator:
            return self.true_positives / denominator
        return 1.0 if self.false_positives == 0 else 0.0

    @property
    def f1(self) -> float:
        precision = self.precision
        recall = self.recall
        if precision + recall == 0:
            return 0.0
        return 2 * precision * recall / (precision + recall)


@dataclass(frozen=True)
class ExtractionBenchmarkCaseResult:
    """Per-case benchmark result with exact misses/extras for review."""

    case_id: str
    title: str
    entity_metrics: MatchMetrics
    relation_metrics: MatchMetrics
    relation_validity_rate: float
    valid_relation_count: int
    relation_count: int
    missing_entities: tuple[str, ...]
    extra_entities: tuple[str, ...]
    missing_relations: tuple[str, ...]
    extra_relations: tuple[str, ...]
    invalid_relation_flag_counts: tuple[tuple[str, int], ...]

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["entity_metrics"] = {
            **asdict(self.entity_metrics),
            "precision": self.entity_metrics.precision,
            "recall": self.entity_metrics.recall,
            "f1": self.entity_metrics.f1,
        }
        payload["relation_metrics"] = {
            **asdict(self.relation_metrics),
            "precision": self.relation_metrics.precision,
            "recall": self.relation_metrics.recall,
            "f1": self.relation_metrics.f1,
        }
        return payload


@dataclass(frozen=True)
class ExtractionBenchmarkReport:
    """Aggregate report across all benchmark cases."""

    case_results: tuple[ExtractionBenchmarkCaseResult, ...]
    entity_metrics: MatchMetrics
    relation_metrics: MatchMetrics
    relation_validity_rate: float
    valid_relation_count: int
    relation_count: int
    invalid_relation_flag_counts: tuple[tuple[str, int], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "case_results": [result.to_dict() for result in self.case_results],
            "entity_metrics": {
                **asdict(self.entity_metrics),
                "precision": self.entity_metrics.precision,
                "recall": self.entity_metrics.recall,
                "f1": self.entity_metrics.f1,
            },
            "relation_metrics": {
                **asdict(self.relation_metrics),
                "precision": self.relation_metrics.precision,
                "recall": self.relation_metrics.recall,
                "f1": self.relation_metrics.f1,
            },
            "relation_validity_rate": self.relation_validity_rate,
            "valid_relation_count": self.valid_relation_count,
            "relation_count": self.relation_count,
            "invalid_relation_flag_counts": list(self.invalid_relation_flag_counts),
        }


def build_relation_signature(
    relation_type: str,
    *,
    roles: Iterable[tuple[str, str]],
    statement_kind: str | None = "finding",
    finding_polarity: str | None = None,
) -> RelationSignature:
    """Construct a normalized relation signature for the benchmark dataset."""

    normalized_roles = tuple(
        sorted(
            (_normalize_role_type_for_benchmark(role_type), slug.strip())
            for role_type, slug in roles
        )
    )
    return RelationSignature(
        relation_type=relation_type.strip(),
        roles=normalized_roles,
        statement_kind=statement_kind,
        finding_polarity=finding_polarity,
    )


def _normalize_role_type_for_benchmark(role_type: str) -> str:
    normalized = role_type.strip()
    aliases = {
        "comparator": "control_group",
    }
    return aliases.get(normalized, normalized)


EXTRACTION_GOLD_BENCHMARK_CASES: tuple[ExtractionBenchmarkCase, ...] = (
    ExtractionBenchmarkCase(
        case_id="ssri-placebo-split-outcomes",
        title="Split placebo findings by outcome",
        source_text=(
            "In adults with fibromyalgia, SSRIs significantly reduced pain, improved "
            "depression, and improved quality of life compared with placebo."
        ),
        expected_entity_slugs=(
            "ssris",
            "fibromyalgia",
            "pain",
            "depression",
            "quality-of-life",
            "placebo",
        ),
        expected_relations=(
            build_relation_signature(
                "treats",
                roles=(
                    ("agent", "ssris"),
                    ("target", "pain"),
                    ("control_group", "placebo"),
                ),
                finding_polarity="supports",
            ),
            build_relation_signature(
                "treats",
                roles=(
                    ("agent", "ssris"),
                    ("target", "depression"),
                    ("control_group", "placebo"),
                ),
                finding_polarity="supports",
            ),
            build_relation_signature(
                "treats",
                roles=(
                    ("agent", "ssris"),
                    ("target", "quality-of-life"),
                    ("control_group", "placebo"),
                ),
                finding_polarity="supports",
            ),
        ),
    ),
    ExtractionBenchmarkCase(
        case_id="ssri-nonpharm-null-finding",
        title="Null finding keeps true comparator",
        source_text=(
            "Compared with acupuncture and aerobic exercise, SSRIs did not "
            "significantly improve depression in fibromyalgia."
        ),
        expected_entity_slugs=(
            "ssris",
            "acupuncture",
            "aerobic-exercise",
            "depression",
            "fibromyalgia",
        ),
        expected_relations=(
            build_relation_signature(
                "treats",
                roles=(
                    ("agent", "ssris"),
                    ("target", "depression"),
                    ("control_group", "acupuncture"),
                    ("control_group", "aerobic-exercise"),
                ),
                finding_polarity="neutral",
            ),
        ),
    ),
    ExtractionBenchmarkCase(
        case_id="ssri-adverse-events-not-symptom-causes",
        title="Adverse-event association stays conservative",
        source_text=(
            "Compared with placebo, SSRI groups reported more adverse events and "
            "higher dropout rates. Dry mouth and headaches were among the common "
            "complaints."
        ),
        expected_entity_slugs=(
            "ssris",
            "placebo",
            "adverse-events",
            "dropout-rates",
            "dry-mouth",
            "headaches",
        ),
        expected_relations=(
            build_relation_signature(
                "causes",
                roles=(
                    ("agent", "ssris"),
                    ("target", "adverse-events"),
                    ("control_group", "placebo"),
                ),
                finding_polarity="supports",
            ),
            build_relation_signature(
                "causes",
                roles=(
                    ("agent", "ssris"),
                    ("target", "dropout-rates"),
                    ("control_group", "placebo"),
                ),
                finding_polarity="supports",
            ),
        ),
    ),
)


class ExtractionEvaluationService:
    """Scores extraction outputs against the curated benchmark cases."""

    def __init__(self, validation_level: ValidationLevel = "moderate"):
        self.validator = TextSpanValidator(validation_level=validation_level)

    def evaluate_case(
        self,
        case: ExtractionBenchmarkCase,
        entities: list[ExtractedEntity],
        relations: list[ExtractedRelation],
    ) -> ExtractionBenchmarkCaseResult:
        expected_entity_counts = Counter(case.expected_entity_slugs)
        actual_entity_counts = Counter(entity.slug for entity in entities)
        entity_metrics = _score_counts(expected_entity_counts, actual_entity_counts)

        expected_relation_counts = Counter(case.expected_relations)
        actual_relation_signatures = [self._build_relation_signature(relation) for relation in relations]
        entity_lookup = {entity.slug: entity for entity in entities}
        relation_results = [
            self.validator.validate_relation(relation, case.source_text, entity_lookup=entity_lookup)
            for relation in relations
        ]
        relation_metrics, missing_relation_signatures, extra_relation_signatures = (
            _score_relation_matches(
                expected_relations=case.expected_relations,
                actual_relations=actual_relation_signatures,
                actual_validity_flags=[result.is_valid for result in relation_results],
            )
        )
        valid_relation_count = sum(1 for result in relation_results if result.is_valid)
        relation_count = len(relation_results)
        relation_validity_rate = (
            valid_relation_count / relation_count if relation_count else 1.0
        )

        invalid_flag_counts: Counter[str] = Counter()
        for result in relation_results:
            if result.is_valid:
                continue
            invalid_flag_counts.update(result.flags)

        return ExtractionBenchmarkCaseResult(
            case_id=case.case_id,
            title=case.title,
            entity_metrics=entity_metrics,
            relation_metrics=relation_metrics,
            relation_validity_rate=relation_validity_rate,
            valid_relation_count=valid_relation_count,
            relation_count=relation_count,
            missing_entities=_expand_missing_items(expected_entity_counts, actual_entity_counts),
            extra_entities=_expand_missing_items(actual_entity_counts, expected_entity_counts),
            missing_relations=tuple(
                signature.to_display_string() for signature in missing_relation_signatures
            ),
            extra_relations=tuple(
                signature.to_display_string() for signature in extra_relation_signatures
            ),
            invalid_relation_flag_counts=tuple(sorted(invalid_flag_counts.items())),
        )

    def evaluate_cases(
        self,
        case_results: Iterable[ExtractionBenchmarkCaseResult],
    ) -> ExtractionBenchmarkReport:
        normalized_results = tuple(case_results)
        entity_metrics = MatchMetrics(
            true_positives=sum(result.entity_metrics.true_positives for result in normalized_results),
            false_positives=sum(result.entity_metrics.false_positives for result in normalized_results),
            false_negatives=sum(result.entity_metrics.false_negatives for result in normalized_results),
        )
        relation_metrics = MatchMetrics(
            true_positives=sum(result.relation_metrics.true_positives for result in normalized_results),
            false_positives=sum(result.relation_metrics.false_positives for result in normalized_results),
            false_negatives=sum(result.relation_metrics.false_negatives for result in normalized_results),
        )
        valid_relation_count = sum(result.valid_relation_count for result in normalized_results)
        relation_count = sum(result.relation_count for result in normalized_results)
        relation_validity_rate = (
            valid_relation_count / relation_count if relation_count else 1.0
        )

        invalid_flag_counts: Counter[str] = Counter()
        for result in normalized_results:
            invalid_flag_counts.update(dict(result.invalid_relation_flag_counts))

        return ExtractionBenchmarkReport(
            case_results=normalized_results,
            entity_metrics=entity_metrics,
            relation_metrics=relation_metrics,
            relation_validity_rate=relation_validity_rate,
            valid_relation_count=valid_relation_count,
            relation_count=relation_count,
            invalid_relation_flag_counts=tuple(sorted(invalid_flag_counts.items())),
        )

    def _build_relation_signature(self, relation: ExtractedRelation) -> RelationSignature:
        evidence_context = relation.evidence_context
        return build_relation_signature(
            relation.relation_type,
            roles=((role.role_type, role.entity_slug) for role in relation.roles),
            statement_kind=(
                evidence_context.statement_kind if evidence_context is not None else None
            ),
            finding_polarity=(
                evidence_context.finding_polarity if evidence_context is not None else None
            ),
        )


def render_extraction_benchmark_report(report: ExtractionBenchmarkReport) -> str:
    """Render a readable text report for CLI use."""

    lines = [
        "=" * 80,
        "EXTRACTION BENCHMARK REPORT",
        "=" * 80,
        (
            "Entities:"
            f" P={report.entity_metrics.precision:.3f}"
            f" R={report.entity_metrics.recall:.3f}"
            f" F1={report.entity_metrics.f1:.3f}"
            f" (tp={report.entity_metrics.true_positives},"
            f" fp={report.entity_metrics.false_positives},"
            f" fn={report.entity_metrics.false_negatives})"
        ),
        (
            "Relations:"
            f" P={report.relation_metrics.precision:.3f}"
            f" R={report.relation_metrics.recall:.3f}"
            f" F1={report.relation_metrics.f1:.3f}"
            f" (tp={report.relation_metrics.true_positives},"
            f" fp={report.relation_metrics.false_positives},"
            f" fn={report.relation_metrics.false_negatives})"
        ),
        (
            "Relation semantic validity:"
            f" {report.relation_validity_rate:.3f}"
            f" ({report.valid_relation_count}/{report.relation_count})"
        ),
        "",
    ]

    for result in report.case_results:
        lines.extend(
            [
                f"- {result.case_id}: {result.title}",
                (
                    "  entities"
                    f" P={result.entity_metrics.precision:.3f}"
                    f" R={result.entity_metrics.recall:.3f}"
                    f" F1={result.entity_metrics.f1:.3f}"
                ),
                (
                    "  relations"
                    f" P={result.relation_metrics.precision:.3f}"
                    f" R={result.relation_metrics.recall:.3f}"
                    f" F1={result.relation_metrics.f1:.3f}"
                    f" validity={result.relation_validity_rate:.3f}"
                ),
            ]
        )
        if result.missing_entities:
            lines.append(f"  missing entities: {', '.join(result.missing_entities)}")
        if result.extra_entities:
            lines.append(f"  extra entities: {', '.join(result.extra_entities)}")
        if result.missing_relations:
            lines.append(f"  missing relations: {'; '.join(result.missing_relations)}")
        if result.extra_relations:
            lines.append(f"  extra relations: {'; '.join(result.extra_relations)}")
        if result.invalid_relation_flag_counts:
            flag_text = ", ".join(
                f"{flag}={count}" for flag, count in result.invalid_relation_flag_counts
            )
            lines.append(f"  invalid relation flags: {flag_text}")
        lines.append("")

    if report.invalid_relation_flag_counts:
        aggregate_flag_text = ", ".join(
            f"{flag}={count}" for flag, count in report.invalid_relation_flag_counts
        )
        lines.append(f"Aggregate invalid relation flags: {aggregate_flag_text}")

    return "\n".join(lines).rstrip()


def _score_counts(
    expected_counts: Counter[str] | Counter[RelationSignature],
    actual_counts: Counter[str] | Counter[RelationSignature],
) -> MatchMetrics:
    keys = set(expected_counts) | set(actual_counts)
    true_positives = sum(min(expected_counts[key], actual_counts[key]) for key in keys)
    false_positives = sum(
        max(actual_counts[key] - expected_counts[key], 0) for key in keys
    )
    false_negatives = sum(
        max(expected_counts[key] - actual_counts[key], 0) for key in keys
    )
    return MatchMetrics(
        true_positives=true_positives,
        false_positives=false_positives,
        false_negatives=false_negatives,
    )


def _score_relation_matches(
    *,
    expected_relations: tuple[RelationSignature, ...],
    actual_relations: list[RelationSignature],
    actual_validity_flags: list[bool],
) -> tuple[MatchMetrics, tuple[RelationSignature, ...], tuple[RelationSignature, ...]]:
    unmatched_actual_indexes = list(range(len(actual_relations)))
    missing_relations: list[RelationSignature] = []
    matched_actual_indexes: list[int] = []

    for expected_relation in expected_relations:
        compatible_indexes = [
            index
            for index in unmatched_actual_indexes
            if _relation_matches(
                expected_relation,
                actual_relations[index],
                actual_is_valid=actual_validity_flags[index],
            )
        ]
        if not compatible_indexes:
            missing_relations.append(expected_relation)
            continue

        best_index = min(
            compatible_indexes,
            key=lambda index: len(actual_relations[index].roles) - len(expected_relation.roles),
        )
        matched_actual_indexes.append(best_index)
        unmatched_actual_indexes.remove(best_index)

    true_positives = len(matched_actual_indexes)
    false_negatives = len(missing_relations)
    false_positives = len(unmatched_actual_indexes)

    extra_relations = tuple(actual_relations[index] for index in unmatched_actual_indexes)
    return (
        MatchMetrics(
            true_positives=true_positives,
            false_positives=false_positives,
            false_negatives=false_negatives,
        ),
        tuple(missing_relations),
        extra_relations,
    )


def _relation_matches(
    expected_relation: RelationSignature,
    actual_relation: RelationSignature,
    *,
    actual_is_valid: bool,
) -> bool:
    if not actual_is_valid:
        return False
    if expected_relation.relation_type != actual_relation.relation_type:
        return False
    if expected_relation.statement_kind != actual_relation.statement_kind:
        return False
    if expected_relation.finding_polarity != actual_relation.finding_polarity:
        return False

    expected_roles = Counter(expected_relation.roles)
    actual_roles = Counter(actual_relation.roles)
    return all(actual_roles[role] >= count for role, count in expected_roles.items())




def _expand_missing_items(
    expected_counts: Counter[str],
    actual_counts: Counter[str],
) -> tuple[str, ...]:
    items: list[str] = []
    for key in sorted(set(expected_counts) | set(actual_counts)):
        deficit = expected_counts[key] - actual_counts[key]
        if deficit > 0:
            items.extend([key] * deficit)
    return tuple(items)


def _expand_missing_signatures(
    expected_counts: Counter[RelationSignature],
    actual_counts: Counter[RelationSignature],
) -> tuple[RelationSignature, ...]:
    signatures: list[RelationSignature] = []
    for signature in sorted(set(expected_counts) | set(actual_counts)):
        deficit = expected_counts[signature] - actual_counts[signature]
        if deficit > 0:
            signatures.extend([signature] * deficit)
    return tuple(signatures)

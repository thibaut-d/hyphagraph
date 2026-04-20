from app.llm.schemas import (
    ExtractedEntity,
    ExtractedRelation,
    ExtractedRelationEvidenceContext,
    ExtractedRole,
)
from app.services.extraction_evaluation import (
    EXTRACTION_GOLD_BENCHMARK_CASES,
    ExtractionEvaluationService,
    render_extraction_benchmark_report,
)


def _entity(slug: str, text_span: str, *, category: str = "other") -> ExtractedEntity:
    return ExtractedEntity(
        slug=slug,
        summary=f"{slug} summary text",
        category=category,
        confidence="high",
        text_span=text_span,
    )


def _relation(
    relation_type: str,
    *,
    roles: list[tuple[str, str, str | None]],
    text_span: str,
    finding_polarity: str | None,
) -> ExtractedRelation:
    return ExtractedRelation(
        relation_type=relation_type,
        roles=[
            ExtractedRole(
                entity_slug=entity_slug,
                role_type=role_type,
                source_mention=source_mention,
            )
            for role_type, entity_slug, source_mention in roles
        ],
        confidence="high",
        text_span=text_span,
        evidence_context=ExtractedRelationEvidenceContext(
            statement_kind="finding",
            finding_polarity=finding_polarity,
            assertion_text=text_span,
        ),
    )


def test_evaluate_case_scores_semantically_correct_extraction() -> None:
    case = EXTRACTION_GOLD_BENCHMARK_CASES[0]
    service = ExtractionEvaluationService()
    entities = [
        _entity("ssris", "SSRIs", category="drug"),
        _entity("fibromyalgia", "fibromyalgia", category="disease"),
        _entity("pain", "pain", category="outcome"),
        _entity("depression", "depression", category="disease"),
        _entity("quality-of-life", "quality of life", category="outcome"),
        _entity("placebo", "placebo", category="other"),
    ]
    relations = [
        _relation(
            "treats",
            roles=[
                ("agent", "ssris", "SSRIs"),
                ("target", "pain", "pain"),
                ("control_group", "placebo", "placebo"),
            ],
            text_span=case.source_text,
            finding_polarity="supports",
        ),
        _relation(
            "treats",
            roles=[
                ("agent", "ssris", "SSRIs"),
                ("target", "depression", "depression"),
                ("control_group", "placebo", "placebo"),
            ],
            text_span=case.source_text,
            finding_polarity="supports",
        ),
        _relation(
            "treats",
            roles=[
                ("agent", "ssris", "SSRIs"),
                ("target", "quality-of-life", "quality of life"),
                ("control_group", "placebo", "placebo"),
            ],
            text_span=case.source_text,
            finding_polarity="supports",
        ),
    ]

    result = service.evaluate_case(case, entities, relations)

    assert result.entity_metrics.true_positives == 6
    assert result.entity_metrics.false_positives == 0
    assert result.entity_metrics.false_negatives == 0
    assert result.entity_metrics.f1 == 1.0
    assert result.relation_metrics.true_positives == 3
    assert result.relation_metrics.false_positives == 0
    assert result.relation_metrics.false_negatives == 0
    assert result.relation_metrics.f1 == 1.0
    assert result.relation_validity_rate == 1.0
    assert result.invalid_relation_flag_counts == ()


def test_evaluate_case_penalizes_wrong_comparator_and_wrong_polarity() -> None:
    case = EXTRACTION_GOLD_BENCHMARK_CASES[1]
    service = ExtractionEvaluationService()
    entities = [
        _entity("ssris", "SSRIs", category="drug"),
        _entity("depression", "depression", category="disease"),
        _entity("placebo", "placebo", category="other"),
    ]
    relations = [
        _relation(
            "treats",
            roles=[
                ("agent", "ssris", "SSRIs"),
                ("target", "depression", "depression"),
                ("control_group", "placebo", "placebo"),
            ],
            text_span=case.source_text,
            finding_polarity="contradicts",
        ),
    ]

    result = service.evaluate_case(case, entities, relations)

    assert result.entity_metrics.true_positives == 2
    assert result.entity_metrics.false_positives == 1
    assert result.entity_metrics.false_negatives == 3
    assert result.relation_metrics.true_positives == 0
    assert result.relation_metrics.false_positives == 1
    assert result.relation_metrics.false_negatives == 1
    assert result.relation_validity_rate == 0.0
    assert "control_group=acupuncture" in result.missing_relations[0]
    assert "finding_polarity=contradicts" in result.extra_relations[0]
    assert ("relation_role_not_grounded_locally", 1) in result.invalid_relation_flag_counts
    assert ("ungrounded_relation_role:control_group:placebo", 1) in result.invalid_relation_flag_counts


def test_evaluate_case_flags_extra_symptom_level_adverse_event_relations() -> None:
    case = EXTRACTION_GOLD_BENCHMARK_CASES[2]
    service = ExtractionEvaluationService()
    entities = [
        _entity("ssris", "SSRI", category="drug"),
        _entity("placebo", "placebo", category="other"),
        _entity("adverse-events", "adverse events", category="other"),
        _entity("dropout-rates", "dropout rates", category="outcome"),
        _entity("dry-mouth", "Dry mouth", category="symptom"),
        _entity("headaches", "headaches", category="symptom"),
    ]
    relations = [
        _relation(
            "causes",
            roles=[
                ("agent", "ssris", "SSRI"),
                ("target", "adverse-events", "adverse events"),
                ("control_group", "placebo", "placebo"),
            ],
            text_span="Compared with placebo, SSRI groups reported more adverse events.",
            finding_polarity="supports",
        ),
        _relation(
            "causes",
            roles=[
                ("agent", "ssris", "SSRI"),
                ("target", "dropout-rates", "dropout rates"),
                ("control_group", "placebo", "placebo"),
            ],
            text_span="Compared with placebo, SSRI groups reported more adverse events and higher dropout rates.",
            finding_polarity="supports",
        ),
        _relation(
            "causes",
            roles=[
                ("agent", "ssris", "SSRI"),
                ("target", "dry-mouth", "Dry mouth"),
                ("control_group", "placebo", "placebo"),
            ],
            text_span="Dry mouth and headaches were among the common complaints.",
            finding_polarity="supports",
        ),
        _relation(
            "causes",
            roles=[
                ("agent", "ssris", "SSRI"),
                ("target", "headaches", "headaches"),
                ("control_group", "placebo", "placebo"),
            ],
            text_span="Dry mouth and headaches were among the common complaints.",
            finding_polarity="supports",
        ),
    ]

    result = service.evaluate_case(case, entities, relations)

    assert result.entity_metrics.f1 == 1.0
    assert result.relation_metrics.true_positives == 2
    assert result.relation_metrics.false_positives == 2
    assert result.relation_metrics.false_negatives == 0
    assert result.relation_metrics.precision == 0.5
    assert result.relation_metrics.recall == 1.0
    assert round(result.relation_metrics.f1, 3) == 0.667
    assert len(result.extra_relations) == 2
    assert result.relation_validity_rate == 0.5
    assert ("relation_role_not_grounded_locally", 2) in result.invalid_relation_flag_counts


def test_evaluate_cases_aggregates_metrics_and_renders_report() -> None:
    service = ExtractionEvaluationService()
    good_case = EXTRACTION_GOLD_BENCHMARK_CASES[0]
    bad_case = EXTRACTION_GOLD_BENCHMARK_CASES[1]

    good_result = service.evaluate_case(
        good_case,
        entities=[
            _entity("ssris", "SSRIs", category="drug"),
            _entity("fibromyalgia", "fibromyalgia", category="disease"),
            _entity("pain", "pain", category="outcome"),
            _entity("depression", "depression", category="disease"),
            _entity("quality-of-life", "quality of life", category="outcome"),
            _entity("placebo", "placebo", category="other"),
        ],
        relations=[
            _relation(
                "treats",
                roles=[
                    ("agent", "ssris", "SSRIs"),
                    ("target", "pain", "pain"),
                    ("control_group", "placebo", "placebo"),
                ],
                text_span=good_case.source_text,
                finding_polarity="supports",
            ),
            _relation(
                "treats",
                roles=[
                    ("agent", "ssris", "SSRIs"),
                    ("target", "depression", "depression"),
                    ("control_group", "placebo", "placebo"),
                ],
                text_span=good_case.source_text,
                finding_polarity="supports",
            ),
            _relation(
                "treats",
                roles=[
                    ("agent", "ssris", "SSRIs"),
                    ("target", "quality-of-life", "quality of life"),
                    ("control_group", "placebo", "placebo"),
                ],
                text_span=good_case.source_text,
                finding_polarity="supports",
            ),
        ],
    )
    bad_result = service.evaluate_case(
        bad_case,
        entities=[
            _entity("ssris", "SSRIs", category="drug"),
            _entity("depression", "depression", category="disease"),
            _entity("placebo", "placebo", category="other"),
        ],
        relations=[
            _relation(
                "treats",
                roles=[
                    ("agent", "ssris", "SSRIs"),
                    ("target", "depression", "depression"),
                    ("control_group", "placebo", "placebo"),
                ],
                text_span=bad_case.source_text,
                finding_polarity="contradicts",
            ),
        ],
    )

    report = service.evaluate_cases([good_result, bad_result])
    rendered = render_extraction_benchmark_report(report)

    assert report.entity_metrics.true_positives == 8
    assert report.entity_metrics.false_positives == 1
    assert report.entity_metrics.false_negatives == 3
    assert report.relation_metrics.true_positives == 3
    assert report.relation_metrics.false_positives == 1
    assert report.relation_metrics.false_negatives == 1
    assert round(report.relation_validity_rate, 3) == 0.75
    assert "EXTRACTION BENCHMARK REPORT" in rendered
    assert "ssri-placebo-split-outcomes" in rendered
    assert "Aggregate invalid relation flags" in rendered

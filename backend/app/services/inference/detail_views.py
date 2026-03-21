from __future__ import annotations

import asyncio

from app.schemas.inference import (
    DisagreementGroupRead,
    EvidenceItemRead,
    InferenceDetailRead,
    InferenceRead,
    InferenceStatsRead,
    RelationKindSummaryRead,
)
from app.schemas.relation import RelationRead
from app.schemas.source import SourceRead
from app.services.inference.math import normalize_direction
from app.services.source_service import SourceService


async def build_inference_detail_read(
    *,
    inference: InferenceRead,
    source_service: SourceService,
) -> InferenceDetailRead:
    relations_by_kind = inference.relations_by_kind or {}
    all_relations = [
        relation
        for relation_group in relations_by_kind.values()
        for relation in relation_group
    ]

    source_map = await _load_sources(source_service, all_relations)
    evidence_items = [
        EvidenceItemRead(**relation.model_dump(), source=source_map.get(str(relation.source_id)))
        for relation in all_relations
    ]
    evidence_items.sort(
        key=lambda relation: (
            relation.confidence or 0.0,
            relation.kind or "",
        ),
        reverse=True,
    )

    relation_kind_summaries = [
        _build_relation_kind_summary(kind, relations)
        for kind, relations in relations_by_kind.items()
    ]
    relation_kind_summaries.sort(key=lambda summary: summary.relation_count, reverse=True)

    disagreement_groups = [
        _build_disagreement_group(kind, relations, source_map)
        for kind, relations in relations_by_kind.items()
        if any(normalize_direction(relation.direction) == "contradicts" for relation in relations)
    ]
    disagreement_groups.sort(key=lambda group: len(group.contradicting), reverse=True)

    return InferenceDetailRead(
        entity_id=inference.entity_id,
        relations_by_kind=relations_by_kind,
        role_inferences=inference.role_inferences,
        stats=_build_inference_stats(all_relations, relation_kind_summaries),
        relation_kind_summaries=relation_kind_summaries,
        evidence_items=evidence_items,
        disagreement_groups=disagreement_groups,
    )


async def _load_sources(
    source_service: SourceService,
    relations: list[RelationRead],
) -> dict[str, SourceRead]:
    source_ids = sorted({str(relation.source_id) for relation in relations if relation.source_id})
    if not source_ids:
        return {}

    results = await asyncio.gather(
        *(source_service.get(source_id) for source_id in source_ids),
        return_exceptions=True,
    )

    source_map: dict[str, SourceRead] = {}
    for source_id, result in zip(source_ids, results, strict=False):
        if not isinstance(result, Exception):
            source_map[source_id] = result
    return source_map


def _build_relation_kind_summary(
    kind: str,
    relations: list[RelationRead],
) -> RelationKindSummaryRead:
    confidence_values = [relation.confidence or 0.0 for relation in relations]
    supporting_count = sum(1 for relation in relations if normalize_direction(relation.direction) == "supports")
    contradicting_count = sum(1 for relation in relations if normalize_direction(relation.direction) == "contradicts")
    neutral_count = len(relations) - supporting_count - contradicting_count

    return RelationKindSummaryRead(
        kind=kind,
        relation_count=len(relations),
        average_confidence=(
            sum(confidence_values) / len(confidence_values) if confidence_values else 0.0
        ),
        supporting_count=supporting_count,
        contradicting_count=contradicting_count,
        neutral_count=neutral_count,
    )


def _build_disagreement_group(
    kind: str,
    relations: list[RelationRead],
    source_map: dict[str, SourceRead],
) -> DisagreementGroupRead:
    supporting = [
        EvidenceItemRead(**relation.model_dump(), source=source_map.get(str(relation.source_id)))
        for relation in relations
        if normalize_direction(relation.direction) == "supports"
    ]
    contradicting = [
        EvidenceItemRead(**relation.model_dump(), source=source_map.get(str(relation.source_id)))
        for relation in relations
        if normalize_direction(relation.direction) == "contradicts"
    ]
    confidence_values = [relation.confidence or 0.0 for relation in relations]

    return DisagreementGroupRead(
        kind=kind,
        supporting=supporting,
        contradicting=contradicting,
        confidence=sum(confidence_values) / len(confidence_values) if confidence_values else 0.0,
    )


def _build_inference_stats(
    relations: list[RelationRead],
    relation_kind_summaries: list[RelationKindSummaryRead],
) -> InferenceStatsRead:
    confidence_values = [relation.confidence for relation in relations if relation.confidence is not None]
    contradiction_count = sum(1 for relation in relations if normalize_direction(relation.direction) == "contradicts")

    return InferenceStatsRead(
        total_relations=len(relations),
        unique_sources_count=len({str(relation.source_id) for relation in relations if relation.source_id}),
        average_confidence=(
            sum(confidence_values) / len(confidence_values) if confidence_values else 0.0
        ),
        confidence_count=len(confidence_values),
        high_confidence_count=sum(1 for value in confidence_values if value > 0.7),
        low_confidence_count=sum(1 for value in confidence_values if value < 0.4),
        contradiction_count=contradiction_count,
        relation_type_count=len(relation_kind_summaries),
    )

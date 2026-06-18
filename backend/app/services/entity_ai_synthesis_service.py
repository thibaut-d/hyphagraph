from __future__ import annotations

import json
import logging

from app.llm.base import LLMError, LLMProvider
from app.schemas.entity import EntityRead
from app.schemas.inference import EntityAISynthesisRead, InferenceDetailRead
from app.schemas.relation import RelationRead
from app.services.inference.math import normalize_direction
from app.utils.errors import AppException, ErrorCode

logger = logging.getLogger(__name__)


class EntityAISynthesisService:
    """Generate non-authoritative, on-demand prose from computed entity evidence."""

    def __init__(self, llm_provider: LLMProvider):
        self.llm_provider = llm_provider

    async def generate(
        self,
        *,
        entity: EntityRead,
        inference: InferenceDetailRead,
        user_language: str,
    ) -> EntityAISynthesisRead:
        evidence_digest = _build_evidence_digest(entity, inference)
        try:
            llm_payload = await self.llm_provider.generate_json(
                prompt=json.dumps(evidence_digest, ensure_ascii=False, indent=2),
                system_prompt=_build_system_prompt(user_language),
                temperature=0.2,
                max_tokens=1200,
            )
        except LLMError as exc:
            logger.exception(
                "Failed to generate AI synthesis for entity_id=%s",
                entity.id,
            )
            raise AppException(
                status_code=502,
                error_code=ErrorCode.LLM_API_ERROR,
                message="AI synthesis generation failed",
                details=str(exc),
            ) from exc

        model_name = self.llm_provider.get_model_name()
        return EntityAISynthesisRead(
            entity_id=entity.id,
            entity_slug=entity.slug,
            synthesis=_coerce_text(llm_payload.get("synthesis")),
            key_points=_coerce_text_list(llm_payload.get("key_points")),
            limitations=_coerce_text_list(llm_payload.get("limitations")),
            evidence_note=_coerce_text(llm_payload.get("evidence_note")),
            general_knowledge_note=_coerce_optional_text(
                llm_payload.get("general_knowledge_note")
            ),
            source_relation_count=inference.stats.total_relations,
            source_count=inference.stats.unique_sources_count,
            generated_with_llm=model_name,
            token_usage={},
        )


def _build_system_prompt(user_language: str) -> str:
    return f"""
You generate a short, human-readable AI synthesis for HyphaGraph.

HyphaGraph rules:
- The graph evidence is the only authoritative project data.
- Your prose is advisory and must never claim to be the truth.
- Preserve visible contradictions and uncertainty.
- Do not resolve disagreements unless the provided evidence already does.
- Use the computed scores, coverage, confidence, disagreement, relation summaries,
  and representative evidence supplied by the application.
- You may add brief general background knowledge only when it is ordinary,
  non-controversial, and broadly consensual. Keep it separate from evidence-backed
  claims and never use it to override graph evidence.
- If graph evidence is thin or contradictory, say so plainly.
- Write in this UI language when possible: {user_language}.

Return only JSON with this exact shape:
{{
  "synthesis": "one concise paragraph",
  "key_points": ["2-5 bullets grounded in graph evidence"],
  "limitations": ["1-4 caveats, including contradictions or low coverage"],
  "evidence_note": "one sentence describing the evidence base used",
  "general_knowledge_note": "optional one sentence for non-graph background, or null"
}}
""".strip()


def _build_evidence_digest(
    entity: EntityRead,
    inference: InferenceDetailRead,
) -> dict[str, object]:
    return {
        "entity": {
            "id": str(entity.id),
            "slug": entity.slug,
            "summary": entity.summary or {},
            "consensus_level": entity.consensus_level,
        },
        "stats": inference.stats.model_dump(mode="json"),
        "role_inferences": [
            role.model_dump(mode="json")
            for role in sorted(
                inference.role_inferences,
                key=lambda item: (item.coverage, item.confidence),
                reverse=True,
            )[:12]
        ],
        "relation_kind_summaries": [
            summary.model_dump(mode="json")
            for summary in inference.relation_kind_summaries[:12]
        ],
        "disagreements": [
            {
                "kind": group.kind,
                "supporting_count": len(group.supporting),
                "contradicting_count": len(group.contradicting),
                "confidence": group.confidence,
            }
            for group in inference.disagreement_groups[:8]
        ],
        "representative_evidence": [
            _relation_digest(relation)
            for relation in inference.evidence_items[:20]
        ],
    }


def _relation_digest(relation: RelationRead) -> dict[str, object]:
    return {
        "kind": relation.kind,
        "direction": normalize_direction(relation.direction),
        "confidence": relation.confidence,
        "scope": relation.scope or {},
        "source_title": relation.source_title,
        "source_year": relation.source_year,
        "roles": [
            {
                "entity_slug": role.entity_slug,
                "role_type": role.role_type,
                "weight": role.weight,
                "coverage": role.coverage,
                "disagreement": role.disagreement,
            }
            for role in relation.roles
        ],
    }


def _coerce_text(value: object) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return "No AI synthesis was returned."


def _coerce_optional_text(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _coerce_text_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]

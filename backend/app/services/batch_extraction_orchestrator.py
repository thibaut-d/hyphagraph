"""
Batch extraction orchestrator for coordinating entity and relation extraction.

Handles:
- Batch LLM calls for entities and relations
- Validation pipeline coordination
- Confidence filtering
- Result aggregation with validation metadata
"""
import logging

from app.llm.client import get_llm_provider
from app.llm.prompts import MEDICAL_KNOWLEDGE_SYSTEM_PROMPT, format_batch_extraction_prompt
from app.llm.schemas import (
    BatchExtractionResponse,
    ExtractedEntity,
    ExtractedRelation,
    validate_batch_extraction,
)
from app.services.extraction_validation_service import (
    ExtractionValidationService,
    ValidationLevel,
    ValidationResult,
)
from app.utils.confidence_filter import filter_by_confidence

logger = logging.getLogger(__name__)


class BatchExtractionOrchestrator:
    """
    Orchestrates batch extraction of entities and source-grounded relations.
    """

    def __init__(
        self,
        temperature: float = 0.0,
        max_tokens: int = 4000,
        enable_validation: bool = True,
        validation_level: ValidationLevel = "moderate",
        db=None,
    ):
        self.llm = get_llm_provider()
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.system_prompt = MEDICAL_KNOWLEDGE_SYSTEM_PROMPT
        self.db = db
        self.enable_validation = enable_validation
        self.validation_service = (
            ExtractionValidationService(
                validation_level=validation_level,
                auto_reject_invalid=(validation_level == "strict"),
            )
            if enable_validation
            else None
        )

    async def extract_batch(
        self,
        text: str,
        min_confidence: str | None = None,
    ) -> tuple[list[ExtractedEntity], list[ExtractedRelation]]:
        logger.info("Batch extraction from text (%d chars)", len(text))
        validated = await self._call_llm_for_batch(text)

        entities = validated.entities
        relations = validated.relations

        if self.enable_validation and self.validation_service:
            entities, relations = await self._validate_extractions_simple(entities, relations, text)

        entities = filter_by_confidence(entities, min_confidence)
        relations = filter_by_confidence(relations, min_confidence)

        logger.info(
            "Batch extraction complete: %d entities, %d relations",
            len(entities),
            len(relations),
        )
        return entities, relations

    async def extract_batch_with_validation_results(
        self,
        text: str,
        min_confidence: str | None = None,
    ) -> tuple[
        list[ExtractedEntity],
        list[ExtractedRelation],
        list[ValidationResult],
        list[ValidationResult],
    ]:
        logger.info("Batch extraction with validation results from text (%d chars)", len(text))
        validated = await self._call_llm_for_batch(text)

        entities = validated.entities
        relations = validated.relations

        entities, relations, entity_results, relation_results = (
            await self._validate_extractions_with_results(entities, relations, text)
        )

        if min_confidence:
            entities, entity_results = self._filter_by_confidence_with_results(
                entities,
                entity_results,
                min_confidence,
            )
            relations, relation_results = self._filter_by_confidence_with_results(
                relations,
                relation_results,
                min_confidence,
            )

        logger.info(
            "Batch extraction complete: %d entities, %d relations",
            len(entities),
            len(relations),
        )
        return entities, relations, entity_results, relation_results

    async def _call_llm_for_batch(self, text: str) -> BatchExtractionResponse:
        prompt = format_batch_extraction_prompt(text)
        response_data = await self.llm.generate_json(
            prompt=prompt,
            system_prompt=self.system_prompt,
            temperature=self.temperature,
            max_tokens=min(self.max_tokens * 2, 6000),
        )
        return validate_batch_extraction(response_data)

    async def _validate_extractions_simple(
        self,
        entities: list[ExtractedEntity],
        relations: list[ExtractedRelation],
        text: str,
    ) -> tuple[list[ExtractedEntity], list[ExtractedRelation]]:
        entities, relations, _, _ = await self._validate_extractions_with_results(
            entities,
            relations,
            text,
        )
        return entities, relations

    async def _validate_extractions_with_results(
        self,
        entities: list[ExtractedEntity],
        relations: list[ExtractedRelation],
        text: str,
    ) -> tuple[
        list[ExtractedEntity],
        list[ExtractedRelation],
        list[ValidationResult],
        list[ValidationResult],
    ]:
        entity_results: list[ValidationResult]
        relation_results: list[ValidationResult]

        if self.enable_validation and self.validation_service:
            logger.info("Validating extractions against source text...")
            entities, entity_results = await self.validation_service.validate_entities(
                entities,
                text,
            )
            relations, relation_results = await self.validation_service.validate_relations(
                relations,
                text,
            )
            relations, relation_results = self._check_entity_slug_coherence(
                entities,
                relations,
                relation_results,
            )

            flagged_entities = sum(1 for result in entity_results if result.flags)
            flagged_relations = sum(1 for result in relation_results if result.flags)
            if flagged_entities + flagged_relations > 0:
                logger.warning(
                    "Validation flagged items: %d entities, %d relations",
                    flagged_entities,
                    flagged_relations,
                )
        else:
            entity_results = [
                ValidationResult(
                    is_valid=True,
                    confidence_adjustment=1.0,
                    validation_score=1.0,
                    flags=[],
                    matched_span=None,
                )
                for _ in entities
            ]
            relation_results = [
                ValidationResult(
                    is_valid=True,
                    confidence_adjustment=1.0,
                    validation_score=1.0,
                    flags=[],
                    matched_span=None,
                )
                for _ in relations
            ]

        return entities, relations, entity_results, relation_results

    def _check_entity_slug_coherence(
        self,
        entities: list[ExtractedEntity],
        relations: list[ExtractedRelation],
        relation_results: list[ValidationResult],
    ) -> tuple[list[ExtractedRelation], list[ValidationResult]]:
        """
        Every entity_slug referenced in relations must appear in the entity list.
        """
        entity_slug_set = {entity.slug for entity in entities}
        auto_reject = (
            self.validation_service is not None
            and self.validation_service.auto_reject_invalid
        )

        out_relations: list[ExtractedRelation] = []
        out_relation_results: list[ValidationResult] = []

        for relation, result in zip(relations, relation_results):
            unknown = sorted(
                {
                    role.entity_slug
                    for role in relation.roles
                    if role.entity_slug not in entity_slug_set
                }
            )
            if unknown:
                result = ValidationResult(
                    is_valid=False if auto_reject else result.is_valid,
                    confidence_adjustment=result.confidence_adjustment * 0.5,
                    validation_score=result.validation_score * 0.5,
                    flags=result.flags + [f"unknown_entity_slug:{','.join(unknown)}"],
                    matched_span=result.matched_span,
                )
                logger.warning(
                    "Relation '%s' references unknown entity slugs: %s",
                    relation.relation_type,
                    unknown,
                )

            if result.is_valid or not auto_reject:
                out_relations.append(relation)
                out_relation_results.append(result)

        return out_relations, out_relation_results

    def _filter_by_confidence_with_results(
        self,
        items: list[ExtractedEntity] | list[ExtractedRelation],
        results: list[ValidationResult],
        min_confidence: str | None,
    ) -> tuple[list, list[ValidationResult]]:
        if not min_confidence:
            return items, results

        confidence_order = {"high": 3, "medium": 2, "low": 1}
        min_level = confidence_order.get(min_confidence, 1)
        filtered = [
            (item, result)
            for item, result in zip(items, results)
            if confidence_order.get(item.confidence, 0) >= min_level
        ]
        if not filtered:
            return [], []

        filtered_items, filtered_results = zip(*filtered)
        return list(filtered_items), list(filtered_results)

"""
Batch extraction orchestrator for coordinating entity and relation extraction.

Handles:
- Batch LLM calls for entities and relations
- Validation pipeline coordination
- Confidence filtering
- Result aggregation with validation metadata
"""
import json
import logging
import re

from app.llm.client import get_llm_provider
from app.llm.prompts import (
    MEDICAL_KNOWLEDGE_SYSTEM_PROMPT,
    format_batch_extraction_prompt,
    format_batch_gleaning_prompt,
)
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
from app.services.extraction_semantic_normalizer import ExtractionSemanticNormalizer
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
        max_gleaning_passes: int = 1,
        max_chunk_chars: int = 12000,
        chunk_overlap_chars: int = 800,
        max_chunks: int = 6,
        db=None,
    ):
        self.llm = get_llm_provider()
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.system_prompt = MEDICAL_KNOWLEDGE_SYSTEM_PROMPT
        self.db = db
        self.enable_validation = enable_validation
        self.max_gleaning_passes = max(0, max_gleaning_passes)
        self.max_chunk_chars = max(1, max_chunk_chars)
        self.chunk_overlap_chars = max(0, min(chunk_overlap_chars, self.max_chunk_chars // 2))
        self.max_chunks = max(1, max_chunks)
        self.semantic_normalizer = ExtractionSemanticNormalizer()
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
            entities, relations = await self._validate_extractions_simple(
                entities,
                relations,
                text,
            )

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
        chunks = self._split_text_for_extraction(text)
        if len(chunks) == 1:
            return await self._extract_single_batch_response(chunks[0])

        logger.info(
            "Batch extraction will run across %d chunks (%d chars total)",
            len(chunks),
            len(text),
        )
        merged_response = BatchExtractionResponse(entities=[], relations=[])
        for chunk_index, chunk_text in enumerate(chunks):
            logger.info(
                "Extracting chunk %d/%d (%d chars)",
                chunk_index + 1,
                len(chunks),
                len(chunk_text),
            )
            chunk_response = await self._extract_single_batch_response(chunk_text)
            merged_response, _ = self._merge_batch_extractions(
                merged_response,
                chunk_response,
            )

        return merged_response

    async def _extract_single_batch_response(self, text: str) -> BatchExtractionResponse:
        prompt = format_batch_extraction_prompt(text)
        response_data = await self.llm.generate_json(
            prompt=prompt,
            system_prompt=self.system_prompt,
            temperature=self.temperature,
            max_tokens=min(self.max_tokens * 2, 6000),
        )
        merged_response = self.semantic_normalizer.normalize_batch_response(
            validate_batch_extraction(response_data)
        )

        for pass_index in range(self.max_gleaning_passes):
            merged_response, added_any = await self._run_gleaning_pass(
                text=text,
                current_response=merged_response,
                pass_index=pass_index,
            )
            if not added_any:
                break

        return merged_response

    def _split_text_for_extraction(self, text: str) -> list[str]:
        normalized_text = text.strip()
        if len(normalized_text) <= self.max_chunk_chars:
            return [normalized_text]

        chunks: list[str] = []
        start = 0
        text_length = len(normalized_text)

        while start < text_length:
            remaining_slots = self.max_chunks - len(chunks)
            if remaining_slots <= 1:
                start = max(start, text_length - self.max_chunk_chars)
                start = self._find_preferred_chunk_start(
                    normalized_text,
                    start,
                )
                end = text_length
            else:
                hard_end = min(start + self.max_chunk_chars, text_length)
                end = self._find_preferred_chunk_end(
                    normalized_text,
                    start,
                    hard_end,
                )

            chunk_text = normalized_text[start:end].strip()
            if chunk_text and (not chunks or chunk_text != chunks[-1]):
                chunks.append(chunk_text)

            if end >= text_length:
                break

            next_start = max(0, end - self.chunk_overlap_chars)
            next_start = self._find_preferred_chunk_start(
                normalized_text,
                next_start,
            )
            if next_start <= start:
                next_start = end
            start = next_start

        return chunks or [normalized_text[: self.max_chunk_chars].strip()]

    def _find_preferred_chunk_end(
        self,
        text: str,
        start: int,
        hard_end: int,
    ) -> int:
        if hard_end >= len(text):
            return len(text)

        search_start = start + max(1, self.max_chunk_chars // 2)
        candidate_positions = [
            match.end()
            for match in re.finditer(r"\n\s*\n|(?<=[.!?])\s+|\n", text[search_start:hard_end])
        ]
        if not candidate_positions:
            return hard_end

        return search_start + candidate_positions[-1]

    def _find_preferred_chunk_start(self, text: str, start: int) -> int:
        search_start = max(0, start - max(10, self.max_chunk_chars // 4))
        candidate_positions = [
            match.end()
            for match in re.finditer(r"\n\s*\n|(?<=[.!?])\s+|\n", text[search_start:start])
        ]
        if candidate_positions:
            start = search_start + candidate_positions[-1]

        while start < len(text) and text[start].isspace():
            start += 1
        return start

    async def _run_gleaning_pass(
        self,
        *,
        text: str,
        current_response: BatchExtractionResponse,
        pass_index: int,
    ) -> tuple[BatchExtractionResponse, bool]:
        glean_prompt = format_batch_gleaning_prompt(
            text=text,
            existing_extraction=current_response.model_dump(mode="json"),
        )
        response_data = await self.llm.generate_json(
            prompt=glean_prompt,
            system_prompt=self.system_prompt,
            temperature=self.temperature,
            max_tokens=min(self.max_tokens * 2, 6000),
        )
        gleaned_response = self.semantic_normalizer.normalize_batch_response(
            validate_batch_extraction(response_data)
        )
        merged_response, added_any = self._merge_batch_extractions(
            current_response,
            gleaned_response,
        )
        logger.info(
            "Batch gleaning pass %d/%d complete: +%d entities, +%d relations",
            pass_index + 1,
            self.max_gleaning_passes,
            len(merged_response.entities) - len(current_response.entities),
            len(merged_response.relations) - len(current_response.relations),
        )
        return merged_response, added_any

    def _merge_batch_extractions(
        self,
        base: BatchExtractionResponse,
        additions: BatchExtractionResponse,
    ) -> tuple[BatchExtractionResponse, bool]:
        merged_entities = list(base.entities)
        merged_relations = list(base.relations)
        seen_entity_slugs = {entity.slug for entity in merged_entities}
        seen_relation_keys = {
            self._relation_merge_key(relation) for relation in merged_relations
        }
        added_any = False

        for entity in additions.entities:
            if entity.slug in seen_entity_slugs:
                continue
            merged_entities.append(entity)
            seen_entity_slugs.add(entity.slug)
            added_any = True

        for relation in additions.relations:
            relation_key = self._relation_merge_key(relation)
            if relation_key in seen_relation_keys:
                continue
            merged_relations.append(relation)
            seen_relation_keys.add(relation_key)
            added_any = True

        return (
            BatchExtractionResponse(
                entities=merged_entities,
                relations=merged_relations,
            ),
            added_any,
        )

    def _relation_merge_key(self, relation: ExtractedRelation) -> tuple[object, ...]:
        roles_key = tuple(
            sorted((role.role_type, role.entity_slug) for role in relation.roles)
        )
        scope_key = json.dumps(
            relation.scope or {},
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        evidence_context = relation.evidence_context
        evidence_key = (
            evidence_context.statement_kind if evidence_context else None,
            evidence_context.finding_polarity if evidence_context else None,
        )
        text_span_key = " ".join(relation.text_span.split())
        return (
            relation.relation_type,
            roles_key,
            text_span_key,
            scope_key,
            evidence_key,
        )

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
                entities=entities,
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

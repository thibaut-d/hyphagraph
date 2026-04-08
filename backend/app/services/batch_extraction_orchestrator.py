"""
Batch extraction orchestrator for coordinating multi-type LLM extractions.

Handles:
- Batch LLM calls for entities, relations, and claims
- Validation pipeline coordination
- Confidence and evidence filtering
- Result aggregation with validation metadata

Used by document extraction workflows where all extraction types
are needed from a single text source.
"""
import logging

from app.llm.client import get_llm_provider
from app.llm.prompts import (
    MEDICAL_KNOWLEDGE_SYSTEM_PROMPT,
    format_batch_extraction_prompt,
)
from app.llm.schemas import (
    ExtractedEntity,
    ExtractedRelation,
    ExtractedClaim,
    BatchExtractionResponse,
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
    Orchestrates batch extraction of entities, relations, and claims.

    Coordinates:
    1. LLM batch extraction
    2. Validation pipeline
    3. Confidence/evidence filtering
    4. Result aggregation

    Used by document extraction workflows where all extraction types
    are needed from a single text source.
    """

    def __init__(
        self,
        temperature: float = 0.0,
        max_tokens: int = 4000,
        enable_validation: bool = True,
        validation_level: ValidationLevel = "moderate",
        db=None,  # For future prompt generation
    ):
        """
        Initialize batch extraction orchestrator.

        Args:
            temperature: LLM temperature for extraction (lower = more deterministic)
            max_tokens: Maximum tokens for LLM response (batch uses 2x)
            enable_validation: Whether to validate extractions against source text
            validation_level: Strictness of validation ("strict", "moderate", "lenient")
            db: Optional database session for future dynamic prompt generation
        """
        self.llm = get_llm_provider()
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.system_prompt = MEDICAL_KNOWLEDGE_SYSTEM_PROMPT
        self.db = db

        # Validation setup
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
        min_evidence_strength: str | None = None,
    ) -> tuple[list[ExtractedEntity], list[ExtractedRelation], list[ExtractedClaim]]:
        """
        Extract entities, relations, and claims in one batch.

        More efficient than calling each extraction separately.

        Args:
            text: Input text to extract from
            min_confidence: Optional minimum confidence for entities/relations
            min_evidence_strength: Optional minimum evidence strength for claims

        Returns:
            Tuple of (entities, relations, claims)

        Raises:
            Exception: If extraction fails or LLM is unavailable
        """
        logger.info(f"Batch extraction from text ({len(text)} chars)")

        # Call LLM for batch extraction
        try:
            validated = await self._call_llm_for_batch(text)
        except Exception as e:
            logger.error(f"Batch extraction failed: {e}")
            raise

        # Extract initial results
        entities = validated.entities
        relations = validated.relations
        claims = validated.claims

        # Validate extractions against source text (hallucination prevention)
        if self.enable_validation and self.validation_service:
            entities, relations, claims = await self._validate_extractions_simple(
                entities, relations, claims, text
            )

        # Filter entities and relations by confidence
        entities = filter_by_confidence(entities, min_confidence)
        relations = filter_by_confidence(relations, min_confidence)

        # Filter claims by evidence strength
        claims = self._filter_by_evidence(claims, min_evidence_strength)

        logger.info(
            f"Batch extraction complete: {len(entities)} entities, "
            f"{len(relations)} relations, {len(claims)} claims"
        )

        return entities, relations, claims

    async def extract_batch_with_validation_results(
        self,
        text: str,
        min_confidence: str | None = None,
        min_evidence_strength: str | None = None,
    ) -> tuple[
        list[ExtractedEntity],
        list[ExtractedRelation],
        list[ExtractedClaim],
        list[ValidationResult],  # Entity validation results
        list[ValidationResult],  # Relation validation results
        list[ValidationResult],  # Claim validation results
    ]:
        """
        Extract entities, relations, and claims with validation results.

        This is an extended version of extract_batch() that returns validation
        metadata alongside extractions. Used for human-in-the-loop review workflow.

        Args:
            text: Input text to extract from
            min_confidence: Optional minimum confidence for entities/relations
            min_evidence_strength: Optional minimum evidence strength for claims

        Returns:
            Tuple of:
            - entities: List of extracted entities
            - relations: List of extracted relations
            - claims: List of extracted claims
            - entity_validation_results: Validation metadata for each entity
            - relation_validation_results: Validation metadata for each relation
            - claim_validation_results: Validation metadata for each claim

        Raises:
            Exception: If extraction fails or LLM is unavailable
        """
        logger.info(f"Batch extraction with validation results from text ({len(text)} chars)")

        # Call LLM for batch extraction
        try:
            validated = await self._call_llm_for_batch(text)
        except Exception as e:
            logger.error(f"Batch extraction with validation failed: {e}")
            raise

        # Get initial extractions
        entities = validated.entities
        relations = validated.relations
        claims = validated.claims

        # Validate extractions against source text
        (
            entities,
            relations,
            claims,
            entity_results,
            relation_results,
            claim_results,
        ) = await self._validate_extractions_with_results(entities, relations, claims, text)

        # Filter by confidence/evidence strength while keeping results aligned
        if min_confidence:
            entities, entity_results = self._filter_by_confidence_with_results(
                entities, entity_results, min_confidence
            )
            relations, relation_results = self._filter_by_confidence_with_results(
                relations, relation_results, min_confidence
            )

        if min_evidence_strength:
            claims, claim_results = self._filter_by_evidence_with_results(
                claims, claim_results, min_evidence_strength
            )

        logger.info(
            f"Batch extraction complete: {len(entities)} entities, "
            f"{len(relations)} relations, {len(claims)} claims"
        )

        return entities, relations, claims, entity_results, relation_results, claim_results

    async def _call_llm_for_batch(self, text: str) -> BatchExtractionResponse:
        """
        Call LLM with batch prompt and return validated response.

        Args:
            text: Input text to extract from

        Returns:
            Validated batch extraction response

        Raises:
            Exception: If LLM call fails or validation fails
        """
        # Format prompt
        prompt = format_batch_extraction_prompt(text)

        # Call LLM with higher token limit for batch
        response_data = await self.llm.generate_json(
            prompt=prompt,
            system_prompt=self.system_prompt,
            temperature=self.temperature,
            max_tokens=min(self.max_tokens * 2, 6000),  # Extra headroom for richer structured extraction
        )

        # Validate response schema
        validated = validate_batch_extraction(response_data)
        return validated

    async def _validate_extractions_simple(
        self,
        entities: list[ExtractedEntity],
        relations: list[ExtractedRelation],
        claims: list[ExtractedClaim],
        text: str,
    ) -> tuple[list[ExtractedEntity], list[ExtractedRelation], list[ExtractedClaim]]:
        """
        Validate extractions and return filtered lists (without validation results).

        Delegates to _validate_extractions_with_results and discards the result metadata.
        """
        entities, relations, claims, _, _, _ = await self._validate_extractions_with_results(
            entities, relations, claims, text
        )
        return entities, relations, claims

    async def _validate_extractions_with_results(
        self,
        entities: list[ExtractedEntity],
        relations: list[ExtractedRelation],
        claims: list[ExtractedClaim],
        text: str,
    ) -> tuple[
        list[ExtractedEntity],
        list[ExtractedRelation],
        list[ExtractedClaim],
        list[ValidationResult],
        list[ValidationResult],
        list[ValidationResult],
    ]:
        """
        Validate extractions and return both filtered lists and validation results.

        Args:
            entities: Extracted entities
            relations: Extracted relations
            claims: Extracted claims
            text: Source text for validation

        Returns:
            Tuple of (entities, relations, claims, entity_results, relation_results, claim_results)
        """
        entity_results = []
        relation_results = []
        claim_results = []

        if self.enable_validation and self.validation_service:
            logger.info("Validating extractions against source text...")

            # Validate entities
            entities, entity_results = await self.validation_service.validate_entities(
                entities, text
            )

            # Validate relations
            relations, relation_results = await self.validation_service.validate_relations(
                relations, text
            )

            # Validate claims
            claims, claim_results = await self.validation_service.validate_claims(claims, text)

            # Semantic cross-field check: entity_slug coherence
            relations, relation_results, claims, claim_results = (
                self._check_entity_slug_coherence(
                    entities, relations, relation_results, claims, claim_results
                )
            )

            # Log validation summary
            flagged_entities = sum(1 for r in entity_results if r.flags)
            flagged_relations = sum(1 for r in relation_results if r.flags)
            flagged_claims = sum(1 for r in claim_results if r.flags)

            if flagged_entities + flagged_relations + flagged_claims > 0:
                logger.warning(
                    f"Validation flagged items: {flagged_entities} entities, "
                    f"{flagged_relations} relations, {flagged_claims} claims"
                )
        else:
            # No validation - create dummy validation results
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
            claim_results = [
                ValidationResult(
                    is_valid=True,
                    confidence_adjustment=1.0,
                    validation_score=1.0,
                    flags=[],
                    matched_span=None,
                )
                for _ in claims
            ]

        return entities, relations, claims, entity_results, relation_results, claim_results

    def _check_entity_slug_coherence(
        self,
        entities: list[ExtractedEntity],
        relations: list[ExtractedRelation],
        relation_results: list[ValidationResult],
        claims: list[ExtractedClaim],
        claim_results: list[ValidationResult],
    ) -> tuple[
        list[ExtractedRelation],
        list[ValidationResult],
        list[ExtractedClaim],
        list[ValidationResult],
    ]:
        """
        Cross-field semantic check: every entity_slug referenced in relations
        and claims must appear in the extracted entity list from the same batch.

        Flags offending items and halves their confidence score.
        In strict mode (auto_reject_invalid=True) they are removed entirely.
        """
        entity_slug_set = {e.slug for e in entities}
        auto_reject = (
            self.validation_service is not None
            and self.validation_service.auto_reject_invalid
        )

        out_relations: list[ExtractedRelation] = []
        out_relation_results: list[ValidationResult] = []
        for relation, result in zip(relations, relation_results):
            unknown = sorted({r.entity_slug for r in relation.roles if r.entity_slug not in entity_slug_set})
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

        out_claims: list[ExtractedClaim] = []
        out_claim_results: list[ValidationResult] = []
        for claim, result in zip(claims, claim_results):
            unknown = sorted({s for s in claim.entities_involved if s not in entity_slug_set})
            if unknown:
                result = ValidationResult(
                    is_valid=False if auto_reject else result.is_valid,
                    confidence_adjustment=result.confidence_adjustment * 0.5,
                    validation_score=result.validation_score * 0.5,
                    flags=result.flags + [f"unknown_entity_slug:{','.join(unknown)}"],
                    matched_span=result.matched_span,
                )
                logger.warning(
                    "Claim references unknown entity slugs: %s",
                    unknown,
                )
            if result.is_valid or not auto_reject:
                out_claims.append(claim)
                out_claim_results.append(result)

        return out_relations, out_relation_results, out_claims, out_claim_results

    def _filter_by_evidence(
        self, claims: list[ExtractedClaim], min_evidence_strength: str | None
    ) -> list[ExtractedClaim]:
        """
        Filter claims by evidence strength.

        Args:
            claims: List of extracted claims
            min_evidence_strength: Minimum evidence strength ("strong", "moderate", "weak", "anecdotal")

        Returns:
            Filtered list of claims
        """
        if not min_evidence_strength:
            return claims

        evidence_order = {"strong": 4, "moderate": 3, "weak": 2, "anecdotal": 1}
        min_level = evidence_order.get(min_evidence_strength, 1)
        return [
            c for c in claims if evidence_order.get(c.evidence_strength, 0) >= min_level
        ]

    def _filter_by_confidence_with_results(
        self,
        items: list[ExtractedEntity] | list[ExtractedRelation],
        results: list[ValidationResult],
        min_confidence: str | None,
    ) -> tuple[list, list[ValidationResult]]:
        """
        Filter items and validation results together by confidence.

        Args:
            items: List of extracted entities or relations
            results: List of validation results (parallel to items)
            min_confidence: Minimum confidence level ("high", "medium", "low")

        Returns:
            Tuple of (filtered_items, filtered_results)
        """
        if not min_confidence:
            return items, results

        confidence_order = {"high": 3, "medium": 2, "low": 1}
        min_level = confidence_order.get(min_confidence, 1)

        # Filter items and results together
        filtered = [
            (item, result)
            for item, result in zip(items, results)
            if confidence_order.get(item.confidence, 0) >= min_level
        ]

        if not filtered:
            return [], []

        filtered_items, filtered_results = zip(*filtered)
        return list(filtered_items), list(filtered_results)

    def _filter_by_evidence_with_results(
        self,
        claims: list[ExtractedClaim],
        results: list[ValidationResult],
        min_evidence_strength: str | None,
    ) -> tuple[list[ExtractedClaim], list[ValidationResult]]:
        """
        Filter claims and validation results together by evidence strength.

        Args:
            claims: List of extracted claims
            results: List of validation results (parallel to claims)
            min_evidence_strength: Minimum evidence strength

        Returns:
            Tuple of (filtered_claims, filtered_results)
        """
        if not min_evidence_strength:
            return claims, results

        evidence_order = {"strong": 4, "moderate": 3, "weak": 2, "anecdotal": 1}
        min_level = evidence_order.get(min_evidence_strength, 1)

        # Filter claims and results together
        filtered = [
            (claim, result)
            for claim, result in zip(claims, results)
            if evidence_order.get(claim.evidence_strength, 0) >= min_level
        ]

        if not filtered:
            return [], []

        filtered_claims, filtered_results = zip(*filtered)
        return list(filtered_claims), list(filtered_results)

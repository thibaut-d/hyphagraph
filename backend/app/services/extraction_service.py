"""
Knowledge extraction service using LLM.

Provides high-level functions for extracting entities, relations, and claims
from text using the LLM integration with built-in hallucination validation.
"""
import logging
from typing import Any

from app.llm.client import get_llm_provider
from app.llm.prompts import (
    MEDICAL_KNOWLEDGE_SYSTEM_PROMPT,
    format_entity_extraction_prompt,
    format_relation_extraction_prompt,
    format_claim_extraction_prompt,
    format_batch_extraction_prompt,
)
from app.llm.schemas import (
    ExtractedEntity,
    ExtractedRelation,
    ExtractedClaim,
    validate_entity_extraction,
    validate_relation_extraction,
    validate_claim_extraction,
    validate_batch_extraction,
)
from app.services.extraction_validation_service import (
    ExtractionValidationService,
    ValidationLevel,
    ValidationResult,
)

logger = logging.getLogger(__name__)


class ExtractionService:
    """
    Service for extracting knowledge from text using LLM.

    Handles entity extraction, relation extraction, claim extraction,
    and batch processing with validation and error handling.

    Uses DYNAMIC prompts generated from database relation types.
    """

    def __init__(
        self,
        temperature: float = 0.2,
        max_tokens: int = 3000,
        db=None,
        enable_validation: bool = True,
        validation_level: ValidationLevel = "moderate"
    ):
        """
        Initialize extraction service.

        Args:
            temperature: LLM temperature for extraction (lower = more deterministic)
            max_tokens: Maximum tokens for LLM response
            db: Optional database session for dynamic prompt generation
            enable_validation: Whether to validate extractions against source text
            validation_level: Strictness of validation ("strict", "moderate", "lenient")
        """
        self.llm = get_llm_provider()
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.system_prompt = MEDICAL_KNOWLEDGE_SYSTEM_PROMPT
        self.db = db
        self._relation_types_cache = None  # Cache relation types for this service instance

        # Hallucination validation
        self.enable_validation = enable_validation
        self.validation_service = ExtractionValidationService(
            validation_level=validation_level,
            auto_reject_invalid=(validation_level == "strict")
        ) if enable_validation else None

    async def _get_relation_types_prompt(self) -> str:
        """
        Generate dynamic relation types prompt from database.

        Returns formatted string with all active relation types from DB.
        Falls back to hardcoded types if database not available.
        """
        if self._relation_types_cache:
            return self._relation_types_cache

        if self.db:
            try:
                from app.services.relation_type_service import RelationTypeService
                service = RelationTypeService(self.db)
                prompt_text = await service.get_for_llm_prompt()
                self._relation_types_cache = prompt_text
                logger.info("Using DYNAMIC relation types from database")
                return prompt_text
            except Exception as e:
                logger.warning(f"Failed to load dynamic relation types, using fallback: {e}")

        # Fallback to static prompt if database not available
        logger.warning("Using STATIC relation types (database not available)")
        return """CRITICAL: relation_type MUST be one of the types in the list above.
   If unsure, use 'other'."""

    async def _get_semantic_roles_prompt(self) -> str:
        """
        Generate dynamic semantic roles prompt from database.

        Returns formatted string with all active semantic roles from DB.
        """
        if self.db:
            try:
                from app.services.semantic_role_service import SemanticRoleService
                service = SemanticRoleService(self.db)
                prompt_text = await service.get_for_llm_prompt()
                logger.info("Using DYNAMIC semantic roles from database")
                return prompt_text
            except Exception as e:
                logger.warning(f"Failed to load dynamic semantic roles, using fallback: {e}")

        # Fallback
        logger.warning("Using STATIC semantic roles (database not available)")
        return """SEMANTIC ROLES: agent, target, population, mechanism, dosage, etc.
   Use appropriate semantic roles for each entity in the relation."""

    async def extract_entities(
        self,
        text: str,
        min_confidence: str | None = None
    ) -> list[ExtractedEntity]:
        """
        Extract entities from text.

        Args:
            text: Input text to extract entities from
            min_confidence: Optional minimum confidence level (high, medium, low)

        Returns:
            List of extracted entities with metadata

        Raises:
            Exception: If extraction fails or LLM is unavailable
        """
        logger.info(f"Extracting entities from text ({len(text)} chars)")

        # Format prompt
        prompt = format_entity_extraction_prompt(text)

        # Call LLM
        try:
            response_data = await self.llm.generate_json(
                prompt=prompt,
                system_prompt=self.system_prompt,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            # Validate response
            validated = validate_entity_extraction(response_data)

            # Filter by confidence if requested
            entities = validated.entities
            if min_confidence:
                confidence_order = {"high": 3, "medium": 2, "low": 1}
                min_level = confidence_order.get(min_confidence, 1)
                entities = [
                    e for e in entities
                    if confidence_order.get(e.confidence, 0) >= min_level
                ]

            logger.info(f"Extracted {len(entities)} entities (filtered: {min_confidence})")
            return entities

        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            raise

    async def extract_relations(
        self,
        text: str,
        entities: list[ExtractedEntity] | list[dict[str, Any]],
        min_confidence: str | None = None
    ) -> list[ExtractedRelation]:
        """
        Extract relations between entities from text.

        Args:
            text: Input text to extract relations from
            entities: List of entities (ExtractedEntity or dict with slug/summary)
            min_confidence: Optional minimum confidence level

        Returns:
            List of extracted relations with metadata

        Raises:
            Exception: If extraction fails or LLM is unavailable
        """
        logger.info(f"Extracting relations from text with {len(entities)} entities")

        # Convert ExtractedEntity to dict if needed
        entities_dict = []
        for e in entities:
            if isinstance(e, ExtractedEntity):
                entities_dict.append({
                    "slug": e.slug,
                    "summary": e.summary,
                    "category": e.category
                })
            else:
                entities_dict.append(e)

        # Format prompt
        prompt = format_relation_extraction_prompt(text, entities_dict)

        # Call LLM
        try:
            response_data = await self.llm.generate_json(
                prompt=prompt,
                system_prompt=self.system_prompt,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            # Validate response
            validated = validate_relation_extraction(response_data)

            # Filter by confidence if requested
            relations = validated.relations
            if min_confidence:
                confidence_order = {"high": 3, "medium": 2, "low": 1}
                min_level = confidence_order.get(min_confidence, 1)
                relations = [
                    r for r in relations
                    if confidence_order.get(r.confidence, 0) >= min_level
                ]

            logger.info(f"Extracted {len(relations)} relations (filtered: {min_confidence})")
            return relations

        except Exception as e:
            logger.error(f"Relation extraction failed: {e}")
            raise

    async def extract_claims(
        self,
        text: str,
        min_evidence_strength: str | None = None
    ) -> list[ExtractedClaim]:
        """
        Extract factual claims from text.

        Args:
            text: Input text to extract claims from
            min_evidence_strength: Optional minimum evidence level (strong, moderate, weak)

        Returns:
            List of extracted claims with metadata

        Raises:
            Exception: If extraction fails or LLM is unavailable
        """
        logger.info(f"Extracting claims from text ({len(text)} chars)")

        # Format prompt
        prompt = format_claim_extraction_prompt(text)

        # Call LLM
        try:
            response_data = await self.llm.generate_json(
                prompt=prompt,
                system_prompt=self.system_prompt,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            # Validate response
            validated = validate_claim_extraction(response_data)

            # Filter by evidence strength if requested
            claims = validated.claims
            if min_evidence_strength:
                evidence_order = {"strong": 4, "moderate": 3, "weak": 2, "anecdotal": 1}
                min_level = evidence_order.get(min_evidence_strength, 1)
                claims = [
                    c for c in claims
                    if evidence_order.get(c.evidence_strength, 0) >= min_level
                ]

            logger.info(f"Extracted {len(claims)} claims (filtered: {min_evidence_strength})")
            return claims

        except Exception as e:
            logger.error(f"Claim extraction failed: {e}")
            raise

    async def extract_batch(
        self,
        text: str,
        min_confidence: str | None = None,
        min_evidence_strength: str | None = None
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

        # Format prompt
        prompt = format_batch_extraction_prompt(text)

        # Call LLM with higher token limit for batch
        try:
            response_data = await self.llm.generate_json(
                prompt=prompt,
                system_prompt=self.system_prompt,
                temperature=self.temperature,
                max_tokens=min(self.max_tokens * 2, 4000),  # Double tokens for batch
            )

            # Validate response schema
            validated = validate_batch_extraction(response_data)

            # Validate extractions against source text (hallucination prevention)
            entities = validated.entities
            relations = validated.relations
            claims = validated.claims

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
                claims, claim_results = await self.validation_service.validate_claims(
                    claims, text
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

            # Filter entities by confidence
            entities = entities
            if min_confidence:
                confidence_order = {"high": 3, "medium": 2, "low": 1}
                min_level = confidence_order.get(min_confidence, 1)
                entities = [
                    e for e in entities
                    if confidence_order.get(e.confidence, 0) >= min_level
                ]

            # Filter relations by confidence
            if min_confidence:
                confidence_order = {"high": 3, "medium": 2, "low": 1}
                min_level = confidence_order.get(min_confidence, 1)
                relations = [
                    r for r in relations
                    if confidence_order.get(r.confidence, 0) >= min_level
                ]

            # Filter claims by evidence strength
            if min_evidence_strength:
                evidence_order = {"strong": 4, "moderate": 3, "weak": 2, "anecdotal": 1}
                min_level = evidence_order.get(min_evidence_strength, 1)
                claims = [
                    c for c in claims
                    if evidence_order.get(c.evidence_strength, 0) >= min_level
                ]

            logger.info(
                f"Batch extraction complete: {len(entities)} entities, "
                f"{len(relations)} relations, {len(claims)} claims"
            )

            return entities, relations, claims

        except Exception as e:
            logger.error(f"Batch extraction failed: {e}")
            raise

    async def extract_batch_with_validation_results(
        self,
        text: str,
        min_confidence: str | None = None,
        min_evidence_strength: str | None = None
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

        # Format prompt
        prompt = format_batch_extraction_prompt(text)

        # Call LLM with higher token limit for batch
        try:
            response_data = await self.llm.generate_json(
                prompt=prompt,
                system_prompt=self.system_prompt,
                temperature=self.temperature,
                max_tokens=min(self.max_tokens * 2, 4000),
            )

            # Validate response schema
            validated = validate_batch_extraction(response_data)

            # Get initial extractions
            entities = validated.entities
            relations = validated.relations
            claims = validated.claims

            # Validate extractions against source text
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
                claims, claim_results = await self.validation_service.validate_claims(
                    claims, text
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
                from app.services.extraction_validation_service import ValidationResult
                entity_results = [
                    ValidationResult(
                        is_valid=True,
                        confidence_adjustment=1.0,
                        validation_score=1.0,
                        flags=[],
                        matched_span=None
                    ) for _ in entities
                ]
                relation_results = [
                    ValidationResult(
                        is_valid=True,
                        confidence_adjustment=1.0,
                        validation_score=1.0,
                        flags=[],
                        matched_span=None
                    ) for _ in relations
                ]
                claim_results = [
                    ValidationResult(
                        is_valid=True,
                        confidence_adjustment=1.0,
                        validation_score=1.0,
                        flags=[],
                        matched_span=None
                    ) for _ in claims
                ]

            # Filter by confidence/evidence strength
            if min_confidence:
                confidence_order = {"high": 3, "medium": 2, "low": 1}
                min_level = confidence_order.get(min_confidence, 1)

                # Filter entities and their validation results together
                filtered = [
                    (e, r) for e, r in zip(entities, entity_results)
                    if confidence_order.get(e.confidence, 0) >= min_level
                ]
                entities, entity_results = zip(*filtered) if filtered else ([], [])
                entities, entity_results = list(entities), list(entity_results)

                # Filter relations and their validation results together
                filtered = [
                    (r, v) for r, v in zip(relations, relation_results)
                    if confidence_order.get(r.confidence, 0) >= min_level
                ]
                relations, relation_results = zip(*filtered) if filtered else ([], [])
                relations, relation_results = list(relations), list(relation_results)

            if min_evidence_strength:
                evidence_order = {"strong": 4, "moderate": 3, "weak": 2, "anecdotal": 1}
                min_level = evidence_order.get(min_evidence_strength, 1)

                # Filter claims and their validation results together
                filtered = [
                    (c, v) for c, v in zip(claims, claim_results)
                    if evidence_order.get(c.evidence_strength, 0) >= min_level
                ]
                claims, claim_results = zip(*filtered) if filtered else ([], [])
                claims, claim_results = list(claims), list(claim_results)

            logger.info(
                f"Batch extraction complete: {len(entities)} entities, "
                f"{len(relations)} relations, {len(claims)} claims"
            )

            return entities, relations, claims, entity_results, relation_results, claim_results

        except Exception as e:
            logger.error(f"Batch extraction with validation failed: {e}")
            raise

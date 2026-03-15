"""
Knowledge extraction service using LLM.

Provides high-level functions for extracting entities, relations, and claims
from text using the LLM integration with built-in hallucination validation.
"""
import logging

from app.llm.client import get_llm_provider
from app.utils.confidence_filter import filter_by_confidence
from app.llm.prompts import (
    MEDICAL_KNOWLEDGE_SYSTEM_PROMPT,
    RelationPromptEntity,
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
from app.services.relation_type_service import RelationTypeService
from app.services.semantic_role_service import SemanticRoleService

logger = logging.getLogger(__name__)


class ExtractionService:
    """
    Service for individual knowledge extraction from text using LLM.

    Handles entity extraction, relation extraction, and claim extraction
    with validation and error handling.

    For batch extraction (entities + relations + claims in one call),
    use BatchExtractionOrchestrator instead.

    Uses DYNAMIC prompts generated from database relation types.
    """

    def __init__(
        self,
        temperature: float = 0.2,
        max_tokens: int = 3000,
        db=None,
        enable_validation: bool = True,
        validation_level: ValidationLevel = "moderate",
        relation_type_service: RelationTypeService | None = None,
        semantic_role_service: SemanticRoleService | None = None,
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
        self.relation_type_service = (
            relation_type_service or RelationTypeService(db)
            if db else relation_type_service
        )
        self.semantic_role_service = (
            semantic_role_service or SemanticRoleService(db)
            if db else semantic_role_service
        )

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
                if not self.relation_type_service:
                    raise RuntimeError("Relation type service unavailable")
                prompt_text = await self.relation_type_service.get_for_llm_prompt()
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
                if not self.semantic_role_service:
                    raise RuntimeError("Semantic role service unavailable")
                prompt_text = await self.semantic_role_service.get_for_llm_prompt()
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
            entities = filter_by_confidence(validated.entities, min_confidence)

            logger.info(f"Extracted {len(entities)} entities (filtered: {min_confidence})")
            return entities

        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            raise

    async def extract_relations(
        self,
        text: str,
        entities: list[ExtractedEntity] | list[RelationPromptEntity],
        min_confidence: str | None = None,
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
        entities_dict: list[RelationPromptEntity] = []
        for e in entities:
            if isinstance(e, ExtractedEntity):
                entities_dict.append({
                    "slug": e.slug,
                    "summary": e.summary,
                    "category": e.category,
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
            relations = filter_by_confidence(validated.relations, min_confidence)

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

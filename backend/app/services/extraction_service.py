"""
Knowledge extraction service using LLM.

Provides high-level functions for extracting entities and relations
from text using the LLM integration with built-in hallucination validation.
"""
import logging

from app.llm.client import get_llm_provider
from app.utils.confidence_filter import filter_by_confidence
from app.services.batch_extraction_orchestrator import BatchExtractionOrchestrator
from app.llm.prompts import (
    MEDICAL_KNOWLEDGE_SYSTEM_PROMPT,
    RelationPromptEntity,
    format_entity_extraction_prompt,
    format_relation_extraction_prompt,
)
from app.llm.schemas import (
    ExtractedEntity,
    ExtractedRelation,
    validate_entity_extraction,
    validate_relation_extraction,
)
from app.services.extraction_validation_service import ValidationResult
from app.services.extraction_validation_service import (
    ExtractionValidationService,
    ValidationLevel,
)
from app.services.relation_type_service import RelationTypeService
from app.services.semantic_role_service import SemanticRoleService

logger = logging.getLogger(__name__)

# Module-level cache for relation types prompt text. Populated on first DB hit and
# reused for the lifetime of the process. Invalidate by restarting the server after
# relation type changes (acceptable for an admin-only configuration surface).
_RELATION_TYPES_PROMPT_CACHE: str | None = None

# Static fallback used when the DB is unavailable. Lists every type from RelationType
# in llm/schemas.py so the LLM always has an explicit, coherent enumeration.
_STATIC_RELATION_TYPES_FALLBACK = """\
Available relation_type values (use exactly one):
  treats, causes, prevents, increases_risk, decreases_risk, mechanism,
  contraindicated, interacts_with, metabolized_by, biomarker_for,
  affects_population, measures, other

CRITICAL: relation_type MUST be one of the values listed above. If unsure, use 'other'.\
"""


class ExtractionService:
    """
    Service for individual knowledge extraction from text using LLM.

    Handles entity extraction and relation extraction
    with validation and error handling.

    For batch extraction (entities + relations in one call),
    use BatchExtractionOrchestrator instead.

    Uses DYNAMIC prompts generated from database relation types.
    """

    def __init__(
        self,
        temperature: float = 0.0,
        max_tokens: int = 4000,
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
        Uses a module-level cache so the DB is only hit once per process lifetime.
        Falls back to a static enumeration if the database is unavailable.
        """
        global _RELATION_TYPES_PROMPT_CACHE

        if _RELATION_TYPES_PROMPT_CACHE:
            return _RELATION_TYPES_PROMPT_CACHE

        if self.db:
            try:
                if not self.relation_type_service:
                    raise RuntimeError("Relation type service unavailable")
                prompt_text = await self.relation_type_service.get_for_llm_prompt()
                _RELATION_TYPES_PROMPT_CACHE = prompt_text
                logger.info("Using DYNAMIC relation types from database")
                return prompt_text
            except Exception as e:
                logger.warning(f"Failed to load dynamic relation types, using fallback: {e}")

        # Fallback: explicit static enumeration so the LLM always has a valid list.
        logger.warning("Using STATIC relation types (database not available)")
        return _STATIC_RELATION_TYPES_FALLBACK

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

    async def extract_batch(
        self,
        text: str,
        min_confidence: str | None = None,
    ) -> tuple[list[ExtractedEntity], list[ExtractedRelation]]:
        """
        Extract entities and relations in one batch.

        Delegates to BatchExtractionOrchestrator for efficient single-pass LLM extraction.
        """
        orchestrator = BatchExtractionOrchestrator(
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            enable_validation=self.enable_validation,
            db=self.db,
        )
        return await orchestrator.extract_batch(
            text=text,
            min_confidence=min_confidence,
        )

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
        """
        Extract entities and relations with per-item validation results.

        Delegates to BatchExtractionOrchestrator. Used by the human-in-the-loop
        review workflow where validation metadata must be stored alongside each item.
        """
        orchestrator = BatchExtractionOrchestrator(
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            enable_validation=self.enable_validation,
            db=self.db,
        )
        return await orchestrator.extract_batch_with_validation_results(
            text=text,
            min_confidence=min_confidence,
        )

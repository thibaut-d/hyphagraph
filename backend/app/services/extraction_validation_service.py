"""
Extraction validation service for LLM-extracted knowledge.

Prevents hallucinations by verifying that extracted entities, relations,
and relations are genuinely grounded in the source document.
"""
import logging

from app.llm.schemas import ExtractedEntity, ExtractedRelation
from app.services.extraction_text_span_validator import (
    TextSpanValidator,
    ValidationLevel,
    ValidationResult,
)

logger = logging.getLogger(__name__)

# Re-export types so callers can import from this module without changes.
__all__ = ["ExtractionValidationService", "TextSpanValidator", "ValidationLevel", "ValidationResult"]


class ExtractionValidationService:
    """
    High-level service for validating batches of extractions.

    Orchestrates validation of entities and relations,
    and provides aggregated validation reports.
    """

    def __init__(
        self,
        validation_level: ValidationLevel = "moderate",
        auto_reject_invalid: bool = False,
    ):
        self.validator = TextSpanValidator(validation_level=validation_level)
        self.auto_reject_invalid = auto_reject_invalid

    async def validate_entities(
        self,
        entities: list[ExtractedEntity],
        source_text: str,
    ) -> tuple[list[ExtractedEntity], list[ValidationResult]]:
        """
        Validate a batch of extracted entities.

        Returns (validated_entities, validation_results).
        If auto_reject_invalid=True, only valid entities are returned.
        """
        results = []
        validated_entities = []

        for entity in entities:
            result = self.validator.validate_entity(entity, source_text)
            results.append(result)
            if result.is_valid or not self.auto_reject_invalid:
                validated_entities.append(entity)

        logger.info(
            "Entity validation: %d/%d valid, %d flagged",
            len(validated_entities),
            len(entities),
            sum(1 for r in results if r.flags),
        )
        return validated_entities, results

    async def validate_relations(
        self,
        relations: list[ExtractedRelation],
        source_text: str,
        entities: list[ExtractedEntity] | None = None,
    ) -> tuple[list[ExtractedRelation], list[ValidationResult]]:
        """
        Validate a batch of extracted relations.

        Returns (validated_relations, validation_results).
        """
        entity_lookup = {entity.slug: entity for entity in entities or []}
        results = []
        validated_relations = []

        for relation in relations:
            result = self.validator.validate_relation(
                relation,
                source_text,
                entity_lookup=entity_lookup,
            )
            results.append(result)
            if result.is_valid or not self.auto_reject_invalid:
                validated_relations.append(relation)

        logger.info(
            "Relation validation: %d/%d valid, %d flagged",
            len(validated_relations),
            len(relations),
            sum(1 for r in results if r.flags),
        )
        return validated_relations, results

def validate_relation_structure(relation: ExtractedRelation) -> ValidationResult | None:
    """
    Validate only the structural semantics of a relation.

    Returns a failing ValidationResult when required core roles are missing or
    filled by contextual pseudo-entities. Returns None when the relation passes
    structural checks and span validation should continue elsewhere.
    """
    return TextSpanValidator(validation_level="moderate")._validate_relation_structure(relation)

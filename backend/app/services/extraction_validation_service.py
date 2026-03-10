"""
Extraction validation service for LLM-extracted knowledge.

Prevents hallucinations by verifying that extracted entities, relations,
and claims are genuinely grounded in the source document.

Validation strategies:
1. Text span verification - Exact substring matching
2. Fuzzy matching - Handling minor variations (punctuation, whitespace)
3. Semantic similarity - Optional vector-based similarity (future)
4. Confidence scoring - Degrade confidence for questionable extractions
"""
import logging
import re
from dataclasses import dataclass
from typing import Literal

from app.llm.schemas import ExtractedEntity, ExtractedRelation, ExtractedClaim

logger = logging.getLogger(__name__)


# =============================================================================
# Validation Result Models
# =============================================================================

@dataclass
class ValidationResult:
    """
    Result of validating a single extraction against source text.

    Attributes:
        is_valid: Whether the extraction passes validation
        confidence_adjustment: Multiplier to apply to original confidence (0.0-1.0)
        validation_score: Overall validation score (0.0-1.0, higher is better)
        flags: List of validation issues found
        matched_span: The actual text span found in source (if any)
    """
    is_valid: bool
    confidence_adjustment: float  # 0.0 (reject) to 1.0 (no change)
    validation_score: float  # 0.0 (failed all checks) to 1.0 (passed all checks)
    flags: list[str]
    matched_span: str | None = None


ValidationLevel = Literal["strict", "moderate", "lenient"]


# =============================================================================
# Text Span Validator
# =============================================================================

class TextSpanValidator:
    """
    Validates that extracted text spans actually exist in the source document.

    Prevents LLM from hallucinating facts by ensuring all extractions
    are grounded in actual source text.
    """

    def __init__(
        self,
        validation_level: ValidationLevel = "moderate",
        min_exact_match_length: int = 10,
        allow_fuzzy_match: bool = True,
        fuzzy_threshold: float = 0.8
    ):
        """
        Initialize text span validator.

        Args:
            validation_level: How strict to be ("strict", "moderate", "lenient")
            min_exact_match_length: Minimum characters required for exact match
            allow_fuzzy_match: Whether to accept fuzzy matches (punctuation, whitespace variations)
            fuzzy_threshold: Minimum similarity score for fuzzy matches (0.0-1.0)
        """
        self.validation_level = validation_level
        self.min_exact_match_length = min_exact_match_length
        self.allow_fuzzy_match = allow_fuzzy_match
        self.fuzzy_threshold = fuzzy_threshold

    def validate_entity(
        self,
        entity: ExtractedEntity,
        source_text: str
    ) -> ValidationResult:
        """
        Validate that an extracted entity's text span exists in source.

        Args:
            entity: Extracted entity to validate
            source_text: Original source document text

        Returns:
            ValidationResult with validation outcome and metadata
        """
        if not entity.text_span or len(entity.text_span.strip()) < 3:
            return ValidationResult(
                is_valid=False,
                confidence_adjustment=0.0,
                validation_score=0.0,
                flags=["text_span_too_short"],
                matched_span=None
            )

        # Try exact match first
        exact_match = self._find_exact_match(entity.text_span, source_text)
        if exact_match:
            return ValidationResult(
                is_valid=True,
                confidence_adjustment=1.0,
                validation_score=1.0,
                flags=[],
                matched_span=exact_match
            )

        # Try fuzzy match if enabled
        if self.allow_fuzzy_match:
            fuzzy_match, similarity = self._find_fuzzy_match(entity.text_span, source_text)
            if fuzzy_match and similarity >= self.fuzzy_threshold:
                # Degrade confidence slightly for fuzzy matches
                confidence_adj = 0.9 * similarity
                return ValidationResult(
                    is_valid=True,
                    confidence_adjustment=confidence_adj,
                    validation_score=similarity,
                    flags=["fuzzy_match"],
                    matched_span=fuzzy_match
                )

        # No match found
        if self.validation_level == "strict":
            return ValidationResult(
                is_valid=False,
                confidence_adjustment=0.0,
                validation_score=0.0,
                flags=["text_span_not_found", "possible_hallucination"],
                matched_span=None
            )
        elif self.validation_level == "moderate":
            # Flag but don't reject
            return ValidationResult(
                is_valid=True,
                confidence_adjustment=0.5,
                validation_score=0.3,
                flags=["text_span_not_found", "confidence_degraded"],
                matched_span=None
            )
        else:  # lenient
            return ValidationResult(
                is_valid=True,
                confidence_adjustment=0.7,
                validation_score=0.5,
                flags=["text_span_not_verified"],
                matched_span=None
            )

    def validate_relation(
        self,
        relation: ExtractedRelation,
        source_text: str
    ) -> ValidationResult:
        """
        Validate that an extracted relation's text span exists in source.

        Relations are held to higher standards than entities because they
        make factual claims about relationships.

        Args:
            relation: Extracted relation to validate
            source_text: Original source document text

        Returns:
            ValidationResult with validation outcome and metadata
        """
        if not relation.text_span or len(relation.text_span.strip()) < self.min_exact_match_length:
            return ValidationResult(
                is_valid=False,
                confidence_adjustment=0.0,
                validation_score=0.0,
                flags=["text_span_too_short_for_relation"],
                matched_span=None
            )

        # Try exact match
        exact_match = self._find_exact_match(relation.text_span, source_text)
        if exact_match:
            return ValidationResult(
                is_valid=True,
                confidence_adjustment=1.0,
                validation_score=1.0,
                flags=[],
                matched_span=exact_match
            )

        # Try fuzzy match
        if self.allow_fuzzy_match:
            fuzzy_match, similarity = self._find_fuzzy_match(relation.text_span, source_text)
            if fuzzy_match and similarity >= self.fuzzy_threshold:
                # Relations need higher similarity threshold
                if similarity >= 0.85:
                    confidence_adj = 0.9 * similarity
                    return ValidationResult(
                        is_valid=True,
                        confidence_adjustment=confidence_adj,
                        validation_score=similarity,
                        flags=["fuzzy_match"],
                        matched_span=fuzzy_match
                    )

        # No reliable match found - relations are critical, so degrade heavily
        if self.validation_level == "strict":
            return ValidationResult(
                is_valid=False,
                confidence_adjustment=0.0,
                validation_score=0.0,
                flags=["relation_text_span_not_found", "possible_hallucination"],
                matched_span=None
            )
        else:
            return ValidationResult(
                is_valid=True,
                confidence_adjustment=0.3,  # Heavy degradation
                validation_score=0.2,
                flags=["relation_text_span_not_found", "high_confidence_degradation"],
                matched_span=None
            )

    def validate_claim(
        self,
        claim: ExtractedClaim,
        source_text: str
    ) -> ValidationResult:
        """
        Validate that an extracted claim's text span exists in source.

        Claims are the most critical extractions and require strict validation.

        Args:
            claim: Extracted claim to validate
            source_text: Original source document text

        Returns:
            ValidationResult with validation outcome and metadata
        """
        if not claim.text_span or len(claim.text_span.strip()) < self.min_exact_match_length:
            return ValidationResult(
                is_valid=False,
                confidence_adjustment=0.0,
                validation_score=0.0,
                flags=["claim_text_span_too_short"],
                matched_span=None
            )

        # Try exact match
        exact_match = self._find_exact_match(claim.text_span, source_text)
        if exact_match:
            return ValidationResult(
                is_valid=True,
                confidence_adjustment=1.0,
                validation_score=1.0,
                flags=[],
                matched_span=exact_match
            )

        # For claims, fuzzy match must be very high quality
        if self.allow_fuzzy_match:
            fuzzy_match, similarity = self._find_fuzzy_match(claim.text_span, source_text)
            if fuzzy_match and similarity >= 0.9:
                confidence_adj = 0.95 * similarity
                return ValidationResult(
                    is_valid=True,
                    confidence_adjustment=confidence_adj,
                    validation_score=similarity,
                    flags=["fuzzy_match"],
                    matched_span=fuzzy_match
                )

        # Claims without valid text spans are rejected in strict/moderate mode
        if self.validation_level == "lenient":
            return ValidationResult(
                is_valid=True,
                confidence_adjustment=0.4,
                validation_score=0.3,
                flags=["claim_text_span_not_found", "severe_confidence_degradation"],
                matched_span=None
            )
        else:
            return ValidationResult(
                is_valid=False,
                confidence_adjustment=0.0,
                validation_score=0.0,
                flags=["claim_text_span_not_found", "possible_hallucination"],
                matched_span=None
            )

    def _find_exact_match(self, text_span: str, source_text: str) -> str | None:
        """
        Find exact substring match in source text.

        Returns the matched text from source if found, None otherwise.
        """
        text_span_clean = text_span.strip()

        # Case-sensitive exact match
        if text_span_clean in source_text:
            return text_span_clean

        # Case-insensitive match
        source_lower = source_text.lower()
        span_lower = text_span_clean.lower()

        if span_lower in source_lower:
            # Find the actual match in source to preserve original casing
            idx = source_lower.index(span_lower)
            return source_text[idx:idx + len(text_span_clean)]

        return None

    def _find_fuzzy_match(self, text_span: str, source_text: str) -> tuple[str | None, float]:
        """
        Find fuzzy match allowing for minor variations.

        Handles:
        - Extra whitespace
        - Punctuation differences
        - Minor formatting variations

        Returns:
            Tuple of (matched_text, similarity_score) or (None, 0.0)
        """
        # Normalize text for fuzzy matching
        normalized_span = self._normalize_text(text_span)

        # Split source into sentences for targeted matching
        sentences = self._split_into_sentences(source_text)

        best_match = None
        best_similarity = 0.0

        for sentence in sentences:
            normalized_sentence = self._normalize_text(sentence)

            # Check if normalized span is in normalized sentence
            if normalized_span in normalized_sentence:
                similarity = self._calculate_similarity(normalized_span, normalized_sentence)
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = sentence.strip()

        return (best_match, best_similarity) if best_similarity > 0 else (None, 0.0)

    def _normalize_text(self, text: str) -> str:
        """
        Normalize text for fuzzy matching.

        - Lowercase
        - Remove extra whitespace
        - Normalize punctuation
        """
        # Lowercase
        text = text.lower()

        # Replace multiple whitespace with single space
        text = re.sub(r'\s+', ' ', text)

        # Remove common punctuation that doesn't affect meaning
        text = text.replace(',', '').replace('.', '').replace(';', '')
        text = text.replace('(', '').replace(')', '').replace('"', '').replace("'", '')

        return text.strip()

    def _split_into_sentences(self, text: str) -> list[str]:
        """
        Split text into sentences for targeted matching.

        Uses simple heuristic: split on . ! ? followed by space and capital letter.
        """
        # Simple sentence splitting (could be improved with spaCy/NLTK)
        sentences = re.split(r'[.!?]\s+(?=[A-Z])', text)
        return [s.strip() for s in sentences if len(s.strip()) > 10]

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate similarity between two normalized texts.

        Uses simple word overlap metric (could be enhanced with embeddings).

        Returns:
            Similarity score 0.0-1.0
        """
        words1 = set(text1.split())
        words2 = set(text2.split())

        if not words1 or not words2:
            return 0.0

        # Jaccard similarity
        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0.0


# =============================================================================
# Batch Validation Service
# =============================================================================

class ExtractionValidationService:
    """
    High-level service for validating batches of extractions.

    Orchestrates validation of entities, relations, and claims,
    and provides aggregated validation reports.
    """

    def __init__(
        self,
        validation_level: ValidationLevel = "moderate",
        auto_reject_invalid: bool = False
    ):
        """
        Initialize validation service.

        Args:
            validation_level: Strictness level for validation
            auto_reject_invalid: Whether to automatically filter out invalid extractions
        """
        self.validator = TextSpanValidator(validation_level=validation_level)
        self.auto_reject_invalid = auto_reject_invalid

    async def validate_entities(
        self,
        entities: list[ExtractedEntity],
        source_text: str
    ) -> tuple[list[ExtractedEntity], list[ValidationResult]]:
        """
        Validate a batch of extracted entities.

        Args:
            entities: List of extracted entities to validate
            source_text: Original source document text

        Returns:
            Tuple of (validated_entities, validation_results)
            If auto_reject_invalid=True, only valid entities are returned
        """
        results = []
        validated_entities = []

        for entity in entities:
            result = self.validator.validate_entity(entity, source_text)
            results.append(result)

            if result.is_valid or not self.auto_reject_invalid:
                validated_entities.append(entity)

        logger.info(
            f"Entity validation: {len(validated_entities)}/{len(entities)} valid, "
            f"{sum(1 for r in results if r.flags)} flagged"
        )

        return validated_entities, results

    async def validate_relations(
        self,
        relations: list[ExtractedRelation],
        source_text: str
    ) -> tuple[list[ExtractedRelation], list[ValidationResult]]:
        """
        Validate a batch of extracted relations.

        Args:
            relations: List of extracted relations to validate
            source_text: Original source document text

        Returns:
            Tuple of (validated_relations, validation_results)
        """
        results = []
        validated_relations = []

        for relation in relations:
            result = self.validator.validate_relation(relation, source_text)
            results.append(result)

            if result.is_valid or not self.auto_reject_invalid:
                validated_relations.append(relation)

        logger.info(
            f"Relation validation: {len(validated_relations)}/{len(relations)} valid, "
            f"{sum(1 for r in results if r.flags)} flagged"
        )

        return validated_relations, results

    async def validate_claims(
        self,
        claims: list[ExtractedClaim],
        source_text: str
    ) -> tuple[list[ExtractedClaim], list[ValidationResult]]:
        """
        Validate a batch of extracted claims.

        Args:
            claims: List of extracted claims to validate
            source_text: Original source document text

        Returns:
            Tuple of (validated_claims, validation_results)
        """
        results = []
        validated_claims = []

        for claim in claims:
            result = self.validator.validate_claim(claim, source_text)
            results.append(result)

            if result.is_valid or not self.auto_reject_invalid:
                validated_claims.append(claim)

        logger.info(
            f"Claim validation: {len(validated_claims)}/{len(claims)} valid, "
            f"{sum(1 for r in results if r.flags)} flagged"
        )

        return validated_claims, results

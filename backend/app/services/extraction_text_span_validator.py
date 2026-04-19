"""
Text span validator for LLM-extracted knowledge.

Verifies that extracted entities and relations are genuinely
grounded in the source document, preventing hallucinations.

Validation strategies:
1. Text span verification - Exact substring matching
2. Fuzzy matching - Handling minor variations (punctuation, whitespace)
3. Confidence scoring - Degrade confidence for questionable extractions
"""
import re
from dataclasses import dataclass
from typing import Literal

from app.llm.schemas import (
    ExtractedEntity,
    ExtractedRelation,
    get_missing_required_relation_roles,
)

ValidationLevel = Literal["strict", "moderate", "lenient"]

_CONTEXTUAL_ENTITY_PREFIXES = (
    "dose-",
    "dosage-",
    "duration-",
    "timeframe-",
    "participants-",
    "participant-count-",
    "sample-size-",
    "study-design-",
)


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
        fuzzy_threshold: float = 0.8,
    ):
        self.validation_level = validation_level
        self.min_exact_match_length = min_exact_match_length
        self.allow_fuzzy_match = allow_fuzzy_match
        self.fuzzy_threshold = fuzzy_threshold

    def validate_entity(self, entity: ExtractedEntity, source_text: str) -> ValidationResult:
        """Validate that an extracted entity's text span exists in source."""
        if not entity.text_span or len(entity.text_span.strip()) < 3:
            return ValidationResult(
                is_valid=False,
                confidence_adjustment=0.0,
                validation_score=0.0,
                flags=["text_span_too_short"],
                matched_span=None,
            )

        exact_match = self._find_exact_match(entity.text_span, source_text)
        if exact_match:
            return ValidationResult(
                is_valid=True,
                confidence_adjustment=1.0,
                validation_score=1.0,
                flags=[],
                matched_span=exact_match,
            )

        if self.allow_fuzzy_match:
            fuzzy_match, similarity = self._find_fuzzy_match(entity.text_span, source_text)
            if fuzzy_match and similarity >= self.fuzzy_threshold:
                return ValidationResult(
                    is_valid=True,
                    confidence_adjustment=0.9 * similarity,
                    validation_score=similarity,
                    flags=["fuzzy_match"],
                    matched_span=fuzzy_match,
                )

        if self.validation_level == "strict":
            return ValidationResult(
                is_valid=False,
                confidence_adjustment=0.0,
                validation_score=0.0,
                flags=["text_span_not_found", "possible_hallucination"],
                matched_span=None,
            )
        elif self.validation_level == "moderate":
            return ValidationResult(
                is_valid=True,
                confidence_adjustment=0.5,
                validation_score=0.3,
                flags=["text_span_not_found", "confidence_degraded"],
                matched_span=None,
            )
        else:  # lenient
            return ValidationResult(
                is_valid=True,
                confidence_adjustment=0.7,
                validation_score=0.5,
                flags=["text_span_not_verified"],
                matched_span=None,
            )

    def validate_relation(
        self, relation: ExtractedRelation, source_text: str
    ) -> ValidationResult:
        """
        Validate that an extracted relation's text span exists in source.

        Relations are held to higher standards than entities because they
        make factual statements about relationships.
        """
        structural_result = self._validate_relation_structure(relation)
        if structural_result is not None:
            return structural_result

        if not relation.text_span or len(relation.text_span.strip()) < self.min_exact_match_length:
            return ValidationResult(
                is_valid=False,
                confidence_adjustment=0.0,
                validation_score=0.0,
                flags=["text_span_too_short_for_relation"],
                matched_span=None,
            )

        exact_match = self._find_exact_match(relation.text_span, source_text)
        if exact_match:
            return ValidationResult(
                is_valid=True,
                confidence_adjustment=1.0,
                validation_score=1.0,
                flags=[],
                matched_span=exact_match,
            )

        if self.allow_fuzzy_match:
            fuzzy_match, similarity = self._find_fuzzy_match(relation.text_span, source_text)
            if fuzzy_match and similarity >= max(self.fuzzy_threshold, 0.85):
                return ValidationResult(
                    is_valid=True,
                    confidence_adjustment=0.9 * similarity,
                    validation_score=similarity,
                    flags=["fuzzy_match"],
                    matched_span=fuzzy_match,
                )

        if self.validation_level == "strict":
            return ValidationResult(
                is_valid=False,
                confidence_adjustment=0.0,
                validation_score=0.0,
                flags=["relation_text_span_not_found", "possible_hallucination"],
                matched_span=None,
            )
        return ValidationResult(
            is_valid=True,
            confidence_adjustment=0.3,
            validation_score=0.2,
            flags=["relation_text_span_not_found", "high_confidence_degradation"],
            matched_span=None,
        )

    def _validate_relation_structure(self, relation: ExtractedRelation) -> ValidationResult | None:
        missing_role_groups = get_missing_required_relation_roles(
            relation.relation_type,
            [role.role_type for role in relation.roles],
        )
        contextual_core_role_flags = self._find_contextual_core_role_flags(relation)
        if missing_role_groups:
            missing_flags = [
                f"missing_core_role:{'|'.join(role_group)}"
                for role_group in missing_role_groups
            ]
            return ValidationResult(
                is_valid=False,
                confidence_adjustment=0.0,
                validation_score=0.0,
                flags=["missing_required_relation_roles", *missing_flags, *contextual_core_role_flags],
                matched_span=None,
            )

        if contextual_core_role_flags:
            return ValidationResult(
                is_valid=False,
                confidence_adjustment=0.0,
                validation_score=0.0,
                flags=["invalid_contextual_core_role", *contextual_core_role_flags],
                matched_span=None,
            )

        return None

    def _find_contextual_core_role_flags(self, relation: ExtractedRelation) -> list[str]:
        invalid_flags: list[str] = []
        missing_role_groups = get_missing_required_relation_roles(
            relation.relation_type,
            [role.role_type for role in relation.roles],
        )
        missing_roles = {role_type for role_group in missing_role_groups for role_type in role_group}

        required_role_types = {
            role_type
            for role_group in get_missing_required_relation_roles(
                relation.relation_type,
                [],
            )
            for role_type in role_group
        }

        for role in relation.roles:
            if role.role_type not in required_role_types or role.role_type in missing_roles:
                continue
            if role.entity_slug.startswith(_CONTEXTUAL_ENTITY_PREFIXES):
                invalid_flags.append(
                    f"invalid_contextual_core_role:{role.role_type}:{role.entity_slug}"
                )

        return invalid_flags

    # -------------------------------------------------------------------------
    # Internal matching helpers
    # -------------------------------------------------------------------------

    def _find_exact_match(self, text_span: str, source_text: str) -> str | None:
        """Return the matched substring from source if found (case-insensitive), else None."""
        text_span_clean = text_span.strip()
        if text_span_clean in source_text:
            return text_span_clean

        source_lower = source_text.lower()
        span_lower = text_span_clean.lower()
        if span_lower in source_lower:
            idx = source_lower.index(span_lower)
            return source_text[idx : idx + len(text_span_clean)]

        return None

    def _find_fuzzy_match(self, text_span: str, source_text: str) -> tuple[str | None, float]:
        """Find a fuzzy match allowing for minor whitespace/punctuation variations."""
        normalized_span = self._normalize_text(text_span)
        best_match = None
        best_similarity = 0.0

        for sentence in self._split_into_sentences(source_text):
            normalized_sentence = self._normalize_text(sentence)
            if normalized_span in normalized_sentence:
                similarity = self._calculate_similarity(normalized_span, normalized_sentence)
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = sentence.strip()

        return (best_match, best_similarity) if best_similarity > 0 else (None, 0.0)

    def _normalize_text(self, text: str) -> str:
        """Lowercase, collapse whitespace, remove common punctuation."""
        text = text.lower()
        text = re.sub(r"\s+", " ", text)
        text = text.replace(",", "").replace(".", "").replace(";", "")
        text = text.replace("(", "").replace(")", "").replace('"', "").replace("'", "")
        return text.strip()

    def _split_into_sentences(self, text: str) -> list[str]:
        """Split text into sentences on . ! ? followed by a capital letter."""
        sentences = re.split(r"[.!?]\s+(?=[A-Z])", text)
        return [s.strip() for s in sentences if len(s.strip()) > 10]

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Jaccard word-overlap similarity between two normalized strings."""
        words1 = set(text1.split())
        words2 = set(text2.split())
        if not words1 or not words2:
            return 0.0
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        return intersection / union if union > 0 else 0.0

"""
Tests for ExplanationService._generate_summary.

Covers:
- All direction tiers (strong_positive / weak_positive / neutral /
  weak_negative / strong_negative / none)
- All confidence tiers (high / moderate / low) at their boundaries
- All disagreement tiers (significant / some / none) at their boundaries
- Edge cases: zero sources, score=None, confidence=0.0, disagreement=0.0
"""
import pytest

from app.schemas.explanation import SummaryData
from app.services.explanation_service import ExplanationService
from app.schemas.inference import RoleInference


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_role_inference(
    score: float | None,
    confidence: float,
    disagreement: float = 0.0,
) -> RoleInference:
    return RoleInference(
        role_type="test_role",
        score=score,
        coverage=1.0,
        confidence=confidence,
        disagreement=disagreement,
    )


def _summarise(
    score: float | None,
    confidence: float,
    disagreement: float = 0.0,
    *,
    role_type: str = "test_role",
    source_count: int = 3,
) -> SummaryData:
    """Call ExplanationService._generate_summary with lightweight mocks."""
    from unittest.mock import MagicMock
    from uuid import uuid4

    svc = ExplanationService.__new__(ExplanationService)
    role_inf = _make_role_inference(score, confidence, disagreement)

    evidence = []
    for _ in range(source_count):
        ev = MagicMock()
        ev.relation.source_id = uuid4()
        evidence.append(ev)

    return svc._generate_summary(role_inf, evidence, role_type)


# ---------------------------------------------------------------------------
# Direction tiers
# ---------------------------------------------------------------------------

class TestDirectionTiers:
    def test_score_above_half_is_strong_positive(self):
        result = _summarise(score=0.6, confidence=0.9)
        assert result.direction == "strong_positive"

    def test_score_exactly_half_is_weak_positive(self):
        result = _summarise(score=0.5, confidence=0.9)
        assert result.direction == "weak_positive"

    def test_score_just_above_zero_is_weak_positive(self):
        result = _summarise(score=0.01, confidence=0.9)
        assert result.direction == "weak_positive"

    def test_score_zero_is_neutral(self):
        result = _summarise(score=0.0, confidence=0.9)
        assert result.direction == "neutral"

    def test_score_just_below_zero_is_weak_negative(self):
        result = _summarise(score=-0.01, confidence=0.9)
        assert result.direction == "weak_negative"

    def test_score_just_above_negative_half_is_weak_negative(self):
        result = _summarise(score=-0.49, confidence=0.9)
        assert result.direction == "weak_negative"

    def test_score_exactly_negative_half_is_strong_negative(self):
        result = _summarise(score=-0.5, confidence=0.9)
        assert result.direction == "strong_negative"

    def test_score_below_negative_half_is_strong_negative(self):
        result = _summarise(score=-0.6, confidence=0.9)
        assert result.direction == "strong_negative"

    def test_score_none_is_none_direction(self):
        result = _summarise(score=None, confidence=0.9)
        assert result.direction == "none"


# ---------------------------------------------------------------------------
# Confidence tiers
# ---------------------------------------------------------------------------

class TestConfidenceTiers:
    def test_confidence_above_eighty_percent_is_high(self):
        result = _summarise(score=0.5, confidence=0.81)
        assert result.confidence_level == "high"

    def test_confidence_exactly_eighty_percent_is_moderate(self):
        result = _summarise(score=0.5, confidence=0.8)
        assert result.confidence_level == "moderate"

    def test_confidence_above_fifty_percent_is_moderate(self):
        result = _summarise(score=0.5, confidence=0.6)
        assert result.confidence_level == "moderate"

    def test_confidence_exactly_fifty_percent_is_low(self):
        result = _summarise(score=0.5, confidence=0.5)
        assert result.confidence_level == "low"

    def test_confidence_below_fifty_percent_is_low(self):
        result = _summarise(score=0.5, confidence=0.3)
        assert result.confidence_level == "low"

    def test_confidence_zero_is_low(self):
        result = _summarise(score=0.5, confidence=0.0)
        assert result.confidence_level == "low"

    def test_confidence_pct_rounded_correctly(self):
        result = _summarise(score=0.5, confidence=0.857)
        assert result.confidence_pct == 86


# ---------------------------------------------------------------------------
# Disagreement tiers
# ---------------------------------------------------------------------------

class TestDisagreementTiers:
    def test_disagreement_above_half_is_significant(self):
        result = _summarise(score=0.5, confidence=0.9, disagreement=0.6)
        assert result.disagreement_level == "significant"

    def test_disagreement_exactly_half_is_some(self):
        result = _summarise(score=0.5, confidence=0.9, disagreement=0.5)
        assert result.disagreement_level == "some"

    def test_disagreement_above_point_two_is_some(self):
        result = _summarise(score=0.5, confidence=0.9, disagreement=0.3)
        assert result.disagreement_level == "some"

    def test_disagreement_exactly_point_two_is_none(self):
        result = _summarise(score=0.5, confidence=0.9, disagreement=0.2)
        assert result.disagreement_level == "none"

    def test_disagreement_zero_is_none(self):
        result = _summarise(score=0.5, confidence=0.9, disagreement=0.0)
        assert result.disagreement_level == "none"


# ---------------------------------------------------------------------------
# Source count and role_type pass-through
# ---------------------------------------------------------------------------

class TestPassThrough:
    def test_source_count_reflects_unique_evidence_items(self):
        result = _summarise(score=0.5, confidence=0.9, source_count=7)
        assert result.source_count == 7

    def test_zero_sources(self):
        result = _summarise(score=0.5, confidence=0.9, source_count=0)
        assert result.source_count == 0

    def test_role_type_preserved(self):
        result = _summarise(score=0.5, confidence=0.9, role_type="drug")
        assert result.role_type == "drug"

    def test_score_preserved_in_output(self):
        result = _summarise(score=0.42, confidence=0.9)
        assert result.score == pytest.approx(0.42)

    def test_score_none_preserved(self):
        result = _summarise(score=None, confidence=0.9)
        assert result.score is None

    def test_returns_summary_data_instance(self):
        result = _summarise(score=0.5, confidence=0.9)
        assert isinstance(result, SummaryData)

"""
Tests for Inference Engine - TDD approach.

Tests the mathematical model from COMPUTED_RELATIONS.md:
- Claim scoring: x(c) = p(c) × i(c)
- Role contribution: normalized sum of claims
- Evidence aggregation: weighted sum across relations
- Confidence: 1 - exp(-λ × Coverage)
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from app.services.inference_service import InferenceService


@pytest.fixture
def mock_db():
    """Mock database session."""
    return AsyncMock()


@pytest.fixture
def mock_repo():
    """Mock relation repository."""
    return AsyncMock()


@pytest.mark.asyncio
class TestClaimScoring:
    """Test claim-level scoring: x(c) = p(c) × i(c)"""

    async def test_positive_claim_score(self, mock_db):
        """Test positive claim: polarity=+1, intensity=0.8 → score=0.8"""
        service = InferenceService(mock_db)

        # Claim: "Aspirin reduces pain" (positive, strong)
        polarity = 1
        intensity = 0.8

        score = service.compute_claim_score(polarity, intensity)

        assert score == 0.8
        assert -1 <= score <= 1

    async def test_negative_claim_score(self, mock_db):
        """Test negative claim: polarity=-1, intensity=0.6 → score=-0.6"""
        service = InferenceService(mock_db)

        # Claim: "Aspirin causes bleeding" (negative, moderate)
        polarity = -1
        intensity = 0.6

        score = service.compute_claim_score(polarity, intensity)

        assert score == -0.6
        assert -1 <= score <= 1

    async def test_neutral_claim_score(self, mock_db):
        """Test neutral claim: polarity=0, intensity=0.5 → score=0"""
        service = InferenceService(mock_db)

        # Claim: "No effect observed"
        polarity = 0
        intensity = 0.5

        score = service.compute_claim_score(polarity, intensity)

        assert score == 0

    async def test_weak_positive_claim(self, mock_db):
        """Test weak positive claim: polarity=+1, intensity=0.2 → score=0.2"""
        service = InferenceService(mock_db)

        polarity = 1
        intensity = 0.2

        score = service.compute_claim_score(polarity, intensity)

        assert score == 0.2


@pytest.mark.asyncio
class TestRoleContribution:
    """Test role contribution within a relation: x(h, r) = sum(x(c)) / sum(|x(c)|)"""

    async def test_single_positive_claim(self, mock_db):
        """Test single claim: [0.8] → contribution = 1.0 (normalized)"""
        service = InferenceService(mock_db)

        claims = [0.8]  # One positive claim

        contribution = service.compute_role_contribution(claims)

        # Single claim normalizes to 1.0: 0.8 / |0.8| = 1.0
        assert contribution == 1.0

    async def test_two_positive_claims(self, mock_db):
        """Test two positive claims: [0.8, 0.6] → contribution = 1.4/1.4 = 1.0"""
        service = InferenceService(mock_db)

        claims = [0.8, 0.6]  # Two positive claims

        contribution = service.compute_role_contribution(claims)

        assert contribution == 1.0  # Saturates at max

    async def test_mixed_claims_slight_positive(self, mock_db):
        """Test mixed claims: [0.8, -0.3] → contribution = 0.5/1.1 ≈ 0.45"""
        service = InferenceService(mock_db)

        claims = [0.8, -0.3]  # Positive outweighs negative

        contribution = service.compute_role_contribution(claims)

        assert abs(contribution - 0.45) < 0.01  # ~0.45

    async def test_contradictory_claims_balanced(self, mock_db):
        """Test balanced contradiction: [0.8, -0.8] → contribution = 0"""
        service = InferenceService(mock_db)

        claims = [0.8, -0.8]  # Perfect contradiction

        contribution = service.compute_role_contribution(claims)

        assert contribution == 0

    async def test_empty_claims(self, mock_db):
        """Test no claims: [] → contribution is None (undefined)"""
        service = InferenceService(mock_db)

        claims = []

        contribution = service.compute_role_contribution(claims)

        assert contribution is None  # Role not exposed


@pytest.mark.asyncio
class TestEvidenceAggregation:
    """Test evidence aggregation across relations."""

    async def test_single_relation_single_role(self, mock_db):
        """
        Test single relation:
        - Relation 1: weight=1.0, role="effect", contribution=0.8
        - Evidence = 1.0 × 0.8 = 0.8
        - Coverage = 1.0
        - Score = 0.8 / 1.0 = 0.8
        """
        service = InferenceService(mock_db)

        relations_data = [
            {"weight": 1.0, "roles": {"effect": 0.8}}
        ]

        result = service.aggregate_evidence(relations_data, role="effect")

        assert result["score"] == 0.8
        assert result["coverage"] == 1.0

    async def test_two_relations_agreeing(self, mock_db):
        """
        Test two agreeing relations:
        - Relation 1: weight=1.0, role="effect", contribution=0.8
        - Relation 2: weight=1.0, role="effect", contribution=0.9
        - Evidence = 1.0×0.8 + 1.0×0.9 = 1.7
        - Coverage = 1.0 + 1.0 = 2.0
        - Score = 1.7 / 2.0 = 0.85
        """
        service = InferenceService(mock_db)

        relations_data = [
            {"weight": 1.0, "roles": {"effect": 0.8}},
            {"weight": 1.0, "roles": {"effect": 0.9}},
        ]

        result = service.aggregate_evidence(relations_data, role="effect")

        assert abs(result["score"] - 0.85) < 0.01  # Floating point tolerance
        assert result["coverage"] == 2.0

    async def test_two_relations_contradicting(self, mock_db):
        """
        Test two contradicting relations:
        - Relation 1: weight=1.0, role="effect", contribution=0.8
        - Relation 2: weight=1.0, role="effect", contribution=-0.6
        - Evidence = 1.0×0.8 + 1.0×(-0.6) = 0.2
        - Coverage = 1.0 + 1.0 = 2.0
        - Score = 0.2 / 2.0 = 0.1
        """
        service = InferenceService(mock_db)

        relations_data = [
            {"weight": 1.0, "roles": {"effect": 0.8}},
            {"weight": 1.0, "roles": {"effect": -0.6}},
        ]

        result = service.aggregate_evidence(relations_data, role="effect")

        assert abs(result["score"] - 0.1) < 0.01  # Floating point tolerance
        assert result["coverage"] == 2.0

    async def test_weighted_relations(self, mock_db):
        """
        Test weighted relations (different source trust):
        - Relation 1: weight=1.0 (high trust), contribution=0.8
        - Relation 2: weight=0.5 (low trust), contribution=-0.6
        - Evidence = 1.0×0.8 + 0.5×(-0.6) = 0.5
        - Coverage = 1.0 + 0.5 = 1.5
        - Score = 0.5 / 1.5 = 0.33
        """
        service = InferenceService(mock_db)

        relations_data = [
            {"weight": 1.0, "roles": {"effect": 0.8}},
            {"weight": 0.5, "roles": {"effect": -0.6}},
        ]

        result = service.aggregate_evidence(relations_data, role="effect")

        assert abs(result["score"] - 0.33) < 0.01
        assert result["coverage"] == 1.5

    async def test_role_not_exposed(self, mock_db):
        """
        Test role not exposed in any relation:
        - Relations have "effect" role, query for "mechanism"
        - Score should be None (undefined)
        """
        service = InferenceService(mock_db)

        relations_data = [
            {"weight": 1.0, "roles": {"effect": 0.8}},
        ]

        result = service.aggregate_evidence(relations_data, role="mechanism")

        assert result["score"] is None
        assert result["coverage"] == 0


@pytest.mark.asyncio
class TestConfidenceComputation:
    """Test confidence computation: confidence = 1 - exp(-λ × Coverage)"""

    async def test_zero_coverage_zero_confidence(self, mock_db):
        """Test zero coverage → zero confidence"""
        service = InferenceService(mock_db)

        coverage = 0

        confidence = service.compute_confidence(coverage)

        assert confidence == 0

    async def test_low_coverage_low_confidence(self, mock_db):
        """Test low coverage (0.5) → low confidence"""
        service = InferenceService(mock_db)

        coverage = 0.5

        confidence = service.compute_confidence(coverage, lambda_param=1.0)

        # confidence = 1 - exp(-1.0 × 0.5) = 1 - exp(-0.5) ≈ 0.39
        expected = 1 - 0.6065  # exp(-0.5) ≈ 0.6065
        assert abs(confidence - expected) < 0.01

    async def test_medium_coverage_medium_confidence(self, mock_db):
        """Test medium coverage (2.0) → medium confidence"""
        service = InferenceService(mock_db)

        coverage = 2.0

        confidence = service.compute_confidence(coverage, lambda_param=1.0)

        # confidence = 1 - exp(-1.0 × 2.0) = 1 - exp(-2.0) ≈ 0.86
        expected = 1 - 0.1353  # exp(-2.0) ≈ 0.1353
        assert abs(confidence - expected) < 0.01

    async def test_high_coverage_high_confidence(self, mock_db):
        """Test high coverage (5.0) → high confidence (approaches 1)"""
        service = InferenceService(mock_db)

        coverage = 5.0

        confidence = service.compute_confidence(coverage, lambda_param=1.0)

        # confidence = 1 - exp(-5.0) ≈ 0.993
        assert confidence > 0.99
        assert confidence < 1.0

    async def test_faster_saturation_with_higher_lambda(self, mock_db):
        """Test higher λ → faster saturation"""
        service = InferenceService(mock_db)

        coverage = 1.0

        # λ = 1.0
        conf1 = service.compute_confidence(coverage, lambda_param=1.0)

        # λ = 2.0 (faster saturation)
        conf2 = service.compute_confidence(coverage, lambda_param=2.0)

        assert conf2 > conf1  # Higher lambda → higher confidence for same coverage


@pytest.mark.asyncio
class TestDisagreementMeasure:
    """Test disagreement (contradiction) measure."""

    async def test_perfect_agreement(self, mock_db):
        """Test all positive claims → zero disagreement"""
        service = InferenceService(mock_db)

        relations_data = [
            {"weight": 1.0, "roles": {"effect": 0.8}},
            {"weight": 1.0, "roles": {"effect": 0.9}},
        ]

        disagreement = service.compute_disagreement(relations_data, role="effect")

        assert disagreement == 0  # Perfect agreement

    async def test_perfect_disagreement(self, mock_db):
        """Test balanced contradictions → high disagreement"""
        service = InferenceService(mock_db)

        relations_data = [
            {"weight": 1.0, "roles": {"effect": 0.8}},
            {"weight": 1.0, "roles": {"effect": -0.8}},
        ]

        disagreement = service.compute_disagreement(relations_data, role="effect")

        assert disagreement == 1.0  # Maximal contradiction

    async def test_partial_disagreement(self, mock_db):
        """Test partial contradiction → medium disagreement"""
        service = InferenceService(mock_db)

        relations_data = [
            {"weight": 1.0, "roles": {"effect": 0.8}},
            {"weight": 1.0, "roles": {"effect": 0.6}},
            {"weight": 1.0, "roles": {"effect": -0.4}},
        ]

        disagreement = service.compute_disagreement(relations_data, role="effect")

        # Some contradiction but not maximal
        assert 0 < disagreement < 1

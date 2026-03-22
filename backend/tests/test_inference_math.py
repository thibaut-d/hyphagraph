"""
Tests for inference math primitives and compute_role_inferences.

Covers:
- normalize_direction: canonical direction mapping
- aggregate_evidence / compute_confidence / compute_disagreement (via math.py)
- compute_role_inferences: end-to-end with mock relation objects
- _find_existing_pmids: PMID deduplication against live DB
"""
import pytest
from unittest.mock import MagicMock
from uuid import uuid4

from app.services.inference.math import (
    normalize_direction,
    aggregate_evidence,
    compute_confidence,
    compute_disagreement,
)
from app.services.inference.read_models import compute_role_inferences


# ---------------------------------------------------------------------------
# normalize_direction
# ---------------------------------------------------------------------------

class TestNormalizeDirection:
    def test_positive_maps_to_supports(self):
        assert normalize_direction("positive") == "supports"

    def test_supports_stays_supports(self):
        assert normalize_direction("supports") == "supports"

    def test_negative_maps_to_contradicts(self):
        assert normalize_direction("negative") == "contradicts"

    def test_contradicts_stays_contradicts(self):
        assert normalize_direction("contradicts") == "contradicts"

    def test_none_maps_to_neutral(self):
        assert normalize_direction(None) == "neutral"

    def test_neutral_stays_neutral(self):
        assert normalize_direction("neutral") == "neutral"

    def test_unknown_value_defaults_to_neutral(self):
        # Since M8 fix: unrecognised values are warned + normalised to "neutral"
        assert normalize_direction("unknown_value") == "neutral"

    def test_empty_string_maps_to_neutral(self):
        assert normalize_direction("") == "neutral"


# ---------------------------------------------------------------------------
# aggregate_evidence
# ---------------------------------------------------------------------------

class TestAggregateEvidence:
    def test_empty_list_returns_none_score_and_zero_coverage(self):
        result = aggregate_evidence([], role="subject")
        assert result["score"] is None
        assert result["coverage"] == 0.0

    def test_single_supporting_relation(self):
        data = [{"weight": 1.0, "roles": {"subject": 1.0}}]
        result = aggregate_evidence(data, role="subject")
        assert result["score"] == pytest.approx(1.0)
        assert result["coverage"] == pytest.approx(1.0)

    def test_role_missing_from_relation_is_skipped(self):
        data = [{"weight": 1.0, "roles": {"other_role": 1.0}}]
        result = aggregate_evidence(data, role="subject")
        assert result["score"] is None
        assert result["coverage"] == 0.0

    def test_weighted_average_across_relations(self):
        data = [
            {"weight": 2.0, "roles": {"subject": 1.0}},
            {"weight": 1.0, "roles": {"subject": -1.0}},
        ]
        result = aggregate_evidence(data, role="subject")
        # (2*1 + 1*-1) / (2+1) = 1/3
        assert result["score"] == pytest.approx(1 / 3)
        assert result["coverage"] == pytest.approx(3.0)

    def test_none_contribution_is_skipped(self):
        data = [
            {"weight": 1.0, "roles": {"subject": None}},
            {"weight": 1.0, "roles": {"subject": 0.5}},
        ]
        result = aggregate_evidence(data, role="subject")
        assert result["score"] == pytest.approx(0.5)
        assert result["coverage"] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# compute_confidence
# ---------------------------------------------------------------------------

class TestComputeConfidence:
    def test_zero_coverage_returns_zero(self):
        assert compute_confidence(0.0) == 0.0

    def test_negative_coverage_returns_zero(self):
        assert compute_confidence(-1.0) == 0.0

    def test_positive_coverage_returns_value_in_0_1(self):
        result = compute_confidence(1.0)
        assert 0 < result < 1

    def test_higher_coverage_gives_higher_confidence(self):
        assert compute_confidence(2.0) > compute_confidence(1.0)


# ---------------------------------------------------------------------------
# compute_disagreement
# ---------------------------------------------------------------------------

class TestComputeDisagreement:
    def test_empty_list_returns_zero(self):
        assert compute_disagreement([], role="subject") == 0.0

    def test_full_agreement_returns_zero(self):
        data = [
            {"weight": 1.0, "roles": {"subject": 1.0}},
            {"weight": 1.0, "roles": {"subject": 1.0}},
        ]
        assert compute_disagreement(data, role="subject") == pytest.approx(0.0)

    def test_full_cancellation_returns_one(self):
        data = [
            {"weight": 1.0, "roles": {"subject": 1.0}},
            {"weight": 1.0, "roles": {"subject": -1.0}},
        ]
        assert compute_disagreement(data, role="subject") == pytest.approx(1.0)

    def test_partial_disagreement_is_in_range(self):
        data = [
            {"weight": 2.0, "roles": {"subject": 1.0}},
            {"weight": 1.0, "roles": {"subject": -1.0}},
        ]
        result = compute_disagreement(data, role="subject")
        assert 0.0 < result < 1.0


# ---------------------------------------------------------------------------
# compute_role_inferences (integration of math primitives)
# ---------------------------------------------------------------------------

def _make_role(entity_id, role_type):
    role = MagicMock()
    role.entity_id = entity_id
    role.role_type = role_type
    return role


def _make_relation(direction, confidence, entity_id, role_type="subject"):
    rev = MagicMock()
    rev.is_current = True
    rev.direction = direction
    rev.confidence = confidence
    rev.roles = [_make_role(entity_id, role_type)]

    rel = MagicMock()
    rel.revisions = [rev]
    return rel


class TestComputeRoleInferences:
    def test_empty_relations_returns_empty_list(self):
        result = compute_role_inferences([])
        assert result == []

    def test_single_supporting_relation(self):
        entity_id = uuid4()
        relation = _make_relation("supports", 0.8, entity_id)
        result = compute_role_inferences([relation], current_entity_id=entity_id)
        assert len(result) == 1
        ri = result[0]
        assert ri.role_type == "subject"
        assert ri.score == pytest.approx(1.0)
        assert ri.coverage == pytest.approx(0.8)
        assert 0 < ri.confidence <= 1
        assert ri.disagreement == pytest.approx(0.0)

    def test_legacy_positive_direction_handled(self):
        entity_id = uuid4()
        relation = _make_relation("positive", 1.0, entity_id)
        result = compute_role_inferences([relation], current_entity_id=entity_id)
        assert len(result) == 1
        assert result[0].score == pytest.approx(1.0)

    def test_legacy_negative_direction_handled(self):
        entity_id = uuid4()
        relation = _make_relation("negative", 1.0, entity_id)
        result = compute_role_inferences([relation], current_entity_id=entity_id)
        assert len(result) == 1
        assert result[0].score == pytest.approx(-1.0)

    def test_neutral_direction_contributes_zero_score(self):
        entity_id = uuid4()
        relation = _make_relation(None, 1.0, entity_id)
        result = compute_role_inferences([relation], current_entity_id=entity_id)
        assert len(result) == 1
        assert result[0].score == pytest.approx(0.0)

    def test_disagreement_detected_on_mixed_directions(self):
        entity_id = uuid4()
        supporting = _make_relation("supports", 1.0, entity_id)
        contradicting = _make_relation("contradicts", 1.0, entity_id)
        result = compute_role_inferences([supporting, contradicting], current_entity_id=entity_id)
        assert len(result) == 1
        assert result[0].disagreement == pytest.approx(1.0)

    def test_current_entity_filter_excludes_other_entities(self):
        entity_a = uuid4()
        entity_b = uuid4()
        relation_a = _make_relation("supports", 1.0, entity_a)
        relation_b = _make_relation("supports", 1.0, entity_b)
        result = compute_role_inferences([relation_a, relation_b], current_entity_id=entity_a)
        # Only entity_a's role should be included
        assert len(result) == 1

    def test_relation_without_current_revision_is_skipped(self):
        rel = MagicMock()
        rev = MagicMock()
        rev.is_current = False
        rev.roles = []
        rel.revisions = [rev]
        result = compute_role_inferences([rel])
        assert result == []

    def test_relation_without_revisions_is_skipped(self):
        rel = MagicMock()
        rel.revisions = []
        result = compute_role_inferences([rel])
        assert result == []


# ---------------------------------------------------------------------------
# _find_existing_pmids — DB-backed test
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestFindExistingPmids:
    async def test_empty_pmids_returns_empty_set(self, db_session):
        from app.services.document_extraction_discovery import _find_existing_pmids
        result = await _find_existing_pmids(db_session, [], user_id=None)
        assert result == set()

    async def test_no_existing_sources_returns_empty_set(self, db_session):
        from app.services.document_extraction_discovery import _find_existing_pmids
        result = await _find_existing_pmids(db_session, ["12345678"], user_id=uuid4())
        assert result == set()

    async def test_existing_pmid_is_found(self, db_session):
        from app.services.document_extraction_discovery import _find_existing_pmids
        from app.services.source_service import SourceService
        from app.schemas.source import SourceWrite

        svc = SourceService(db_session)
        await svc.create(
            SourceWrite(
                kind="article",
                title="Test PubMed Source",
                url="https://pubmed.ncbi.nlm.nih.gov/99999999/",
                source_metadata={"pmid": "99999999"},
            ),
            user_id=None,
        )

        result = await _find_existing_pmids(db_session, ["99999999"], user_id=None)
        assert "99999999" in result

    async def test_pmid_from_other_user_is_not_returned(self, db_session):
        from app.services.document_extraction_discovery import _find_existing_pmids
        from app.services.source_service import SourceService
        from app.schemas.source import SourceWrite

        svc = SourceService(db_session)
        # Create without user attribution (user_id=None)
        await svc.create(
            SourceWrite(
                kind="article",
                title="No User Source",
                url="https://pubmed.ncbi.nlm.nih.gov/88888888/",
                source_metadata={"pmid": "88888888"},
            ),
            user_id=None,
        )

        # Query with a different (non-None) user id should not find it
        result = await _find_existing_pmids(db_session, ["88888888"], user_id=uuid4())
        assert "88888888" not in result

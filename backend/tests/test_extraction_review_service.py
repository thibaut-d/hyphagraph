"""
Tests for ExtractionReviewService (human-in-the-loop review system).

Tests cover:
- Staging extractions with validation results
- Auto-verification logic (high confidence → auto_verified)
- Manual review workflow (approve/reject)
- Immediate materialization (entities/relations created immediately)
- Status transitions and lifecycle
- Batch operations
- Query filters
- Statistics calculation
"""

import pytest
from datetime import datetime, timezone, UTC
from uuid import uuid4, UUID

from app.models.staged_extraction import StagedExtraction, ExtractionStatus, ExtractionType
from app.models.source import Source
from app.models.entity import Entity
from app.models.relation import Relation
from app.models.user import User
from app.services.extraction_review_service import ExtractionReviewService
from app.services.extraction_validation_service import ValidationResult
from app.llm.schemas import ExtractedEntity, ExtractedRelation


@pytest.fixture
async def sample_user(db_session):
    """Create a sample user for testing (needed for created_by_user_id foreign keys)."""
    user = User(
        id=uuid4(),
        email="reviewer@example.com",
        hashed_password="$2b$12$hashed_password_placeholder",
        is_active=True,
        is_superuser=False,
        is_verified=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def sample_source(db_session, sample_user):
    """Create a sample source for testing."""
    from app.models.source_revision import SourceRevision

    # Create base source (immutable)
    source = Source(id=uuid4())
    db_session.add(source)
    await db_session.flush()

    # Create revision with actual content
    revision = SourceRevision(
        id=uuid4(),
        source_id=source.id,
        kind="document",
        title="Test Document",
        url="test://document",
        is_current=True,
        created_by_user_id=sample_user.id,  # Use real user ID
    )
    db_session.add(revision)
    await db_session.commit()
    await db_session.refresh(source)
    return source


@pytest.fixture
def review_service(db_session):
    """Create ExtractionReviewService with default settings."""
    return ExtractionReviewService(
        db=db_session,
        auto_commit_enabled=True,
        auto_commit_threshold=0.9,
        require_no_flags_for_auto_commit=True,
    )


@pytest.fixture
def high_confidence_entity():
    """Entity with exact text span match (should auto-verify)."""
    return ExtractedEntity(
        slug="duloxetine",
        category="drug",
        summary="An FDA-approved medication for fibromyalgia",
        text_span="Duloxetine is an FDA-approved medication for fibromyalgia",
        confidence="high",
    )


@pytest.fixture
def high_confidence_validation():
    """Validation result for high-confidence extraction."""
    return ValidationResult(
        is_valid=True,
        confidence_adjustment=1.0,
        validation_score=1.0,
        flags=[],
        matched_span="Duloxetine is an FDA-approved medication for fibromyalgia",
    )


@pytest.fixture
def uncertain_entity():
    """Entity with fuzzy match (should flag for review)."""
    return ExtractedEntity(
        slug="serotonin-modulator",
        category="biological_mechanism",
        summary="A medication that affects serotonin levels in the brain",
        text_span="affects serotonin levels",
        confidence="medium",
    )


@pytest.fixture
def uncertain_validation():
    """Validation result for uncertain extraction."""
    return ValidationResult(
        is_valid=True,
        confidence_adjustment=0.75,
        validation_score=0.75,
        flags=["fuzzy_match"],
        matched_span="affecting serotonin levels",
    )


@pytest.fixture
def low_confidence_entity():
    """Entity that should be rejected (text span not found)."""
    return ExtractedEntity(
        slug="invented-drug",
        category="drug",
        summary="A completely made-up medication that does not exist",
        text_span="This text does not exist in the source",
        confidence="low",
    )


@pytest.fixture
def low_confidence_validation():
    """Validation result for hallucinated extraction."""
    return ValidationResult(
        is_valid=False,
        confidence_adjustment=0.0,
        validation_score=0.0,
        flags=["text_span_not_found", "possible_hallucination"],
        matched_span=None,
    )


# === Test Auto-Verification Logic ===


@pytest.mark.asyncio
async def test_stage_high_confidence_entity_auto_verifies(
    review_service, sample_source, high_confidence_entity, high_confidence_validation
):
    """High-confidence entity should auto-verify and materialize immediately."""
    staged, entity_id = await review_service.stage_extraction(
        extraction_type=ExtractionType.ENTITY,
        extraction_data=high_confidence_entity,
        source_id=sample_source.id,
        validation_result=high_confidence_validation,
        llm_model="claude-sonnet-4-5",
        llm_provider="anthropic",
        auto_materialize=True,
    )

    # Should auto-verify
    assert staged.status == ExtractionStatus.AUTO_VERIFIED
    assert staged.validation_score == 1.0
    assert staged.validation_flags == []

    # Should materialize immediately
    assert entity_id is not None
    assert staged.materialized_entity_id == entity_id

    # Verify entity was created
    from sqlalchemy import select
    result = await review_service.db.execute(select(Entity).where(Entity.id == entity_id))
    entity = result.scalar_one_or_none()
    assert entity is not None


@pytest.mark.asyncio
async def test_stage_uncertain_entity_flags_for_review(
    review_service, sample_source, uncertain_entity, uncertain_validation
):
    """Uncertain entity should be flagged for review but still materialized."""
    staged, entity_id = await review_service.stage_extraction(
        extraction_type=ExtractionType.ENTITY,
        extraction_data=uncertain_entity,
        source_id=sample_source.id,
        validation_result=uncertain_validation,
        llm_model="claude-sonnet-4-5",
        llm_provider="anthropic",
        auto_materialize=True,
    )

    # Should flag for review
    assert staged.status == ExtractionStatus.PENDING
    assert staged.validation_score == 0.75
    assert "fuzzy_match" in staged.validation_flags

    # Should still materialize
    assert entity_id is not None
    assert staged.materialized_entity_id == entity_id

    # Verify entity exists (visible but flagged)
    from sqlalchemy import select
    result = await review_service.db.execute(select(Entity).where(Entity.id == entity_id))
    entity = result.scalar_one_or_none()
    assert entity is not None


@pytest.mark.asyncio
async def test_stage_low_confidence_entity_flags_for_review(
    review_service, sample_source, low_confidence_entity, low_confidence_validation
):
    """Low-confidence entity should be flagged for review and still materialized."""
    staged, entity_id = await review_service.stage_extraction(
        extraction_type=ExtractionType.ENTITY,
        extraction_data=low_confidence_entity,
        source_id=sample_source.id,
        validation_result=low_confidence_validation,
        llm_model="claude-sonnet-4-5",
        llm_provider="anthropic",
        auto_materialize=True,
    )

    # Should flag for review due to low score and flags
    assert staged.status == ExtractionStatus.PENDING
    assert staged.validation_score == 0.0
    assert "text_span_not_found" in staged.validation_flags
    assert "possible_hallucination" in staged.validation_flags

    # Should still materialize (visibility strategy)
    assert entity_id is not None
    assert staged.materialized_entity_id == entity_id


@pytest.mark.asyncio
async def test_auto_commit_disabled_flags_all_for_review(
    db_session, sample_source, high_confidence_entity, high_confidence_validation
):
    """When auto-commit disabled, even high-confidence extractions should be pending."""
    service = ExtractionReviewService(
        db=db_session,
        auto_commit_enabled=False,  # Disabled
        auto_commit_threshold=0.9,
    )

    staged, entity_id = await service.stage_extraction(
        extraction_type=ExtractionType.ENTITY,
        extraction_data=high_confidence_entity,
        source_id=sample_source.id,
        validation_result=high_confidence_validation,
        llm_model="claude-sonnet-4-5",
        llm_provider="anthropic",
        auto_materialize=True,
    )

    # Should flag for review even though high confidence
    assert staged.status == ExtractionStatus.PENDING

    # Should still materialize
    assert entity_id is not None


@pytest.mark.asyncio
async def test_auto_materialize_false_skips_creation(
    review_service, sample_source, high_confidence_entity, high_confidence_validation
):
    """When auto_materialize=False, should not create entity immediately."""
    staged, entity_id = await review_service.stage_extraction(
        extraction_type=ExtractionType.ENTITY,
        extraction_data=high_confidence_entity,
        source_id=sample_source.id,
        validation_result=high_confidence_validation,
        llm_model="claude-sonnet-4-5",
        llm_provider="anthropic",
        auto_materialize=False,  # Don't materialize
    )

    # Should not materialize
    assert entity_id is None
    assert staged.materialized_entity_id is None

    # Can materialize later
    entity_id = await review_service.materialize_extraction(staged.id)
    assert entity_id is not None


# === Test Review Workflow ===


@pytest.mark.asyncio
async def test_approve_extraction_updates_status(
    review_service, sample_source, sample_user, uncertain_entity, uncertain_validation
):
    """Approving extraction should update status to APPROVED."""
    # Stage uncertain extraction
    staged, entity_id = await review_service.stage_extraction(
        extraction_type=ExtractionType.ENTITY,
        extraction_data=uncertain_entity,
        source_id=sample_source.id,
        validation_result=uncertain_validation,
        llm_model="claude-sonnet-4-5",
        llm_provider="anthropic",
        auto_materialize=True,
    )

    assert staged.status == ExtractionStatus.PENDING

    # Approve
    result = await review_service.approve_extraction(
        extraction_id=staged.id,
        reviewer_id=sample_user.id,
        notes="Verified against source document",
        auto_materialize=False,  # Don't materialize again, already done
    )

    # Check result
    assert result.success is True


@pytest.mark.asyncio
async def test_get_extraction_returns_staged_record(
    review_service, sample_source, uncertain_entity, uncertain_validation
):
    staged, _ = await review_service.stage_extraction(
        extraction_type=ExtractionType.ENTITY,
        extraction_data=uncertain_entity,
        source_id=sample_source.id,
        validation_result=uncertain_validation,
        llm_model="claude-sonnet-4-5",
        llm_provider="anthropic",
        auto_materialize=False,
    )

    loaded = await review_service.get_extraction(staged.id)

    assert loaded is not None
    assert loaded.id == staged.id


@pytest.mark.asyncio
async def test_delete_extraction_removes_record(
    review_service, sample_source, uncertain_entity, uncertain_validation
):
    staged, _ = await review_service.stage_extraction(
        extraction_type=ExtractionType.ENTITY,
        extraction_data=uncertain_entity,
        source_id=sample_source.id,
        validation_result=uncertain_validation,
        llm_model="claude-sonnet-4-5",
        llm_provider="anthropic",
        auto_materialize=False,
    )

    deleted = await review_service.delete_extraction(staged.id)
    loaded = await review_service.get_extraction(staged.id)

    assert deleted is True
    assert loaded is None


@pytest.mark.asyncio
async def test_reject_extraction_updates_status(
    review_service, sample_source, sample_user, low_confidence_entity, low_confidence_validation
):
    """Rejecting extraction should update status to REJECTED but keep entity."""
    # Stage low-confidence extraction
    staged, entity_id = await review_service.stage_extraction(
        extraction_type=ExtractionType.ENTITY,
        extraction_data=low_confidence_entity,
        source_id=sample_source.id,
        validation_result=low_confidence_validation,
        llm_model="claude-sonnet-4-5",
        llm_provider="anthropic",
        auto_materialize=True,
    )

    assert staged.status == ExtractionStatus.PENDING

    # Reject
    success = await review_service.reject_extraction(
        extraction_id=staged.id,
        reviewer_id=sample_user.id,
        notes="Text span not found in source",
    )

    # Check result
    assert success is True

    # Verify status was updated in database
    from sqlalchemy import select
    db_result = await review_service.db.execute(
        select(StagedExtraction).where(StagedExtraction.id == staged.id)
    )
    updated = db_result.scalar_one()
    assert updated.status == ExtractionStatus.REJECTED
    assert updated.reviewed_by == sample_user.id
    assert updated.review_notes == "Text span not found in source"

    # Entity should still exist (visibility strategy)
    result = await review_service.db.execute(select(Entity).where(Entity.id == entity_id))
    entity = result.scalar_one_or_none()
    assert entity is not None


@pytest.mark.asyncio
async def test_cannot_review_auto_verified_extraction(
    review_service, sample_source, sample_user, high_confidence_entity, high_confidence_validation
):
    """Cannot manually review an auto-verified extraction."""
    staged, _ = await review_service.stage_extraction(
        extraction_type=ExtractionType.ENTITY,
        extraction_data=high_confidence_entity,
        source_id=sample_source.id,
        validation_result=high_confidence_validation,
        llm_model="claude-sonnet-4-5",
        llm_provider="anthropic",
        auto_materialize=True,
    )

    assert staged.status == ExtractionStatus.AUTO_VERIFIED

    # Attempting to review should fail
    result = await review_service.approve_extraction(
        extraction_id=staged.id,
        reviewer_id=sample_user.id,
        auto_materialize=False,
    )

    assert result.success is False
    assert "already" in result.error.lower()


# === Test Batch Operations ===


@pytest.mark.asyncio
async def test_stage_batch_entities(
    review_service, sample_source, high_confidence_entity, uncertain_entity,
    high_confidence_validation, uncertain_validation
):
    """Batch staging should handle multiple entities with different confidence levels."""
    # stage_batch takes tuples of (extraction, validation_result)
    entities = [
        (high_confidence_entity, high_confidence_validation),
        (uncertain_entity, uncertain_validation),
    ]

    staged_list = await review_service.stage_batch(
        entities=entities,
        relations=[],
        claims=[],
        source_id=sample_source.id,
        llm_model="claude-sonnet-4-5",
        llm_provider="anthropic",
    )

    assert len(staged_list) == 2

    # First should auto-verify
    assert staged_list[0].status == ExtractionStatus.AUTO_VERIFIED
    assert staged_list[0].materialized_entity_id is not None

    # Second should flag for review
    assert staged_list[1].status == ExtractionStatus.PENDING
    assert staged_list[1].materialized_entity_id is not None


@pytest.mark.asyncio
async def test_batch_review_approve_multiple(
    review_service, sample_source, sample_user, uncertain_entity, uncertain_validation
):
    """Batch review should approve multiple extractions at once."""
    # Stage 3 uncertain extractions
    extractions = []
    for i in range(3):
        entity = ExtractedEntity(
            slug=f"test-entity-{i}",
            category="drug",
            summary=f"Test entity number {i} for batch review testing",
            text_span="affecting serotonin levels",
            confidence="medium",
        )
        staged, _ = await review_service.stage_extraction(
            extraction_type=ExtractionType.ENTITY,
            extraction_data=entity,
            source_id=sample_source.id,
            validation_result=uncertain_validation,
            llm_model="claude-sonnet-4-5",
            llm_provider="anthropic",
            auto_materialize=True,
        )
        extractions.append(staged)

    # Batch approve
    extraction_ids = [e.id for e in extractions]
    results = await review_service.batch_review(
        extraction_ids=extraction_ids,
        decision="approve",
        reviewer_id=sample_user.id,
        notes="Batch approval",
    )

    assert results.succeeded == 3
    assert results.failed == 0

    # Verify all are approved
    from sqlalchemy import select
    for extraction_id in extraction_ids:
        result = await review_service.db.execute(
            select(StagedExtraction).where(StagedExtraction.id == extraction_id)
        )
        staged = result.scalar_one_or_none()
        assert staged.status == ExtractionStatus.APPROVED


@pytest.mark.asyncio
async def test_batch_review_mixed_results(
    review_service, sample_source, sample_user, uncertain_entity, high_confidence_entity,
    uncertain_validation, high_confidence_validation
):
    """Batch review should handle mixed success/failure."""
    # Stage uncertain extraction (can review)
    staged_pending, _ = await review_service.stage_extraction(
        extraction_type=ExtractionType.ENTITY,
        extraction_data=uncertain_entity,
        source_id=sample_source.id,
        validation_result=uncertain_validation,
        llm_model="claude-sonnet-4-5",
        llm_provider="anthropic",
        auto_materialize=True,
    )

    # Stage auto-verified extraction (cannot review)
    staged_verified, _ = await review_service.stage_extraction(
        extraction_type=ExtractionType.ENTITY,
        extraction_data=high_confidence_entity,
        source_id=sample_source.id,
        validation_result=high_confidence_validation,
        llm_model="claude-sonnet-4-5",
        llm_provider="anthropic",
        auto_materialize=True,
    )

    # Try to batch approve both
    results = await review_service.batch_review(
        extraction_ids=[staged_pending.id, staged_verified.id],
        decision="approve",
        reviewer_id=sample_user.id,
    )

    # Should have 1 success, 1 failure
    assert results.succeeded == 1
    assert results.failed == 1


# === Test Query Filters ===


@pytest.mark.asyncio
async def test_list_extractions_filter_by_status(
    review_service, sample_source, uncertain_entity, uncertain_validation
):
    """Should filter extractions by status."""
    # Create pending and approved extractions
    staged1, _ = await review_service.stage_extraction(
        extraction_type=ExtractionType.ENTITY,
        extraction_data=uncertain_entity,
        source_id=sample_source.id,
        validation_result=uncertain_validation,
        llm_model="claude-sonnet-4-5",
        llm_provider="anthropic",
        auto_materialize=True,
    )

    staged2, _ = await review_service.stage_extraction(
        extraction_type=ExtractionType.ENTITY,
        extraction_data=ExtractedEntity(
            slug="entity-2",
            category="drug",
            summary="Test entity for approval workflow testing purposes",
            text_span="affecting serotonin levels",
            confidence="medium",
        ),
        source_id=sample_source.id,
        validation_result=uncertain_validation,
        llm_model="claude-sonnet-4-5",
        llm_provider="anthropic",
        auto_materialize=True,
    )

    # Approve one (need a real user ID for FK constraint)
    await review_service.approve_extraction(
        extraction_id=staged2.id,
        reviewer_id=sample_source.revisions[0].created_by_user_id,  # Use existing user
        auto_materialize=False,
    )

    # Filter for pending
    from app.schemas.staged_extraction import StagedExtractionFilters
    pending, count = await review_service.list_extractions(
        filters=StagedExtractionFilters(
            status="pending",
            page_size=10,
        )
    )
    assert len(pending) == 1
    assert pending[0].id == staged1.id

    # Filter for approved
    approved, count = await review_service.list_extractions(
        filters=StagedExtractionFilters(
            status="approved",
            page_size=10,
        )
    )
    assert len(approved) == 1
    assert approved[0].id == staged2.id


@pytest.mark.asyncio
async def test_list_extractions_filter_by_score(
    review_service, sample_source, high_confidence_entity, uncertain_entity,
    high_confidence_validation, uncertain_validation
):
    """Should filter extractions by validation score."""
    # Create high and low confidence extractions
    await review_service.stage_extraction(
        extraction_type=ExtractionType.ENTITY,
        extraction_data=high_confidence_entity,
        source_id=sample_source.id,
        validation_result=high_confidence_validation,
        llm_model="claude-sonnet-4-5",
        llm_provider="anthropic",
        auto_materialize=True,
    )

    await review_service.stage_extraction(
        extraction_type=ExtractionType.ENTITY,
        extraction_data=uncertain_entity,
        source_id=sample_source.id,
        validation_result=uncertain_validation,
        llm_model="claude-sonnet-4-5",
        llm_provider="anthropic",
        auto_materialize=True,
    )

    # Filter for high scores
    from app.schemas.staged_extraction import StagedExtractionFilters
    high_scores, count = await review_service.list_extractions(
        filters=StagedExtractionFilters(
            min_validation_score=0.9,
            page_size=10,
        )
    )
    assert len(high_scores) == 1
    assert high_scores[0].validation_score >= 0.9

    # Filter for medium scores
    medium_scores, count = await review_service.list_extractions(
        filters=StagedExtractionFilters(
            min_validation_score=0.7,
            max_validation_score=0.8,
            page_size=10,
        )
    )
    assert len(medium_scores) == 1
    assert 0.7 <= medium_scores[0].validation_score <= 0.8


@pytest.mark.asyncio
async def test_list_extractions_filter_by_flags(
    review_service, sample_source, uncertain_entity, uncertain_validation
):
    """Should filter extractions by validation flags."""
    # Create extraction with fuzzy_match flag
    await review_service.stage_extraction(
        extraction_type=ExtractionType.ENTITY,
        extraction_data=uncertain_entity,
        source_id=sample_source.id,
        validation_result=uncertain_validation,
        llm_model="claude-sonnet-4-5",
        llm_provider="anthropic",
        auto_materialize=True,
    )

    # Create extraction with hallucination flag
    hallucination_validation = ValidationResult(
        is_valid=False,
        confidence_adjustment=0.0,
        validation_score=0.0,
        flags=["text_span_not_found", "possible_hallucination"],
        matched_span=None,
    )

    await review_service.stage_extraction(
        extraction_type=ExtractionType.ENTITY,
        extraction_data=ExtractedEntity(
            slug="hallucinated-entity",
            category="drug",
            summary="Made up entity for hallucination detection testing",
            text_span="nonexistent text span",
            confidence="low",
        ),
        source_id=sample_source.id,
        validation_result=hallucination_validation,
        llm_model="claude-sonnet-4-5",
        llm_provider="anthropic",
        auto_materialize=True,
    )

    # Filter for extractions with any flags
    from app.schemas.staged_extraction import StagedExtractionFilters
    with_flags, count = await review_service.list_extractions(
        filters=StagedExtractionFilters(
            has_flags=True,
            page_size=10,
        )
    )
    assert len(with_flags) == 2  # Both have flags
    assert all(len(e.validation_flags) > 0 for e in with_flags)


# === Test Statistics ===


@pytest.mark.asyncio
async def test_get_stats_calculates_correctly(
    review_service, sample_source, high_confidence_entity, uncertain_entity,
    high_confidence_validation, uncertain_validation
):
    """Should calculate review statistics correctly."""
    # Create various extractions
    # 1 auto-verified
    await review_service.stage_extraction(
        extraction_type=ExtractionType.ENTITY,
        extraction_data=high_confidence_entity,
        source_id=sample_source.id,
        validation_result=high_confidence_validation,
        llm_model="claude-sonnet-4-5",
        llm_provider="anthropic",
        auto_materialize=True,
    )

    # 2 pending
    for i in range(2):
        await review_service.stage_extraction(
            extraction_type=ExtractionType.ENTITY,
            extraction_data=ExtractedEntity(
                slug=f"pending-entity-{i}",
                category="drug",
                summary=f"Pending entity {i} for statistics aggregation testing",
                text_span="affecting serotonin levels",
                confidence="medium",
            ),
            source_id=sample_source.id,
            validation_result=uncertain_validation,
            llm_model="claude-sonnet-4-5",
            llm_provider="anthropic",
            auto_materialize=True,
        )

    stats = await review_service.get_stats()

    # Check status counts
    assert stats.total_auto_verified == 1
    assert stats.total_pending == 2
    assert stats.total_approved == 0
    assert stats.total_rejected == 0

    # Check type breakdown (all pending are entities)
    assert stats.pending_entities == 2

    # Check quality metrics
    assert 0.7 <= stats.avg_validation_score <= 0.8  # Average of 2 pending with score 0.75
    assert stats.flagged_count == 2  # 2 pending with fuzzy_match flag


@pytest.mark.asyncio
async def test_get_stats_after_reviews(
    review_service, sample_source, sample_user, uncertain_entity, uncertain_validation
):
    """Statistics should update after reviews."""
    # Create 2 pending extractions
    staged_list = []
    for i in range(2):
        staged, _ = await review_service.stage_extraction(
            extraction_type=ExtractionType.ENTITY,
            extraction_data=ExtractedEntity(
                slug=f"stats-entity-{i}",
                category="drug",
                summary=f"Test entity {i} for statistics calculation testing",
                text_span="affecting serotonin levels",
                confidence="medium",
            ),
            source_id=sample_source.id,
            validation_result=uncertain_validation,
            llm_model="claude-sonnet-4-5",
            llm_provider="anthropic",
            auto_materialize=True,
        )
        staged_list.append(staged)

    # Approve one, reject one
    await review_service.approve_extraction(
        extraction_id=staged_list[0].id,
        reviewer_id=sample_user.id,
        auto_materialize=False,
    )
    await review_service.reject_extraction(staged_list[1].id, sample_user.id)

    stats = await review_service.get_stats()

    assert stats.total_pending == 0
    assert stats.total_approved == 1
    assert stats.total_rejected == 1

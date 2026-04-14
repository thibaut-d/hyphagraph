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
from datetime import datetime, timezone
from uuid import uuid4

from app.models.staged_extraction import StagedExtraction, ExtractionStatus, ExtractionType
from app.models.source import Source
from app.models.entity import Entity
from app.models.user import User
from app.services.extraction_review_service import ExtractionReviewService
from app.services.extraction_validation_service import ValidationResult
from app.llm.schemas import ExtractedEntity


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
        kind="study",
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
    assert updated.reviewed_at is not None
    assert updated.reviewed_at.tzinfo is None
    assert updated.review_notes == "Text span not found in source"

    # Entity still exists in the DB (soft-delete, not hard-delete)
    result = await review_service.db.execute(select(Entity).where(Entity.id == entity_id))
    entity = result.scalar_one_or_none()
    assert entity is not None
    # Entity is now flagged as rejected and hidden from standard queries
    assert entity.is_rejected is True


@pytest.mark.asyncio
async def test_can_approve_auto_verified_extraction(
    review_service, sample_source, sample_user, high_confidence_entity, high_confidence_validation
):
    """Human reviewer can explicitly approve an auto-verified extraction (DF-RVW-M2)."""
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

    # A human reviewer should be able to confirm an auto-verified item
    result = await review_service.approve_extraction(
        extraction_id=staged.id,
        reviewer_id=sample_user.id,
        auto_materialize=False,
    )

    assert result.success is True
    assert result.error is None

    from sqlalchemy import select

    db_result = await review_service.db.execute(
        select(StagedExtraction).where(StagedExtraction.id == staged.id)
    )
    updated = db_result.scalar_one()
    assert updated.reviewed_at is not None
    assert updated.reviewed_at.tzinfo is None


@pytest.mark.asyncio
async def test_materialized_entity_revision_carries_llm_model(
    review_service, sample_source, high_confidence_entity, high_confidence_validation
):
    """EntityRevision created during materialization should record the LLM model."""
    staged, entity_id = await review_service.stage_extraction(
        extraction_type=ExtractionType.ENTITY,
        extraction_data=high_confidence_entity,
        source_id=sample_source.id,
        validation_result=high_confidence_validation,
        llm_model="claude-sonnet-4-5",
        llm_provider="anthropic",
        auto_materialize=True,
    )

    assert entity_id is not None

    from sqlalchemy import select
    from app.models.entity_revision import EntityRevision
    result = await review_service.db.execute(
        select(EntityRevision)
        .where(EntityRevision.entity_id == entity_id)
        .where(EntityRevision.is_current == True)
    )
    revision = result.scalar_one()
    assert revision.created_with_llm == "claude-sonnet-4-5"
    assert revision.created_by_user_id is None  # LLM-created, not user-created


@pytest.mark.asyncio
async def test_reject_auto_verified_extraction_transitions_to_rejected(
    review_service, sample_source, sample_user, high_confidence_entity, high_confidence_validation
):
    """Rejecting an AUTO_VERIFIED extraction should succeed and mark it REJECTED."""
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

    success = await review_service.reject_extraction(
        extraction_id=staged.id,
        reviewer_id=sample_user.id,
        notes="Reject even though auto-verified",
    )

    assert success is True

    from sqlalchemy import select
    db_result = await review_service.db.execute(
        select(StagedExtraction).where(StagedExtraction.id == staged.id)
    )
    updated = db_result.scalar_one()
    assert updated.status == ExtractionStatus.REJECTED
    assert updated.reviewed_by == sample_user.id


@pytest.mark.asyncio
async def test_auto_materialize_false_high_confidence_status_is_pending(
    review_service, sample_source, high_confidence_entity, high_confidence_validation
):
    """High-confidence + auto_materialize=False should produce PENDING status, not AUTO_VERIFIED."""
    staged, entity_id = await review_service.stage_extraction(
        extraction_type=ExtractionType.ENTITY,
        extraction_data=high_confidence_entity,
        source_id=sample_source.id,
        validation_result=high_confidence_validation,
        llm_model="claude-sonnet-4-5",
        llm_provider="anthropic",
        auto_materialize=False,
    )

    assert entity_id is None
    assert staged.status == ExtractionStatus.PENDING


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

    # Batch approve both — AUTO_VERIFIED is now reviewable (DF-RVW-M2)
    results = await review_service.batch_review(
        extraction_ids=[staged_pending.id, staged_verified.id],
        decision="approve",
        reviewer_id=sample_user.id,
    )

    # Both should succeed now that AUTO_VERIFIED is a reviewable status
    assert results.succeeded == 2
    assert results.failed == 0


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


@pytest.mark.asyncio
async def test_list_extractions_repairs_stale_structurally_invalid_relation(review_service, sample_source):
    from app.schemas.staged_extraction import StagedExtractionFilters

    staged = StagedExtraction(
        extraction_type=ExtractionType.RELATION,
        status=ExtractionStatus.PENDING,
        source_id=sample_source.id,
        extraction_data={
            "relation_type": "causes",
            "roles": [
                {"entity_slug": "nausea", "role_type": "target"},
                {"entity_slug": "placebo", "role_type": "control_group"},
            ],
            "confidence": "high",
            "text_span": "adverse events experienced by participants were not serious",
            "notes": "Common adverse event reported.",
        },
        validation_score=1.0,
        confidence_adjustment=1.0,
        validation_flags=[],
        matched_span="adverse events experienced by participants were not serious",
        llm_model="gpt-5.4",
        llm_provider="openai",
        auto_commit_eligible=True,
        auto_commit_threshold=0.9,
    )
    review_service.db.add(staged)
    await review_service.db.commit()

    results, count = await review_service.list_extractions(
        StagedExtractionFilters(extraction_type="relation", page_size=10)
    )

    assert count == 1
    assert results[0].id == staged.id
    assert results[0].validation_score == 0.0
    assert results[0].confidence_adjustment == 0.0
    assert "missing_required_relation_roles" in results[0].validation_flags
    assert "missing_core_role:agent" in results[0].validation_flags
    assert results[0].auto_commit_eligible is False


@pytest.mark.asyncio
async def test_get_stats_repairs_stale_auto_verified_invalid_relation(review_service, sample_source):
    staged = StagedExtraction(
        extraction_type=ExtractionType.RELATION,
        status=ExtractionStatus.AUTO_VERIFIED,
        source_id=sample_source.id,
        extraction_data={
            "relation_type": "causes",
            "roles": [
                {"entity_slug": "nausea", "role_type": "target"},
                {"entity_slug": "placebo", "role_type": "control_group"},
            ],
            "confidence": "high",
            "text_span": "adverse events experienced by participants were not serious",
            "notes": "Common adverse event reported.",
        },
        validation_score=1.0,
        confidence_adjustment=1.0,
        validation_flags=[],
        matched_span="adverse events experienced by participants were not serious",
        llm_model="gpt-5.4",
        llm_provider="openai",
        auto_commit_eligible=True,
        auto_commit_threshold=0.9,
    )
    review_service.db.add(staged)
    await review_service.db.commit()

    stats = await review_service.get_stats()
    await review_service.db.refresh(staged)

    assert staged.status == ExtractionStatus.PENDING
    assert staged.validation_score == 0.0
    assert staged.auto_commit_eligible is False
    assert stats.total_pending == 1
    assert stats.total_auto_verified == 0
    assert stats.pending_relations == 1
    assert stats.avg_validation_score == 0.0
    assert stats.flagged_count == 1


# === Pure Function Tests: check_auto_commit_eligible ===


from app.services.extraction_review.auto_commit import check_auto_commit_eligible


def test_check_auto_commit_eligible_all_criteria_met():
    """All criteria met → True."""
    result = ValidationResult(
        is_valid=True, confidence_adjustment=1.0, validation_score=0.95,
        flags=[], matched_span="some text",
    )
    assert check_auto_commit_eligible(result, True, 0.9, True) is True


def test_check_auto_commit_eligible_disabled():
    """auto_commit_enabled=False always returns False regardless of score."""
    result = ValidationResult(
        is_valid=True, confidence_adjustment=1.0, validation_score=0.99,
        flags=[], matched_span="some text",
    )
    assert check_auto_commit_eligible(result, False, 0.9, True) is False


def test_check_auto_commit_eligible_score_below_threshold():
    """Score below threshold → False."""
    result = ValidationResult(
        is_valid=True, confidence_adjustment=0.8, validation_score=0.8,
        flags=[], matched_span="some text",
    )
    assert check_auto_commit_eligible(result, True, 0.9, True) is False


def test_check_auto_commit_eligible_score_at_threshold():
    """Score exactly at threshold passes (>= comparison)."""
    result = ValidationResult(
        is_valid=True, confidence_adjustment=0.9, validation_score=0.9,
        flags=[], matched_span="some text",
    )
    assert check_auto_commit_eligible(result, True, 0.9, True) is True


def test_check_auto_commit_eligible_fails_with_flags_when_required():
    """Has flags + require_no_flags=True → False even if score is high."""
    result = ValidationResult(
        is_valid=True, confidence_adjustment=1.0, validation_score=0.95,
        flags=["fuzzy_match"], matched_span="some text",
    )
    assert check_auto_commit_eligible(result, True, 0.9, True) is False


def test_check_auto_commit_eligible_allows_flags_when_not_required():
    """Has flags + require_no_flags=False → True if score passes."""
    result = ValidationResult(
        is_valid=True, confidence_adjustment=1.0, validation_score=0.95,
        flags=["fuzzy_match"], matched_span="some text",
    )
    assert check_auto_commit_eligible(result, True, 0.9, False) is True


# === Test Relation Staging and Materialization ===


@pytest.fixture
async def entity_slugs_in_db(review_service, sample_source, high_confidence_validation):
    """Ensure two entities with known slugs exist in the database."""
    for slug, summary in [
        ("drug-agent", "A drug used as the agent in a treatment relation"),
        ("pain-condition", "A chronic pain condition used as target in a relation"),
    ]:
        await review_service.stage_extraction(
            extraction_type=ExtractionType.ENTITY,
            extraction_data=ExtractedEntity(
                slug=slug,
                category="drug" if "drug" in slug else "disease",
                summary=summary,
                text_span=summary,
                confidence="high",
            ),
            source_id=sample_source.id,
            validation_result=high_confidence_validation,
            auto_materialize=True,
        )
    return ["drug-agent", "pain-condition"]


@pytest.fixture
def high_confidence_relation(entity_slugs_in_db):
    from app.llm.schemas import ExtractedRelation, ExtractedRole
    return ExtractedRelation(
        relation_type="treats",
        roles=[
            ExtractedRole(entity_slug="drug-agent", role_type="agent"),
            ExtractedRole(entity_slug="pain-condition", role_type="target"),
        ],
        confidence="high",
        text_span="Drug-agent treats pain-condition in clinical studies",
    )


@pytest.mark.asyncio
async def test_stage_relation_auto_verifies_and_materializes(
    review_service, sample_source, entity_slugs_in_db, high_confidence_relation,
    high_confidence_validation
):
    """High-confidence relation should auto-verify and materialize into a Relation row."""
    from app.models.relation import Relation
    from sqlalchemy import select

    staged, relation_id = await review_service.stage_extraction(
        extraction_type=ExtractionType.RELATION,
        extraction_data=high_confidence_relation,
        source_id=sample_source.id,
        validation_result=high_confidence_validation,
        llm_model="claude-sonnet-4-5",
        llm_provider="anthropic",
        auto_materialize=True,
    )

    assert staged.status == ExtractionStatus.AUTO_VERIFIED
    assert relation_id is not None
    assert staged.materialized_relation_id == relation_id

    result = await review_service.db.execute(select(Relation).where(Relation.id == relation_id))
    assert result.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_stage_relation_materialization_persists_direction_and_scope(
    review_service, sample_source, entity_slugs_in_db, high_confidence_validation
):
    from app.llm.schemas import ExtractedRelation, ExtractedRelationEvidenceContext, ExtractedRole
    from app.models.relation_revision import RelationRevision
    from sqlalchemy import select

    relation = ExtractedRelation(
        relation_type="treats",
        roles=[
            ExtractedRole(entity_slug="drug-agent", role_type="agent"),
            ExtractedRole(entity_slug="pain-condition", role_type="target"),
        ],
        confidence="high",
        text_span="In a randomized trial (n=84), the drug-agent did not reduce pain-condition severity.",
        notes="Null effect in the randomized trial.",
        evidence_context=ExtractedRelationEvidenceContext(
            statement_kind="finding",
            finding_polarity="contradicts",
            evidence_strength="strong",
            study_design="randomized_controlled_trial",
            sample_size=84,
            sample_size_text="n=84",
            assertion_text="The drug-agent did not reduce pain-condition severity.",
            methodology_text="Randomized trial.",
            statistical_support="p=0.27",
        ),
    )

    staged, relation_id = await review_service.stage_extraction(
        extraction_type=ExtractionType.RELATION,
        extraction_data=relation,
        source_id=sample_source.id,
        validation_result=high_confidence_validation,
        auto_materialize=True,
    )

    assert staged.materialized_relation_id == relation_id

    result = await review_service.db.execute(
        select(RelationRevision).where(
            RelationRevision.relation_id == relation_id,
            RelationRevision.is_current.is_(True),
        )
    )
    revision = result.scalar_one()
    assert revision.direction == "contradicts"
    assert revision.scope == {
        "evidence_context": {
            "statement_kind": "finding",
            "finding_polarity": "contradicts",
            "evidence_strength": "strong",
            "study_design": "randomized_controlled_trial",
            "sample_size": 84,
            "sample_size_text": "n=84",
            "assertion_text": "The drug-agent did not reduce pain-condition severity.",
            "methodology_text": "Randomized trial.",
            "statistical_support": "p=0.27",
        }
    }


@pytest.mark.asyncio
async def test_stage_relation_without_matching_entities_raises(
    review_service, sample_source, high_confidence_validation
):
    """Relation with unknown entity slugs raises ValueError during materialization (DF-EXT-M1)."""
    from app.llm.schemas import ExtractedRelation, ExtractedRole

    relation = ExtractedRelation(
        relation_type="treats",
        roles=[
            ExtractedRole(entity_slug="unknown-entity-a", role_type="agent"),
            ExtractedRole(entity_slug="unknown-entity-b", role_type="target"),
        ],
        confidence="high",
        text_span="unknown-entity-a treats unknown-entity-b",
    )

    with pytest.raises(ValueError, match="not found"):
        await review_service.stage_extraction(
            extraction_type=ExtractionType.RELATION,
            extraction_data=relation,
            source_id=sample_source.id,
            validation_result=high_confidence_validation,
            auto_materialize=True,
        )


# === Test Claim Staging ===


@pytest.mark.asyncio
async def test_stage_claim_without_auto_materialize_stays_unmaterialized(
    review_service, sample_source, uncertain_validation
):
    """Claims staged with auto_materialize=False are stored as PENDING without a relation."""
    from app.llm.schemas import ExtractedClaim

    claim = ExtractedClaim(
        claim_text="Duloxetine reduces pain scores by 50% in fibromyalgia patients",
        entities_involved=["duloxetine", "fibromyalgia"],
        claim_type="efficacy",
        evidence_strength="moderate",
        confidence="medium",
        text_span="reduces pain scores by 50%",
    )

    staged, materialized_id = await review_service.stage_extraction(
        extraction_type=ExtractionType.CLAIM,
        extraction_data=claim,
        source_id=sample_source.id,
        validation_result=uncertain_validation,
        auto_materialize=False,
    )

    assert staged is not None
    assert staged.extraction_type == ExtractionType.CLAIM
    assert staged.status.value == "pending"
    assert materialized_id is None
    assert staged.materialized_entity_id is None
    assert staged.materialized_relation_id is None


@pytest.mark.asyncio
async def test_stage_batch_with_all_types(
    review_service, sample_source, entity_slugs_in_db,
    high_confidence_entity, uncertain_entity,
    high_confidence_validation, uncertain_validation
):
    """stage_batch should handle entities, relations, and claims together."""
    from app.llm.schemas import ExtractedClaim, ExtractedRelation, ExtractedRole

    relation = ExtractedRelation(
        relation_type="treats",
        roles=[
            ExtractedRole(entity_slug="drug-agent", role_type="agent"),
            ExtractedRole(entity_slug="pain-condition", role_type="target"),
        ],
        confidence="medium",
        text_span="drug-agent treats pain-condition",
    )
    claim = ExtractedClaim(
        claim_text="Drug-agent reduces pain scores significantly in clinical trials",
        entities_involved=["drug-agent"],
        claim_type="efficacy",
        evidence_strength="moderate",
        confidence="medium",
        text_span="reduces pain scores significantly",
    )

    staged_list = await review_service.stage_batch(
        entities=[(high_confidence_entity, high_confidence_validation)],
        relations=[(relation, uncertain_validation)],
        claims=[(claim, uncertain_validation)],
        source_id=sample_source.id,
        llm_model="claude-sonnet-4-5",
        llm_provider="anthropic",
    )

    assert len(staged_list) == 3
    types = {s.extraction_type for s in staged_list}
    assert ExtractionType.ENTITY in types
    assert ExtractionType.RELATION in types
    assert ExtractionType.CLAIM in types


# === Test auto_commit_eligible_extractions ===


@pytest.mark.asyncio
async def test_auto_commit_eligible_extractions_when_disabled(db_session, sample_source):
    """When auto-commit is disabled, returns early with 'disabled' message."""
    service = ExtractionReviewService(db=db_session, auto_commit_enabled=False)
    response = await service.auto_commit_eligible_extractions()
    assert response.auto_committed == 0
    assert "disabled" in response.message.lower()


@pytest.mark.asyncio
async def test_auto_commit_eligible_extractions_no_eligible(review_service):
    """When no eligible pending extractions exist, reports 0 committed."""
    response = await review_service.auto_commit_eligible_extractions()
    assert response.auto_committed == 0


@pytest.mark.asyncio
async def test_auto_commit_eligible_extractions_materializes_pending(
    review_service, sample_source, high_confidence_entity, high_confidence_validation
):
    """Eligible pending extractions should be auto-approved and materialized."""
    from sqlalchemy import select

    # Stage without materializing — high confidence stays PENDING with auto_commit_eligible=True
    staged, entity_id = await review_service.stage_extraction(
        extraction_type=ExtractionType.ENTITY,
        extraction_data=high_confidence_entity,
        source_id=sample_source.id,
        validation_result=high_confidence_validation,
        auto_materialize=False,
    )
    assert staged.status == ExtractionStatus.PENDING
    assert staged.auto_commit_eligible is True
    assert entity_id is None

    response = await review_service.auto_commit_eligible_extractions()

    assert response.auto_committed == 1

    # Verify DB state: APPROVED and materialized
    result = await review_service.db.execute(
        select(StagedExtraction).where(StagedExtraction.id == staged.id)
    )
    updated = result.scalar_one()
    assert updated.status == ExtractionStatus.APPROVED
    assert updated.materialized_entity_id is not None
    assert updated.reviewed_at is not None
    assert updated.reviewed_at.tzinfo is None


# === Test materialize_extraction Edge Cases ===


@pytest.mark.asyncio
async def test_materialize_extraction_not_found(review_service):
    """materialize_extraction returns failure when ID does not exist."""
    fake_id = uuid4()
    result = await review_service.materialize_extraction(fake_id)
    assert result.success is False
    assert "not found" in result.error.lower()


@pytest.mark.asyncio
async def test_materialize_extraction_wrong_status(
    review_service, sample_source, uncertain_entity, uncertain_validation
):
    """materialize_extraction returns failure when extraction is not APPROVED."""
    staged, _ = await review_service.stage_extraction(
        extraction_type=ExtractionType.ENTITY,
        extraction_data=uncertain_entity,
        source_id=sample_source.id,
        validation_result=uncertain_validation,
        auto_materialize=False,
    )
    assert staged.status == ExtractionStatus.PENDING

    result = await review_service.materialize_extraction(staged.id)
    assert result.success is False
    assert "not approved" in result.error.lower()


@pytest.mark.asyncio
async def test_materialize_extraction_after_manual_approval(
    review_service, sample_source, sample_user, uncertain_entity, uncertain_validation
):
    """materialize_extraction succeeds on an APPROVED extraction that was not yet materialized."""
    from sqlalchemy import select

    staged, _ = await review_service.stage_extraction(
        extraction_type=ExtractionType.ENTITY,
        extraction_data=uncertain_entity,
        source_id=sample_source.id,
        validation_result=uncertain_validation,
        auto_materialize=False,
    )

    # Approve without materializing
    approval = await review_service.approve_extraction(
        extraction_id=staged.id,
        reviewer_id=sample_user.id,
        auto_materialize=False,
    )
    assert approval.success is True

    # Materialize explicitly
    result = await review_service.materialize_extraction(staged.id)
    assert result.success is True
    assert result.materialized_entity_id is not None


@pytest.mark.asyncio
async def test_materialize_claim_creates_relation(
    review_service, sample_source, entity_slugs_in_db, uncertain_validation, sample_user
):
    """Materializing a claim creates a relation with claim_type as kind and claim_text in notes."""
    from app.llm.schemas import ExtractedClaim
    from app.models.relation_revision import RelationRevision
    from sqlalchemy import select

    claim = ExtractedClaim(
        claim_text="Some factual claim about a drug with sufficient length",
        entities_involved=["drug-agent"],
        claim_type="efficacy",
        evidence_strength="moderate",
        confidence="medium",
        text_span="factual claim about a drug",
    )

    staged, _ = await review_service.stage_extraction(
        extraction_type=ExtractionType.CLAIM,
        extraction_data=claim,
        source_id=sample_source.id,
        validation_result=uncertain_validation,
        auto_materialize=False,
    )

    await review_service.approve_extraction(
        extraction_id=staged.id,
        reviewer_id=sample_user.id,
        auto_materialize=False,
    )

    result = await review_service.materialize_extraction(staged.id)

    assert result.success is True
    assert result.extraction_type == "claim"
    assert result.materialized_relation_id is not None

    # Verify the relation revision has correct fields
    db = review_service.db
    revision_result = await db.execute(
        select(RelationRevision)
        .where(RelationRevision.relation_id == result.materialized_relation_id)
        .where(RelationRevision.is_current == True)  # noqa: E712
    )
    revision = revision_result.scalar_one()
    assert revision.kind == "efficacy"
    assert revision.notes == {"en": "Some factual claim about a drug with sufficient length"}
    assert revision.scope == {"evidence_strength": "moderate"}
    assert revision.confidence is not None


@pytest.mark.asyncio
async def test_stage_claim_auto_materializes_when_high_confidence(
    review_service, sample_source, entity_slugs_in_db, high_confidence_validation
):
    """High-confidence claims are auto-materialized as relations on staging."""
    from app.llm.schemas import ExtractedClaim

    claim = ExtractedClaim(
        claim_text="Drug-agent significantly reduces risk of pain-condition in high-risk patients",
        entities_involved=["drug-agent"],
        claim_type="efficacy",
        evidence_strength="strong",
        confidence="high",
        text_span="reduces risk of cardiovascular events",
    )

    staged, materialized_id = await review_service.stage_extraction(
        extraction_type=ExtractionType.CLAIM,
        extraction_data=claim,
        source_id=sample_source.id,
        validation_result=high_confidence_validation,
        auto_materialize=True,
    )

    assert staged.extraction_type == ExtractionType.CLAIM
    assert materialized_id is not None
    assert staged.materialized_relation_id == materialized_id


@pytest.mark.asyncio
async def test_materialize_claim_raises_on_missing_entities(
    review_service, sample_source, uncertain_validation
):
    """Claim with unknown entity slugs raises ValueError during materialization (DF-EXT-M1)."""
    from app.llm.schemas import ExtractedClaim

    claim = ExtractedClaim(
        claim_text="Nonexistent-drug reduces some-unknown-condition symptoms reliably",
        entities_involved=["nonexistent-slug-abc", "another-missing-slug-xyz"],
        claim_type="safety",
        evidence_strength="weak",
        confidence="low",
        text_span="reduces some-unknown-condition symptoms",
    )

    with pytest.raises(ValueError, match="not found"):
        await review_service.stage_extraction(
            extraction_type=ExtractionType.CLAIM,
            extraction_data=claim,
            source_id=sample_source.id,
            validation_result=uncertain_validation,
            auto_materialize=True,
        )


@pytest.mark.asyncio
async def test_materialize_claim_with_known_entities_creates_roles(
    review_service, sample_source, entity_slugs_in_db, uncertain_validation, sample_user
):
    """Claim materialization creates RelationRoleRevision entries for known entity slugs."""
    from app.llm.schemas import ExtractedClaim
    from app.models.relation_role_revision import RelationRoleRevision
    from app.models.relation_revision import RelationRevision
    from sqlalchemy import select

    claim = ExtractedClaim(
        claim_text="Drug-agent reduces pain-condition severity in chronic patients significantly",
        entities_involved=["drug-agent", "pain-condition"],
        claim_type="mechanism",
        evidence_strength="moderate",
        confidence="medium",
        text_span="reduces pain-condition severity",
    )

    staged, _ = await review_service.stage_extraction(
        extraction_type=ExtractionType.CLAIM,
        extraction_data=claim,
        source_id=sample_source.id,
        validation_result=uncertain_validation,
        auto_materialize=False,
    )

    await review_service.approve_extraction(
        extraction_id=staged.id,
        reviewer_id=sample_user.id,
        auto_materialize=False,
    )

    result = await review_service.materialize_extraction(staged.id)
    assert result.success is True

    db = review_service.db
    revision_result = await db.execute(
        select(RelationRevision)
        .where(RelationRevision.relation_id == result.materialized_relation_id)
        .where(RelationRevision.is_current == True)  # noqa: E712
    )
    revision = revision_result.scalar_one()

    roles_result = await db.execute(
        select(RelationRoleRevision)
        .where(RelationRoleRevision.relation_revision_id == revision.id)
    )
    roles = list(roles_result.scalars().all())

    assert len(roles) == 2
    assert all(r.role_type == "participant" for r in roles)


# === Test Review Edge Cases (not found) ===


@pytest.mark.asyncio
async def test_approve_extraction_not_found(review_service, sample_user):
    """approve_extraction returns failure result for unknown ID."""
    result = await review_service.approve_extraction(
        extraction_id=uuid4(),
        reviewer_id=sample_user.id,
    )
    assert result.success is False
    assert result.error is not None


@pytest.mark.asyncio
async def test_reject_extraction_not_found(review_service, sample_user):
    """reject_extraction returns False for unknown ID."""
    success = await review_service.reject_extraction(
        extraction_id=uuid4(),
        reviewer_id=sample_user.id,
    )
    assert success is False


@pytest.mark.asyncio
async def test_delete_extraction_not_found(review_service):
    """delete_extraction returns False for unknown ID."""
    deleted = await review_service.delete_extraction(uuid4())
    assert deleted is False


# === Test Additional list_extractions Filters ===


@pytest.mark.asyncio
async def test_list_extractions_filter_by_type(
    review_service, sample_source, high_confidence_entity, high_confidence_validation,
    entity_slugs_in_db, high_confidence_relation
):
    """Should return only extractions matching the requested extraction_type."""
    from app.schemas.staged_extraction import StagedExtractionFilters

    await review_service.stage_extraction(
        ExtractionType.ENTITY, high_confidence_entity, sample_source.id,
        high_confidence_validation, auto_materialize=True,
    )
    await review_service.stage_extraction(
        ExtractionType.RELATION, high_confidence_relation, sample_source.id,
        high_confidence_validation, auto_materialize=True,
    )

    entities, _ = await review_service.list_extractions(
        StagedExtractionFilters(extraction_type="entity", page_size=10)
    )
    assert all(e.extraction_type == ExtractionType.ENTITY for e in entities)

    relations, _ = await review_service.list_extractions(
        StagedExtractionFilters(extraction_type="relation", page_size=10)
    )
    assert all(r.extraction_type == ExtractionType.RELATION for r in relations)


@pytest.mark.asyncio
async def test_list_extractions_filter_by_source(
    review_service, sample_source, db_session, sample_user,
    uncertain_entity, uncertain_validation
):
    """Should return only extractions from the specified source."""
    from app.models.source import Source
    from app.models.source_revision import SourceRevision
    from app.schemas.staged_extraction import StagedExtractionFilters

    # Create a second source
    source2 = Source(id=uuid4())
    db_session.add(source2)
    await db_session.flush()
    db_session.add(SourceRevision(
        id=uuid4(), source_id=source2.id,
        kind="study", title="Another Document", url="test://other",
        is_current=True, created_by_user_id=sample_user.id,
    ))
    await db_session.commit()

    await review_service.stage_extraction(
        ExtractionType.ENTITY, uncertain_entity, sample_source.id,
        uncertain_validation, auto_materialize=False,
    )
    await review_service.stage_extraction(
        ExtractionType.ENTITY,
        ExtractedEntity(
            slug="other-entity", category="drug",
            summary="Entity from another source document for testing",
            text_span="other source text", confidence="medium",
        ),
        source2.id, uncertain_validation, auto_materialize=False,
    )

    results, count = await review_service.list_extractions(
        StagedExtractionFilters(source_id=sample_source.id, page_size=10)
    )
    assert count == 1
    assert results[0].source_id == sample_source.id


@pytest.mark.asyncio
async def test_list_extractions_filter_has_no_flags(
    review_service, sample_source,
    high_confidence_entity, uncertain_entity,
    high_confidence_validation, uncertain_validation
):
    """has_flags=False should return only extractions with empty validation_flags."""
    from app.schemas.staged_extraction import StagedExtractionFilters

    await review_service.stage_extraction(
        ExtractionType.ENTITY, high_confidence_entity, sample_source.id,
        high_confidence_validation, auto_materialize=True,
    )
    await review_service.stage_extraction(
        ExtractionType.ENTITY, uncertain_entity, sample_source.id,
        uncertain_validation, auto_materialize=True,
    )

    results, count = await review_service.list_extractions(
        StagedExtractionFilters(has_flags=False, page_size=10)
    )
    assert count >= 1
    assert all(len(e.validation_flags) == 0 for e in results)


@pytest.mark.asyncio
async def test_list_extractions_pagination(
    review_service, sample_source, uncertain_validation
):
    """Pagination should return the correct page and total count."""
    from app.schemas.staged_extraction import StagedExtractionFilters

    for i in range(5):
        await review_service.stage_extraction(
            ExtractionType.ENTITY,
            ExtractedEntity(
                slug=f"paged-entity-{i}", category="drug",
                summary=f"Entity {i} created for pagination testing purposes",
                text_span="affecting serotonin levels", confidence="medium",
            ),
            sample_source.id, uncertain_validation, auto_materialize=False,
        )

    page1, total = await review_service.list_extractions(
        StagedExtractionFilters(
            status="pending", page=1, page_size=3,
            sort_by="created_at", sort_order="asc",
        )
    )
    page2, _ = await review_service.list_extractions(
        StagedExtractionFilters(
            status="pending", page=2, page_size=3,
            sort_by="created_at", sort_order="asc",
        )
    )

    assert total >= 5
    assert len(page1) == 3
    assert len(page2) >= 2
    # Pages should not overlap
    page1_ids = {e.id for e in page1}
    page2_ids = {e.id for e in page2}
    assert page1_ids.isdisjoint(page2_ids)


@pytest.mark.asyncio
async def test_list_extractions_sort_by_validation_score(
    review_service, sample_source, high_confidence_entity, uncertain_entity,
    high_confidence_validation, uncertain_validation
):
    """sort_by=validation_score desc should return highest score first."""
    from app.schemas.staged_extraction import StagedExtractionFilters

    await review_service.stage_extraction(
        ExtractionType.ENTITY, high_confidence_entity, sample_source.id,
        high_confidence_validation, auto_materialize=True,
    )
    await review_service.stage_extraction(
        ExtractionType.ENTITY, uncertain_entity, sample_source.id,
        uncertain_validation, auto_materialize=True,
    )

    results, _ = await review_service.list_extractions(
        StagedExtractionFilters(sort_by="validation_score", sort_order="desc", page_size=10)
    )
    scores = [e.validation_score for e in results]
    assert scores == sorted(scores, reverse=True)


# === Test Batch Review with Reject Decision ===


@pytest.mark.asyncio
async def test_batch_review_reject_multiple(
    review_service, sample_source, sample_user, uncertain_validation
):
    """Batch reject should update all targeted extractions to REJECTED."""
    from sqlalchemy import select

    staged_list = []
    for i in range(3):
        staged, _ = await review_service.stage_extraction(
            extraction_type=ExtractionType.ENTITY,
            extraction_data=ExtractedEntity(
                slug=f"reject-entity-{i}", category="drug",
                summary=f"Entity {i} for batch rejection workflow testing",
                text_span="affecting serotonin levels", confidence="medium",
            ),
            source_id=sample_source.id,
            validation_result=uncertain_validation,
            auto_materialize=True,
        )
        staged_list.append(staged)

    result = await review_service.batch_review(
        extraction_ids=[s.id for s in staged_list],
        decision="reject",
        reviewer_id=sample_user.id,
        notes="Batch rejection",
    )

    assert result.succeeded == 3
    assert result.failed == 0

    for staged in staged_list:
        db_result = await review_service.db.execute(
            select(StagedExtraction).where(StagedExtraction.id == staged.id)
        )
        updated = db_result.scalar_one()
        assert updated.status == ExtractionStatus.REJECTED


# ---------------------------------------------------------------------------
# DF-RVW-M1: rejected extractions soft-delete the materialized entity/relation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reject_entity_extraction_sets_is_rejected(
    review_service, sample_source, sample_user, low_confidence_entity, low_confidence_validation
):
    """Rejecting an entity extraction sets is_rejected=True on the entity."""
    staged, entity_id = await review_service.stage_extraction(
        extraction_type=ExtractionType.ENTITY,
        extraction_data=low_confidence_entity,
        source_id=sample_source.id,
        validation_result=low_confidence_validation,
        llm_model="test-model",
        llm_provider="test",
        auto_materialize=True,
    )

    ok = await review_service.reject_extraction(
        extraction_id=staged.id,
        reviewer_id=sample_user.id,
    )
    assert ok is True

    from sqlalchemy import select
    result = await review_service.db.execute(select(Entity).where(Entity.id == entity_id))
    entity = result.scalar_one()
    assert entity.is_rejected is True


@pytest.mark.asyncio
async def test_rejected_entity_hidden_from_list_query(
    review_service, sample_source, sample_user, low_confidence_entity, low_confidence_validation
):
    """Rejected entity does not appear in the standard list query."""
    from sqlalchemy import select
    from app.models.entity_revision import EntityRevision

    staged, entity_id = await review_service.stage_extraction(
        extraction_type=ExtractionType.ENTITY,
        extraction_data=low_confidence_entity,
        source_id=sample_source.id,
        validation_result=low_confidence_validation,
        llm_model="test-model",
        llm_provider="test",
        auto_materialize=True,
    )
    await review_service.reject_extraction(
        extraction_id=staged.id,
        reviewer_id=sample_user.id,
    )

    # Standard list query (entity_query_builder pattern) must not return it
    list_result = await review_service.db.execute(
        select(Entity, EntityRevision)
        .join(EntityRevision, Entity.id == EntityRevision.entity_id)
        .where(EntityRevision.is_current == True)  # noqa: E712
        .where(Entity.is_rejected == False)  # noqa: E712
        .where(Entity.id == entity_id)
    )
    assert list_result.first() is None


@pytest.mark.asyncio
async def test_rejected_entity_still_accessible_by_direct_id(
    review_service, sample_source, sample_user, low_confidence_entity, low_confidence_validation
):
    """Rejected entity remains accessible by direct ID lookup for audit purposes."""
    from sqlalchemy import select

    staged, entity_id = await review_service.stage_extraction(
        extraction_type=ExtractionType.ENTITY,
        extraction_data=low_confidence_entity,
        source_id=sample_source.id,
        validation_result=low_confidence_validation,
        llm_model="test-model",
        llm_provider="test",
        auto_materialize=True,
    )
    await review_service.reject_extraction(
        extraction_id=staged.id,
        reviewer_id=sample_user.id,
    )

    # Direct ID lookup without is_rejected filter still returns the entity
    result = await review_service.db.execute(select(Entity).where(Entity.id == entity_id))
    entity = result.scalar_one_or_none()
    assert entity is not None
    assert entity.is_rejected is True


@pytest.mark.asyncio
async def test_approve_extraction_does_not_set_is_rejected(
    review_service, sample_source, sample_user, uncertain_entity, uncertain_validation
):
    """Approving an extraction must leave is_rejected=False."""
    from sqlalchemy import select

    staged, entity_id = await review_service.stage_extraction(
        extraction_type=ExtractionType.ENTITY,
        extraction_data=uncertain_entity,
        source_id=sample_source.id,
        validation_result=uncertain_validation,
        llm_model="test-model",
        llm_provider="test",
        auto_materialize=True,
    )
    await review_service.approve_extraction(
        extraction_id=staged.id,
        reviewer_id=sample_user.id,
    )

    result = await review_service.db.execute(select(Entity).where(Entity.id == entity_id))
    entity = result.scalar_one()
    assert entity.is_rejected is False

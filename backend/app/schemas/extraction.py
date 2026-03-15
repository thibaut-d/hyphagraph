from typing import Literal

from pydantic import BaseModel, Field

from app.llm.schemas import ExtractedClaim, ExtractedEntity, ExtractedRelation


class TextExtractionRequest(BaseModel):
    """Request schema for text-based extraction."""

    text: str = Field(
        ...,
        description="Text to extract knowledge from",
        min_length=10,
        max_length=50000,
    )
    min_confidence: Literal["high", "medium", "low"] | None = Field(
        None,
        description="Minimum confidence level for results (filters out lower confidence)",
    )


class EntityExtractionRequest(TextExtractionRequest):
    """Request schema for entity extraction."""


class ExtractionStatusResponse(BaseModel):
    """Response schema for extraction service status."""

    status: Literal["ready", "unavailable"]
    available: bool
    message: str
    provider: str | None
    model: str | None


class EntityExtractionResponse(BaseModel):
    """Response schema for entity extraction."""

    entities: list[ExtractedEntity]
    count: int = Field(..., description="Number of entities extracted")
    text_length: int = Field(..., description="Length of input text in characters")


class RelationExtractionEntity(BaseModel):
    """Entity payload used as extraction context for relation extraction."""

    slug: str
    summary: str | None = None
    category: str | None = None


class RelationExtractionRequest(TextExtractionRequest):
    """Request schema for relation extraction."""

    entities: list[RelationExtractionEntity] = Field(
        ...,
        description="List of entities to find relations between (with slug, summary, category)",
    )


class RelationExtractionResponse(BaseModel):
    """Response schema for relation extraction."""

    relations: list[ExtractedRelation]
    count: int = Field(..., description="Number of relations extracted")
    text_length: int = Field(..., description="Length of input text in characters")


class ClaimExtractionRequest(TextExtractionRequest):
    """Request schema for claim extraction."""

    min_evidence_strength: Literal["strong", "moderate", "weak", "anecdotal"] | None = Field(
        None,
        description="Minimum evidence strength for results",
    )


class ClaimExtractionResponse(BaseModel):
    """Response schema for claim extraction."""

    claims: list[ExtractedClaim]
    count: int = Field(..., description="Number of claims extracted")
    text_length: int = Field(..., description="Length of input text in characters")


class BatchExtractionRequest(TextExtractionRequest):
    """Request schema for batch extraction."""

    min_evidence_strength: Literal["strong", "moderate", "weak", "anecdotal"] | None = Field(
        None,
        description="Minimum evidence strength for claims",
    )


class BatchExtractionResponse(BaseModel):
    """Response schema for batch extraction."""

    entities: list[ExtractedEntity]
    relations: list[ExtractedRelation]
    claims: list[ExtractedClaim]
    entity_count: int
    relation_count: int
    claim_count: int
    text_length: int

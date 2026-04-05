from typing import TypedDict
from uuid import UUID
from app.models.source import Source
from app.models.source_revision import SourceRevision
from app.schemas.source import SourceWrite, SourceRead, SourceRevisionRead


class SourceRevisionPayload(TypedDict, total=False):
    kind: str
    title: str
    authors: list[str] | None
    year: int | None
    origin: str | None
    url: str
    trust_level: float | None
    calculated_trust_level: float | None
    summary: dict[str, str] | None
    source_metadata: dict[str, object] | None
    created_with_llm: str | None
    created_by_user_id: UUID | None


def source_revision_from_write(payload: SourceWrite) -> SourceRevisionPayload:
    """
    Convert SourceWrite payload to SourceRevision data dict.

    Returns a dict (not ORM instance) for flexibility with revision helpers.
    """
    return {
        "kind": payload.kind,
        "title": payload.title,
        "authors": payload.authors,
        "year": payload.year,
        "origin": payload.origin,
        "url": payload.url,
        "trust_level": payload.trust_level,
        "calculated_trust_level": payload.calculated_trust_level,
        "summary": payload.summary,
        "source_metadata": payload.source_metadata,
        "created_with_llm": payload.created_with_llm,
    }


def source_to_read(
    source: Source,
    current_revision: SourceRevision | None = None,
    *,
    graph_usage_count: int = 0,
) -> SourceRead:
    """
    ORM → Read

    Combines base source + current revision data.
    Falls back to deprecated fields if no revision exists.
    """
    if current_revision:
        return SourceRead(
            id=source.id,
            created_at=source.created_at,
            kind=current_revision.kind,
            title=current_revision.title,
            authors=current_revision.authors,
            year=current_revision.year,
            origin=current_revision.origin,
            url=current_revision.url,
            trust_level=current_revision.trust_level,
            summary=current_revision.summary,
            source_metadata=current_revision.source_metadata,
            created_with_llm=current_revision.created_with_llm,
            created_by_user_id=current_revision.created_by_user_id,
            status=current_revision.status,
            llm_review_status=current_revision.llm_review_status,
            document_format=current_revision.document_format,
            document_file_name=current_revision.document_file_name,
            document_extracted_at=current_revision.document_extracted_at,
            graph_usage_count=graph_usage_count,
        )
    else:
        raise ValueError(f"Source {source.id} has no current revision")


def source_revision_to_read(revision: SourceRevision) -> SourceRevisionRead:
    """Convert SourceRevision ORM to SourceRevisionRead schema."""
    return SourceRevisionRead(
        id=revision.id,
        source_id=revision.source_id,
        kind=revision.kind,
        title=revision.title,
        authors=revision.authors,
        year=revision.year,
        origin=revision.origin,
        url=revision.url,
        trust_level=revision.trust_level,
        summary=revision.summary,
        source_metadata=revision.source_metadata,
        created_with_llm=revision.created_with_llm,
        created_by_user_id=revision.created_by_user_id,
        created_at=revision.created_at,
        is_current=revision.is_current,
        status=revision.status,
        llm_review_status=revision.llm_review_status,
    )

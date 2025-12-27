from app.models.source import Source
from app.models.source_revision import SourceRevision
from app.schemas.source import SourceWrite, SourceRead, SourceRevisionRead


def source_revision_from_write(payload: SourceWrite) -> dict:
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
        "summary": payload.summary,
        "source_metadata": payload.source_metadata,
        "created_with_llm": payload.created_with_llm,
    }


def source_to_read(source: Source, current_revision: SourceRevision = None) -> SourceRead:
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
        )
    else:
        # Fallback to legacy fields (for old data)
        return SourceRead(
            id=source.id,
            created_at=source.created_at,
            kind=source.kind or "",
            title=source.title or "",
            authors=None,
            year=source.year,
            origin=source.origin,
            url=source.url or "",
            trust_level=source.trust_level,
            summary=None,
            source_metadata=None,
        )


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
    )
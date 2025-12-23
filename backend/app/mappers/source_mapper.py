from app.models.source import Source
from app.schemas.source import SourceWrite, SourceRead


def source_from_write(payload: SourceWrite) -> Source:
    return Source(
        kind=payload.kind,
        title=payload.title,
        year=payload.year,
        origin=payload.origin,
        url=payload.url,
        trust_level=payload.trust_level,
    )


def source_to_read(source: Source) -> SourceRead:
    return SourceRead(
        id=source.id,
        kind=source.kind,
        title=source.title,
        year=source.year,
        origin=source.origin,
        url=source.url,
        trust_level=source.trust_level,
    )
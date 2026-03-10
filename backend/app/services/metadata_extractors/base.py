"""
Base protocol for metadata extraction strategies.

Defines the interface that all metadata extractors must implement.
"""
from typing import Protocol
from app.schemas.source import SourceMetadataSuggestion


class MetadataExtractor(Protocol):
    """
    Protocol for metadata extraction strategies.

    Each extractor is responsible for:
    1. Detecting if it can handle a given URL (can_handle)
    2. Extracting structured metadata from that URL (extract_metadata)
    3. Declaring its priority for selection (get_priority)
    4. Identifying the source types it supports (get_source_types)
    """

    async def can_handle(self, url: str) -> bool:
        """
        Check if this extractor can handle the given URL.

        Args:
            url: The URL to check

        Returns:
            True if this extractor can process the URL, False otherwise
        """
        ...

    async def extract_metadata(self, url: str) -> SourceMetadataSuggestion:
        """
        Extract metadata from URL and return standardized suggestion.

        Args:
            url: The URL to extract metadata from

        Returns:
            SourceMetadataSuggestion with extracted metadata

        Raises:
            AppException: If extraction fails
        """
        ...

    def get_priority(self) -> int:
        """
        Return priority for extractor selection.

        Lower values = higher priority. Used to order extractors
        when multiple extractors can handle a URL.

        Returns:
            Priority as integer (0-100, where 0 is highest priority)
        """
        ...

    def get_source_types(self) -> list[str]:
        """
        Return list of source type identifiers this extractor supports.

        Returns:
            List of source type strings (e.g., ['pubmed', 'pmc'])
        """
        ...

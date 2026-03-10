"""
Factory for selecting appropriate metadata extractor based on URL.

Manages extractor instances and delegates metadata extraction to the
appropriate extractor based on URL pattern matching and priority.
"""
import logging
from typing import TYPE_CHECKING

from app.schemas.source import SourceMetadataSuggestion
from app.utils.errors import AppException, ErrorCode

if TYPE_CHECKING:
    from app.services.metadata_extractors.base import MetadataExtractor

logger = logging.getLogger(__name__)


class MetadataExtractorFactory:
    """
    Factory for selecting appropriate metadata extractor based on URL.

    Maintains a registry of extractors ordered by priority and delegates
    metadata extraction to the first extractor that can handle the URL.
    """

    def __init__(self):
        """
        Initialize factory with default extractors.

        Extractors are automatically ordered by priority (lower = higher priority).
        """
        # Import here to avoid circular dependencies
        from app.services.metadata_extractors.pubmed_extractor import PubMedMetadataExtractor
        from app.services.metadata_extractors.generic_extractor import GenericUrlMetadataExtractor

        # Register extractors (will be sorted by priority)
        self.extractors: list["MetadataExtractor"] = [
            PubMedMetadataExtractor(),
            GenericUrlMetadataExtractor(),  # Fallback - always last
        ]

        # Sort by priority (lower number = higher priority)
        self.extractors.sort(key=lambda x: x.get_priority())

        logger.info(
            f"Initialized MetadataExtractorFactory with {len(self.extractors)} extractors"
        )

    async def get_extractor(self, url: str) -> "MetadataExtractor":
        """
        Find first extractor that can handle the URL.

        Extractors are checked in priority order until one matches.

        Args:
            url: The URL to find an extractor for

        Returns:
            MetadataExtractor that can handle the URL

        Raises:
            AppException: If no extractor can handle the URL (should never happen
                         since GenericUrlMetadataExtractor is fallback)
        """
        for extractor in self.extractors:
            if await extractor.can_handle(url):
                logger.info(
                    f"Selected {extractor.__class__.__name__} for URL: {url[:50]}..."
                )
                return extractor

        # This should never happen since GenericUrlMetadataExtractor accepts all URLs
        raise AppException(
            status_code=500,
            error_code=ErrorCode.INTERNAL_SERVER_ERROR,
            message="No metadata extractor found",
            details="No extractor could handle the URL",
            context={"url": url},
        )

    async def extract_metadata(self, url: str) -> SourceMetadataSuggestion:
        """
        Convenience method: find extractor and extract metadata in one call.

        Args:
            url: The URL to extract metadata from

        Returns:
            SourceMetadataSuggestion with extracted metadata

        Raises:
            AppException: If extraction fails
        """
        extractor = await self.get_extractor(url)
        return await extractor.extract_metadata(url)

    def get_supported_source_types(self) -> set[str]:
        """
        Get all source types supported by registered extractors.

        Returns:
            Set of source type strings
        """
        source_types = set()
        for extractor in self.extractors:
            source_types.update(extractor.get_source_types())
        return source_types

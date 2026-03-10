"""
Generic URL metadata extractor.

Fallback extractor for any URL not handled by specialized extractors.
Uses HTML parsing to extract basic metadata.
"""
import logging
from app.schemas.source import SourceMetadataSuggestion
from app.services.url_fetcher import UrlFetcher
from app.utils.source_quality import website_trust_level

logger = logging.getLogger(__name__)


class GenericUrlMetadataExtractor:
    """
    Generic metadata extractor for web URLs.

    Fallback extractor that uses HTML parsing to extract basic metadata
    from any web page. Always accepts URLs (lowest priority extractor).
    """

    def __init__(self):
        """Initialize generic extractor with URL fetcher instance."""
        self.url_fetcher = UrlFetcher()

    async def can_handle(self, url: str) -> bool:
        """
        Check if URL can be handled.

        Always returns True as this is the fallback extractor.

        Args:
            url: The URL to check

        Returns:
            Always True (fallback accepts all URLs)
        """
        return True

    async def extract_metadata(self, url: str) -> SourceMetadataSuggestion:
        """
        Extract metadata from generic web URL.

        Args:
            url: Web page URL

        Returns:
            SourceMetadataSuggestion with basic metadata

        Raises:
            AppException: If URL fetching or parsing fails
        """
        logger.info(f"Extracting metadata from generic URL: {url[:50]}...")

        # Fetch and parse URL content
        fetch_result = await self.url_fetcher.fetch_url(url)

        # Detect kind based on URL patterns
        kind = self._detect_kind(url)

        # Apply generic website trust level
        trust_level = website_trust_level()

        return SourceMetadataSuggestion(
            url=url,
            title=fetch_result.title or url,  # Fallback to URL if no title
            kind=kind,
            trust_level=trust_level,
            source_metadata={
                "source": "generic_url",
                "char_count": fetch_result.char_count,
                "truncated": fetch_result.truncated,
            },
        )

    def _detect_kind(self, url: str) -> str:
        """
        Detect source kind based on URL patterns.

        Args:
            url: The URL to analyze

        Returns:
            Suggested kind ('video', 'article', or 'website')
        """
        url_lower = url.lower()

        if "youtube.com" in url_lower or "youtu.be" in url_lower:
            return "video"
        elif ".pdf" in url_lower or "arxiv.org" in url_lower:
            return "article"
        else:
            return "website"

    def get_priority(self) -> int:
        """
        Return priority for generic extractor.

        Returns:
            100 (lowest priority - fallback extractor)
        """
        return 100

    def get_source_types(self) -> list[str]:
        """
        Return supported source types.

        Returns:
            List containing 'website', 'article', 'video' (generic types)
        """
        return ["website", "article", "video"]

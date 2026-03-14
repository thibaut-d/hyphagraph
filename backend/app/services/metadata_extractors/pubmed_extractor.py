"""
PubMed metadata extractor.

Extracts structured metadata from PubMed article URLs using NCBI E-utilities API.
"""
import logging

from app.schemas.source import SourceMetadataSuggestion
from app.services.pubmed_fetcher import PubMedFetcher
from app.utils.errors import ValidationException
from app.utils.source_quality import infer_trust_level_from_pubmed_metadata

logger = logging.getLogger(__name__)


class PubMedMetadataExtractor:
    """
    Metadata extractor for PubMed articles.

    Uses PubMedFetcher to fetch article metadata from NCBI E-utilities API
    and converts it to SourceMetadataSuggestion format for source creation autofill.
    """

    def __init__(self):
        """Initialize PubMed extractor with fetcher instance."""
        self.pubmed_fetcher = PubMedFetcher()

    async def can_handle(self, url: str) -> bool:
        """
        Check if URL is a valid PubMed URL.

        Args:
            url: The URL to check

        Returns:
            True if URL contains a valid PMID, False otherwise
        """
        pmid = self.pubmed_fetcher.extract_pmid_from_url(url)
        return pmid is not None

    async def extract_metadata(self, url: str) -> SourceMetadataSuggestion:
        """
        Extract metadata from PubMed URL.

        Args:
            url: PubMed article URL

        Returns:
            SourceMetadataSuggestion with article metadata

        Raises:
            AppException: If PMID extraction or API fetch fails
        """
        # Extract PMID from URL
        pmid = self.pubmed_fetcher.extract_pmid_from_url(url)
        if not pmid:
            raise ValidationException(
                message="Invalid PubMed URL",
                field="url",
            )

        logger.info(f"Extracting metadata for PubMed article PMID: {pmid}")

        # Fetch article metadata via E-utilities API
        article = await self.pubmed_fetcher.fetch_by_pmid(pmid)

        # Calculate trust level based on publication metadata
        trust_level = infer_trust_level_from_pubmed_metadata(
            title=article.title,
            journal=article.journal,
            year=article.year,
            abstract=article.abstract,
        )

        # Convert to SourceMetadataSuggestion format
        return SourceMetadataSuggestion(
            url=article.url,
            title=article.title,
            authors=article.authors,
            year=article.year,
            origin=article.journal,
            kind="article",
            trust_level=trust_level,
            summary_en=article.abstract,
            source_metadata={
                "pmid": article.pmid,
                "doi": article.doi,
                "source": "pubmed",
            },
        )

    def get_priority(self) -> int:
        """
        Return priority for PubMed extractor.

        Returns:
            10 (high priority - specific academic source)
        """
        return 10

    def get_source_types(self) -> list[str]:
        """
        Return supported source types.

        Returns:
            List containing 'pubmed'
        """
        return ["pubmed"]

"""
PubMed E-utilities API integration for fetching medical literature.

Uses NCBI's official E-utilities API to fetch PubMed articles, abstracts,
and metadata. This is the recommended way to access PubMed programmatically.

API Documentation: https://www.ncbi.nlm.nih.gov/books/NBK25501/
"""
import logging
import re
import asyncio
from dataclasses import dataclass
from urllib.parse import urlparse, parse_qs
import httpx
import xml.etree.ElementTree as ET

from app.utils.errors import (
    AppException,
    ErrorCode,
    ValidationException,
)

logger = logging.getLogger(__name__)


def _load_pmc_fetcher():
    """
    Load the optional PMC fetcher lazily.

    PMC enrichment is a secondary enhancement step on top of PubMed metadata.
    Keeping this behind a dedicated loader makes the optional dependency
    explicit without hiding the late binding inside the request flow.
    """
    from app.services.pmc_fetcher import PMCFetcher

    return PMCFetcher


@dataclass
class PubMedArticle:
    """PubMed article data extracted from E-utilities API."""
    pmid: str
    title: str
    abstract: str | None
    authors: list[str]
    journal: str | None
    year: int | None
    doi: str | None
    url: str
    full_text: str  # Combined title + abstract for extraction


class PubMedFetcher:
    """
    Service for fetching PubMed articles using NCBI E-utilities API.

    Uses efetch to retrieve article metadata and abstracts in XML format.
    """

    # E-utilities base URL
    EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    # Timeout for API requests
    TIMEOUT_SECONDS = 30

    # User agent for API requests (NCBI requests identification)
    USER_AGENT = "HyphaGraph/1.0 (Knowledge Extraction; mailto:admin@example.com)"

    def extract_pmid_from_url(self, url: str) -> str | None:
        """
        Extract PubMed ID (PMID) from a PubMed URL.

        Supports formats:
        - https://pubmed.ncbi.nlm.nih.gov/12345678/
        - https://www.ncbi.nlm.nih.gov/pubmed/12345678
        - https://pubmed.ncbi.nlm.nih.gov/12345678

        Args:
            url: PubMed URL

        Returns:
            PMID as string, or None if not found
        """
        # Match various PubMed URL formats
        patterns = [
            r'pubmed\.ncbi\.nlm\.nih\.gov/(\d+)',
            r'ncbi\.nlm\.nih\.gov/pubmed/(\d+)',
            r'pubmed/(\d+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        return None

    async def fetch_by_pmid(self, pmid: str, skip_pmc_enrichment: bool = False) -> PubMedArticle:
        """
        Fetch PubMed article by PMID using E-utilities API.

        Args:
            pmid: PubMed ID (e.g., "30280642")
            skip_pmc_enrichment: If True, skip PMC full-text enrichment for speed (default False)

        Returns:
            PubMedArticle with extracted data

        Raises:
            HTTPException: If API request fails or article not found
        """
        try:
            # Build efetch URL
            url = (
                f"{self.EUTILS_BASE}/efetch.fcgi"
                f"?db=pubmed"
                f"&id={pmid}"
                f"&retmode=xml"
                f"&rettype=abstract"
            )

            # Make API request
            async with httpx.AsyncClient(
                timeout=self.TIMEOUT_SECONDS,
                headers={"User-Agent": self.USER_AGENT}
            ) as client:
                logger.info(f"Fetching PubMed article PMID {pmid}")
                response = await client.get(url)
                response.raise_for_status()

                # Parse XML response
                xml_content = response.text
                article = self._parse_pubmed_xml(xml_content, pmid)

                logger.info(
                    f"Successfully fetched PMID {pmid}: "
                    f"'{article.title[:50]}...'"
                )

                # Try to enrich with PMC full text if available (unless skipped)
                if not skip_pmc_enrichment:
                    try:
                        pmc_fetcher = _load_pmc_fetcher()()
                        pmc_article = await pmc_fetcher.fetch_by_pmid(pmid)

                        if pmc_article:
                            # Replace abstract-only full_text with PMC full text
                            article.full_text = pmc_article.full_text
                            logger.info(
                                f"✅ Enriched PMID {pmid} with PMC full text: "
                                f"{pmc_article.char_count} chars ({len(pmc_article.sections)} sections)"
                            )
                    except Exception as e:
                        # PMC enrichment is optional - don't fail if it doesn't work
                        logger.debug(f"PMC enrichment not available for PMID {pmid}: {e}")

                return article

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching PMID {pmid}: {e.response.status_code}")
            raise AppException(
                status_code=502,
                error_code=ErrorCode.DOCUMENT_FETCH_FAILED,
                message="Failed to fetch PubMed article",
                details=f"HTTP {e.response.status_code} error while fetching PMID {pmid}",
                context={"pmid": pmid, "http_status": e.response.status_code}
            )
        except httpx.TimeoutException:
            logger.error(f"Timeout fetching PMID {pmid}")
            raise AppException(
                status_code=504,
                error_code=ErrorCode.DOCUMENT_FETCH_FAILED,
                message="PubMed request timeout",
                details=f"Request timeout after {self.TIMEOUT_SECONDS}s for PMID {pmid}",
                context={"pmid": pmid, "timeout_seconds": self.TIMEOUT_SECONDS}
            )
        except httpx.RequestError as e:
            logger.error(f"Request error fetching PMID {pmid}: {e}")
            raise AppException(
                status_code=502,
                error_code=ErrorCode.DOCUMENT_FETCH_FAILED,
                message="Failed to fetch PubMed article",
                details=f"Network error: {str(e)}",
                context={"pmid": pmid}
            )
        except AppException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching PMID {pmid}: {e}")
            raise AppException(
                status_code=500,
                error_code=ErrorCode.INTERNAL_SERVER_ERROR,
                message="Failed to process PubMed article",
                details=str(e),
                context={"pmid": pmid}
            )

    async def fetch_by_url(self, url: str) -> PubMedArticle:
        """
        Fetch PubMed article by URL.

        Extracts PMID from URL and fetches article data.

        Args:
            url: PubMed URL

        Returns:
            PubMedArticle with extracted data

        Raises:
            HTTPException: If URL is invalid or fetch fails
        """
        pmid = self.extract_pmid_from_url(url)
        if not pmid:
            raise ValidationException(
                message="Invalid PubMed URL",
                details=f"Could not extract PMID from URL: {url}",
                context={"url": url}
            )

        return await self.fetch_by_pmid(pmid)

    def _parse_pubmed_xml(self, xml_content: str, pmid: str) -> PubMedArticle:
        """
        Parse PubMed XML response from E-utilities.

        Args:
            xml_content: XML response from efetch
            pmid: PubMed ID (for error messages)

        Returns:
            PubMedArticle with extracted data

        Raises:
            HTTPException: If XML parsing fails or article not found
        """
        try:
            root = ET.fromstring(xml_content)

            # Find the PubmedArticle element
            article_elem = root.find('.//PubmedArticle')
            if article_elem is None:
                raise AppException(
                    status_code=404,
                    error_code=ErrorCode.NOT_FOUND,
                    message="PubMed article not found",
                    details=f"Article with PMID {pmid} does not exist or is not available",
                    context={"pmid": pmid}
                )

            # Extract title
            title_elem = article_elem.find('.//ArticleTitle')
            title = title_elem.text if title_elem is not None and title_elem.text else "Untitled"

            # Extract abstract (may have multiple parts)
            abstract_parts = []
            abstract_elem = article_elem.find('.//Abstract')
            if abstract_elem is not None:
                for text_elem in abstract_elem.findall('.//AbstractText'):
                    # Get label if present (e.g., "BACKGROUND", "METHODS")
                    label = text_elem.get('Label')
                    text = text_elem.text or ""

                    # Only add non-empty text
                    if text:
                        if label:
                            abstract_parts.append(f"{label}: {text}")
                        else:
                            abstract_parts.append(text)

            abstract = "\n\n".join(abstract_parts) if abstract_parts else None

            # Extract authors
            authors = []
            author_list = article_elem.find('.//AuthorList')
            if author_list is not None:
                for author in author_list.findall('.//Author'):
                    last_name = author.find('LastName')
                    fore_name = author.find('ForeName')

                    if last_name is not None and last_name.text:
                        if fore_name is not None and fore_name.text:
                            authors.append(f"{fore_name.text} {last_name.text}")
                        else:
                            authors.append(last_name.text)

            # Extract journal
            journal_elem = article_elem.find('.//Journal/Title')
            journal = journal_elem.text if journal_elem is not None and journal_elem.text else None

            # Extract year
            year = None
            year_elem = article_elem.find('.//PubDate/Year')
            if year_elem is not None and year_elem.text:
                try:
                    year = int(year_elem.text)
                except (ValueError, TypeError):
                    pass

            # Extract DOI
            doi = None
            for article_id in article_elem.findall('.//ArticleId'):
                if article_id.get('IdType') == 'doi' and article_id.text:
                    doi = article_id.text
                    break

            # Build full text for extraction (title + abstract)
            full_text_parts = [title]
            if abstract:
                full_text_parts.append("\n\nAbstract:\n" + abstract)
            full_text = "\n".join(full_text_parts)

            # Build URL
            url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"

            return PubMedArticle(
                pmid=pmid,
                title=title,
                abstract=abstract,
                authors=authors,
                journal=journal,
                year=year,
                doi=doi,
                url=url,
                full_text=full_text
            )

        except ET.ParseError as e:
            logger.error(f"XML parse error for PMID {pmid}: {e}")
            raise AppException(
                status_code=500,
                error_code=ErrorCode.DOCUMENT_PARSE_ERROR,
                message="Failed to parse PubMed XML",
                details=str(e),
                context={"pmid": pmid}
            )
        except AppException:
            raise
        except Exception as e:
            logger.error(f"Error parsing PubMed XML for PMID {pmid}: {e}")
            raise AppException(
                status_code=500,
                error_code=ErrorCode.DOCUMENT_PARSE_ERROR,
                message="Failed to extract article data",
                details=str(e),
                context={"pmid": pmid}
            )

    def extract_query_from_search_url(self, url: str) -> str | None:
        """
        Extract search query from PubMed search URL.

        Supports URLs like:
        - https://pubmed.ncbi.nlm.nih.gov/?term=cancer+AND+2024[pdat]
        - https://pubmed.ncbi.nlm.nih.gov/?term=aspirin&filter=years.2020-2024

        Args:
            url: PubMed search URL from web interface

        Returns:
            Search query string, or None if not found
        """
        try:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)

            # The 'term' parameter contains the search query
            if 'term' in params:
                return params['term'][0]

            return None
        except Exception as e:
            logger.error(f"Error extracting query from URL {url}: {e}")
            return None

    async def search_pubmed(
        self,
        query: str,
        max_results: int = 20,
        retstart: int = 0
    ) -> tuple[list[str], int]:
        """
        Search PubMed using esearch API.

        Args:
            query: PubMed search query (e.g., "cancer AND 2024[pdat]")
            max_results: Maximum number of PMIDs to return (default 20, max 10000)
            retstart: Starting index for pagination (default 0)

        Returns:
            Tuple of (pmid_list, total_count)
            - pmid_list: List of PMIDs matching the query
            - total_count: Total number of results available

        Raises:
            HTTPException: If search request fails
        """
        try:
            # Build esearch URL
            url = (
                f"{self.EUTILS_BASE}/esearch.fcgi"
                f"?db=pubmed"
                f"&term={query}"
                f"&retmax={min(max_results, 10000)}"
                f"&retstart={retstart}"
                f"&retmode=xml"
                f"&usehistory=y"
            )

            # Make API request
            async with httpx.AsyncClient(
                timeout=self.TIMEOUT_SECONDS,
                headers={"User-Agent": self.USER_AGENT}
            ) as client:
                logger.info(f"Searching PubMed: '{query}' (max_results={max_results})")
                response = await client.get(url)
                response.raise_for_status()

                # Parse XML response
                xml_content = response.text
                root = ET.fromstring(xml_content)

                # Extract PMIDs
                pmids = []
                for id_elem in root.findall('.//Id'):
                    if id_elem.text:
                        pmids.append(id_elem.text)

                # Get total count
                count_elem = root.find('.//Count')
                total_count = int(count_elem.text) if count_elem is not None and count_elem.text else 0

                logger.info(
                    f"PubMed search found {total_count} results, "
                    f"returning {len(pmids)} PMIDs"
                )

                return pmids, total_count

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error searching PubMed: {e.response.status_code}")
            raise AppException(
                status_code=502,
                error_code=ErrorCode.DOCUMENT_FETCH_FAILED,
                message="Failed to search PubMed",
                details=f"HTTP {e.response.status_code} error",
                context={"query": query, "http_status": e.response.status_code}
            )
        except httpx.TimeoutException:
            logger.error(f"Timeout searching PubMed: {query}")
            raise AppException(
                status_code=504,
                error_code=ErrorCode.DOCUMENT_FETCH_FAILED,
                message="PubMed search timeout",
                details=f"Request timeout after {self.TIMEOUT_SECONDS}s",
                context={"query": query, "timeout_seconds": self.TIMEOUT_SECONDS}
            )
        except httpx.RequestError as e:
            logger.error(f"Request error searching PubMed: {e}")
            raise AppException(
                status_code=502,
                error_code=ErrorCode.DOCUMENT_FETCH_FAILED,
                message="Failed to search PubMed",
                details=str(e),
                context={"query": query}
            )
        except AppException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error searching PubMed: {e}")
            raise AppException(
                status_code=500,
                error_code=ErrorCode.INTERNAL_SERVER_ERROR,
                message="Failed to process PubMed search",
                details=str(e),
                context={"query": query}
            )

    async def bulk_fetch_articles(
        self,
        pmids: list[str],
        rate_limit_delay: float = 0.34,
        skip_pmc_enrichment: bool = False
    ) -> list[PubMedArticle]:
        """
        Fetch multiple PubMed articles with rate limiting.

        NCBI guidelines:
        - Without API key: 3 requests per second (0.33s delay)
        - With API key: 10 requests per second (0.1s delay)

        Args:
            pmids: List of PubMed IDs to fetch
            rate_limit_delay: Delay between requests in seconds (default 0.34 for ~3 req/sec)
            skip_pmc_enrichment: If True, skip PMC full-text enrichment for speed (default False)

        Returns:
            List of PubMedArticle objects (may be shorter if some fetches fail)

        Note:
            Failed article fetches are logged but don't stop the entire operation.
        """
        articles = []
        total = len(pmids)

        logger.info(f"Bulk fetching {total} PubMed articles (rate limit: {1/rate_limit_delay:.1f} req/s)")

        for i, pmid in enumerate(pmids, 1):
            try:
                article = await self.fetch_by_pmid(pmid, skip_pmc_enrichment=skip_pmc_enrichment)
                articles.append(article)

                logger.info(f"Progress: {i}/{total} articles fetched")

                # Rate limiting (except for last request)
                if i < total:
                    await asyncio.sleep(rate_limit_delay)

            except AppException as e:
                logger.warning(f"Failed to fetch PMID {pmid}: {e.detail}")
                # Continue with next article
                continue
            except Exception as e:
                logger.warning(f"Unexpected error fetching PMID {pmid}: {e}")
                continue

        logger.info(f"Bulk fetch complete: {len(articles)}/{total} articles successfully fetched")

        return articles

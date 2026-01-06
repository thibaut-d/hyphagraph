"""
PubMed E-utilities API integration for fetching medical literature.

Uses NCBI's official E-utilities API to fetch PubMed articles, abstracts,
and metadata. This is the recommended way to access PubMed programmatically.

API Documentation: https://www.ncbi.nlm.nih.gov/books/NBK25501/
"""
import logging
import re
from dataclasses import dataclass
import httpx
import xml.etree.ElementTree as ET
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


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

    async def fetch_by_pmid(self, pmid: str) -> PubMedArticle:
        """
        Fetch PubMed article by PMID using E-utilities API.

        Args:
            pmid: PubMed ID (e.g., "30280642")

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

                return article

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching PMID {pmid}: {e.response.status_code}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to fetch PubMed article (HTTP {e.response.status_code}): PMID {pmid}"
            )
        except httpx.TimeoutException:
            logger.error(f"Timeout fetching PMID {pmid}")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=f"Request timeout after {self.TIMEOUT_SECONDS}s: PMID {pmid}"
            )
        except httpx.RequestError as e:
            logger.error(f"Request error fetching PMID {pmid}: {e}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to fetch PubMed article: {str(e)}"
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching PMID {pmid}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to process PubMed article: {str(e)}"
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
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not extract PMID from URL: {url}"
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
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Article not found: PMID {pmid}"
                )

            # Extract title
            title_elem = article_elem.find('.//ArticleTitle')
            title = title_elem.text if title_elem is not None else "Untitled"

            # Extract abstract (may have multiple parts)
            abstract_parts = []
            abstract_elem = article_elem.find('.//Abstract')
            if abstract_elem is not None:
                for text_elem in abstract_elem.findall('.//AbstractText'):
                    # Get label if present (e.g., "BACKGROUND", "METHODS")
                    label = text_elem.get('Label')
                    text = text_elem.text or ""

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

                    if last_name is not None:
                        if fore_name is not None:
                            authors.append(f"{fore_name.text} {last_name.text}")
                        else:
                            authors.append(last_name.text)

            # Extract journal
            journal_elem = article_elem.find('.//Journal/Title')
            journal = journal_elem.text if journal_elem is not None else None

            # Extract year
            year = None
            year_elem = article_elem.find('.//PubDate/Year')
            if year_elem is not None:
                try:
                    year = int(year_elem.text)
                except ValueError:
                    pass

            # Extract DOI
            doi = None
            for article_id in article_elem.findall('.//ArticleId'):
                if article_id.get('IdType') == 'doi':
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
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to parse PubMed XML: {str(e)}"
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error parsing PubMed XML for PMID {pmid}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to extract article data: {str(e)}"
            )

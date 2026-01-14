"""
PubMed Central (PMC) fetcher for full-text articles.

PMC provides free access to full-text articles in the Open Access subset.
This service attempts to fetch full text when available, falling back to
abstract if not in PMC OA.

API Documentation: https://pmc.ncbi.nlm.nih.gov/tools/oa-service/
"""
import logging
import httpx
import xml.etree.ElementTree as ET
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PMCFullText:
    """PMC full-text article data."""
    pmcid: str  # PMC ID (e.g., "PMC12345678")
    pmid: str  # PubMed ID
    title: str
    abstract: str | None
    full_text: str  # Complete article text
    sections: dict[str, str]  # Section title -> content
    char_count: int
    is_open_access: bool


class PMCFetcher:
    """
    Service for fetching full-text articles from PubMed Central.

    PMC Open Access subset provides ~30-40% coverage of PubMed articles.
    """

    # PMC OA Web Service base URL
    PMC_BASE = "https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi"

    # Timeout for API requests
    TIMEOUT_SECONDS = 30

    # User agent
    USER_AGENT = "HyphaGraph/1.0 (Knowledge Extraction; mailto:admin@example.com)"

    async def check_pmc_availability(self, pmid: str) -> str | None:
        """
        Check if article is available in PMC Open Access subset.

        Args:
            pmid: PubMed ID

        Returns:
            PMCID if available, None otherwise
        """
        try:
            # Use PMC ID Converter API (updated URL as of 2026)
            url = f"https://pmc.ncbi.nlm.nih.gov/tools/idconv/api/v1/articles/?ids={pmid}&format=json"

            async with httpx.AsyncClient(
                timeout=self.TIMEOUT_SECONDS,
                headers={"User-Agent": self.USER_AGENT},
                follow_redirects=True  # Handle any redirects
            ) as client:
                logger.info(f"Checking PMC availability for PMID {pmid}")
                response = await client.get(url)
                response.raise_for_status()

                data = response.json()
                records = data.get("records", [])

                if records and len(records) > 0:
                    record = records[0]

                    # Check if record has error
                    if record.get("status") == "error":
                        logger.info(f"Article PMID {pmid} not found in PMC")
                        return None

                    pmcid = record.get("pmcid")

                    if pmcid:
                        logger.info(f"Article PMID {pmid} available in PMC as {pmcid}")
                        return pmcid

                logger.info(f"Article PMID {pmid} not in PMC")
                return None

        except Exception as e:
            logger.warning(f"Failed to check PMC availability for PMID {pmid}: {e}")
            return None

    async def fetch_full_text(self, pmcid: str) -> PMCFullText | None:
        """
        Fetch full text from PMC using BioC format.

        BioC provides structured full text with sections.

        Args:
            pmcid: PMC ID (e.g., "PMC12345678")

        Returns:
            PMCFullText if successful, None otherwise
        """
        try:
            # Use BioC API for structured full text
            url = f"{self.PMC_BASE}/BioC_json/{pmcid}/unicode"

            async with httpx.AsyncClient(
                timeout=self.TIMEOUT_SECONDS,
                headers={"User-Agent": self.USER_AGENT}
            ) as client:
                logger.info(f"Fetching full text for {pmcid} from PMC")
                response = await client.get(url)
                response.raise_for_status()

                data = response.json()

                # Parse BioC JSON format
                # Response can be a dict with "documents" or a list
                if isinstance(data, list):
                    documents = data
                else:
                    documents = data.get("documents", [])
                if not documents:
                    logger.warning(f"No documents in PMC response for {pmcid}")
                    return None

                doc = documents[0]
                passages = doc.get("passages", [])

                # Extract title and abstract
                title = ""
                abstract = ""
                sections = {}
                full_text_parts = []

                for passage in passages:
                    section_type = passage.get("infons", {}).get("section_type", "body")
                    text = passage.get("text", "")

                    if section_type == "TITLE" or section_type == "title":
                        title = text
                    elif section_type == "ABSTRACT" or section_type == "abstract":
                        abstract = text
                    else:
                        # Body sections
                        section_name = passage.get("infons", {}).get("type", "body")
                        sections[section_name] = text
                        full_text_parts.append(text)

                # Combine all text
                full_text = title + "\n\n" + abstract + "\n\n" + "\n\n".join(full_text_parts)

                # Get PMID from annotations
                pmid = doc.get("infons", {}).get("article-id_pmid", "")

                result = PMCFullText(
                    pmcid=pmcid,
                    pmid=pmid,
                    title=title,
                    abstract=abstract,
                    full_text=full_text.strip(),
                    sections=sections,
                    char_count=len(full_text),
                    is_open_access=True
                )

                logger.info(
                    f"Successfully fetched full text for {pmcid}: "
                    f"{result.char_count} characters ({len(sections)} sections)"
                )

                return result

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching PMC {pmcid}: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Failed to fetch full text for {pmcid}: {e}")
            return None

    async def fetch_by_pmid(self, pmid: str) -> PMCFullText | None:
        """
        Fetch full text for a PubMed article (if available in PMC OA).

        Args:
            pmid: PubMed ID

        Returns:
            PMCFullText if available, None if not in PMC OA subset
        """
        # Check if article is in PMC
        pmcid = await self.check_pmc_availability(pmid)

        if not pmcid:
            return None

        # Fetch full text
        return await self.fetch_full_text(pmcid)

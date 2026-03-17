"""
URL fetching service for web-based document extraction.

Fetches content from URLs (PubMed, web pages, etc.) and extracts text.
Supports HTML parsing and basic text extraction.
"""
import logging
from dataclasses import dataclass
import httpx
from bs4 import BeautifulSoup

from app.utils.errors import (
    AppException,
    ErrorCode,
)

logger = logging.getLogger(__name__)


@dataclass
class UrlFetchResult:
    """Result of URL content fetching."""
    text: str
    url: str
    title: str | None
    char_count: int
    truncated: bool
    warnings: list[str]


class UrlFetcher:
    """
    Service for fetching and extracting text from URLs.

    Supports:
    - PubMed articles (extracts abstract and main content)
    - General web pages (extracts text from HTML)
    """

    # Constants
    MAX_TEXT_LENGTH = 50000  # Characters (~10-15 pages)
    TIMEOUT_SECONDS = 30
    MAX_RESPONSE_SIZE_MB = 10

    # User agent to identify our requests (browser-like to avoid blocking)
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    REQUEST_HEADERS = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    async def fetch_url(
        self,
        url: str,
        max_length: int | None = None
    ) -> UrlFetchResult:
        """
        Fetch and extract text from a URL.

        Args:
            url: The URL to fetch
            max_length: Maximum text length (defaults to MAX_TEXT_LENGTH)

        Returns:
            UrlFetchResult with extracted text and metadata

        Raises:
            AppException: If fetching or parsing fails
        """
        max_len = max_length or self.MAX_TEXT_LENGTH
        warnings: list[str] = []

        try:
            response = await self._fetch_response(url)
            self._validate_html_content_type(response, url)
            self._validate_response_size(response, url)

            extracted_text, title = self._extract_text_from_html(response.text, url)
            extracted_text, was_truncated, truncation_warnings = self._truncate_text(
                extracted_text,
                max_len,
            )
            warnings.extend(truncation_warnings)

            logger.info(
                f"Successfully fetched {url}: "
                f"{len(extracted_text)} chars, title='{title}'"
            )

            return UrlFetchResult(
                text=extracted_text,
                url=url,
                title=title,
                char_count=len(extracted_text),
                truncated=was_truncated,
                warnings=warnings
            )

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching {url}: {e.response.status_code}")
            raise AppException(
                status_code=502,
                error_code=ErrorCode.DOCUMENT_FETCH_FAILED,
                message="Failed to fetch URL",
                details=f"HTTP {e.response.status_code} error",
                context={"url": url, "http_status": e.response.status_code}
            )
        except httpx.TimeoutException:
            logger.error(f"Timeout fetching {url}")
            raise AppException(
                status_code=504,
                error_code=ErrorCode.DOCUMENT_FETCH_FAILED,
                message="URL fetch timeout",
                details=f"Request timeout after {self.TIMEOUT_SECONDS}s",
                context={"url": url, "timeout_seconds": self.TIMEOUT_SECONDS}
            )
        except httpx.RequestError as e:
            logger.error(f"Request error fetching {url}: {e}")
            raise AppException(
                status_code=502,
                error_code=ErrorCode.DOCUMENT_FETCH_FAILED,
                message="Failed to fetch URL",
                details=str(e),
                context={"url": url}
            )
        except AppException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching {url}: {e}")
            raise AppException(
                status_code=500,
                error_code=ErrorCode.INTERNAL_SERVER_ERROR,
                message="Failed to process URL",
                details=str(e),
                context={"url": url}
            )

    async def _fetch_response(self, url: str) -> httpx.Response:
        logger.info(f"Fetching URL: {url}")
        async with httpx.AsyncClient(
            timeout=self.TIMEOUT_SECONDS,
            headers=self.REQUEST_HEADERS,
            follow_redirects=True
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response

    def _validate_html_content_type(self, response: httpx.Response, url: str) -> None:
        content_type = response.headers.get("content-type", "").lower()
        if "html" in content_type:
            return

        raise AppException(
            status_code=415,
            error_code=ErrorCode.DOCUMENT_UNSUPPORTED_FORMAT,
            message="Unsupported content type",
            details=f"Content type '{content_type}' is not supported. Only HTML pages are supported.",
            context={"content_type": content_type, "url": url}
        )

    def _validate_response_size(self, response: httpx.Response, url: str) -> None:
        content_size_bytes = len(response.content)
        max_size_bytes = self.MAX_RESPONSE_SIZE_MB * 1024 * 1024
        if content_size_bytes <= max_size_bytes:
            return

        content_size_mb = content_size_bytes / 1024 / 1024
        raise AppException(
            status_code=413,
            error_code=ErrorCode.DOCUMENT_TOO_LARGE,
            message="Response too large",
            details=(
                f"Response size {content_size_mb:.1f}MB exceeds maximum "
                f"of {self.MAX_RESPONSE_SIZE_MB}MB"
            ),
            context={
                "size_mb": content_size_mb,
                "max_mb": self.MAX_RESPONSE_SIZE_MB,
                "url": url,
            }
        )

    def _truncate_text(self, text: str, max_length: int) -> tuple[str, bool, list[str]]:
        if len(text) <= max_length:
            return text, False, []

        warning = (
            f"Content truncated to {max_length} characters "
            f"(~10-15 pages) for processing"
        )
        return text[:max_length], True, [warning]

    def _extract_text_from_html(self, html: str, url: str) -> tuple[str, str | None]:
        """
        Extract text from HTML content.

        Handles:
        - PubMed articles (abstract + main content)
        - General web pages (main content)

        Args:
            html: HTML content
            url: Original URL (for format detection)

        Returns:
            Tuple of (extracted_text, page_title)
        """
        soup = BeautifulSoup(html, "html.parser")

        # Get page title
        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else None

        # PubMed-specific extraction
        if "pubmed.ncbi.nlm.nih.gov" in url.lower():
            return self._extract_pubmed_text(soup), title

        # General web page extraction
        return self._extract_general_text(soup), title

    def _extract_pubmed_text(self, soup: BeautifulSoup) -> str:
        """
        Extract text from PubMed article page.

        Extracts:
        - Article title
        - Abstract
        - Full text if available

        Args:
            soup: BeautifulSoup parsed HTML

        Returns:
            Extracted text content
        """
        parts = []

        # Title (usually in h1.heading-title or similar)
        title = soup.find("h1", class_="heading-title")
        if title:
            parts.append(title.get_text(strip=True))

        # Abstract
        abstract_div = soup.find("div", class_="abstract-content")
        if not abstract_div:
            # Try alternative selectors
            abstract_div = soup.find("div", id="abstract")
            if not abstract_div:
                abstract_div = soup.find("abstract")

        if abstract_div:
            abstract_text = abstract_div.get_text(separator="\n", strip=True)
            parts.append("\n\nAbstract:\n" + abstract_text)

        # Full text if available (usually in article body)
        article_body = soup.find("div", class_="article-body")
        if not article_body:
            article_body = soup.find("div", class_="full-text")

        if article_body:
            body_text = article_body.get_text(separator="\n", strip=True)
            parts.append("\n\nFull Text:\n" + body_text)

        text = "\n".join(parts)

        if not text.strip():
            # Fallback: get all paragraph text
            paragraphs = soup.find_all("p")
            text = "\n\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))

        return text

    def _extract_general_text(self, soup: BeautifulSoup) -> str:
        """
        Extract text from general web page.

        Removes scripts, styles, and navigation elements.

        Args:
            soup: BeautifulSoup parsed HTML

        Returns:
            Extracted text content
        """
        # Remove unwanted elements
        for element in soup(["script", "style", "nav", "header", "footer", "aside"]):
            element.decompose()

        # Try to find main content area
        main_content = soup.find("main") or soup.find("article") or soup.find("div", class_="content")

        if main_content:
            text = main_content.get_text(separator="\n", strip=True)
        else:
            # Fallback: get all text
            text = soup.get_text(separator="\n", strip=True)

        # Clean up excessive whitespace
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        text = "\n\n".join(lines)

        return text

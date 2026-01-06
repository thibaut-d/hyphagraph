# URL Fetching for Document Extraction

## Overview

The `UrlFetcher` service allows fetching content from web URLs for knowledge extraction. This is useful for extracting information from online articles, documentation, and research papers.

## Usage

```python
from app.services.url_fetcher import UrlFetcher

fetcher = UrlFetcher()
result = await fetcher.fetch_url("https://example.com/article")

# Result contains:
# - text: Extracted text content
# - title: Page title
# - url: Original URL
# - char_count: Number of characters
# - truncated: Whether content was truncated
# - warnings: Any warnings during fetching
```

## Limitations

### PubMed and NCBI

**IMPORTANT**: Direct web scraping of PubMed (pubmed.ncbi.nlm.nih.gov) is blocked by NCBI.

For PubMed articles, use the official NCBI E-utilities API instead:
- **E-utilities API**: https://www.ncbi.nlm.nih.gov/books/NBK25501/
- **PubMed Central API**: https://www.ncbi.nlm.nih.gov/pmc/tools/developers/

Example using E-utilities to fetch PubMed abstract:
```bash
# Fetch abstract for PMID 30280642
curl "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=30280642&retmode=xml&rettype=abstract"
```

### Other Protected Sites

Many websites use anti-bot protection (Cloudflare, etc.) that may block automated requests. For these sites:

1. **Use official APIs** when available (preferred)
2. **Respect robots.txt** and terms of service
3. **Add delays** between requests if scraping is permitted
4. **Consider alternatives** like RSS feeds or public datasets

## Supported Sites

The URL fetcher works best with:
- Open access publications
- Documentation sites without anti-bot protection
- Internal/corporate knowledge bases
- Simple web pages and blogs
- News articles (check terms of service)

## Implementation Details

### Headers

The fetcher uses browser-like headers to avoid basic bot detection:
- User-Agent: Chrome browser string
- Accept: Standard browser accept headers
- Accept-Language, Accept-Encoding, etc.

### Extraction

- **PubMed/PMC**: Attempts to extract title + abstract + full text
- **General pages**: Extracts main content, removes nav/header/footer
- **Fallback**: Extracts all paragraph text if specific selectors fail

### Limits

- **Timeout**: 30 seconds
- **Max size**: 10 MB
- **Max text**: 50,000 characters (~10-15 pages)
- Content exceeding limits is truncated with a warning

## PubMed E-utilities API (Implemented!)

For PubMed articles, use the `PubMedFetcher` service which uses the official NCBI E-utilities API:

```python
from app.services.pubmed_fetcher import PubMedFetcher

fetcher = PubMedFetcher()

# Fetch by PMID
article = await fetcher.fetch_by_pmid("23953482")

# Fetch by URL (extracts PMID automatically)
article = await fetcher.fetch_by_url("https://pubmed.ncbi.nlm.nih.gov/23953482/")

# Article contains:
# - pmid, title, abstract, authors, journal, year, doi, url
# - full_text: Combined title + abstract for extraction
```

Supported URL formats:
- `https://pubmed.ncbi.nlm.nih.gov/12345678/`
- `https://www.ncbi.nlm.nih.gov/pubmed/12345678`
- `pubmed/12345678`

## Future Improvements

- [ ] Add support for PDF URLs (download + extract)
- [ ] Add rate limiting for bulk URL fetching
- [ ] Add caching layer for repeated URLs
- [ ] Support for authentication/cookies for protected content
- [ ] Implement retry logic with exponential backoff
- [ ] Add support for PubMed Central full-text articles
- [ ] Add support for batch fetching multiple PMIDs

"""
Metadata extraction strategies for various source types.

Provides a factory-based system for extracting metadata from URLs:
- PubMed articles (NCBI E-utilities API)
- Generic web pages (HTML parsing)

Future extractors can be added by implementing the MetadataExtractor protocol.
"""
from app.services.metadata_extractors.base import MetadataExtractor
from app.services.metadata_extractors.factory import MetadataExtractorFactory
from app.services.metadata_extractors.pubmed_extractor import PubMedMetadataExtractor
from app.services.metadata_extractors.generic_extractor import GenericUrlMetadataExtractor

__all__ = [
    "MetadataExtractor",
    "MetadataExtractorFactory",
    "PubMedMetadataExtractor",
    "GenericUrlMetadataExtractor",
]

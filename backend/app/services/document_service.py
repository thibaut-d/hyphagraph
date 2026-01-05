"""
Document processing service for uploaded files.

Handles text extraction from PDFs and plain text files, with validation
and error handling for file uploads.
"""
import logging
from dataclasses import dataclass
from fastapi import UploadFile, HTTPException, status
from pypdf import PdfReader
import io

logger = logging.getLogger(__name__)


@dataclass
class DocumentExtractionResult:
    """Result of document text extraction."""
    text: str
    format: str  # pdf, txt, etc.
    filename: str
    char_count: int
    truncated: bool
    warnings: list[str]


class DocumentService:
    """
    Service for processing uploaded documents.

    Supports PDF and plain text file extraction with validation.
    """

    # Constants
    MAX_FILE_SIZE_MB = 10
    MAX_TEXT_LENGTH = 50000  # Characters (~10-15 pages)
    SUPPORTED_FORMATS = {
        "application/pdf": "pdf",
        "text/plain": "txt",
    }

    def validate_file(
        self,
        file: UploadFile,
        max_size_mb: int | None = None
    ) -> None:
        """
        Validate uploaded file format and size.

        Args:
            file: The uploaded file to validate
            max_size_mb: Maximum file size in MB (defaults to MAX_FILE_SIZE_MB)

        Raises:
            HTTPException: If file is invalid (wrong format, too large, etc.)
        """
        max_size = (max_size_mb or self.MAX_FILE_SIZE_MB) * 1024 * 1024

        # Check content type
        if file.content_type not in self.SUPPORTED_FORMATS:
            supported = ", ".join(self.SUPPORTED_FORMATS.keys())
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Unsupported file type: {file.content_type}. "
                       f"Supported types: {supported}"
            )

        # Check file size (if available in headers)
        if file.size and file.size > max_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large: {file.size / 1024 / 1024:.1f}MB. "
                       f"Maximum size: {max_size_mb or self.MAX_FILE_SIZE_MB}MB"
            )

    async def extract_text_from_pdf(self, file: UploadFile) -> str:
        """
        Extract text from PDF file.

        Args:
            file: PDF file to extract text from

        Returns:
            Extracted text content

        Raises:
            HTTPException: If PDF extraction fails
        """
        try:
            # Read file content
            content = await file.read()
            pdf_file = io.BytesIO(content)

            # Extract text from all pages
            reader = PdfReader(pdf_file)
            text_parts = []

            for page in reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)

            # Combine all pages
            full_text = "\n\n".join(text_parts)

            if not full_text.strip():
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="PDF contains no extractable text. "
                           "It may be a scanned image or encrypted."
                )

            return full_text

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"PDF text extraction failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to extract text from PDF: {str(e)}"
            )

    async def extract_text_from_txt(self, file: UploadFile) -> str:
        """
        Extract text from plain text file.

        Args:
            file: Text file to read

        Returns:
            File content as string

        Raises:
            HTTPException: If text reading fails
        """
        try:
            content = await file.read()

            # Try UTF-8 first, fall back to Latin-1 if that fails
            try:
                text = content.decode("utf-8")
            except UnicodeDecodeError:
                logger.warning(f"UTF-8 decode failed for {file.filename}, trying Latin-1")
                text = content.decode("latin-1")

            if not text.strip():
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Text file is empty"
                )

            return text

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Text file reading failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to read text file: {str(e)}"
            )

    async def extract_text_from_file(
        self,
        file: UploadFile
    ) -> DocumentExtractionResult:
        """
        Extract text from uploaded file (router method).

        Automatically detects file type and calls appropriate extraction method.
        Handles truncation for very long documents.

        Args:
            file: The uploaded file

        Returns:
            DocumentExtractionResult with text and metadata

        Raises:
            HTTPException: If extraction fails or file type unsupported
        """
        # Validate file first
        self.validate_file(file)

        # Get format from content type
        file_format = self.SUPPORTED_FORMATS.get(file.content_type)
        if not file_format:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Unsupported file type: {file.content_type}"
            )

        # Extract text based on format
        if file_format == "pdf":
            text = await self.extract_text_from_pdf(file)
        elif file_format == "txt":
            text = await self.extract_text_from_txt(file)
        else:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Unsupported format: {file_format}"
            )

        # Check for truncation
        truncated = False
        warnings = []

        if len(text) > self.MAX_TEXT_LENGTH:
            truncated = True
            text = text[:self.MAX_TEXT_LENGTH]
            warnings.append(
                f"Document truncated to {self.MAX_TEXT_LENGTH} characters "
                f"(~10-15 pages) for processing"
            )

        # Build result
        return DocumentExtractionResult(
            text=text,
            format=file_format,
            filename=file.filename or "unknown",
            char_count=len(text),
            truncated=truncated,
            warnings=warnings
        )

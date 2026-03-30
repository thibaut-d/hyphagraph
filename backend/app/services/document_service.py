"""
Document processing service for uploaded files.

Handles text extraction from PDFs and plain text files, with validation
and error handling for file uploads.
"""
import logging
from dataclasses import dataclass
from fastapi import UploadFile
from pypdf import PdfReader
import io

from app.utils.errors import (
    AppException,
    ErrorCode,
    ValidationException,
)

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
            raise AppException(
                status_code=415,
                error_code=ErrorCode.DOCUMENT_UNSUPPORTED_FORMAT,
                message="Unsupported file type",
                details=f"File type '{file.content_type}' is not supported. Supported types: {supported}",
                context={"file_type": file.content_type, "filename": file.filename}
            )

        # Check file size (if available in headers)
        if file.size and file.size > max_size:
            raise AppException(
                status_code=413,
                error_code=ErrorCode.DOCUMENT_TOO_LARGE,
                message="File too large",
                details=f"File size {file.size / 1024 / 1024:.1f}MB exceeds maximum of {max_size_mb or self.MAX_FILE_SIZE_MB}MB",
                context={"size_mb": file.size / 1024 / 1024, "max_mb": max_size_mb or self.MAX_FILE_SIZE_MB, "filename": file.filename}
            )

    async def _read_bounded(self, file: UploadFile, max_bytes: int) -> bytes:
        """
        Read file content up to max_bytes, raising 413 before full buffering.

        Reads in 64 KB chunks so oversized uploads are rejected as soon as the
        limit is crossed, rather than after the entire file is in memory.  This
        is needed when UploadFile.size is absent (e.g. chunked transfer encoding).
        """
        chunks: list[bytes] = []
        total = 0
        chunk_size = 64 * 1024  # 64 KB

        while True:
            chunk = await file.read(chunk_size)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                max_mb = max_bytes // (1024 * 1024)
                raise AppException(
                    status_code=413,
                    error_code=ErrorCode.DOCUMENT_TOO_LARGE,
                    message="File too large",
                    details=f"File size exceeds maximum of {max_mb}MB",
                    context={"max_mb": max_mb, "filename": file.filename},
                )
            chunks.append(chunk)

        return b"".join(chunks)

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
            max_size = self.MAX_FILE_SIZE_MB * 1024 * 1024
            content = await self._read_bounded(file, max_size)

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
                raise ValidationException(
                    message="PDF contains no extractable text",
                    details="The PDF may be a scanned image without OCR or encrypted",
                    context={"filename": file.filename}
                )

            return full_text

        except (ValidationException, AppException):
            raise
        except Exception:
            logger.exception("PDF text extraction failed for %s", file.filename)
            raise AppException(
                status_code=500,
                error_code=ErrorCode.DOCUMENT_PARSE_ERROR,
                message="Failed to extract text from PDF",
                context={"filename": file.filename}
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
            max_size = self.MAX_FILE_SIZE_MB * 1024 * 1024
            content = await self._read_bounded(file, max_size)

            # Try UTF-8 first, fall back to Latin-1 if that fails
            try:
                text = content.decode("utf-8")
            except UnicodeDecodeError:
                logger.warning(f"UTF-8 decode failed for {file.filename}, trying Latin-1")
                text = content.decode("latin-1")

            if not text.strip():
                raise ValidationException(
                    message="Text file is empty",
                    details="The uploaded text file contains no content",
                    context={"filename": file.filename}
                )

            return text

        except (ValidationException, AppException):
            raise
        except Exception:
            logger.exception("Text file reading failed for %s", file.filename)
            raise AppException(
                status_code=500,
                error_code=ErrorCode.DOCUMENT_PARSE_ERROR,
                message="Failed to read text file",
                context={"filename": file.filename}
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
            raise AppException(
                status_code=415,
                error_code=ErrorCode.DOCUMENT_UNSUPPORTED_FORMAT,
                message="Unsupported file type",
                details=f"File type '{file.content_type}' is not supported",
                context={"file_type": file.content_type, "filename": file.filename}
            )

        # Extract text based on format
        if file_format == "pdf":
            text = await self.extract_text_from_pdf(file)
        elif file_format == "txt":
            text = await self.extract_text_from_txt(file)
        else:
            raise AppException(
                status_code=415,
                error_code=ErrorCode.DOCUMENT_UNSUPPORTED_FORMAT,
                message="Unsupported format",
                details=f"Format '{file_format}' is not supported",
                context={"format": file_format, "filename": file.filename}
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

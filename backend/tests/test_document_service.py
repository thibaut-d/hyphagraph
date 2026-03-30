"""
Unit tests for DocumentService.

Focused on the bounded streaming reader and size enforcement when
UploadFile.size is absent (chunked transfer encoding / missing Content-Length).
"""
import io
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.document_service import DocumentService
from app.utils.errors import AppException, ErrorCode


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_upload_file(content: bytes, content_type: str = "text/plain", filename: str = "test.txt", size: int | None = None):
    """Build a minimal UploadFile-like mock."""
    mock_file = MagicMock()
    mock_file.filename = filename
    mock_file.content_type = content_type
    mock_file.size = size  # None simulates missing Content-Length

    # Simulate chunked reads: each call to read(n) returns the next n bytes.
    buf = io.BytesIO(content)

    async def _read(n: int = -1) -> bytes:
        return buf.read(n) if n != -1 else buf.read()

    mock_file.read = _read
    return mock_file


MAX_BYTES = DocumentService.MAX_FILE_SIZE_MB * 1024 * 1024


# ---------------------------------------------------------------------------
# _read_bounded
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestReadBounded:
    service = DocumentService()

    async def test_reads_content_within_limit(self):
        content = b"hello world"
        f = _make_upload_file(content)
        result = await self.service._read_bounded(f, MAX_BYTES)
        assert result == content

    async def test_raises_413_when_content_exceeds_limit(self):
        # One byte over the limit
        oversized = b"x" * (MAX_BYTES + 1)
        f = _make_upload_file(oversized)
        with pytest.raises(AppException) as exc_info:
            await self.service._read_bounded(f, MAX_BYTES)
        assert exc_info.value.status_code == 413
        assert exc_info.value.error_detail.code == ErrorCode.DOCUMENT_TOO_LARGE

    async def test_exactly_at_limit_is_accepted(self):
        content = b"x" * MAX_BYTES
        f = _make_upload_file(content)
        result = await self.service._read_bounded(f, MAX_BYTES)
        assert len(result) == MAX_BYTES

    async def test_empty_file_is_accepted(self):
        f = _make_upload_file(b"")
        result = await self.service._read_bounded(f, MAX_BYTES)
        assert result == b""

    async def test_raises_before_full_buffer(self):
        """Verify rejection happens mid-stream, not after reading everything.

        We patch read() to count how many bytes were actually delivered before
        the exception fires, and assert it is strictly less than the total
        oversized content length.
        """
        oversized_size = MAX_BYTES + 128 * 1024  # 128 KB over the limit
        oversized = b"x" * oversized_size
        buf = io.BytesIO(oversized)
        delivered = 0

        async def counting_read(n: int = -1) -> bytes:
            nonlocal delivered
            chunk = buf.read(n) if n != -1 else buf.read()
            delivered += len(chunk)
            return chunk

        mock_file = MagicMock()
        mock_file.filename = "big.txt"
        mock_file.read = counting_read

        with pytest.raises(AppException) as exc_info:
            await self.service._read_bounded(mock_file, MAX_BYTES)

        assert exc_info.value.status_code == 413
        # Must have stopped reading before consuming the full oversized payload
        assert delivered < oversized_size


# ---------------------------------------------------------------------------
# extract_text_from_txt — missing-size path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestExtractTextFromTxtMissingSize:
    service = DocumentService()

    async def test_rejects_oversized_txt_when_size_is_none(self):
        oversized = b"a" * (MAX_BYTES + 1)
        f = _make_upload_file(oversized, content_type="text/plain", filename="big.txt", size=None)
        with pytest.raises(AppException) as exc_info:
            await self.service.extract_text_from_txt(f)
        assert exc_info.value.status_code == 413
        assert exc_info.value.error_detail.code == ErrorCode.DOCUMENT_TOO_LARGE

    async def test_accepts_normal_txt_when_size_is_none(self):
        content = b"Hello, world."
        f = _make_upload_file(content, content_type="text/plain", filename="hello.txt", size=None)
        text = await self.service.extract_text_from_txt(f)
        assert text == "Hello, world."


# ---------------------------------------------------------------------------
# extract_text_from_pdf — missing-size path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestExtractTextFromPdfMissingSize:
    service = DocumentService()

    async def test_rejects_oversized_pdf_when_size_is_none(self):
        # A non-PDF blob that exceeds the size limit — rejection must happen
        # before the PDF parser ever sees the content.
        oversized = b"%PDF-fake" + b"x" * (MAX_BYTES + 1)
        f = _make_upload_file(oversized, content_type="application/pdf", filename="big.pdf", size=None)
        with pytest.raises(AppException) as exc_info:
            await self.service.extract_text_from_pdf(f)
        assert exc_info.value.status_code == 413
        assert exc_info.value.error_detail.code == ErrorCode.DOCUMENT_TOO_LARGE

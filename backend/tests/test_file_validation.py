"""Unit tests for upload validation, filename sanitizing, and rate limiting."""

import pytest

from app.core.file_validation import (
    FileValidationError,
    sanitize_filename,
    sniff_file_kind,
    validate_upload,
)
from app.core.rate_limit import SlidingWindowRateLimiter
from tests.fakes import build_docx


def test_sniffs_pdf_by_magic_bytes():
    assert sniff_file_kind(b"%PDF-1.7 fake body") == "pdf"


def test_sniffs_real_docx():
    assert sniff_file_kind(build_docx("Hello resume")) == "docx"


def test_rejects_plain_text_regardless_of_extension():
    assert sniff_file_kind(b"I am a resume, honest") is None
    with pytest.raises(FileValidationError, match="Unsupported file type"):
        validate_upload(b"I am a resume, honest", max_bytes=1024)


def test_rejects_zip_that_is_not_docx():
    import io
    import zipfile

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("something.txt", "not a docx")
    assert sniff_file_kind(buffer.getvalue()) is None


def test_rejects_oversized_file():
    with pytest.raises(FileValidationError, match="too large"):
        validate_upload(b"%PDF-" + b"0" * 2048, max_bytes=1024)


def test_rejects_empty_file():
    with pytest.raises(FileValidationError, match="empty"):
        validate_upload(b"", max_bytes=1024)


def test_sanitize_filename_strips_paths_and_specials():
    assert sanitize_filename("../../etc/passwd") == "passwd"
    assert sanitize_filename("my resume (final)!.pdf") == "my_resume__final__.pdf"
    assert sanitize_filename("") == "resume"


def test_rate_limiter_blocks_after_max_events():
    limiter = SlidingWindowRateLimiter(max_events=3, window_seconds=3600)
    assert [limiter.allow("u1") for _ in range(4)] == [True, True, True, False]
    # A different user is unaffected.
    assert limiter.allow("u2") is True

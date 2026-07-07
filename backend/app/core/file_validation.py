"""Upload validation: content-type by magic bytes, size limit, safe filenames.

File kind is determined by inspecting content (spec 4) — a ``.pdf`` extension
on a non-PDF payload is rejected. Only PDF and DOCX are accepted.
"""

import io
import re
import zipfile

PDF_MAGIC = b"%PDF-"
ZIP_MAGIC = b"PK\x03\x04"

CONTENT_TYPES = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


class FileValidationError(ValueError):
    """Raised with a user-facing message when an upload fails validation."""


def sniff_file_kind(data: bytes) -> str | None:
    """Return 'pdf' or 'docx' based on file content, or None if neither."""
    if data.startswith(PDF_MAGIC):
        return "pdf"
    if data.startswith(ZIP_MAGIC):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                names = set(zf.namelist())
            if "[Content_Types].xml" in names and any(
                n.startswith("word/") for n in names
            ):
                return "docx"
        except zipfile.BadZipFile:
            return None
    return None


def validate_upload(data: bytes, max_bytes: int) -> str:
    """Validate size + content type; return the detected kind or raise."""
    if not data:
        raise FileValidationError("The uploaded file is empty.")
    if len(data) > max_bytes:
        raise FileValidationError(
            f"File is too large ({len(data) / (1024 * 1024):.1f} MB). "
            f"The limit is {max_bytes // (1024 * 1024)} MB."
        )
    kind = sniff_file_kind(data)
    if kind is None:
        raise FileValidationError(
            "Unsupported file type. Please upload a PDF or DOCX resume "
            "(content is inspected — renaming the extension won't work)."
        )
    return kind


def sanitize_filename(name: str) -> str:
    """Strip path components and unsafe characters before storage."""
    base = (name or "resume").replace("\\", "/").split("/")[-1]
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", base).strip("._") or "resume"
    return cleaned[:120]

"""Content hashing used by the cache-before-Gemini strategy (spec 3.3)."""

import hashlib


def sha256_bytes(data: bytes) -> str:
    """Hash raw file bytes (resume uploads)."""
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    """Hash user-pasted text (job descriptions), whitespace-trimmed."""
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


def combined_hash(*parts: str) -> str:
    """Hash resume + JD hashes together for cross-module cache keys."""
    return hashlib.sha256(":".join(parts).encode("utf-8")).hexdigest()

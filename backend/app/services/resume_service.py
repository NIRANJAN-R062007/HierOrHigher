"""Module 5.1 — Resume Parser + Score pipeline.

Flow: validate upload → hash → cache check (spec 3.3) → extract text →
Gemini parse + human score (structured output) → rule-based ATS score →
persist → respond. Uses GEMINI_API_KEY_RESUME_PARSER for its single Gemini
call; the ATS score never touches the LLM.
"""

from app.config import get_settings
from app.core.file_validation import CONTENT_TYPES, sanitize_filename, validate_upload
from app.core.hashing import sha256_bytes
from app.core.prompts import load_prompt, wrap_untrusted
from app.models.resume import (
    ATSScore,
    HumanScore,
    ParsedResume,
    ResumeAnalysis,
    ResumeResponse,
)
from app.services.ats_scorer import score_resume
from app.services.text_extraction import extract_text


class UnparseableResumeError(ValueError):
    """Fewer than 2 structured fields extracted — ask the user to re-upload."""


def response_from_row(row: dict, *, cached: bool) -> ResumeResponse:
    """Build the module 5.1 response contract from a stored resumes row."""
    return ResumeResponse(
        resume_id=str(row["id"]),
        parsed=ParsedResume.model_validate(row["parsed_json"]),
        ats_score=ATSScore.model_validate(row["ats_score"]),
        human_score=HumanScore.model_validate(row["human_score"]),
        cached=cached,
        file_url=row.get("file_url"),
    )


def process_resume(
    user_id: str,
    file_bytes: bytes,
    filename: str,
    repo,
    gemini,
) -> ResumeResponse:
    """Parse and dual-score one uploaded resume for ``user_id``.

    Inputs: authenticated user id, raw upload bytes + original filename, a
    repository, and the resume_parser Gemini client (GEMINI_API_KEY_RESUME_PARSER).
    Returns the stored result when the identical file was processed before —
    the cache check runs BEFORE any Gemini call.
    """
    settings = get_settings()
    kind = validate_upload(file_bytes, settings.max_upload_bytes)
    content_hash = sha256_bytes(file_bytes)

    cached_row = repo.get_resume_by_hash(user_id, content_hash)
    if cached_row is not None:
        return response_from_row(cached_row, cached=True)

    raw_text = extract_text(file_bytes, kind)

    prompt = load_prompt("resume_parser") + "\n\n" + wrap_untrusted(raw_text)
    analysis: ResumeAnalysis = gemini.generate_structured(
        prompt, ResumeAnalysis, max_output_tokens=4096, temperature=0.1
    )

    field_count = analysis.parsed.structured_field_count()
    if field_count < 2:
        raise UnparseableResumeError(
            "We couldn't extract enough structure from this resume. "
            "Please re-upload a text-based PDF or DOCX version."
        )

    ats_score = score_resume(raw_text, field_count, kind)

    stored_name = f"{content_hash[:12]}_{sanitize_filename(filename)}"
    file_url = repo.upload_resume_file(
        user_id, stored_name, file_bytes, CONTENT_TYPES[kind]
    )

    row = repo.insert_resume(
        {
            "user_id": user_id,
            "file_url": file_url,
            "content_hash": content_hash,
            "parsed_json": analysis.parsed.model_dump(),
            "ats_score": ats_score.model_dump(),
            "human_score": analysis.human_score.model_dump(),
        }
    )
    return response_from_row(row, cached=False)

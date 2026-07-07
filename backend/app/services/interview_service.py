"""Module 5.3 — Mock Interview Generator.

Builds 8–10 categorized questions from module 5.1's stored parse, the stored
job description, and module 5.2's gap report (when present) — no user re-entry
of any input (spec 12). Uses GEMINI_API_KEY_INTERVIEW_GENERATOR. Caches by
sha256(resume hash + JD hash) before any Gemini call.
"""

import json

from app.core.hashing import combined_hash
from app.core.prompts import load_prompt, wrap_untrusted
from app.models.interview import (
    InterviewQuestion,
    InterviewQuestions,
    InterviewSetResponse,
)


def _response_from_row(row: dict, *, cached: bool) -> InterviewSetResponse:
    return InterviewSetResponse(
        interview_set_id=str(row["id"]),
        resume_id=str(row["resume_id"]),
        jd_id=str(row["jd_id"]),
        questions=[InterviewQuestion.model_validate(q) for q in row["questions"]],
        cached=cached,
    )


def generate_interview_set(
    user_id: str,
    resume_id: str,
    jd_id: str,
    repo,
    gemini,
) -> InterviewSetResponse:
    """Generate (or return the cached) interview set for one resume/JD pair.

    Inputs: authenticated user id, ids of the stored resume and job
    description, a repository, and the interview_generator Gemini client
    (GEMINI_API_KEY_INTERVIEW_GENERATOR). Raises LookupError (→ 404) when
    either input is missing; never re-parses the resume or the JD.
    """
    resume = repo.get_resume(user_id, resume_id)
    if resume is None:
        raise LookupError("Resume not found. Upload a resume first.")
    jd_row = repo.get_job_description(user_id, jd_id)
    if jd_row is None:
        raise LookupError("Job description not found. Run the gap mapper first.")

    cache_key = combined_hash(resume["content_hash"], jd_row["content_hash"])
    cached_row = repo.get_interview_set_by_hash(resume_id, cache_key)
    if cached_row is not None:
        return _response_from_row(cached_row, cached=True)

    # Reuse module 5.2's gap findings for the Role-Fit questions when the
    # user has already mapped this exact resume/JD pair.
    gap_row = repo.get_gap_report_by_hash(resume_id, cache_key)
    missing_skills: list[str] = gap_row["missing"] if gap_row else []

    context = (
        "PARSED RESUME (JSON):\n"
        + wrap_untrusted(json.dumps(resume["parsed_json"], ensure_ascii=False))
        + "\n\nTARGET JOB DESCRIPTION:\n"
        + wrap_untrusted(jd_row["raw_text"])
        + "\n\nIDENTIFIED MISSING SKILLS: "
        + (", ".join(missing_skills) if missing_skills else "none identified yet")
    )
    prompt = load_prompt("interview_generator") + "\n\n" + context
    generated: InterviewQuestions = gemini.generate_structured(
        prompt, InterviewQuestions, max_output_tokens=2048, temperature=0.7
    )

    row = repo.insert_interview_set(
        {
            "resume_id": resume_id,
            "jd_id": jd_id,
            "content_hash": cache_key,
            "questions": [q.model_dump() for q in generated.questions],
        }
    )
    return _response_from_row(row, cached=False)

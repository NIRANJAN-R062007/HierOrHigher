"""Module 5.4 — LinkedIn / Portfolio Optimizer.

Rewrites module 5.1's stored parse into headline/About/project copy with two
tone variants each — the resume is never re-entered or re-parsed (spec 12).
Uses GEMINI_API_KEY_PROFILE_OPTIMIZER. Caches by the resume's content hash
(this module has no JD input) before any Gemini call.
"""

import json

from app.core.prompts import load_prompt, wrap_untrusted
from app.models.profile import (
    ProfileDraftContent,
    ProfileDraftResponse,
    ProjectRewrite,
    ToneVariants,
)


def _response_from_row(row: dict, *, cached: bool) -> ProfileDraftResponse:
    return ProfileDraftResponse(
        profile_draft_id=str(row["id"]),
        resume_id=str(row["resume_id"]),
        headline=ToneVariants.model_validate(row["headline"]),
        about=ToneVariants.model_validate(row["about"]),
        project_descriptions=[
            ProjectRewrite.model_validate(p) for p in row["project_descriptions"]
        ],
        cached=cached,
    )


def generate_profile_draft(
    user_id: str,
    resume_id: str,
    repo,
    gemini,
) -> ProfileDraftResponse:
    """Generate (or return the cached) profile draft for one stored resume.

    Inputs: authenticated user id, the id of an already-parsed resume, a
    repository, and the profile_optimizer Gemini client
    (GEMINI_API_KEY_PROFILE_OPTIMIZER). Raises LookupError (→ 404) when the
    resume doesn't exist or belongs to another user.
    """
    resume = repo.get_resume(user_id, resume_id)
    if resume is None:
        raise LookupError("Resume not found. Upload a resume first.")

    cache_key = resume["content_hash"]
    cached_row = repo.get_profile_draft_by_hash(resume_id, cache_key)
    if cached_row is not None:
        return _response_from_row(cached_row, cached=True)

    prompt = (
        load_prompt("profile_optimizer")
        + "\n\nPARSED RESUME (JSON):\n"
        + wrap_untrusted(json.dumps(resume["parsed_json"], ensure_ascii=False))
    )
    content: ProfileDraftContent = gemini.generate_structured(
        prompt, ProfileDraftContent, max_output_tokens=2048, temperature=0.8
    )

    row = repo.insert_profile_draft(
        {
            "resume_id": resume_id,
            "content_hash": cache_key,
            "headline": content.headline.model_dump(),
            "about": content.about.model_dump(),
            "project_descriptions": [
                p.model_dump() for p in content.project_descriptions
            ],
        }
    )
    return _response_from_row(row, cached=False)

"""Module 5.2 — Gap-to-Job Mapper.

Compares an ALREADY-PARSED resume (module 5.1's stored output — this module
never re-parses, spec 12) against a job description using embedding-based
semantic similarity rather than keyword matching. Uses
GEMINI_API_KEY_GAP_MAPPER for both requirement extraction and embeddings.

Two callers, one matching core. ``match_resume_to_jd`` is the whole
comparison — requirement extraction plus cosine classification — expressed
purely in terms of parsed resume JSON and JD text, with no notion of who owns
either. On top of it sit:

* ``build_gap_report`` — the student-facing flow, which fetches the resume by
  ``(user_id, resume_id)`` and caches per user.
* ``application_service`` — the recruiter flow, where a candidate has no
  ``auth.uid()`` at all and the JD comes from a job posting.

Both cache by content hash before reaching Gemini; only the cache's *location*
differs (``gap_reports`` vs ``applications``), never the matching itself.
"""

import math
from typing import NamedTuple

from app.core.hashing import combined_hash, sha256_text
from app.core.prompts import load_prompt, wrap_untrusted
from app.models.gap_report import GapReportResponse, JDRequirements

# Minimum cosine similarity between a JD requirement and the closest resume
# skill for the requirement to count as matched. Tuned for
# gemini-embedding-001: semantically-equivalent skill phrases score well
# above this; unrelated skills score well below it.
MATCH_THRESHOLD = 0.72


class ResumeNotFoundError(LookupError):
    """The referenced resume doesn't exist or belongs to another user."""


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


def _resume_skill_terms(parsed_json: dict) -> list[str]:
    """Skills plus project technologies, deduplicated case-insensitively."""
    terms: list[str] = list(parsed_json.get("skills", []))
    for project in parsed_json.get("projects", []):
        terms.extend(project.get("technologies", []))
    seen: set[str] = set()
    unique = []
    for term in terms:
        key = " ".join(term.lower().split())
        if key and key not in seen:
            seen.add(key)
            unique.append(term)
    return unique


def _classify_requirements(
    requirements: list[str], skills: list[str], gemini
) -> tuple[list[str], list[str]]:
    """Split JD requirements into matched/missing by nearest-skill cosine."""
    if not requirements:
        return [], []
    if not skills:
        return [], list(requirements)

    vectors = gemini.embed(requirements + skills)
    requirement_vectors = vectors[: len(requirements)]
    skill_vectors = vectors[len(requirements):]

    matched, missing = [], []
    for requirement, req_vec in zip(requirements, requirement_vectors):
        best = max(_cosine(req_vec, skill_vec) for skill_vec in skill_vectors)
        (matched if best >= MATCH_THRESHOLD else missing).append(requirement)
    return matched, missing


def _normalize(term: str) -> str:
    return " ".join(term.lower().split())


def _group_by_category(
    matched: list[str], missing: list[str], skill_to_category: dict[str, str]
) -> dict[str, dict[str, list[str]]] | None:
    """Bucket matched/missing requirements by taxonomy category for the radar.

    Returns ``{category: {"matched": [...], "missing": [...]}}`` or ``None``
    when no requirement carried a category (nothing to plot — the UI then
    falls back to the flat matched/missing view).
    """
    grouped: dict[str, dict[str, list[str]]] = {}
    for bucket, skills in (("matched", matched), ("missing", missing)):
        for skill in skills:
            category = skill_to_category.get(_normalize(skill))
            if category is None:
                continue
            grouped.setdefault(category, {"matched": [], "missing": []})
            grouped[category][bucket].append(skill)
    return grouped or None


class MatchOutcome(NamedTuple):
    """One resume scored against one JD — the matching core's whole result.

    ``requirements`` is echoed back so callers can persist the extraction they
    just paid Gemini for and pass it in as ``cached_requirements`` next time.
    """

    requirements: list[str]
    matched: list[str]
    missing: list[str]
    match_percentage: int
    categories: dict | None


def match_resume_to_jd(
    parsed_json: dict,
    jd_text: str,
    gemini,
    *,
    cached_requirements: list[str] | None = None,
) -> MatchOutcome:
    """Score parsed resume JSON against JD text. The matching core.

    Inputs: a parsed resume (module 5.1's ``parsed_json``, whoever produced
    it), the JD text, the gap_mapper Gemini client
    (GEMINI_API_KEY_GAP_MAPPER), and optionally this JD's already-extracted
    requirements. Knows nothing about users, resumes, postings, or candidates
    — callers own fetching, caching, and persistence.

    Passing ``cached_requirements`` (including an empty list) skips
    requirement extraction entirely, saving one Gemini call. It also means no
    category tags are available for that run, since the model produces them
    alongside the extraction — the report then falls back to the flat
    matched/missing view.
    """
    skill_to_category: dict[str, str] = {}
    requirements = cached_requirements
    if requirements is None:
        prompt = load_prompt("gap_mapper") + "\n\n" + wrap_untrusted(jd_text)
        extraction: JDRequirements = gemini.generate_structured(
            prompt, JDRequirements, max_output_tokens=1024, temperature=0.0
        )
        requirements = extraction.requirements
        skill_to_category = {
            _normalize(item.skill): item.category for item in extraction.categories
        }

    skills = _resume_skill_terms(parsed_json)
    matched, missing = _classify_requirements(requirements, skills, gemini)
    match_percentage = (
        round(100 * len(matched) / len(requirements)) if requirements else 0
    )
    return MatchOutcome(
        requirements=requirements,
        matched=matched,
        missing=missing,
        match_percentage=match_percentage,
        categories=_group_by_category(matched, missing, skill_to_category),
    )


def _response_from_row(row: dict, resume_id: str, *, cached: bool) -> GapReportResponse:
    return GapReportResponse(
        gap_report_id=str(row["id"]),
        resume_id=resume_id,
        jd_id=str(row["jd_id"]),
        matched=row["matched"],
        missing=row["missing"],
        match_percentage=row["match_percentage"],
        cached=cached,
        # ``source``/``ml_score`` linger as nullable columns for gap reports
        # written while the offline ML scorer was in play; new reports are
        # always Gemini-sourced with no ml_score.
        source=row.get("source") or "gemini",
        ml_score=row.get("ml_score"),
        categories=row.get("categories"),
    )


def build_gap_report(
    user_id: str,
    resume_id: str,
    jd_text: str,
    repo,
    gemini,
) -> GapReportResponse:
    """Produce matched/missing skills + match percentage for one resume/JD pair.

    Inputs: authenticated user id, the id of an already-parsed resume, pasted
    JD text, a repository, and the gap_mapper Gemini client
    (GEMINI_API_KEY_GAP_MAPPER). The resume parse is reused as stored —
    module 5.1 is never re-run. Returns the cached report when this exact
    resume+JD content pair was mapped before.

    Every mapping runs ``match_resume_to_jd`` — the same core the recruiter
    side scores candidates with. On a cache hit for this exact resume+JD pair,
    no Gemini call is spent.
    """
    resume = repo.get_resume(user_id, resume_id)
    if resume is None:
        raise ResumeNotFoundError("Resume not found. Upload a resume first.")

    jd_hash = sha256_text(jd_text)
    cache_key = combined_hash(resume["content_hash"], jd_hash)

    cached_row = repo.get_gap_report_by_hash(resume_id, cache_key)
    if cached_row is not None:
        return _response_from_row(cached_row, resume_id, cached=True)

    # A JD this user has mapped before already has its requirements stored, so
    # the core is told to skip extraction. Category tags come out of that same
    # extraction call, so a re-used JD has none and falls back to the flat view.
    jd_row = repo.get_jd_by_hash(user_id, jd_hash)
    outcome = match_resume_to_jd(
        resume["parsed_json"],
        jd_text,
        gemini,
        cached_requirements=(jd_row["parsed_requirements"] or []) if jd_row else None,
    )

    if jd_row is None:
        jd_row = repo.insert_job_description(
            {
                "user_id": user_id,
                "raw_text": jd_text,
                "content_hash": jd_hash,
                "parsed_requirements": outcome.requirements,
            }
        )

    row = repo.insert_gap_report(
        {
            "resume_id": resume_id,
            "jd_id": jd_row["id"],
            "content_hash": cache_key,
            "matched": outcome.matched,
            "missing": outcome.missing,
            "match_percentage": outcome.match_percentage,
            "source": "gemini",
            "categories": outcome.categories,
        }
    )
    return _response_from_row(row, resume_id, cached=False)

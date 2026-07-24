"""Module 5.2 — Gap-to-Job Mapper.

Compares the ALREADY-PARSED resume (module 5.1's stored output — this module
never re-parses, spec 12) against a pasted job description using
embedding-based semantic similarity rather than keyword matching.
Uses GEMINI_API_KEY_GAP_MAPPER for both requirement extraction and
embeddings. Caches by sha256(resume hash + JD hash) before any Gemini call.
"""

import math

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

    Every mapping runs the Gemini pipeline: extract the JD's requirements,
    embed them alongside the resume's skills, and match by cosine similarity.
    On a cache hit for this exact resume+JD pair, no Gemini call is spent.
    """
    resume = repo.get_resume(user_id, resume_id)
    if resume is None:
        raise ResumeNotFoundError("Resume not found. Upload a resume first.")

    jd_hash = sha256_text(jd_text)
    cache_key = combined_hash(resume["content_hash"], jd_hash)

    cached_row = repo.get_gap_report_by_hash(resume_id, cache_key)
    if cached_row is not None:
        return _response_from_row(cached_row, resume_id, cached=True)

    # Category tags are produced alongside requirement extraction, so they're
    # available only on a fresh JD. For a JD already extracted (cache hit) we
    # skip re-spending Gemini, and the report falls back to the flat view.
    skill_to_category: dict[str, str] = {}
    jd_row = repo.get_jd_by_hash(user_id, jd_hash)
    if jd_row is None:
        prompt = load_prompt("gap_mapper") + "\n\n" + wrap_untrusted(jd_text)
        extraction: JDRequirements = gemini.generate_structured(
            prompt, JDRequirements, max_output_tokens=1024, temperature=0.0
        )
        skill_to_category = {
            _normalize(item.skill): item.category for item in extraction.categories
        }
        jd_row = repo.insert_job_description(
            {
                "user_id": user_id,
                "raw_text": jd_text,
                "content_hash": jd_hash,
                "parsed_requirements": extraction.requirements,
            }
        )
    requirements: list[str] = jd_row["parsed_requirements"] or []

    skills = _resume_skill_terms(resume["parsed_json"])
    matched, missing = _classify_requirements(requirements, skills, gemini)
    match_percentage = (
        round(100 * len(matched) / len(requirements)) if requirements else 0
    )

    row = repo.insert_gap_report(
        {
            "resume_id": resume_id,
            "jd_id": jd_row["id"],
            "content_hash": cache_key,
            "matched": matched,
            "missing": missing,
            "match_percentage": match_percentage,
            "source": "gemini",
            "categories": _group_by_category(matched, missing, skill_to_category),
        }
    )
    return _response_from_row(row, resume_id, cached=False)

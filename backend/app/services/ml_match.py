"""Bridge between module 5.2 and the offline ML match scorer.

The scorer's FeatureExtractor reads raw text, while the gap mapper works from
module 5.1's stored parse — so this module rebuilds a sectioned resume text
from ``parsed_json`` (never re-calling the parser, spec 12) and runs the
in-process model that also backs POST /ml/score.

Escalation contract: the gap mapper trusts the ML result outright unless the
model itself asks for review (``recommend_gemini_review``: confidence < 0.6
or a score in the ambiguous 45-55 band), in which case the existing
Gemini pipeline runs and no quota is saved for that pair.
"""

import logging

logger = logging.getLogger(__name__)

ESCALATION_CONFIDENCE = 0.6
AMBIGUOUS_BAND = (45.0, 55.0)


def needs_gemini_review(result: dict) -> bool:
    """The hybrid-fallback rule shared with POST /ml/score."""
    return bool(
        result["confidence"] < ESCALATION_CONFIDENCE
        or AMBIGUOUS_BAND[0] <= result["match_score"] <= AMBIGUOUS_BAND[1]
    )


def _last_year(value) -> str:
    """'2017 – 2021' -> '2021'; keeps education ranges from inflating the
    extractor's experience-years signal."""
    tail = str(value or "").replace("–", "-").split("-")[-1].strip()
    return tail


def resume_text_from_parse(parsed: dict) -> str:
    """Rebuild sectioned resume text in the layout the FeatureExtractor
    parses (SUMMARY / SKILLS / EXPERIENCE / EDUCATION / PROJECTS)."""
    contact = parsed.get("contact") or {}
    parts = [
        parsed.get("name") or "",
        " | ".join(filter(None, [contact.get("email"), contact.get("phone")])),
        "",
    ]
    if parsed.get("summary"):
        parts += ["SUMMARY", str(parsed["summary"]), ""]
    if parsed.get("skills"):
        parts += ["SKILLS", ", ".join(parsed["skills"]), ""]
    if parsed.get("experience"):
        parts.append("EXPERIENCE")
        for role in parsed["experience"]:
            dates = " - ".join(
                filter(None, [str(role.get("start_date") or ""), str(role.get("end_date") or "")])
            )
            parts.append(
                f"{role.get('title', '')} | {role.get('company', '')} | {dates}".strip(" |")
            )
            parts.extend(f"- {b}" for b in role.get("bullets", []))
        parts.append("")
    if parsed.get("education"):
        parts.append("EDUCATION")
        for edu in parsed["education"]:
            parts.append(
                f"{edu.get('degree', '')}, {edu.get('institution', '')}, "
                f"{_last_year(edu.get('year'))}".strip(", ")
            )
        parts.append("")
    if parsed.get("projects"):
        parts.append("PROJECTS")
        for project in parsed["projects"]:
            tech = ", ".join(project.get("technologies", []))
            parts.append(
                f"{project.get('name', '')}: {project.get('description', '')}"
                + (f" ({tech})" if tech else "")
            )
        parts.append("")
    return "\n".join(parts)


def score_resume_jd(scorer, parsed_json: dict, jd_text: str) -> dict | None:
    """Run the offline scorer for the gap mapper.

    Returns ``{"result": <ml/score contract + recommend_gemini_review>,
    "matched_skills": [...], "missing_skills": [...], "jd_skills": [...]}``,
    or None when the scorer is unavailable or fails — the caller then falls
    back to the Gemini pipeline (graceful degradation, never a 5xx here).
    """
    if scorer is None:
        return None
    try:
        resume_text = resume_text_from_parse(parsed_json)
        result = scorer.predict(resume_text, jd_text)
        result["recommend_gemini_review"] = needs_gemini_review(result)

        extractor = scorer.extractor
        resume_skills = extractor.extract_skills(resume_text)
        jd_skills = extractor.extract_skills(jd_text)
        return {
            "result": result,
            "matched_skills": sorted(jd_skills & resume_skills),
            "missing_skills": sorted(jd_skills - resume_skills),
            "jd_skills": sorted(jd_skills),
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("ML match scoring failed, falling back to Gemini: %s", exc)
        return None

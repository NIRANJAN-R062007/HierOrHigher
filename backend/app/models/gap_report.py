"""Module 5.2 contracts: JD requirement extraction and the gap report."""

from typing import Literal

from pydantic import BaseModel, Field

# Fixed skill taxonomy — the stable axes of the dashboard's gap radar. Gemini
# tags each extracted requirement with exactly one of these, so the radar's
# shape is comparable across resumes and job descriptions.
SkillCategoryName = Literal[
    "Languages",
    "Frameworks & Libraries",
    "Tools & Platforms",
    "Cloud & DevOps",
    "Data & ML",
    "Concepts & Soft Skills",
]

SKILL_CATEGORIES: tuple[str, ...] = SkillCategoryName.__args__


class SkillCategory(BaseModel):
    """One extracted requirement tagged with its taxonomy category."""

    skill: str
    category: SkillCategoryName


class JDRequirements(BaseModel):
    """Gemini structured-output schema for the gap_mapper module.

    ``categories`` is additive and optional: when present it tags each
    requirement with a taxonomy category (powering the gap radar). Older
    responses / dataset fixtures that omit it still validate — the report just
    falls back to the flat matched/missing view.
    """

    requirements: list[str] = Field(
        description="Concrete skills/technologies/competencies the job requires"
    )
    categories: list[SkillCategory] = Field(
        default_factory=list,
        description="Each requirement tagged with one taxonomy category",
    )


class GapReportRequest(BaseModel):
    resume_id: str
    job_description: str = Field(
        min_length=40,
        description="The pasted job description text (untrusted user input)",
    )


class GapReportListItem(BaseModel):
    """One entry in a resume's gap-report history — the cheap summary the
    history panel lists. Full matched/missing arrays are fetched on demand."""

    id: str
    jd_id: str
    match_percentage: int = Field(ge=0, le=100)
    created_at: str


class GapReportResponse(BaseModel):
    """POST /api/gap-reports response — the module 5.2 contract.

    New reports are always ``source="gemini"`` with ``ml_score=None``. Both
    fields are retained for reports written while the offline ML scorer was
    still in the loop, where ``source`` could be ``ml`` and ``ml_score``
    carried the model's output.

    ``categories`` groups the matched/missing requirements by taxonomy
    category for the gap radar — ``{category: {"matched": [...],
    "missing": [...]}}`` — or ``None`` when the model returned no categories.
    """

    gap_report_id: str
    resume_id: str
    jd_id: str
    matched: list[str]
    missing: list[str]
    match_percentage: int = Field(ge=0, le=100)
    cached: bool = False
    source: str = "gemini"
    ml_score: dict | None = None
    categories: dict | None = None

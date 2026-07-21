"""Module 5.2 contracts: JD requirement extraction and the gap report."""

from pydantic import BaseModel, Field


class JDRequirements(BaseModel):
    """Gemini structured-output schema for the gap_mapper module."""

    requirements: list[str] = Field(
        description="Concrete skills/technologies/competencies the job requires"
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

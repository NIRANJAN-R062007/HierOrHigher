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


class GapReportResponse(BaseModel):
    """POST /api/gap-reports response — the module 5.2 contract.

    ``source`` says which engine produced matched/missing: ``ml`` (confident
    offline scorer, zero Gemini quota) or ``gemini`` (embedding pipeline).
    ``ml_score`` carries the full /ml/score contract whenever the model ran.
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

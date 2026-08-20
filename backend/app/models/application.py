"""Contracts for candidate intake and the ranked screening view.

Two audiences, two shapes, and the split is a security boundary rather than a
convenience: ``ApplicationReceipt`` is returned to an unauthenticated
candidate and deliberately carries no score, no skill breakdown, and nothing
about any other applicant. ``ApplicantListItem`` — the ranked view — is only
ever served to a member of the posting's org.
"""

from pydantic import BaseModel, Field


class ApplicationReceipt(BaseModel):
    """The apply page's confirmation. Screening results are recruiter-only,
    so the candidate learns only that the submission landed."""

    application_id: str
    posting_title: str
    candidate_name: str = ""
    already_applied: bool = False


class ApplicantListItem(BaseModel):
    """One applicant on the recruiter's ranked screening list.

    ``matched``/``missing``/``categories`` come straight from the shared
    matching core, so a candidate's breakdown reads identically to a
    student's gap report for the same JD.
    """

    application_id: str
    candidate_id: str
    name: str = ""
    email: str = ""
    match_percentage: int = Field(ge=0, le=100)
    matched: list[str]
    missing: list[str]
    categories: dict | None = None
    created_at: str

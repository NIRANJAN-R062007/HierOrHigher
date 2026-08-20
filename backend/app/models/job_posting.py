"""Recruiter-side contracts: job postings and their public apply view.

A posting's ``description`` is JD text — the same input the student-facing
Gap-to-Job Mapper takes — so the identical matching core scores candidates
against it (see app/services/gap_service.py).

Two response shapes on purpose: ``JobPostingResponse`` is what a signed-in org
member sees, and ``PublicJobPosting`` is the strictly smaller projection an
unauthenticated visitor gets on /apply/{posting_id}. Nothing about the org's
other postings, its members, or anyone else's application is reachable there.
"""

from typing import Literal

from pydantic import BaseModel, Field, computed_field, field_validator

PostingStatus = Literal["draft", "open", "closed"]


class JobPostingCreate(BaseModel):
    org_id: str
    title: str = Field(min_length=2, max_length=160)
    description: str = Field(
        min_length=40,
        description="The job description text (untrusted user input)",
    )
    status: PostingStatus = "draft"

    @field_validator("title")
    @classmethod
    def _trimmed(cls, value: str) -> str:
        title = " ".join(value.split())
        if len(title) < 2:
            raise ValueError("Title must be at least 2 characters.")
        return title


class JobPostingUpdate(BaseModel):
    """Partial edit — only the fields present are written. Closing a posting
    is just ``{"status": "closed"}``, which immediately stops its apply link
    accepting submissions."""

    title: str | None = Field(default=None, min_length=2, max_length=160)
    description: str | None = Field(default=None, min_length=40)
    status: PostingStatus | None = None


class JobPostingResponse(BaseModel):
    """One posting as its org sees it, with the applicant count for the list."""

    id: str
    org_id: str
    title: str
    description: str
    status: PostingStatus
    application_count: int = 0
    created_at: str
    updated_at: str

    @computed_field
    @property
    def apply_path(self) -> str:
        """The public, unauthenticated apply link for this posting. Relative
        so the frontend can render it against whatever origin it is served
        from (local dev, preview, or production)."""
        return f"/apply/{self.id}"


class PublicJobPosting(BaseModel):
    """What an unauthenticated visitor sees on the apply page: the role and
    who it is at, and nothing else about the org."""

    id: str
    title: str
    description: str
    organization_name: str

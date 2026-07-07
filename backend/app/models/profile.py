"""Module 5.4 contracts: LinkedIn/portfolio drafts with two tone variants."""

from pydantic import BaseModel, Field


class ToneVariants(BaseModel):
    """Every output ships in two tones so the user can pick (spec 5.4)."""

    concise: str
    detailed: str


class ProjectRewrite(BaseModel):
    title: str
    concise: str
    detailed: str


class ProfileDraftContent(BaseModel):
    """Gemini structured-output schema for the profile_optimizer module."""

    headline: ToneVariants
    about: ToneVariants
    project_descriptions: list[ProjectRewrite] = Field(min_length=1, max_length=3)


class ProfileDraftRequest(BaseModel):
    resume_id: str


class ProfileDraftResponse(BaseModel):
    """POST /api/profile-drafts response — the module 5.4 contract."""

    profile_draft_id: str
    resume_id: str
    headline: ToneVariants
    about: ToneVariants
    project_descriptions: list[ProjectRewrite]
    cached: bool = False

"""Routes for module 5.4 — LinkedIn/portfolio draft generation."""

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import (
    AuthenticatedUser,
    enforce_upload_rate_limit,
    get_current_user,
    get_profile_optimizer_gemini,
    get_repository,
)
from app.models.profile import (
    ProfileDraftListItem,
    ProfileDraftRequest,
    ProfileDraftResponse,
    ProjectRewrite,
    ToneVariants,
)
from app.services.profile_service import generate_profile_draft

router = APIRouter(prefix="/profile-drafts", tags=["profiles"])


@router.post("", response_model=ProfileDraftResponse)
def create_profile_draft(
    payload: ProfileDraftRequest,
    user: AuthenticatedUser = Depends(enforce_upload_rate_limit),
    repo=Depends(get_repository),
    gemini=Depends(get_profile_optimizer_gemini),
) -> ProfileDraftResponse:
    """Generate LinkedIn headline/About/project rewrites in two tones.

    Uses GEMINI_API_KEY_PROFILE_OPTIMIZER — but only on a cache miss for this
    resume's content hash. Reuses module 5.1's stored parse; no re-entry.
    """
    try:
        return generate_profile_draft(user.id, payload.resume_id, repo, gemini)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("", response_model=list[ProfileDraftListItem])
def list_profile_drafts(
    resume_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    repo=Depends(get_repository),
) -> list[ProfileDraftListItem]:
    """List every past profile draft for one of the caller's resumes, newest
    first — the history panel's cheap summary view. Uses no Gemini key.

    This module caches by the resume's content hash alone, so a given resume
    has a single draft row; the list is returned for consistency with the
    other modules' history.
    """
    if repo.get_resume(user.id, resume_id) is None:
        raise HTTPException(status_code=404, detail="Resume not found.")
    return [
        ProfileDraftListItem(id=str(row["id"]), created_at=str(row["created_at"]))
        for row in repo.list_profile_drafts(resume_id)
    ]


@router.get("/{profile_draft_id}", response_model=ProfileDraftResponse)
def get_profile_draft(
    profile_draft_id: str,
    resume_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    repo=Depends(get_repository),
) -> ProfileDraftResponse:
    """Fetch one past profile draft in full so the dashboard can re-display it.

    Scoped to a resume the caller owns (``resume_id`` query param). Uses no
    Gemini key — persisted data only.
    """
    if repo.get_resume(user.id, resume_id) is None:
        raise HTTPException(status_code=404, detail="Resume not found.")
    row = repo.get_profile_draft(resume_id, profile_draft_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Profile draft not found.")
    return ProfileDraftResponse(
        profile_draft_id=str(row["id"]),
        resume_id=resume_id,
        headline=ToneVariants.model_validate(row["headline"]),
        about=ToneVariants.model_validate(row["about"]),
        project_descriptions=[
            ProjectRewrite.model_validate(p) for p in row["project_descriptions"]
        ],
        cached=True,
    )

"""Routes for module 5.4 — LinkedIn/portfolio draft generation."""

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import (
    AuthenticatedUser,
    enforce_upload_rate_limit,
    get_profile_optimizer_gemini,
    get_repository,
)
from app.models.profile import ProfileDraftRequest, ProfileDraftResponse
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

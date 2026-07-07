"""Routes for module 5.3 — personalized mock interview generation."""

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import (
    AuthenticatedUser,
    enforce_upload_rate_limit,
    get_interview_generator_gemini,
    get_repository,
)
from app.models.interview import InterviewSetRequest, InterviewSetResponse
from app.services.interview_service import generate_interview_set

router = APIRouter(prefix="/interview-sets", tags=["interviews"])


@router.post("", response_model=InterviewSetResponse)
def create_interview_set(
    payload: InterviewSetRequest,
    user: AuthenticatedUser = Depends(enforce_upload_rate_limit),
    repo=Depends(get_repository),
    gemini=Depends(get_interview_generator_gemini),
) -> InterviewSetResponse:
    """Generate 8–10 categorized mock interview questions for a resume/JD pair.

    Uses GEMINI_API_KEY_INTERVIEW_GENERATOR — but only on a cache miss for
    this exact resume+JD content pair. Reuses stored outputs of modules 5.1
    and 5.2; nothing is re-parsed or re-entered.
    """
    try:
        return generate_interview_set(
            user.id, payload.resume_id, payload.jd_id, repo, gemini
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

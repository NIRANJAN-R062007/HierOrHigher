"""Routes for module 5.3 — personalized mock interview generation."""

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import (
    AuthenticatedUser,
    enforce_upload_rate_limit,
    get_current_user,
    get_interview_generator_gemini,
    get_repository,
)
from app.models.interview import (
    InterviewQuestion,
    InterviewSetListItem,
    InterviewSetRequest,
    InterviewSetResponse,
)
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


@router.get("", response_model=list[InterviewSetListItem])
def list_interview_sets(
    resume_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    repo=Depends(get_repository),
) -> list[InterviewSetListItem]:
    """List every past interview set for one of the caller's resumes, newest
    first — the history panel's cheap summary view. Uses no Gemini key.
    """
    if repo.get_resume(user.id, resume_id) is None:
        raise HTTPException(status_code=404, detail="Resume not found.")
    return [
        InterviewSetListItem(
            id=str(row["id"]),
            jd_id=str(row["jd_id"]),
            created_at=str(row["created_at"]),
        )
        for row in repo.list_interview_sets(resume_id)
    ]


@router.get("/{interview_set_id}", response_model=InterviewSetResponse)
def get_interview_set(
    interview_set_id: str,
    resume_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    repo=Depends(get_repository),
) -> InterviewSetResponse:
    """Fetch one past interview set in full so the dashboard can re-display it.

    Scoped to a resume the caller owns (``resume_id`` query param). Uses no
    Gemini key — persisted data only.
    """
    if repo.get_resume(user.id, resume_id) is None:
        raise HTTPException(status_code=404, detail="Resume not found.")
    row = repo.get_interview_set(resume_id, interview_set_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Interview set not found.")
    return InterviewSetResponse(
        interview_set_id=str(row["id"]),
        resume_id=resume_id,
        jd_id=str(row["jd_id"]),
        questions=[InterviewQuestion.model_validate(q) for q in row["questions"]],
        cached=True,
    )

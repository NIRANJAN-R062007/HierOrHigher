"""Routes for module 5.1 — resume upload, parse, and dual scoring."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.api.deps import (
    AuthenticatedUser,
    enforce_upload_rate_limit,
    get_current_user,
    get_repository,
    get_resume_parser_gemini,
)
from app.core.file_validation import FileValidationError
from app.models.resume import ResumeListItem, ResumeResponse
from app.services.resume_service import (
    UnparseableResumeError,
    process_resume,
    response_from_row,
)
from app.services.text_extraction import TextExtractionError

router = APIRouter(prefix="/resumes", tags=["resumes"])


@router.post("", response_model=ResumeResponse)
async def upload_resume(
    file: UploadFile = File(...),
    user: AuthenticatedUser = Depends(enforce_upload_rate_limit),
    repo=Depends(get_repository),
    gemini=Depends(get_resume_parser_gemini),
) -> ResumeResponse:
    """Upload a resume (PDF/DOCX ≤ 5MB) and get parsed fields + dual scores.

    Uses GEMINI_API_KEY_RESUME_PARSER — but only on a cache miss; identical
    re-uploads return the stored result with ``cached: true``.
    """
    data = await file.read()
    try:
        return process_resume(user.id, data, file.filename or "resume", repo, gemini)
    except FileValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (TextExtractionError, UnparseableResumeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("", response_model=list[ResumeListItem])
def list_resumes(
    user: AuthenticatedUser = Depends(get_current_user),
    repo=Depends(get_repository),
) -> list[ResumeListItem]:
    """List the caller's resumes, newest first. Uses no Gemini key."""
    return [
        ResumeListItem(
            id=str(row["id"]),
            content_hash=row["content_hash"],
            ats_score=row["ats_score"],
            human_score=row["human_score"],
            created_at=str(row["created_at"]),
        )
        for row in repo.list_resumes(user.id)
    ]


@router.get("/{resume_id}", response_model=ResumeResponse)
def get_resume(
    resume_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    repo=Depends(get_repository),
) -> ResumeResponse:
    """Fetch one stored resume result. Uses no Gemini key (persisted data)."""
    row = repo.get_resume(user.id, resume_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Resume not found.")
    return response_from_row(row, cached=True)

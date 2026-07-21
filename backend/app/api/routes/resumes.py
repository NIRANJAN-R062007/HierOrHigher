"""Routes for module 5.1 — resume upload, parse, and dual scoring."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.api.deps import (
    AuthenticatedUser,
    enforce_upload_rate_limit,
    get_current_user,
    get_repository,
    get_resume_parser_gemini,
)
from app.config import get_settings
from app.core.file_validation import FileValidationError
from app.models.gap_report import GapReportResponse
from app.models.interview import InterviewQuestion, InterviewSetResponse
from app.models.overview import ResumeOverview
from app.models.profile import ProfileDraftResponse, ProjectRewrite, ToneVariants
from app.models.resume import ResumeListItem, ResumeResponse
from app.services.resume_service import (
    UnparseableResumeError,
    process_resume,
    response_from_row,
)
from app.services.text_extraction import TextExtractionError

router = APIRouter(prefix="/resumes", tags=["resumes"])


@router.post("", response_model=ResumeResponse)
def upload_resume(
    file: UploadFile = File(...),
    user: AuthenticatedUser = Depends(enforce_upload_rate_limit),
    repo=Depends(get_repository),
    gemini=Depends(get_resume_parser_gemini),
) -> ResumeResponse:
    """Upload a resume (PDF/DOCX ≤ 5MB) and get parsed fields + dual scores.

    Uses GEMINI_API_KEY_RESUME_PARSER — but only on a cache miss; identical
    re-uploads return the stored result with ``cached: true``.

    Declared sync (``def``, not ``async``) so FastAPI runs the blocking work —
    text extraction, the Gemini call, and Supabase round-trips — in the
    threadpool instead of stalling the single-process event loop.
    """
    # Read at most one byte past the limit: an oversized upload is capped in
    # memory here and rejected by ``validate_upload`` rather than being fully
    # buffered first (the 512MB free tier can't absorb a large payload).
    max_bytes = get_settings().max_upload_bytes
    data = file.file.read(max_bytes + 1)
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
            name=row.get("name") or "",
            content_hash=row["content_hash"],
            ats_score=row["ats_score"],
            human_score=row["human_score"],
            created_at=str(row["created_at"]),
        )
        for row in repo.list_resumes(user.id)
    ]


@router.get("/{resume_id}/overview", response_model=ResumeOverview)
def get_resume_overview(
    resume_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    repo=Depends(get_repository),
) -> ResumeOverview:
    """Return every module's persisted result for one resume in a single call.

    Powers the dashboard reload: previous results render without any
    re-processing. Uses no Gemini key (persisted data only).
    """
    row = repo.get_resume(user.id, resume_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Resume not found.")

    gap_row = repo.latest_gap_report(resume_id)
    interview_row = repo.latest_interview_set(resume_id)
    profile_row = repo.latest_profile_draft(resume_id)

    jd_text = None
    if gap_row is not None:
        jd_row = repo.get_job_description(user.id, str(gap_row["jd_id"]))
        jd_text = jd_row["raw_text"] if jd_row else None

    return ResumeOverview(
        resume=response_from_row(row, cached=True),
        gap_report=GapReportResponse(
            gap_report_id=str(gap_row["id"]),
            resume_id=resume_id,
            jd_id=str(gap_row["jd_id"]),
            matched=gap_row["matched"],
            missing=gap_row["missing"],
            match_percentage=gap_row["match_percentage"],
            cached=True,
        )
        if gap_row
        else None,
        interview_set=InterviewSetResponse(
            interview_set_id=str(interview_row["id"]),
            resume_id=resume_id,
            jd_id=str(interview_row["jd_id"]),
            questions=[
                InterviewQuestion.model_validate(q)
                for q in interview_row["questions"]
            ],
            cached=True,
        )
        if interview_row
        else None,
        profile_draft=ProfileDraftResponse(
            profile_draft_id=str(profile_row["id"]),
            resume_id=resume_id,
            headline=ToneVariants.model_validate(profile_row["headline"]),
            about=ToneVariants.model_validate(profile_row["about"]),
            project_descriptions=[
                ProjectRewrite.model_validate(p)
                for p in profile_row["project_descriptions"]
            ],
            cached=True,
        )
        if profile_row
        else None,
        job_description_text=jd_text,
    )


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

"""Routes for module 5.2 — gap-to-job mapping."""

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import (
    AuthenticatedUser,
    enforce_upload_rate_limit,
    get_current_user,
    get_gap_mapper_gemini,
    get_repository,
)
from app.models.gap_report import (
    GapReportListItem,
    GapReportRequest,
    GapReportResponse,
)
from app.services.gap_service import ResumeNotFoundError, build_gap_report

router = APIRouter(prefix="/gap-reports", tags=["gap-reports"])


@router.post("", response_model=GapReportResponse)
def create_gap_report(
    payload: GapReportRequest,
    user: AuthenticatedUser = Depends(enforce_upload_rate_limit),
    repo=Depends(get_repository),
    gemini=Depends(get_gap_mapper_gemini),
) -> GapReportResponse:
    """Map a pasted job description against an already-parsed resume.

    Spends GEMINI_API_KEY_GAP_MAPPER (requirement extraction + embeddings) on
    a cache miss for this exact resume+JD content pair. Reuses module 5.1's
    stored parse; the resume is never re-parsed here.
    """
    try:
        return build_gap_report(
            user.id, payload.resume_id, payload.job_description, repo, gemini,
        )
    except ResumeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("", response_model=list[GapReportListItem])
def list_gap_reports(
    resume_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    repo=Depends(get_repository),
) -> list[GapReportListItem]:
    """List every past gap report for one of the caller's resumes, newest
    first — the history panel's cheap summary view. Uses no Gemini key.
    """
    if repo.get_resume(user.id, resume_id) is None:
        raise HTTPException(status_code=404, detail="Resume not found.")
    return [
        GapReportListItem(
            id=str(row["id"]),
            jd_id=str(row["jd_id"]),
            match_percentage=row["match_percentage"],
            created_at=str(row["created_at"]),
        )
        for row in repo.list_gap_reports(resume_id)
    ]


@router.get("/{gap_report_id}", response_model=GapReportResponse)
def get_gap_report(
    gap_report_id: str,
    resume_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    repo=Depends(get_repository),
) -> GapReportResponse:
    """Fetch one past gap report in full so the dashboard can re-display it.

    Scoped to a resume the caller owns (``resume_id`` query param). Uses no
    Gemini key — persisted data only.
    """
    if repo.get_resume(user.id, resume_id) is None:
        raise HTTPException(status_code=404, detail="Resume not found.")
    row = repo.get_gap_report(resume_id, gap_report_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Gap report not found.")
    return GapReportResponse(
        gap_report_id=str(row["id"]),
        resume_id=resume_id,
        jd_id=str(row["jd_id"]),
        matched=row["matched"],
        missing=row["missing"],
        match_percentage=row["match_percentage"],
        cached=True,
        source=row.get("source") or "gemini",
        ml_score=row.get("ml_score"),
        categories=row.get("categories"),
    )

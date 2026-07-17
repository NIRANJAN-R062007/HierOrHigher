"""Routes for module 5.2 — gap-to-job mapping."""

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import (
    AuthenticatedUser,
    enforce_upload_rate_limit,
    get_gap_mapper_gemini,
    get_ml_scorer,
    get_repository,
)
from app.models.gap_report import GapReportRequest, GapReportResponse
from app.services.gap_service import ResumeNotFoundError, build_gap_report

router = APIRouter(prefix="/gap-reports", tags=["gap-reports"])


@router.post("", response_model=GapReportResponse)
def create_gap_report(
    payload: GapReportRequest,
    user: AuthenticatedUser = Depends(enforce_upload_rate_limit),
    repo=Depends(get_repository),
    gemini=Depends(get_gap_mapper_gemini),
    scorer=Depends(get_ml_scorer),
) -> GapReportResponse:
    """Map a pasted job description against an already-parsed resume.

    The offline ML scorer runs first; a confident result is served with zero
    Gemini calls. GEMINI_API_KEY_GAP_MAPPER (requirement extraction +
    embeddings) is only spent when the model is unsure or unavailable — and,
    as always, only on a cache miss for this exact resume+JD content pair.
    Reuses module 5.1's stored parse; the resume is never re-parsed here.
    """
    try:
        return build_gap_report(
            user.id, payload.resume_id, payload.job_description, repo, gemini,
            scorer=scorer,
        )
    except ResumeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

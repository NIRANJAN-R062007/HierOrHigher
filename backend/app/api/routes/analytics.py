"""Routes for the cross-run analytics dashboard.

Read-only aggregations over a user's persisted results across every resume and
job description. Kept in its own router (not under ``/gap-reports``, whose
``/{gap_report_id}`` path param would otherwise swallow these paths) and
prefixed ``/analytics``. Uses no Gemini key — persisted data only.
"""

from fastapi import APIRouter, Depends

from app.api.deps import AuthenticatedUser, get_current_user, get_repository
from app.models.analytics import MatchDistributionItem

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/gap-distribution", response_model=list[MatchDistributionItem])
def gap_distribution(
    user: AuthenticatedUser = Depends(get_current_user),
    repo=Depends(get_repository),
) -> list[MatchDistributionItem]:
    """Every gap report's match percentage across all of the caller's
    resumes, newest first — the data behind the match-distribution histogram.
    """
    return [
        MatchDistributionItem(
            match_percentage=row["match_percentage"],
            created_at=str(row["created_at"]),
            jd_id=str(row["jd_id"]),
        )
        for row in repo.list_gap_matches_for_user(user.id)
    ]

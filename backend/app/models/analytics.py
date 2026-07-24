"""Contracts for the cross-run analytics dashboard.

These endpoints aggregate a user's persisted results across every resume/JD —
no Gemini key, persisted data only — for trend/distribution visualizations.
"""

from pydantic import BaseModel, Field


class MatchDistributionItem(BaseModel):
    """One gap report reduced to what the match-percentage histogram needs."""

    match_percentage: int = Field(ge=0, le=100)
    created_at: str
    jd_id: str

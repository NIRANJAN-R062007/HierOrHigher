"""Dashboard aggregation contract: every module's persisted result in one call.

Reloading the dashboard renders from this — no module is re-processed just
to display previous results (spec 1's definition of done).
"""

from pydantic import BaseModel

from app.models.gap_report import GapReportResponse
from app.models.interview import InterviewSetResponse
from app.models.profile import ProfileDraftResponse
from app.models.resume import ResumeResponse


class ResumeOverview(BaseModel):
    resume: ResumeResponse
    gap_report: GapReportResponse | None = None
    interview_set: InterviewSetResponse | None = None
    profile_draft: ProfileDraftResponse | None = None
    job_description_text: str | None = None

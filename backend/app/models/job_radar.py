"""Job Radar contracts: a role+location search over live SerpApi postings,
each one scored through the existing Gap-to-Job Mapper (module 5.2)."""

from pydantic import BaseModel, Field


class JobRadarRequest(BaseModel):
    resume_id: str
    role: str = Field(min_length=2, description="Role to search, e.g. 'backend engineer'")
    location: str = Field(min_length=2, description="e.g. 'Chennai, Tamil Nadu, India'")


class JobRadarResultItem(BaseModel):
    """One live posting scored against the resume via the Gap Mapper."""

    job_title: str
    company: str
    job_url: str
    match_percentage: float
    gap_report_id: str  # FK into the existing gap_reports table


class JobRadarSearchResponse(BaseModel):
    """Response for both POST /job-radar and GET /job-radar/{search_id}."""

    search_id: str
    results: list[JobRadarResultItem]
    skipped_count: int = Field(
        default=0,
        description="Listings SerpApi returned that failed gap-mapping and were skipped",
    )


class JobRadarSearchListItem(BaseModel):
    """One entry in a resume's Job Radar search history."""

    id: str
    role: str
    location: str
    result_count: int
    created_at: str

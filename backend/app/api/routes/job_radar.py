"""Routes for Job Radar — live SerpApi postings scored through the existing
Gap-to-Job Mapper (module 5.2), instead of one manually pasted JD.
"""

import concurrent.futures
import logging

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import (
    AuthenticatedUser,
    enforce_upload_rate_limit,
    get_current_user,
    get_gap_mapper_gemini,
    get_repository,
    get_serpapi_client,
)
from app.models.job_radar import (
    JobRadarRequest,
    JobRadarResultItem,
    JobRadarSearchListItem,
    JobRadarSearchResponse,
)
from app.services.gap_service import build_gap_report
from app.services.serpapi_client import SerpApiError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/job-radar", tags=["job-radar"])

# Caps Gemini spend per search (one search = many gap-report calls). SerpApi
# itself costs exactly one search regardless of listing count.
MAX_LISTINGS = 15
MAX_CONCURRENCY = 5


def _score_listing(
    user_id: str, resume_id: str, listing: dict, repo, gemini
) -> JobRadarResultItem | None:
    """Run one listing through the existing Gap Mapper, or ``None`` on failure.

    A single bad listing (malformed description, a transient Gemini error)
    must not fail the whole search — it's logged and skipped instead.
    """
    try:
        report = build_gap_report(
            user_id, resume_id, listing["description"], repo, gemini
        )
    except Exception as exc:  # noqa: BLE001 — isolate one listing's failure
        logger.warning(
            "Job Radar: skipping listing %s: %s", listing.get("job_url"), exc
        )
        return None
    return JobRadarResultItem(
        job_title=listing["title"],
        company=listing["company_name"],
        job_url=listing["job_url"],
        match_percentage=float(report.match_percentage),
        gap_report_id=report.gap_report_id,
    )


@router.post("", response_model=JobRadarSearchResponse)
def create_job_radar_search(
    payload: JobRadarRequest,
    user: AuthenticatedUser = Depends(enforce_upload_rate_limit),
    repo=Depends(get_repository),
    gemini=Depends(get_gap_mapper_gemini),
    serpapi=Depends(get_serpapi_client),
) -> JobRadarSearchResponse:
    """Pull live postings for a role/location and score each against the
    caller's resume via the existing Gap Mapper.

    Spends one SerpApi search plus, per listing (capped at ``MAX_LISTINGS``,
    run at bounded concurrency), whatever GEMINI_API_KEY_GAP_MAPPER call the
    Gap Mapper's own content-hash cache doesn't already cover. A zero-result
    search still creates a search row and returns an empty result list —
    that's a normal outcome, not an error.
    """
    if repo.get_resume(user.id, payload.resume_id) is None:
        raise HTTPException(status_code=404, detail="Resume not found.")

    try:
        listings = serpapi.search_jobs(payload.role, payload.location)
    except SerpApiError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    listings = listings[:MAX_LISTINGS]

    results: list[JobRadarResultItem] = []
    skipped_count = 0

    if listings:
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=MAX_CONCURRENCY
        ) as pool:
            futures = [
                pool.submit(
                    _score_listing, user.id, payload.resume_id, listing, repo, gemini
                )
                for listing in listings
            ]
            for future in futures:
                result = future.result()
                if result is None:
                    skipped_count += 1
                else:
                    results.append(result)

    results.sort(key=lambda item: item.match_percentage, reverse=True)

    search_row = repo.insert_job_radar_search(
        {
            "user_id": user.id,
            "resume_id": payload.resume_id,
            "role": payload.role,
            "location": payload.location,
            "gap_report_ids": [item.gap_report_id for item in results],
            "results": [
                {
                    "gap_report_id": item.gap_report_id,
                    "job_title": item.job_title,
                    "company": item.company,
                    "job_url": item.job_url,
                }
                for item in results
            ],
        }
    )

    return JobRadarSearchResponse(
        search_id=str(search_row["id"]), results=results, skipped_count=skipped_count
    )


@router.get("", response_model=list[JobRadarSearchListItem])
def list_job_radar_searches(
    resume_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    repo=Depends(get_repository),
) -> list[JobRadarSearchListItem]:
    """List past Job Radar searches for a resume, newest first. No new
    SerpApi/Gemini calls — persisted data only."""
    if repo.get_resume(user.id, resume_id) is None:
        raise HTTPException(status_code=404, detail="Resume not found.")
    return [
        JobRadarSearchListItem(
            id=str(row["id"]),
            role=row["role"],
            location=row["location"],
            result_count=len(row["gap_report_ids"] or []),
            created_at=str(row["searched_at"]),
        )
        for row in repo.list_job_radar_searches(resume_id)
    ]


@router.get("/{search_id}", response_model=JobRadarSearchResponse)
def get_job_radar_search(
    search_id: str,
    resume_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    repo=Depends(get_repository),
) -> JobRadarSearchResponse:
    """Replay one past search in full, joined against gap_reports for
    current match percentages. No new SerpApi/Gemini calls."""
    if repo.get_resume(user.id, resume_id) is None:
        raise HTTPException(status_code=404, detail="Resume not found.")
    search_row = repo.get_job_radar_search(resume_id, search_id)
    if search_row is None:
        raise HTTPException(status_code=404, detail="Search not found.")

    results: list[JobRadarResultItem] = []
    for entry in search_row.get("results") or []:
        gap_row = repo.get_gap_report(resume_id, entry["gap_report_id"])
        if gap_row is None:
            continue
        results.append(
            JobRadarResultItem(
                job_title=entry["job_title"],
                company=entry["company"],
                job_url=entry["job_url"],
                match_percentage=float(gap_row["match_percentage"]),
                gap_report_id=entry["gap_report_id"],
            )
        )
    results.sort(key=lambda item: item.match_percentage, reverse=True)

    return JobRadarSearchResponse(
        search_id=str(search_row["id"]), results=results, skipped_count=0
    )

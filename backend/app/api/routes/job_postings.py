"""Routes for job postings and the ranked screening view.

Authenticated and org-membership-gated: every handler resolves access through
app/services/org_service.py before touching a posting, so a posting id alone
grants nothing. Uses no Gemini key — candidate scoring happens at submission
time on the public apply route, and this reads the stored results.
"""

from fastapi import APIRouter, Depends

from app.api.deps import AuthenticatedUser, get_current_user, get_repository
from app.models.application import ApplicantListItem
from app.models.job_posting import (
    JobPostingCreate,
    JobPostingResponse,
    JobPostingUpdate,
)
from app.services import application_service, org_service

router = APIRouter(prefix="/job-postings", tags=["job-postings"])


def _response(row: dict, application_count: int = 0) -> JobPostingResponse:
    return JobPostingResponse(
        id=str(row["id"]),
        org_id=str(row["org_id"]),
        title=row["title"],
        description=row["description"],
        status=row["status"],
        application_count=application_count,
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


@router.post("", response_model=JobPostingResponse)
def create_job_posting(
    payload: JobPostingCreate,
    user: AuthenticatedUser = Depends(get_current_user),
    repo=Depends(get_repository),
) -> JobPostingResponse:
    """Create a posting for an org the caller belongs to.

    Its description is JD text, so no separate job-description step is needed
    before candidates can be scored against it. Postings start as drafts
    unless created ``open``; only an open posting's apply link accepts
    submissions.
    """
    org_service.require_membership(user.id, user.email, payload.org_id, repo)
    row = repo.insert_job_posting(
        {
            "org_id": payload.org_id,
            "title": payload.title,
            "description": payload.description,
            "status": payload.status,
            "created_by": user.id,
        }
    )
    return _response(row)


@router.get("", response_model=list[JobPostingResponse])
def list_job_postings(
    org_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    repo=Depends(get_repository),
) -> list[JobPostingResponse]:
    """One org's postings, newest first, each with its applicant count."""
    org_service.require_membership(user.id, user.email, org_id, repo)
    rows = repo.list_job_postings(org_id)
    counts = repo.count_applications_by_posting([str(row["id"]) for row in rows])
    return [_response(row, counts.get(str(row["id"]), 0)) for row in rows]


@router.get("/{posting_id}", response_model=JobPostingResponse)
def get_job_posting(
    posting_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    repo=Depends(get_repository),
) -> JobPostingResponse:
    """One posting in full, including its public apply path."""
    row = org_service.require_posting_access(user.id, user.email, posting_id, repo)
    counts = repo.count_applications_by_posting([posting_id])
    return _response(row, counts.get(posting_id, 0))


@router.patch("/{posting_id}", response_model=JobPostingResponse)
def update_job_posting(
    posting_id: str,
    payload: JobPostingUpdate,
    user: AuthenticatedUser = Depends(get_current_user),
    repo=Depends(get_repository),
) -> JobPostingResponse:
    """Edit a posting, or close it with ``{"status": "closed"}``.

    Closing takes its apply link down immediately. Editing the description
    invalidates the posting's cached requirements by content hash, so the next
    applicant is scored against the new text.
    """
    updates = payload.model_dump(exclude_none=True)
    row = org_service.require_posting_access(user.id, user.email, posting_id, repo)
    if updates:
        row = repo.update_job_posting(posting_id, updates)
    counts = repo.count_applications_by_posting([posting_id])
    return _response(row, counts.get(posting_id, 0))


@router.get("/{posting_id}/applications", response_model=list[ApplicantListItem])
def list_applications(
    posting_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    repo=Depends(get_repository),
) -> list[ApplicantListItem]:
    """This posting's applicants ranked by match percentage, with each
    candidate's matched and missing skills — the screening view.

    Reads scores computed at submission time; spends no Gemini quota.
    """
    org_service.require_posting_access(user.id, user.email, posting_id, repo)
    return application_service.list_applicants(posting_id, repo)

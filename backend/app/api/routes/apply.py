"""Public, unauthenticated routes for a job posting's apply link.

The only routes in the app with no ``get_current_user`` dependency. A visitor
opens /apply/{posting_id}, uploads a resume, and submits — no account is
created for them, and no Supabase auth user ever exists on their behalf.

Because there is no caller identity, the guards are different in kind:

* only an ``open`` posting resolves at all, so closing one takes its link down;
* the upload gets the same magic-byte, size, and parse validation as the
  signed-in path, so an open endpoint is no laxer about what reaches Gemini;
* ``enforce_apply_rate_limit`` throttles per posting + client IP, since there
  is no user id to key on;
* the response is a receipt only — the score it triggers is written for the
  recruiter and never returned here.
"""

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.api.deps import (
    enforce_apply_rate_limit,
    get_gap_mapper_gemini,
    get_repository,
    get_resume_parser_gemini,
)
from app.config import get_settings
from app.core.file_validation import FileValidationError
from app.models.application import ApplicationReceipt
from app.models.job_posting import PublicJobPosting
from app.services.application_service import public_posting_view, submit_application
from app.services.resume_service import UnparseableResumeError
from app.services.text_extraction import TextExtractionError

router = APIRouter(prefix="/apply", tags=["apply"])


def _resolve_open_posting(posting_id: str, repo) -> dict:
    posting = repo.get_job_posting(posting_id)
    if posting is None:
        raise HTTPException(status_code=404, detail="Job posting not found.")
    return posting


@router.get("/{posting_id}", response_model=PublicJobPosting)
def get_public_posting(
    posting_id: str,
    repo=Depends(get_repository),
) -> PublicJobPosting:
    """What the apply page renders: the role, its description, and the org
    name. Nothing else about the org, its other postings, or its applicants
    is reachable without authentication. Uses no Gemini key.
    """
    return public_posting_view(_resolve_open_posting(posting_id, repo), repo)


@router.post(
    "/{posting_id}",
    response_model=ApplicationReceipt,
    dependencies=[Depends(enforce_apply_rate_limit)],
)
def submit(
    posting_id: str,
    file: UploadFile = File(...),
    name: str = Form(""),
    email: str = Form(""),
    repo=Depends(get_repository),
    parser_gemini=Depends(get_resume_parser_gemini),
    mapper_gemini=Depends(get_gap_mapper_gemini),
) -> ApplicationReceipt:
    """Submit a resume to an open posting. No authentication, no account.

    Spends GEMINI_API_KEY_RESUME_PARSER to structure the resume and
    GEMINI_API_KEY_GAP_MAPPER to score it against the posting — both only on a
    cache miss. Name and email are optional; anything left blank falls back to
    what the parser found in the resume.

    Declared sync (``def``, not ``async``) so FastAPI runs the blocking work in
    the threadpool rather than stalling the event loop, matching the
    signed-in upload route.
    """
    posting = _resolve_open_posting(posting_id, repo)
    public_posting_view(posting, repo)  # rejects draft/closed postings

    # Read one byte past the limit so an oversized upload is capped in memory
    # here and rejected by validation, never fully buffered.
    max_bytes = get_settings().max_upload_bytes
    data = file.file.read(max_bytes + 1)
    try:
        return submit_application(
            posting,
            data,
            file.filename or "resume",
            name,
            email,
            repo,
            parser_gemini,
            mapper_gemini,
        )
    except FileValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (TextExtractionError, UnparseableResumeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

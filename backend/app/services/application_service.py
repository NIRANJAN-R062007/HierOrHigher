"""Candidate intake and screening — the recruiter side's Gemini-spending path.

Runs when an unauthenticated visitor submits a resume to a public apply link.
The pipeline mirrors the student-facing one and reuses its parts rather than
re-implementing them:

* validation, text extraction, and the resume parse are module 5.1's
  (GEMINI_API_KEY_RESUME_PARSER, same prompt, same garbled-parse guard);
* the scoring is ``gap_service.match_resume_to_jd`` (GEMINI_API_KEY_GAP_MAPPER),
  the same matching core the Gap-to-Job Mapper uses.

No new Gemini key: both calls are the same underlying capability, just fed by
a candidate with no ``auth.uid()`` instead of a signed-in student.

Caching runs before every Gemini call, at two levels. A resume already seen by
this org is one ``candidates`` row and is never re-parsed. A posting's JD
requirements are extracted once and stored on the posting until its text
changes. And an unchanged resubmission to an unchanged posting re-scores
nothing at all.
"""

from app.config import get_settings
from app.core.file_validation import validate_upload
from app.core.hashing import combined_hash, sha256_bytes, sha256_text
from app.core.prompts import load_prompt, wrap_untrusted
from app.models.application import ApplicantListItem, ApplicationReceipt
from app.models.job_posting import PublicJobPosting
from app.models.resume import ResumeAnalysis
from app.services.gap_service import match_resume_to_jd
from app.services.resume_service import UnparseableResumeError
from app.services.text_extraction import extract_text


class PostingClosedError(LookupError):
    """The posting exists but its apply link isn't accepting submissions."""


def public_posting_view(posting: dict, repo) -> PublicJobPosting:
    """Project a posting down to what an unauthenticated visitor may see.

    Only an ``open`` posting is reachable: a draft has never been published,
    and a closed one has stopped taking applicants. Both raise rather than
    render, so closing a posting takes its apply link down immediately.
    """
    if posting["status"] != "open":
        raise PostingClosedError(
            "This job posting is no longer accepting applications."
        )
    org = repo.get_organization(str(posting["org_id"]))
    return PublicJobPosting(
        id=str(posting["id"]),
        title=posting["title"],
        description=posting["description"],
        organization_name=org["name"] if org else "",
    )


def _parse_candidate_resume(file_bytes: bytes, gemini) -> dict:
    """Validate, extract, and parse one uploaded resume into stored fields.

    Same three guards as the student upload path — magic-byte content type
    plus size cap, unreadable/scanned documents, and a garbled parse — so a
    public endpoint is no laxer about what it feeds Gemini than an
    authenticated one.
    """
    settings = get_settings()
    kind = validate_upload(file_bytes, settings.max_upload_bytes)
    raw_text = extract_text(file_bytes, kind)

    prompt = load_prompt("resume_parser") + "\n\n" + wrap_untrusted(raw_text)
    analysis: ResumeAnalysis = gemini.generate_structured(
        prompt, ResumeAnalysis, max_output_tokens=4096, temperature=0.1
    )
    if analysis.parsed.structured_field_count() < 2:
        raise UnparseableResumeError(
            "We couldn't read enough detail from this resume. "
            "Please upload a text-based PDF or DOCX version."
        )
    # The parser also returns a human-readability score. That is coaching for
    # the person writing the resume, not a screening signal, so it is dropped
    # here rather than stored against a candidate who will never see it.
    return analysis.parsed.model_dump()


def _resolve_identity(parsed: dict, form_name: str, form_email: str) -> tuple[str, str]:
    """Prefer what the candidate typed over what the parser inferred."""
    name = form_name.strip() or (parsed.get("name") or "").strip()
    email = form_email.strip() or (parsed.get("contact", {}) or {}).get("email", "")
    return name, email.strip().lower()


def submit_application(
    posting: dict,
    file_bytes: bytes,
    filename: str,
    form_name: str,
    form_email: str,
    repo,
    parser_gemini,
    mapper_gemini,
) -> ApplicationReceipt:
    """Take one public submission from resume bytes to a scored application.

    Inputs: the already-resolved posting (open, verified by the route), the
    upload, optional self-reported name/email, a repository, and the
    resume_parser and gap_mapper Gemini clients. Creates no auth user — the
    candidate row it writes is an identity that exists only inside this org.

    Returns a receipt. The score never travels back to the candidate; it is
    written to the application row for the recruiter's screening view.
    """
    org_id = str(posting["org_id"])
    posting_id = str(posting["id"])
    content_hash = sha256_bytes(file_bytes)

    candidate = repo.get_candidate_by_hash(org_id, content_hash)
    if candidate is None:
        parsed = _parse_candidate_resume(file_bytes, parser_gemini)
        name, email = _resolve_identity(parsed, form_name, form_email)
        candidate = repo.insert_candidate(
            {
                "org_id": org_id,
                "full_name": name,
                "email": email,
                "content_hash": content_hash,
                "parsed_json": parsed,
            }
        )
    else:
        # Same resume, second posting: reuse the parse, but let this
        # submission fill in contact details the earlier one left blank.
        name, email = _resolve_identity(
            candidate["parsed_json"], form_name, form_email
        )
        fresh = {
            key: value
            for key, value in (("full_name", name), ("email", email))
            if value and not (candidate.get(key) or "").strip()
        }
        if fresh:
            candidate = repo.update_candidate(str(candidate["id"]), fresh)

    candidate_id = str(candidate["id"])
    jd_text = posting["description"]
    jd_hash = sha256_text(jd_text)
    cache_key = combined_hash(content_hash, jd_hash)

    existing = repo.get_application(posting_id, candidate_id)
    if existing is not None and existing["content_hash"] == cache_key:
        # This exact resume was already scored against this exact JD text.
        return ApplicationReceipt(
            application_id=str(existing["id"]),
            posting_title=posting["title"],
            candidate_name=candidate.get("full_name") or "",
            already_applied=True,
        )

    # Requirements are cached on the posting and re-extracted only when its
    # description text has actually changed since the last extraction.
    cached_requirements = (
        (posting["parsed_requirements"] or [])
        if posting.get("requirements_hash") == jd_hash
        else None
    )
    outcome = match_resume_to_jd(
        candidate["parsed_json"],
        jd_text,
        mapper_gemini,
        cached_requirements=cached_requirements,
    )
    if cached_requirements is None:
        repo.cache_posting_requirements(posting_id, outcome.requirements, jd_hash)

    score = {
        "content_hash": cache_key,
        "match_percentage": outcome.match_percentage,
        "matched": outcome.matched,
        "missing": outcome.missing,
        "categories": outcome.categories,
    }
    if existing is not None:
        # Re-applied after the recruiter edited the JD: one application per
        # candidate per posting, re-scored against the current text.
        row = repo.update_application(str(existing["id"]), score)
    else:
        row = repo.insert_application(
            {"posting_id": posting_id, "candidate_id": candidate_id, **score}
        )

    return ApplicationReceipt(
        application_id=str(row["id"]),
        posting_title=posting["title"],
        candidate_name=candidate.get("full_name") or "",
        already_applied=False,
    )


def list_applicants(posting_id: str, repo) -> list[ApplicantListItem]:
    """One posting's applicants, best match first — the screening view.

    Uses no Gemini key: every score was computed at submission time and read
    back from ``applications`` here.
    """
    applications = repo.list_applications_for_posting(posting_id)
    if not applications:
        return []

    candidates = {
        str(row["id"]): row
        for row in repo.list_candidates_by_ids(
            [str(app["candidate_id"]) for app in applications]
        )
    }
    items = []
    for app in applications:
        candidate = candidates.get(str(app["candidate_id"])) or {}
        items.append(
            ApplicantListItem(
                application_id=str(app["id"]),
                candidate_id=str(app["candidate_id"]),
                name=candidate.get("full_name") or "",
                email=candidate.get("email") or "",
                match_percentage=app["match_percentage"],
                matched=app["matched"],
                missing=app["missing"],
                categories=app.get("categories"),
                created_at=str(app["created_at"]),
            )
        )
    return items

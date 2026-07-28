"""Repository over Supabase tables — the single place the app touches the DB.

Every read is scoped to the caller's identity, mirroring the RLS policies in
``supabase/migrations``. On the student side that identity is the
authenticated user (directly via ``user_id`` or through the owning resume);
on the recruiter side it is org membership, which the service layer resolves
once and then passes down as an ``org_id``. The ``get_*_by_hash`` methods
implement the check-cache-before-Gemini strategy (spec 3.3): callers must
consult them before spending any module's Gemini quota.

The recruiter tables have no owner column the client could be trusted on —
``candidates``/``applications`` have no ``auth.uid()`` at all — so their
methods take the already-verified ``org_id``/``posting_id`` and never a raw
user-supplied scope.

Services depend on this class through FastAPI dependencies, so integration
tests substitute an in-memory implementation with the same interface.
"""

import logging
from collections import Counter
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

RESUME_BUCKET = "resumes"


class SupabaseRepository:
    """Data access for every table plus resume file storage."""

    def __init__(self, client):
        self.client = client

    # -- helpers -----------------------------------------------------------

    def _one(self, query) -> dict | None:
        rows = query.limit(1).execute().data
        return rows[0] if rows else None

    # -- resumes (module 5.1) ----------------------------------------------

    def get_resume_by_hash(self, user_id: str, content_hash: str) -> dict | None:
        """Cache lookup: an identical re-upload must not re-call Gemini."""
        return self._one(
            self.client.table("resumes")
            .select("*")
            .eq("user_id", user_id)
            .eq("content_hash", content_hash)
        )

    def get_resume(self, user_id: str, resume_id: str) -> dict | None:
        return self._one(
            self.client.table("resumes")
            .select("*")
            .eq("user_id", user_id)
            .eq("id", resume_id)
        )

    def list_resumes(self, user_id: str) -> list[dict]:
        return (
            self.client.table("resumes")
            .select(
                "id, content_hash, ats_score, human_score, created_at, "
                "name:parsed_json->>name"
            )
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
            .data
        )

    def insert_resume(self, row: dict) -> dict:
        return self.client.table("resumes").insert(row).execute().data[0]

    def upload_resume_file(
        self, user_id: str, filename: str, data: bytes, content_type: str
    ) -> str | None:
        """Store the original file under the owner's folder; never fail the
        request over storage — the parsed result is the source of truth."""
        path = f"{user_id}/{filename}"
        try:
            self.client.storage.from_(RESUME_BUCKET).upload(
                path, data, {"content-type": content_type, "upsert": "true"}
            )
            return path
        except Exception as exc:  # noqa: BLE001
            logger.warning("Resume file storage failed for %s: %s", path, exc)
            return None

    # -- job descriptions (module 5.2) ---------------------------------------

    def get_jd_by_hash(self, user_id: str, content_hash: str) -> dict | None:
        return self._one(
            self.client.table("job_descriptions")
            .select("*")
            .eq("user_id", user_id)
            .eq("content_hash", content_hash)
        )

    def get_job_description(self, user_id: str, jd_id: str) -> dict | None:
        return self._one(
            self.client.table("job_descriptions")
            .select("*")
            .eq("user_id", user_id)
            .eq("id", jd_id)
        )

    def insert_job_description(self, row: dict) -> dict:
        return self.client.table("job_descriptions").insert(row).execute().data[0]

    # -- gap reports (module 5.2) --------------------------------------------

    def get_gap_report_by_hash(self, resume_id: str, content_hash: str) -> dict | None:
        return self._one(
            self.client.table("gap_reports")
            .select("*")
            .eq("resume_id", resume_id)
            .eq("content_hash", content_hash)
        )

    def latest_gap_report(self, resume_id: str) -> dict | None:
        return self._one(
            self.client.table("gap_reports")
            .select("*")
            .eq("resume_id", resume_id)
            .order("created_at", desc=True)
        )

    def list_gap_reports(self, resume_id: str) -> list[dict]:
        """Every past gap report for a resume, newest first — lightweight
        columns only (the history list never needs the full skill arrays)."""
        return (
            self.client.table("gap_reports")
            .select("id, jd_id, match_percentage, created_at")
            .eq("resume_id", resume_id)
            .order("created_at", desc=True)
            .execute()
            .data
        )

    def get_gap_report(self, resume_id: str, gap_report_id: str) -> dict | None:
        """One past gap report in full, scoped to its owning resume."""
        return self._one(
            self.client.table("gap_reports")
            .select("*")
            .eq("resume_id", resume_id)
            .eq("id", gap_report_id)
        )

    def list_gap_matches_for_user(self, user_id: str) -> list[dict]:
        """Every gap report's match percentage across ALL the caller's
        resumes, newest first — the source for the analytics distribution.

        ``gap_reports`` has no ``user_id`` of its own, so this joins through
        the owning resume (``resumes!inner``) and filters by ``resumes.user_id``
        — mirroring the RLS policy. Lightweight columns only."""
        return (
            self.client.table("gap_reports")
            .select("match_percentage, created_at, jd_id, resumes!inner(user_id)")
            .eq("resumes.user_id", user_id)
            .order("created_at", desc=True)
            .execute()
            .data
        )

    def insert_gap_report(self, row: dict) -> dict:
        return self.client.table("gap_reports").insert(row).execute().data[0]

    # -- interview sets (module 5.3) ------------------------------------------

    def get_interview_set_by_hash(
        self, resume_id: str, content_hash: str
    ) -> dict | None:
        return self._one(
            self.client.table("interview_sets")
            .select("*")
            .eq("resume_id", resume_id)
            .eq("content_hash", content_hash)
        )

    def latest_interview_set(self, resume_id: str) -> dict | None:
        return self._one(
            self.client.table("interview_sets")
            .select("*")
            .eq("resume_id", resume_id)
            .order("created_at", desc=True)
        )

    def list_interview_sets(self, resume_id: str) -> list[dict]:
        """Every past interview set for a resume, newest first — lightweight
        columns only (the full question list is fetched on demand)."""
        return (
            self.client.table("interview_sets")
            .select("id, jd_id, created_at")
            .eq("resume_id", resume_id)
            .order("created_at", desc=True)
            .execute()
            .data
        )

    def get_interview_set(self, resume_id: str, interview_set_id: str) -> dict | None:
        """One past interview set in full, scoped to its owning resume."""
        return self._one(
            self.client.table("interview_sets")
            .select("*")
            .eq("resume_id", resume_id)
            .eq("id", interview_set_id)
        )

    def insert_interview_set(self, row: dict) -> dict:
        return self.client.table("interview_sets").insert(row).execute().data[0]

    # -- profile drafts (module 5.4) -------------------------------------------

    def get_profile_draft_by_hash(
        self, resume_id: str, content_hash: str
    ) -> dict | None:
        return self._one(
            self.client.table("profile_drafts")
            .select("*")
            .eq("resume_id", resume_id)
            .eq("content_hash", content_hash)
        )

    def latest_profile_draft(self, resume_id: str) -> dict | None:
        return self._one(
            self.client.table("profile_drafts")
            .select("*")
            .eq("resume_id", resume_id)
            .order("created_at", desc=True)
        )

    def list_profile_drafts(self, resume_id: str) -> list[dict]:
        """Every past profile draft for a resume, newest first — lightweight
        columns only. Note: this module caches by the resume's content hash
        alone (no JD input), so in practice a resume has a single draft row."""
        return (
            self.client.table("profile_drafts")
            .select("id, created_at")
            .eq("resume_id", resume_id)
            .order("created_at", desc=True)
            .execute()
            .data
        )

    def get_profile_draft(self, resume_id: str, profile_draft_id: str) -> dict | None:
        """One past profile draft in full, scoped to its owning resume."""
        return self._one(
            self.client.table("profile_drafts")
            .select("*")
            .eq("resume_id", resume_id)
            .eq("id", profile_draft_id)
        )

    def insert_profile_draft(self, row: dict) -> dict:
        return self.client.table("profile_drafts").insert(row).execute().data[0]

    # -- organizations & members (recruiter side) ------------------------------

    def insert_organization(self, row: dict) -> dict:
        return self.client.table("organizations").insert(row).execute().data[0]

    def get_organization(self, org_id: str) -> dict | None:
        """Fetch one org by id. Unscoped by design — every caller has already
        proved membership via ``get_org_membership``."""
        return self._one(
            self.client.table("organizations").select("*").eq("id", org_id)
        )

    def list_organizations_by_ids(self, org_ids: list[str]) -> list[dict]:
        """Hydrate the orgs behind a caller's membership rows in one query."""
        if not org_ids:
            return []
        return (
            self.client.table("organizations")
            .select("*")
            .in_("id", org_ids)
            .execute()
            .data
        )

    def list_memberships_for_user(self, user_id: str, email: str) -> list[dict]:
        """Every membership belonging to this person, newest first.

        Two lookups, not one: a claimed row matches on ``user_id``, while an
        invite sent before they ever signed up has a null ``user_id`` and is
        only findable by the email it was addressed to (which is matched
        against their verified session email, never a client-supplied one).
        """
        claimed = (
            self.client.table("org_members")
            .select("*")
            .eq("user_id", user_id)
            .execute()
            .data
        )
        invited = []
        if email:
            invited = (
                self.client.table("org_members")
                .select("*")
                .is_("user_id", "null")
                .eq("email", email.lower())
                .execute()
                .data
            )
        rows = claimed + [r for r in invited if r["id"] not in {c["id"] for c in claimed}]
        return sorted(rows, key=lambda r: r["created_at"], reverse=True)

    def get_org_membership(
        self, org_id: str, user_id: str, email: str
    ) -> dict | None:
        """The caller's membership row for one org, or None if not a member."""
        return next(
            (
                row
                for row in self.list_memberships_for_user(user_id, email)
                if str(row["org_id"]) == org_id
            ),
            None,
        )

    def list_org_members(self, org_id: str) -> list[dict]:
        return (
            self.client.table("org_members")
            .select("*")
            .eq("org_id", org_id)
            .order("created_at")
            .execute()
            .data
        )

    def get_org_member_by_email(self, org_id: str, email: str) -> dict | None:
        """Invite idempotency: re-inviting an existing member is a no-op."""
        return self._one(
            self.client.table("org_members")
            .select("*")
            .eq("org_id", org_id)
            .eq("email", email.lower())
        )

    def insert_org_member(self, row: dict) -> dict:
        return self.client.table("org_members").insert(row).execute().data[0]

    def claim_org_membership(self, membership_id: str, user_id: str) -> dict:
        """Bind an email-only invite to the auth user who just proved that
        email, so later lookups match on ``user_id`` directly."""
        return (
            self.client.table("org_members")
            .update({"user_id": user_id})
            .eq("id", membership_id)
            .execute()
            .data[0]
        )

    # -- job postings (recruiter side) -----------------------------------------

    def insert_job_posting(self, row: dict) -> dict:
        return self.client.table("job_postings").insert(row).execute().data[0]

    def get_job_posting(self, posting_id: str) -> dict | None:
        """Fetch one posting by id, unscoped.

        Deliberately not org-scoped: the public apply route resolves a posting
        with no caller identity at all. Authenticated callers must check
        ``row["org_id"]`` against their membership — which is exactly what
        ``org_service.require_posting_access`` does.
        """
        return self._one(
            self.client.table("job_postings").select("*").eq("id", posting_id)
        )

    def list_job_postings(self, org_id: str) -> list[dict]:
        return (
            self.client.table("job_postings")
            .select("*")
            .eq("org_id", org_id)
            .order("created_at", desc=True)
            .execute()
            .data
        )

    def update_job_posting(self, posting_id: str, updates: dict) -> dict:
        return (
            self.client.table("job_postings")
            .update({**updates, "updated_at": datetime.now(timezone.utc).isoformat()})
            .eq("id", posting_id)
            .execute()
            .data[0]
        )

    def cache_posting_requirements(
        self, posting_id: str, requirements: list[str], requirements_hash: str
    ) -> dict:
        """Store the JD requirements just extracted for this posting.

        Separate from ``update_job_posting`` because this is a cache fill, not
        an edit: it must not move ``updated_at``, which recruiters read as
        "when the posting last changed"."""
        return (
            self.client.table("job_postings")
            .update(
                {
                    "parsed_requirements": requirements,
                    "requirements_hash": requirements_hash,
                }
            )
            .eq("id", posting_id)
            .execute()
            .data[0]
        )

    # -- candidates (recruiter side; no auth.uid() owner) ----------------------

    def get_candidate_by_hash(self, org_id: str, content_hash: str) -> dict | None:
        """Cache lookup: the same resume submitted twice to one org is one
        candidate, and is parsed by Gemini only once."""
        return self._one(
            self.client.table("candidates")
            .select("*")
            .eq("org_id", org_id)
            .eq("content_hash", content_hash)
        )

    def insert_candidate(self, row: dict) -> dict:
        return self.client.table("candidates").insert(row).execute().data[0]

    def update_candidate(self, candidate_id: str, updates: dict) -> dict:
        return (
            self.client.table("candidates")
            .update(updates)
            .eq("id", candidate_id)
            .execute()
            .data[0]
        )

    def list_candidates_by_ids(self, candidate_ids: list[str]) -> list[dict]:
        if not candidate_ids:
            return []
        return (
            self.client.table("candidates")
            .select("*")
            .in_("id", candidate_ids)
            .execute()
            .data
        )

    # -- applications (recruiter side; no auth.uid() owner) --------------------

    def get_application(self, posting_id: str, candidate_id: str) -> dict | None:
        return self._one(
            self.client.table("applications")
            .select("*")
            .eq("posting_id", posting_id)
            .eq("candidate_id", candidate_id)
        )

    def insert_application(self, row: dict) -> dict:
        return self.client.table("applications").insert(row).execute().data[0]

    def update_application(self, application_id: str, updates: dict) -> dict:
        return (
            self.client.table("applications")
            .update(updates)
            .eq("id", application_id)
            .execute()
            .data[0]
        )

    def list_applications_for_posting(self, posting_id: str) -> list[dict]:
        """One posting's applicants, best match first — the screening view."""
        return (
            self.client.table("applications")
            .select("*")
            .eq("posting_id", posting_id)
            .order("match_percentage", desc=True)
            .order("created_at")
            .execute()
            .data
        )

    def count_applications_by_posting(self, posting_ids: list[str]) -> dict[str, int]:
        """Applicant counts for a whole posting list in one query, so the
        postings page doesn't fan out into one count per row."""
        if not posting_ids:
            return {}
        rows = (
            self.client.table("applications")
            .select("posting_id")
            .in_("posting_id", posting_ids)
            .execute()
            .data
        )
        return Counter(str(row["posting_id"]) for row in rows)

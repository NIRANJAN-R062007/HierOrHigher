"""Repository over Supabase tables — the single place the app touches the DB.

Every read is scoped to the authenticated user (directly via ``user_id`` or
through the owning resume), mirroring the RLS policies in
``supabase/migrations``. The ``get_*_by_hash`` methods implement the
check-cache-before-Gemini strategy (spec 3.3): callers must consult them
before spending any module's Gemini quota.

Services depend on this class through FastAPI dependencies, so integration
tests substitute an in-memory implementation with the same interface.
"""

import logging

logger = logging.getLogger(__name__)

RESUME_BUCKET = "resumes"


class SupabaseRepository:
    """Data access for all six tables plus resume file storage."""

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
            .select("id, content_hash, ats_score, human_score, created_at")
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

    def insert_profile_draft(self, row: dict) -> dict:
        return self.client.table("profile_drafts").insert(row).execute().data[0]

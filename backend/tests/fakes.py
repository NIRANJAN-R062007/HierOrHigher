"""Hermetic test doubles.

``FakeRepository`` mirrors the ``SupabaseRepository`` interface in memory.
``FakeGemini`` mirrors the ``GeminiClient`` interface and answers from the
sample dataset, so integration tests run real sample resume/JD pairs through
the actual endpoints (spec 10) with no network and no API keys — while its
call counters prove the caching rules ("never call Gemini on a cache hit",
"module 5.2 never re-parses") actually hold.
"""

import io
import uuid
from collections import Counter
from datetime import datetime, timezone


def build_docx(text: str) -> bytes:
    """Build a real DOCX in memory from plain resume text (test fixture)."""
    import docx

    document = docx.Document()
    for line in text.splitlines():
        document.add_paragraph(line)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class FakeRepository:
    """In-memory stand-in for SupabaseRepository (same method surface)."""

    def __init__(self):
        self.resumes: dict[str, dict] = {}
        self.jds: dict[str, dict] = {}
        self.gap_reports: dict[str, dict] = {}
        self.interview_sets: dict[str, dict] = {}
        self.profile_drafts: dict[str, dict] = {}
        self.uploaded_files: dict[str, bytes] = {}

    @staticmethod
    def _insert(table: dict, row: dict) -> dict:
        stored = {**row, "id": str(uuid.uuid4()), "created_at": _now()}
        table[stored["id"]] = stored
        return stored

    @staticmethod
    def _latest(rows: list[dict]) -> dict | None:
        return max(rows, key=lambda r: r["created_at"], default=None)

    # -- resumes --

    def get_resume_by_hash(self, user_id, content_hash):
        return next(
            (r for r in self.resumes.values()
             if r["user_id"] == user_id and r["content_hash"] == content_hash),
            None,
        )

    def get_resume(self, user_id, resume_id):
        row = self.resumes.get(resume_id)
        return row if row and row["user_id"] == user_id else None

    def list_resumes(self, user_id):
        rows = [r for r in self.resumes.values() if r["user_id"] == user_id]
        return sorted(rows, key=lambda r: r["created_at"], reverse=True)

    def insert_resume(self, row):
        return self._insert(self.resumes, row)

    def upload_resume_file(self, user_id, filename, data, content_type):
        path = f"{user_id}/{filename}"
        self.uploaded_files[path] = data
        return path

    # -- job descriptions --

    def get_jd_by_hash(self, user_id, content_hash):
        return next(
            (r for r in self.jds.values()
             if r["user_id"] == user_id and r["content_hash"] == content_hash),
            None,
        )

    def get_job_description(self, user_id, jd_id):
        row = self.jds.get(jd_id)
        return row if row and row["user_id"] == user_id else None

    def insert_job_description(self, row):
        return self._insert(self.jds, row)

    # -- gap reports --

    def get_gap_report_by_hash(self, resume_id, content_hash):
        return next(
            (r for r in self.gap_reports.values()
             if r["resume_id"] == resume_id and r["content_hash"] == content_hash),
            None,
        )

    def latest_gap_report(self, resume_id):
        return self._latest(
            [r for r in self.gap_reports.values() if r["resume_id"] == resume_id]
        )

    def insert_gap_report(self, row):
        return self._insert(self.gap_reports, row)

    # -- interview sets --

    def get_interview_set_by_hash(self, resume_id, content_hash):
        return next(
            (r for r in self.interview_sets.values()
             if r["resume_id"] == resume_id and r["content_hash"] == content_hash),
            None,
        )

    def latest_interview_set(self, resume_id):
        return self._latest(
            [r for r in self.interview_sets.values() if r["resume_id"] == resume_id]
        )

    def insert_interview_set(self, row):
        return self._insert(self.interview_sets, row)

    # -- profile drafts --

    def get_profile_draft_by_hash(self, resume_id, content_hash):
        return next(
            (r for r in self.profile_drafts.values()
             if r["resume_id"] == resume_id and r["content_hash"] == content_hash),
            None,
        )

    def latest_profile_draft(self, resume_id):
        return self._latest(
            [r for r in self.profile_drafts.values() if r["resume_id"] == resume_id]
        )

    def insert_profile_draft(self, row):
        return self._insert(self.profile_drafts, row)


class FakeGemini:
    """Dataset-driven stand-in for GeminiClient (same method surface).

    ``calls`` counts generate/embed invocations per schema name, which is how
    tests assert the cache prevented a Gemini call. ``overrides`` forces a
    specific response; ``fail_with`` raises instead (error-path tests).
    """

    def __init__(self, dataset: dict):
        self.dataset = dataset
        self.calls: Counter = Counter()
        self.overrides: dict[str, object] = {}
        self.fail_with: Exception | None = None
        self._dims: dict[str, int] = {}

    def _persona_for(self, prompt: str) -> dict:
        haystack = prompt.lower()
        for persona in self.dataset["personas"]:
            if persona["parsed"]["name"].lower() in haystack:
                return persona
        for persona in self.dataset["personas"]:
            if persona["job_description"]["company"].lower() in haystack:
                return persona
        raise AssertionError("FakeGemini: no dataset persona matches the prompt")

    def generate_structured(self, prompt, schema, **_kwargs):
        self.calls[schema.__name__] += 1
        if self.fail_with is not None:
            raise self.fail_with
        if schema.__name__ in self.overrides:
            return self.overrides[schema.__name__]

        persona = self._persona_for(prompt)
        if schema.__name__ == "ResumeAnalysis":
            return schema.model_validate(
                {"parsed": persona["parsed"], "human_score": persona["human_score"]}
            )
        if schema.__name__ == "JDRequirements":
            return schema.model_validate(
                {"requirements": persona["job_description"]["requirements"]}
            )
        if schema.__name__ == "InterviewQuestions":
            return schema.model_validate(
                {"questions": persona["interview_questions"]}
            )
        if schema.__name__ == "ProfileDraftContent":
            return schema.model_validate(persona["profile_draft"])
        raise AssertionError(f"FakeGemini: unexpected schema {schema.__name__}")

    def embed(self, texts):
        self.calls["embed"] += 1
        if self.fail_with is not None:
            raise self.fail_with
        return [self._vector(t) for t in texts]

    def _vector(self, text: str) -> list[float]:
        # Deterministic orthogonal vectors: identical normalized strings get
        # identical one-hot vectors (cosine 1.0), distinct strings get
        # orthogonal ones (cosine 0.0) — exact, repeatable gap results.
        key = " ".join(text.lower().split())
        index = self._dims.setdefault(key, len(self._dims))
        vector = [0.0] * 4096
        vector[index] = 1.0
        return vector

"""Seed the sample dataset into Supabase for an instant, Gemini-free demo.

Creates a confirmed demo user, then loads every persona from
data/samples/dataset.json: resume file (DOCX built from the sample text),
parsed resume with both scores, job description, gap report, interview set,
and profile draft. Idempotent — rows already present (matched by content
hash) are skipped, so re-running is safe.

Usage (from the repo root, with .env filled in):
    .venv/bin/python scripts/seed.py

Demo login (printed on success):
    email    demo@hireorhigher.dev
    password $DEMO_USER_PASSWORD or the default below

Uses SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY. Uses no Gemini key — scores
and generated content come from the dataset; the ATS score is recomputed with
the real rule-based scorer so seeded rows match live behavior exactly.
"""

import io
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.config import get_settings  # noqa: E402
from app.core.file_validation import CONTENT_TYPES  # noqa: E402
from app.core.hashing import combined_hash, sha256_bytes, sha256_text  # noqa: E402
from app.db.repository import SupabaseRepository  # noqa: E402
from app.db.supabase_client import get_supabase  # noqa: E402
from app.models.resume import ParsedResume  # noqa: E402
from app.services.ats_scorer import score_resume  # noqa: E402

DATASET_PATH = REPO_ROOT / "data" / "samples" / "dataset.json"
DEMO_EMAIL = "demo@hireorhigher.dev"
DEMO_PASSWORD = os.environ.get("DEMO_USER_PASSWORD", "HireOrHigher-Demo-2026")


def build_docx(text: str) -> bytes:
    """Build the persona's resume DOCX in memory from the sample text."""
    import docx

    document = docx.Document()
    for line in text.splitlines():
        document.add_paragraph(line)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def ensure_demo_user(client) -> str:
    """Create (or find) the confirmed demo auth user; return its id."""
    try:
        result = client.auth.admin.create_user(
            {
                "email": DEMO_EMAIL,
                "password": DEMO_PASSWORD,
                "email_confirm": True,
            }
        )
        return str(result.user.id)
    except Exception:  # noqa: BLE001 — most likely "already registered"
        users = client.auth.admin.list_users()
        for user in users:
            if user.email == DEMO_EMAIL:
                return str(user.id)
        raise


def seed_persona(repo: SupabaseRepository, user_id: str, persona: dict) -> str:
    key = persona["key"]
    file_bytes = build_docx(persona["resume_text"])
    resume_hash = sha256_bytes(file_bytes)

    if repo.get_resume_by_hash(user_id, resume_hash) is not None:
        return f"  [{key}] already seeded — skipped"

    parsed = ParsedResume.model_validate(persona["parsed"])
    ats_score = score_resume(
        persona["resume_text"], parsed.structured_field_count(), "docx"
    )
    file_url = repo.upload_resume_file(
        user_id,
        f"{resume_hash[:12]}_{persona['resume_filename']}",
        file_bytes,
        CONTENT_TYPES["docx"],
    )
    resume = repo.insert_resume(
        {
            "user_id": user_id,
            "file_url": file_url,
            "content_hash": resume_hash,
            "parsed_json": parsed.model_dump(),
            "ats_score": ats_score.model_dump(),
            "human_score": persona["human_score"],
        }
    )

    jd_text = persona["job_description"]["raw_text"]
    jd_hash = sha256_text(jd_text)
    jd = repo.get_jd_by_hash(user_id, jd_hash) or repo.insert_job_description(
        {
            "user_id": user_id,
            "raw_text": jd_text,
            "content_hash": jd_hash,
            "parsed_requirements": persona["job_description"]["requirements"],
        }
    )

    pair_hash = combined_hash(resume_hash, jd_hash)
    gap = persona["expected_gap"]
    repo.insert_gap_report(
        {
            "resume_id": resume["id"],
            "jd_id": jd["id"],
            "content_hash": pair_hash,
            "matched": gap["matched"],
            "missing": gap["missing"],
            "match_percentage": gap["match_percentage"],
        }
    )
    repo.insert_interview_set(
        {
            "resume_id": resume["id"],
            "jd_id": jd["id"],
            "content_hash": pair_hash,
            "questions": persona["interview_questions"],
        }
    )
    draft = persona["profile_draft"]
    repo.insert_profile_draft(
        {
            "resume_id": resume["id"],
            "content_hash": resume_hash,
            "headline": draft["headline"],
            "about": draft["about"],
            "project_descriptions": draft["project_descriptions"],
        }
    )
    return f"  [{key}] seeded resume {resume['id']} with all four module results"


def main() -> None:
    settings = get_settings()
    settings.validate_required()

    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    client = get_supabase()
    repo = SupabaseRepository(client)

    print("Ensuring demo user exists…")
    user_id = ensure_demo_user(client)

    print(f"Seeding {len(dataset['personas'])} persona(s)…")
    for persona in dataset["personas"]:
        print(seed_persona(repo, user_id, persona))

    print("\nDone. Demo login:")
    print(f"  email:    {DEMO_EMAIL}")
    print(f"  password: {DEMO_PASSWORD}")


if __name__ == "__main__":
    main()

"""Module 5.1 integration tests — real sample resume through the endpoint.

Covers the spec's acceptance criteria: both scores returned with populated
breakdowns, and an identical re-upload served from the cache with no second
Gemini call.
"""

from app.core.gemini import GeminiError
from app.models.resume import HumanScore, ParsedResume, ResumeAnalysis
from tests.fakes import build_docx

DOCX_CT = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def upload_resume(client, dataset, key="asha"):
    persona = next(p for p in dataset["personas"] if p["key"] == key)
    payload = build_docx(persona["resume_text"])
    return client.post(
        "/api/resumes",
        files={"file": (persona["resume_filename"], payload, DOCX_CT)},
    )


def test_upload_returns_dual_scores_with_populated_breakdowns(client, dataset):
    response = upload_resume(client, dataset)
    assert response.status_code == 200
    body = response.json()

    assert body["resume_id"]
    assert body["cached"] is False
    assert body["parsed"]["name"] == "Asha Venkat"
    assert body["parsed"]["skills"], "parsed skills must be populated"
    assert body["parsed"]["experience"], "parsed experience must be populated"

    ats = body["ats_score"]
    assert 0 <= ats["value"] <= 100
    assert ats["breakdown"], "ATS breakdown must not be empty"
    assert all("check" in c and "passed" in c for c in ats["breakdown"])

    human = body["human_score"]
    assert 0 <= human["value"] <= 100
    assert human["breakdown"], "human-readability breakdown must not be empty"


def test_identical_reupload_hits_cache_without_gemini_call(
    client, dataset, fake_gemini
):
    first = upload_resume(client, dataset)
    second = upload_resume(client, dataset)

    assert second.status_code == 200
    assert second.json()["cached"] is True
    assert second.json()["resume_id"] == first.json()["resume_id"]
    assert fake_gemini.calls["ResumeAnalysis"] == 1, (
        "an identical re-upload must be served from the content-hash cache, "
        "not a second Gemini call"
    )


def test_rejects_disguised_text_file(client):
    response = client.post(
        "/api/resumes",
        files={"file": ("resume.pdf", b"plain text pretending", "application/pdf")},
    )
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_rejects_oversized_upload(client):
    blob = b"%PDF-" + b"0" * (5 * 1024 * 1024)
    response = client.post(
        "/api/resumes", files={"file": ("big.pdf", blob, "application/pdf")}
    )
    assert response.status_code == 400
    assert "too large" in response.json()["detail"]


def test_garbled_parse_asks_for_reupload(client, dataset, fake_gemini):
    fake_gemini.overrides["ResumeAnalysis"] = ResumeAnalysis(
        parsed=ParsedResume(),  # zero structured fields extracted
        human_score=HumanScore(value=10, breakdown=["unreadable"]),
    )
    response = upload_resume(client, dataset)
    assert response.status_code == 422
    assert "re-upload" in response.json()["detail"]


def test_gemini_failure_after_retry_returns_clear_502(client, dataset, fake_gemini):
    fake_gemini.fail_with = GeminiError("resume_parser", "quota exhausted")
    response = upload_resume(client, dataset)
    assert response.status_code == 502
    assert "temporarily unavailable" in response.json()["detail"]


def test_stored_resume_is_retrievable_after_reload(client, dataset):
    resume_id = upload_resume(client, dataset).json()["resume_id"]
    response = client.get(f"/api/resumes/{resume_id}")
    assert response.status_code == 200
    assert response.json()["parsed"]["name"] == "Asha Venkat"

    listing = client.get("/api/resumes")
    assert listing.status_code == 200
    assert [r["id"] for r in listing.json()] == [resume_id]
    assert listing.json()[0]["name"] == "Asha Venkat", (
        "the listing must carry the parsed name for the resume switcher"
    )

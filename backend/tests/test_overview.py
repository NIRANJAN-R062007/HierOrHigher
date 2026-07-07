"""Dashboard overview test — all four modules' persisted results, one call.

Simulates the MVP definition of done: run the full pipeline once, then verify
a "reload" renders everything from storage with zero additional Gemini calls.
"""

from tests.test_gap_module import create_gap_report
from tests.test_interview_module import create_interview_set
from tests.test_profile_module import create_profile_draft
from tests.test_resume_module import upload_resume


def test_overview_returns_all_module_results_without_reprocessing(
    client, dataset, fake_gemini
):
    resume_id = upload_resume(client, dataset).json()["resume_id"]
    gap = create_gap_report(client, dataset, resume_id).json()
    create_interview_set(client, resume_id, gap["jd_id"])
    create_profile_draft(client, resume_id)

    calls_before = dict(fake_gemini.calls)
    response = client.get(f"/api/resumes/{resume_id}/overview")
    assert response.status_code == 200
    body = response.json()

    assert body["resume"]["parsed"]["name"] == "Asha Venkat"
    assert body["gap_report"]["missing"] == ["Kubernetes", "GraphQL", "Terraform"]
    assert 8 <= len(body["interview_set"]["questions"]) <= 10
    assert body["profile_draft"]["headline"]["concise"].strip()
    assert body["job_description_text"], "JD text must persist for the dashboard"

    assert dict(fake_gemini.calls) == calls_before, (
        "reloading the dashboard must not trigger any Gemini call"
    )


def test_overview_with_only_resume_has_null_sections(client, dataset):
    resume_id = upload_resume(client, dataset).json()["resume_id"]
    body = client.get(f"/api/resumes/{resume_id}/overview").json()
    assert body["resume"]["resume_id"] == resume_id
    assert body["gap_report"] is None
    assert body["interview_set"] is None
    assert body["profile_draft"] is None

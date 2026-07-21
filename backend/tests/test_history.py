"""History endpoints — list past runs per module and re-open one in full.

Every create_* call persists a new content-hash-keyed row; these tests cover
the read-only endpoints that expose those rows (list = lightweight summaries,
detail = full record) without spending any Gemini key.
"""

import uuid

from tests.test_gap_module import create_gap_report
from tests.test_interview_module import create_interview_set
from tests.test_profile_module import create_profile_draft
from tests.test_resume_module import upload_resume


def _dates_non_increasing(items) -> bool:
    dates = [item["created_at"] for item in items]
    return dates == sorted(dates, reverse=True)


# -- gap reports ---------------------------------------------------------------


def test_gap_history_lists_every_run_newest_first(client, dataset):
    resume_id = upload_resume(client, dataset).json()["resume_id"]
    first = create_gap_report(client, dataset, resume_id, key="asha").json()
    second = create_gap_report(client, dataset, resume_id, key="rohan").json()

    response = client.get(f"/api/gap-reports?resume_id={resume_id}")
    assert response.status_code == 200
    items = response.json()

    assert {i["id"] for i in items} == {
        first["gap_report_id"],
        second["gap_report_id"],
    }
    assert _dates_non_increasing(items)
    for item in items:  # the lightweight summary carries the match percentage
        assert 0 <= item["match_percentage"] <= 100


def test_gap_history_detail_returns_the_full_record(client, dataset):
    resume_id = upload_resume(client, dataset).json()["resume_id"]
    created = create_gap_report(client, dataset, resume_id, key="asha").json()

    body = client.get(
        f"/api/gap-reports/{created['gap_report_id']}?resume_id={resume_id}"
    ).json()

    assert body["gap_report_id"] == created["gap_report_id"]
    assert body["matched"] == created["matched"]
    assert body["missing"] == created["missing"]
    assert body["source"] == "gemini"
    assert body["cached"] is True


def test_gap_history_unknown_resume_is_404(client):
    response = client.get(f"/api/gap-reports?resume_id={uuid.uuid4()}")
    assert response.status_code == 404


def test_gap_detail_unknown_id_is_404(client, dataset):
    resume_id = upload_resume(client, dataset).json()["resume_id"]
    response = client.get(f"/api/gap-reports/{uuid.uuid4()}?resume_id={resume_id}")
    assert response.status_code == 404


def test_history_reads_never_spend_gemini(client, dataset, fake_gemini):
    resume_id = upload_resume(client, dataset).json()["resume_id"]
    create_gap_report(client, dataset, resume_id).json()

    calls_before = dict(fake_gemini.calls)
    listing = client.get(f"/api/gap-reports?resume_id={resume_id}").json()
    client.get(f"/api/gap-reports/{listing[0]['id']}?resume_id={resume_id}")
    assert dict(fake_gemini.calls) == calls_before, "history reads must not call Gemini"


# -- interview sets ------------------------------------------------------------


def _two_jd_ids(client, dataset, resume_id) -> tuple[str, str]:
    jd_a = create_gap_report(client, dataset, resume_id, key="asha").json()["jd_id"]
    jd_b = create_gap_report(client, dataset, resume_id, key="rohan").json()["jd_id"]
    return jd_a, jd_b


def test_interview_history_lists_every_run(client, dataset):
    resume_id = upload_resume(client, dataset).json()["resume_id"]
    jd_a, jd_b = _two_jd_ids(client, dataset, resume_id)
    set_a = create_interview_set(client, resume_id, jd_a).json()
    set_b = create_interview_set(client, resume_id, jd_b).json()

    items = client.get(f"/api/interview-sets?resume_id={resume_id}").json()
    assert {i["id"] for i in items} == {
        set_a["interview_set_id"],
        set_b["interview_set_id"],
    }
    assert _dates_non_increasing(items)


def test_interview_history_detail_returns_the_questions(client, dataset):
    resume_id = upload_resume(client, dataset).json()["resume_id"]
    jd_a, _ = _two_jd_ids(client, dataset, resume_id)
    created = create_interview_set(client, resume_id, jd_a).json()

    body = client.get(
        f"/api/interview-sets/{created['interview_set_id']}?resume_id={resume_id}"
    ).json()

    assert body["interview_set_id"] == created["interview_set_id"]
    assert 8 <= len(body["questions"]) <= 10
    assert body["cached"] is True


# -- profile drafts ------------------------------------------------------------


def test_profile_history_lists_the_single_cached_draft(client, dataset):
    resume_id = upload_resume(client, dataset).json()["resume_id"]
    created = create_profile_draft(client, resume_id).json()
    # Re-running hits the per-resume-hash cache — no new row is written.
    create_profile_draft(client, resume_id)

    items = client.get(f"/api/profile-drafts?resume_id={resume_id}").json()
    assert [i["id"] for i in items] == [created["profile_draft_id"]]


def test_profile_history_detail_returns_the_full_draft(client, dataset):
    resume_id = upload_resume(client, dataset).json()["resume_id"]
    created = create_profile_draft(client, resume_id).json()

    body = client.get(
        f"/api/profile-drafts/{created['profile_draft_id']}?resume_id={resume_id}"
    ).json()

    assert body["profile_draft_id"] == created["profile_draft_id"]
    assert body["headline"]["concise"].strip()
    assert body["cached"] is True

"""Public candidate intake and the recruiter's ranked screening view.

The end-to-end path this file covers: a recruiter opens a posting, a visitor
with no account submits a resume to its public link, and the recruiter sees
that candidate ranked with matched and missing skills.

Two properties get the most attention because they are the point of the
feature. First, the apply route really is unauthenticated — proven by making
``get_current_user`` fail outright and submitting anyway. Second, the score
never travels back to the candidate.
"""

import uuid

from fastapi import HTTPException

from app.api import deps
from app.main import app
from tests.fakes import build_docx
from tests.test_job_posting_module import create_posting, open_posting
from tests.test_recruiter_org_module import OUTSIDER_ID, as_user, create_org
from tests.test_resume_module import DOCX_CT


def sign_everyone_out() -> None:
    """Make authentication fail for the rest of the test.

    Any route that touches ``get_current_user`` now 401s, so a request that
    still succeeds provably never asked who the caller was.
    """

    def _no_session():
        raise HTTPException(status_code=401, detail="Missing bearer token.")

    app.dependency_overrides[deps.get_current_user] = _no_session


def apply_to(client, dataset, posting_id, key="asha", **form):
    persona = next(p for p in dataset["personas"] if p["key"] == key)
    return client.post(
        f"/api/apply/{posting_id}",
        files={
            "file": (
                persona["resume_filename"],
                build_docx(persona["resume_text"]),
                DOCX_CT,
            )
        },
        data=form,
    )


def test_apply_page_is_readable_without_a_session(client, dataset):
    _, posting_id = open_posting(client, dataset)

    sign_everyone_out()
    response = client.get(f"/api/apply/{posting_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Backend Engineer"
    assert body["organization_name"] == "CloudCore Recruiting"
    assert body["description"]
    # The public projection carries the role and who it is at — nothing about
    # the org's other postings, its members, or anyone else's application.
    assert set(body) == {"id", "title", "description", "organization_name"}


def test_a_visitor_with_no_account_can_submit(client, dataset):
    _, posting_id = open_posting(client, dataset)

    sign_everyone_out()
    response = apply_to(client, dataset, posting_id)

    assert response.status_code == 200, "the apply route must not require auth"
    body = response.json()
    assert body["application_id"]
    assert body["posting_title"] == "Backend Engineer"
    assert body["candidate_name"] == "Asha Venkat"
    assert body["already_applied"] is False


def test_the_receipt_never_carries_the_score(client, dataset):
    _, posting_id = open_posting(client, dataset)
    body = apply_to(client, dataset, posting_id).json()

    assert set(body) == {
        "application_id",
        "posting_title",
        "candidate_name",
        "already_applied",
    }, "screening results are recruiter-only and must not leak to the candidate"


def test_submitted_candidate_appears_ranked_with_skills(client, dataset):
    _, posting_id = open_posting(client, dataset)
    apply_to(client, dataset, posting_id)

    applicants = client.get(f"/api/job-postings/{posting_id}/applications").json()
    assert len(applicants) == 1

    expected = next(p for p in dataset["personas"] if p["key"] == "asha")[
        "expected_gap"
    ]
    applicant = applicants[0]
    assert applicant["name"] == "Asha Venkat"
    assert applicant["match_percentage"] == expected["match_percentage"]
    assert applicant["matched"] == expected["matched"]
    assert applicant["missing"] == expected["missing"]
    assert applicant["candidate_id"]


def test_applicants_are_ranked_by_match_percentage(client, dataset):
    _, posting_id = open_posting(client, dataset)
    apply_to(client, dataset, posting_id, key="rohan")
    apply_to(client, dataset, posting_id, key="asha")

    applicants = client.get(f"/api/job-postings/{posting_id}/applications").json()
    scores = [a["match_percentage"] for a in applicants]

    assert len(applicants) == 2
    assert scores == sorted(scores, reverse=True), "best match first"
    # Asha's resume is the one written against this JD, so she must outrank
    # the analytics resume even though it applied first.
    assert applicants[0]["name"] == "Asha Venkat"
    assert applicants[0]["match_percentage"] > applicants[1]["match_percentage"]


def test_self_reported_name_and_email_win_over_the_parse(client, dataset):
    _, posting_id = open_posting(client, dataset)
    apply_to(
        client,
        dataset,
        posting_id,
        name="A. Venkat",
        email="Asha.Applies@Example.com",
    )

    applicant = client.get(f"/api/job-postings/{posting_id}/applications").json()[0]
    assert applicant["name"] == "A. Venkat"
    assert applicant["email"] == "asha.applies@example.com"


def test_resubmitting_the_same_resume_spends_no_gemini(client, dataset, fake_gemini):
    _, posting_id = open_posting(client, dataset)
    first = apply_to(client, dataset, posting_id)
    before = dict(fake_gemini.calls)

    second = apply_to(client, dataset, posting_id)

    assert second.json()["already_applied"] is True
    assert second.json()["application_id"] == first.json()["application_id"]
    assert dict(fake_gemini.calls) == before, "an unchanged resubmission re-scores nothing"
    assert len(client.get(f"/api/job-postings/{posting_id}/applications").json()) == 1


def test_one_resume_across_two_postings_is_parsed_once(client, dataset, fake_gemini):
    org_id, first_posting = open_posting(client, dataset)
    second_posting = create_posting(
        client, org_id, dataset, status="open", key="rohan"
    ).json()["id"]

    apply_to(client, dataset, first_posting)
    apply_to(client, dataset, second_posting)

    assert fake_gemini.calls["ResumeAnalysis"] == 1, (
        "a resume this org has already seen is one candidate, parsed once"
    )
    # Scored against both postings all the same.
    for posting_id in (first_posting, second_posting):
        assert len(client.get(f"/api/job-postings/{posting_id}/applications").json()) == 1


def test_posting_requirements_are_extracted_once_per_description(
    client, dataset, fake_gemini
):
    _, posting_id = open_posting(client, dataset)
    apply_to(client, dataset, posting_id, key="asha")
    apply_to(client, dataset, posting_id, key="rohan")

    assert fake_gemini.calls["JDRequirements"] == 1, (
        "the second applicant reuses the requirements cached on the posting"
    )


def test_editing_the_description_rescores_the_next_applicant(
    client, dataset, fake_gemini
):
    _, posting_id = open_posting(client, dataset)
    apply_to(client, dataset, posting_id)
    assert fake_gemini.calls["JDRequirements"] == 1

    client.patch(
        f"/api/job-postings/{posting_id}",
        json={
            "description": next(
                p for p in dataset["personas"] if p["key"] == "rohan"
            )["job_description"]["raw_text"]
        },
    )
    apply_to(client, dataset, posting_id)

    assert fake_gemini.calls["JDRequirements"] == 2, (
        "a changed description invalidates the cached requirements by hash"
    )
    applicants = client.get(f"/api/job-postings/{posting_id}/applications").json()
    assert len(applicants) == 1, "still one application, re-scored in place"


def test_draft_postings_have_no_live_apply_link(client, dataset):
    org_id = create_org(client).json()["id"]
    posting_id = create_posting(client, org_id, dataset).json()["id"]

    assert client.get(f"/api/apply/{posting_id}").status_code == 404
    assert apply_to(client, dataset, posting_id).status_code == 404


def test_closing_a_posting_takes_its_apply_link_down(client, dataset):
    _, posting_id = open_posting(client, dataset)
    apply_to(client, dataset, posting_id)
    client.patch(f"/api/job-postings/{posting_id}", json={"status": "closed"})

    assert client.get(f"/api/apply/{posting_id}").status_code == 404
    assert apply_to(client, dataset, posting_id, key="rohan").status_code == 404
    # Applicants received while it was open remain on the screening view.
    assert len(client.get(f"/api/job-postings/{posting_id}/applications").json()) == 1


def test_unknown_posting_is_404(client, dataset):
    assert client.get(f"/api/apply/{uuid.uuid4()}").status_code == 404


def test_public_upload_gets_the_same_file_validation(client, dataset, fake_gemini):
    _, posting_id = open_posting(client, dataset)

    response = client.post(
        f"/api/apply/{posting_id}",
        files={"file": ("resume.pdf", b"plain text pretending", "application/pdf")},
    )
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]
    assert fake_gemini.calls["ResumeAnalysis"] == 0, (
        "validation must reject before any Gemini key is spent"
    )


def test_public_upload_rejects_unreadable_documents(client, dataset, fake_gemini):
    _, posting_id = open_posting(client, dataset)

    response = client.post(
        f"/api/apply/{posting_id}",
        files={"file": ("resume.docx", build_docx("Hi"), DOCX_CT)},
    )
    assert response.status_code == 422
    assert fake_gemini.calls["ResumeAnalysis"] == 0


def test_candidates_are_invisible_to_other_orgs(client, dataset):
    _, posting_id = open_posting(client, dataset)
    apply_to(client, dataset, posting_id)

    as_user(OUTSIDER_ID, "outsider@example.com")
    create_org(client, "Rival Talent")
    assert (
        client.get(f"/api/job-postings/{posting_id}/applications").status_code == 404
    )


def test_apply_endpoint_is_rate_limited_per_posting(client, dataset):
    """The limiter keys on posting + client IP, since there is no user id.

    The cap is 5/hour, and it is checked before the cache short-circuit — so
    repeated identical submissions still count, which is exactly what stops a
    script from hammering the endpoint.
    """
    _, posting_id = open_posting(client, dataset)

    statuses = [
        apply_to(client, dataset, posting_id).status_code for _ in range(6)
    ]
    assert statuses[:5] == [200] * 5
    assert statuses[5] == 429

    # Other postings are unaffected — the key includes the posting id.
    _, other_posting = open_posting(client, dataset)
    assert apply_to(client, dataset, other_posting).status_code == 200

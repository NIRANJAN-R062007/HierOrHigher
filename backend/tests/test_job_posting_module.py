"""Job-posting CRUD and its org gating.

A posting id is a bearer of nothing on the authenticated side: every route
re-derives access from the caller's membership in the posting's org, which is
what these tests pin.
"""

from tests.test_recruiter_org_module import OUTSIDER_ID, as_user, create_org


def jd_text(dataset, key="asha"):
    persona = next(p for p in dataset["personas"] if p["key"] == key)
    return persona["job_description"]["raw_text"]


def create_posting(client, org_id, dataset, *, status="draft", key="asha"):
    return client.post(
        "/api/job-postings",
        json={
            "org_id": org_id,
            "title": "Backend Engineer",
            "description": jd_text(dataset, key),
            "status": status,
        },
    )


def open_posting(client, dataset, key="asha"):
    """The common setup: an org with one open posting, ready to receive
    applications. Returns (org_id, posting_id)."""
    org_id = create_org(client).json()["id"]
    posting = create_posting(client, org_id, dataset, status="open", key=key)
    return org_id, posting.json()["id"]


def test_create_posting_defaults_to_draft_with_an_apply_path(client, dataset):
    org_id = create_org(client).json()["id"]
    response = create_posting(client, org_id, dataset)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "draft"
    assert body["org_id"] == org_id
    assert body["application_count"] == 0
    assert body["apply_path"] == f"/apply/{body['id']}"


def test_posting_description_must_be_substantial(client, dataset):
    org_id = create_org(client).json()["id"]
    response = client.post(
        "/api/job-postings",
        json={"org_id": org_id, "title": "Backend Engineer", "description": "hiring"},
    )
    assert response.status_code == 422


def test_cannot_create_a_posting_in_someone_elses_org(client, dataset):
    org_id = create_org(client).json()["id"]

    as_user(OUTSIDER_ID, "outsider@example.com")
    assert create_posting(client, org_id, dataset).status_code == 404


def test_listing_is_scoped_to_the_org(client, dataset):
    org_id = create_org(client).json()["id"]
    posting_id = create_posting(client, org_id, dataset).json()["id"]

    listing = client.get(f"/api/job-postings?org_id={org_id}")
    assert [p["id"] for p in listing.json()] == [posting_id]

    as_user(OUTSIDER_ID, "outsider@example.com")
    assert client.get(f"/api/job-postings?org_id={org_id}").status_code == 404


def test_a_posting_is_not_readable_by_another_org(client, dataset):
    _, posting_id = open_posting(client, dataset)

    as_user(OUTSIDER_ID, "outsider@example.com")
    create_org(client, "Rival Talent")
    assert client.get(f"/api/job-postings/{posting_id}").status_code == 404
    assert (
        client.get(f"/api/job-postings/{posting_id}/applications").status_code == 404
    )


def test_editing_a_posting(client, dataset):
    org_id = create_org(client).json()["id"]
    posting_id = create_posting(client, org_id, dataset).json()["id"]

    response = client.patch(
        f"/api/job-postings/{posting_id}",
        json={"title": "Senior Backend Engineer", "status": "open"},
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Senior Backend Engineer"
    assert response.json()["status"] == "open"


def test_closing_a_posting_keeps_it_visible_to_the_org(client, dataset):
    _, posting_id = open_posting(client, dataset)

    assert (
        client.patch(
            f"/api/job-postings/{posting_id}", json={"status": "closed"}
        ).json()["status"]
        == "closed"
    )
    # Closing takes the public link down (see test_apply_module) but the
    # posting and its applicants stay readable to the recruiter.
    assert client.get(f"/api/job-postings/{posting_id}").status_code == 200


def test_empty_patch_leaves_the_posting_unchanged(client, dataset):
    org_id = create_org(client).json()["id"]
    created = create_posting(client, org_id, dataset).json()

    response = client.patch(f"/api/job-postings/{created['id']}", json={})
    assert response.status_code == 200
    assert response.json()["title"] == created["title"]
    assert response.json()["status"] == created["status"]


def test_unknown_posting_is_404(client):
    assert (
        client.get("/api/job-postings/44444444-4444-4444-4444-444444444444").status_code
        == 404
    )


def test_applications_list_is_empty_before_anyone_applies(client, dataset):
    _, posting_id = open_posting(client, dataset)
    response = client.get(f"/api/job-postings/{posting_id}/applications")
    assert response.status_code == 200
    assert response.json() == []

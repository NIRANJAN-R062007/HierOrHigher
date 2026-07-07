"""Module 5.4 integration tests — tone variants, reuse, caching."""

import uuid

from tests.test_resume_module import upload_resume


def create_profile_draft(client, resume_id):
    return client.post("/api/profile-drafts", json={"resume_id": resume_id})


def test_draft_has_two_tone_variants_for_every_output(client, dataset):
    resume_id = upload_resume(client, dataset).json()["resume_id"]
    response = create_profile_draft(client, resume_id)
    assert response.status_code == 200
    body = response.json()

    assert body["profile_draft_id"]
    for section in ("headline", "about"):
        assert body[section]["concise"].strip()
        assert body[section]["detailed"].strip()
    projects = body["project_descriptions"]
    assert 1 <= len(projects) <= 3
    for project in projects:
        assert project["title"].strip()
        assert project["concise"].strip()
        assert project["detailed"].strip()


def test_optimizer_reuses_parse_without_reentry(client, dataset, fake_gemini):
    resume_id = upload_resume(client, dataset).json()["resume_id"]
    create_profile_draft(client, resume_id)
    assert fake_gemini.calls["ResumeAnalysis"] == 1, (
        "module 5.4 must reuse module 5.1's stored parse, never re-parse"
    )
    assert fake_gemini.calls["ProfileDraftContent"] == 1


def test_repeat_draft_hits_cache(client, dataset, fake_gemini):
    resume_id = upload_resume(client, dataset).json()["resume_id"]
    first = create_profile_draft(client, resume_id)
    second = create_profile_draft(client, resume_id)

    assert second.json()["cached"] is True
    assert second.json()["profile_draft_id"] == first.json()["profile_draft_id"]
    assert fake_gemini.calls["ProfileDraftContent"] == 1, "cache hit must skip Gemini"


def test_unknown_resume_returns_404(client):
    response = create_profile_draft(client, str(uuid.uuid4()))
    assert response.status_code == 404

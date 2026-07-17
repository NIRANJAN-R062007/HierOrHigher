"""Module 5.2 integration tests — real sample resume/JD pair through the endpoint.

Covers the spec's acceptance criteria: the pair marked "should show 3 missing
skills" returns exactly those 3, and the mapper reuses module 5.1's stored
parse instead of re-calling the parser.
"""

import uuid

from app.api import deps
from app.main import app
from tests.fakes import FakeMatchScorer
from tests.test_resume_module import upload_resume


def create_gap_report(client, dataset, resume_id, key="asha"):
    persona = next(p for p in dataset["personas"] if p["key"] == key)
    return client.post(
        "/api/gap-reports",
        json={
            "resume_id": resume_id,
            "job_description": persona["job_description"]["raw_text"],
        },
    )


def test_marked_pair_returns_exactly_three_missing_skills(client, dataset):
    resume_id = upload_resume(client, dataset).json()["resume_id"]
    response = create_gap_report(client, dataset, resume_id)
    assert response.status_code == 200
    body = response.json()

    expected = next(p for p in dataset["personas"] if p["key"] == "asha")[
        "expected_gap"
    ]
    assert body["missing"] == expected["missing"], (
        "the fixture marked 'should show 3 missing skills' must return exactly those"
    )
    assert len(body["missing"]) == 3
    assert body["matched"] == expected["matched"]
    assert body["match_percentage"] == expected["match_percentage"]
    assert body["resume_id"] == resume_id
    assert body["gap_report_id"]
    assert body["cached"] is False


def test_gap_mapper_never_recalls_the_resume_parser(client, dataset, fake_gemini):
    resume_id = upload_resume(client, dataset).json()["resume_id"]
    assert fake_gemini.calls["ResumeAnalysis"] == 1

    create_gap_report(client, dataset, resume_id)
    assert fake_gemini.calls["ResumeAnalysis"] == 1, (
        "module 5.2 must reuse module 5.1's stored parse, never re-parse"
    )
    assert fake_gemini.calls["JDRequirements"] == 1
    assert fake_gemini.calls["embed"] == 1


def test_identical_resume_jd_pair_hits_cache(client, dataset, fake_gemini):
    resume_id = upload_resume(client, dataset).json()["resume_id"]
    first = create_gap_report(client, dataset, resume_id)
    second = create_gap_report(client, dataset, resume_id)

    assert second.status_code == 200
    assert second.json()["cached"] is True
    assert second.json()["gap_report_id"] == first.json()["gap_report_id"]
    assert fake_gemini.calls["JDRequirements"] == 1, "cache hit must skip Gemini"
    assert fake_gemini.calls["embed"] == 1, "cache hit must skip embeddings"


def test_unknown_resume_returns_404(client, dataset):
    response = create_gap_report(client, dataset, str(uuid.uuid4()))
    assert response.status_code == 404


def test_second_persona_pair_maps_correctly(client, dataset):
    resume_id = upload_resume(client, dataset, key="rohan").json()["resume_id"]
    body = create_gap_report(client, dataset, resume_id, key="rohan").json()
    expected = next(p for p in dataset["personas"] if p["key"] == "rohan")[
        "expected_gap"
    ]
    assert body["missing"] == expected["missing"]
    assert body["match_percentage"] == expected["match_percentage"]


def test_confident_ml_score_spends_zero_gemini_quota(client, dataset, fake_gemini):
    """Hybrid rule: a confident offline score serves the whole report."""
    scorer = FakeMatchScorer(
        match_score=88.4, confidence=0.95,
        resume_skills={"Python", "FastAPI", "Docker"},
        jd_skills={"Python", "FastAPI", "Kubernetes"},
    )
    app.dependency_overrides[deps.get_ml_scorer] = lambda: scorer

    resume_id = upload_resume(client, dataset).json()["resume_id"]
    body = create_gap_report(client, dataset, resume_id).json()

    assert body["source"] == "ml"
    assert body["matched"] == ["FastAPI", "Python"]
    assert body["missing"] == ["Kubernetes"]
    assert body["match_percentage"] == 88
    assert body["ml_score"]["label"] == "Strong Fit"
    assert body["ml_score"]["recommend_gemini_review"] is False
    assert fake_gemini.calls["JDRequirements"] == 0, "confident ML must skip Gemini"
    assert fake_gemini.calls["embed"] == 0, "confident ML must skip embeddings"

    cached = create_gap_report(client, dataset, resume_id).json()
    assert cached["cached"] is True
    assert cached["source"] == "ml"
    assert scorer.predict_calls == 1, "cache hit must skip the model too"


def test_unsure_ml_escalates_to_gemini(client, dataset, fake_gemini):
    """Ambiguous-band score (45-55) falls back to the embedding pipeline."""
    scorer = FakeMatchScorer(
        match_score=50.0, confidence=0.9,
        resume_skills={"Python"}, jd_skills={"Python", "Go"},
    )
    app.dependency_overrides[deps.get_ml_scorer] = lambda: scorer

    resume_id = upload_resume(client, dataset).json()["resume_id"]
    body = create_gap_report(client, dataset, resume_id).json()

    expected = next(p for p in dataset["personas"] if p["key"] == "asha")[
        "expected_gap"
    ]
    assert body["source"] == "gemini"
    assert body["missing"] == expected["missing"], (
        "escalated reports must come from the Gemini pipeline unchanged"
    )
    assert body["match_percentage"] == expected["match_percentage"]
    assert body["ml_score"]["recommend_gemini_review"] is True, (
        "the deferred ML result still rides along for the UI"
    )
    assert fake_gemini.calls["JDRequirements"] == 1
    assert fake_gemini.calls["embed"] == 1

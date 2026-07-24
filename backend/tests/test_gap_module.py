"""Module 5.2 integration tests — real sample resume/JD pair through the endpoint.

Covers the spec's acceptance criteria: the pair marked "should show 3 missing
skills" returns exactly those 3, and the mapper reuses module 5.1's stored
parse instead of re-calling the parser.
"""

import uuid

from app.models.gap_report import JDRequirements, SkillCategory
from app.services.gap_service import _group_by_category
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


def test_gap_report_is_always_gemini_sourced(client, dataset):
    """Every fresh report comes from the Gemini pipeline, with no ml_score."""
    resume_id = upload_resume(client, dataset).json()["resume_id"]
    body = create_gap_report(client, dataset, resume_id).json()

    assert body["source"] == "gemini"
    assert body["ml_score"] is None


def test_group_by_category_buckets_and_normalizes():
    grouped = _group_by_category(
        matched=["Python", "React"],
        missing=["Kubernetes"],
        skill_to_category={
            "python": "Languages",
            "react": "Frameworks & Libraries",
            "kubernetes": "Cloud & DevOps",
        },
    )
    assert grouped["Languages"] == {"matched": ["Python"], "missing": []}
    assert grouped["Frameworks & Libraries"]["matched"] == ["React"]
    assert grouped["Cloud & DevOps"]["missing"] == ["Kubernetes"]


def test_group_by_category_is_none_without_tags():
    """No category tags (e.g. a legacy/dataset response) -> flat-view fallback."""
    assert _group_by_category(["Python"], ["Go"], {}) is None


def test_gap_report_groups_requirements_by_category(client, dataset, fake_gemini):
    """When the model tags requirements, the report carries a radar breakdown."""
    persona = next(p for p in dataset["personas"] if p["key"] == "asha")
    reqs = persona["job_description"]["requirements"]
    fake_gemini.overrides["JDRequirements"] = JDRequirements(
        requirements=reqs,
        categories=[SkillCategory(skill=r, category="Languages") for r in reqs],
    )

    resume_id = upload_resume(client, dataset).json()["resume_id"]
    body = create_gap_report(client, dataset, resume_id).json()

    assert body["categories"] is not None
    bucket = body["categories"]["Languages"]
    assert sorted(bucket["matched"]) == sorted(body["matched"])
    assert sorted(bucket["missing"]) == sorted(body["missing"])

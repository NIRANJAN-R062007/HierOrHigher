"""Module 5.3 integration tests — question count, categories, reuse, caching."""

import uuid

from tests.test_gap_module import create_gap_report
from tests.test_resume_module import upload_resume


def create_interview_set(client, resume_id, jd_id):
    return client.post(
        "/api/interview-sets", json={"resume_id": resume_id, "jd_id": jd_id}
    )


def _setup_pair(client, dataset, key="asha"):
    resume_id = upload_resume(client, dataset, key=key).json()["resume_id"]
    gap = create_gap_report(client, dataset, resume_id, key=key).json()
    return resume_id, gap["jd_id"]


def test_generates_8_to_10_categorized_questions(client, dataset):
    resume_id, jd_id = _setup_pair(client, dataset)
    response = create_interview_set(client, resume_id, jd_id)
    assert response.status_code == 200
    body = response.json()

    questions = body["questions"]
    assert 8 <= len(questions) <= 10
    assert body["interview_set_id"]
    categories = {q["category"] for q in questions}
    assert categories <= {"Technical", "Behavioral", "Role-Fit"}
    assert categories == {"Technical", "Behavioral", "Role-Fit"}, (
        "the mix must include all three categories"
    )
    assert all(q["question"].strip() for q in questions)


def test_role_fit_questions_use_identified_gaps(client, dataset):
    resume_id, jd_id = _setup_pair(client, dataset)
    body = create_interview_set(client, resume_id, jd_id).json()
    role_fit_text = " ".join(
        q["question"] for q in body["questions"] if q["category"] == "Role-Fit"
    )
    assert "Kubernetes" in role_fit_text, (
        "Role-Fit questions must be tied to the gaps found by module 5.2"
    )


def test_repeat_generation_hits_cache(client, dataset, fake_gemini):
    resume_id, jd_id = _setup_pair(client, dataset)
    first = create_interview_set(client, resume_id, jd_id)
    second = create_interview_set(client, resume_id, jd_id)

    assert second.json()["cached"] is True
    assert second.json()["interview_set_id"] == first.json()["interview_set_id"]
    assert fake_gemini.calls["InterviewQuestions"] == 1, "cache hit must skip Gemini"


def test_unknown_jd_returns_404(client, dataset):
    resume_id = upload_resume(client, dataset).json()["resume_id"]
    response = create_interview_set(client, resume_id, str(uuid.uuid4()))
    assert response.status_code == 404

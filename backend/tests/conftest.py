"""Shared fixtures: dummy env (set before the app imports), dataset, fakes."""

import json
import os
from pathlib import Path

# Required env vars must exist before app.main imports (fail-fast validation).
_DUMMY_ENV = {
    "GEMINI_API_KEY_RESUME_PARSER": "test-key-resume-parser",
    "GEMINI_API_KEY_GAP_MAPPER": "test-key-gap-mapper",
    "GEMINI_API_KEY_INTERVIEW_GENERATOR": "test-key-interview-generator",
    "GEMINI_API_KEY_PROFILE_OPTIMIZER": "test-key-profile-optimizer",
    "SUPABASE_URL": "https://test.supabase.co",
    "SUPABASE_SERVICE_ROLE_KEY": "test-service-role-key",
}
for _name, _value in _DUMMY_ENV.items():
    os.environ.setdefault(_name, _value)

import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.main import app
from tests.fakes import FakeGemini, FakeRepository

DATASET_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "samples" / "dataset.json"
)

TEST_USER_ID = "11111111-1111-1111-1111-111111111111"


@pytest.fixture(scope="session")
def dataset() -> dict:
    return json.loads(DATASET_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def fake_repo() -> FakeRepository:
    return FakeRepository()


@pytest.fixture
def fake_gemini(dataset) -> FakeGemini:
    return FakeGemini(dataset)


@pytest.fixture
def client(fake_repo, fake_gemini):
    test_user = deps.AuthenticatedUser(id=TEST_USER_ID, email="test@example.com")
    app.dependency_overrides[deps.get_current_user] = lambda: test_user
    app.dependency_overrides[deps.enforce_upload_rate_limit] = lambda: test_user
    app.dependency_overrides[deps.get_repository] = lambda: fake_repo
    for gemini_dep in (
        deps.get_resume_parser_gemini,
        deps.get_gap_mapper_gemini,
        deps.get_interview_generator_gemini,
        deps.get_profile_optimizer_gemini,
    ):
        app.dependency_overrides[gemini_dep] = lambda: fake_gemini
    # No real ML artifact in hermetic tests: the gap mapper sees "scorer
    # unavailable" by default; ML-path tests inject FakeMatchScorer instead.
    app.dependency_overrides[deps.get_ml_scorer] = lambda: None
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

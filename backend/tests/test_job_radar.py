"""Job Radar integration tests — SerpApi mocked via FakeSerpApi (fixture
JSON, no live network), each listing scored through the real Gap Mapper
endpoint machinery (build_gap_report) with FakeGemini/FakeRepository.

Covers: listings without a description are dropped, duplicate job_urls are
deduplicated, results are sorted by match_percentage descending, a
job_radar_searches row is created with the right gap_report_ids, a
zero-results search degrades to an empty list (not an error), and a single
listing's scoring failure is skipped without failing the whole search.
"""

import json
from pathlib import Path

from app.services.serpapi_client import _normalize_results
from tests.test_resume_module import upload_resume

SERPAPI_FIXTURE_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "samples" / "serpapi_sample_response.json"
)


def load_serpapi_listings() -> list[dict]:
    payload = json.loads(SERPAPI_FIXTURE_PATH.read_text(encoding="utf-8"))
    return _normalize_results(payload)


def run_radar_search(client, resume_id, role="backend engineer", location="Remote"):
    return client.post(
        "/api/job-radar",
        json={"resume_id": resume_id, "role": role, "location": location},
    )


def test_fixture_drops_description_less_listings_and_dedupes_by_url():
    listings = load_serpapi_listings()
    # 4 raw entries: 2 CloudCore duplicates (same share_link), 1 Metricly,
    # 1 with no description at all.
    assert len(listings) == 2
    urls = {listing["job_url"] for listing in listings}
    assert len(urls) == 2
    assert all(listing["description"] for listing in listings)


def test_search_scores_each_deduped_listing_and_sorts_descending(client, dataset, fake_serpapi):
    fake_serpapi.listings = load_serpapi_listings()
    resume_id = upload_resume(client, dataset, key="asha").json()["resume_id"]

    response = run_radar_search(client, resume_id)
    assert response.status_code == 200
    body = response.json()

    assert len(body["results"]) == 2
    assert body["skipped_count"] == 0
    percentages = [item["match_percentage"] for item in body["results"]]
    assert percentages == sorted(percentages, reverse=True)
    companies = {item["company"] for item in body["results"]}
    assert companies == {"CloudCore", "Metricly"}
    assert all(item["gap_report_id"] for item in body["results"])


def test_search_creates_job_radar_search_row_with_right_gap_report_ids(
    client, dataset, fake_serpapi, fake_repo
):
    fake_serpapi.listings = load_serpapi_listings()
    resume_id = upload_resume(client, dataset, key="asha").json()["resume_id"]

    body = run_radar_search(client, resume_id).json()

    assert len(fake_repo.job_radar_searches) == 1
    row = next(iter(fake_repo.job_radar_searches.values()))
    assert row["id"] == body["search_id"]
    assert sorted(row["gap_report_ids"]) == sorted(
        item["gap_report_id"] for item in body["results"]
    )
    assert row["role"] == "backend engineer"
    assert row["location"] == "Remote"


def test_zero_results_search_returns_empty_list_not_error(client, dataset, fake_serpapi):
    fake_serpapi.listings = []
    resume_id = upload_resume(client, dataset, key="asha").json()["resume_id"]

    response = run_radar_search(client, resume_id)
    assert response.status_code == 200
    body = response.json()
    assert body["results"] == []
    assert body["skipped_count"] == 0
    assert body["search_id"]


def test_one_bad_listing_is_skipped_without_failing_the_search(client, dataset, fake_serpapi):
    good_listing = load_serpapi_listings()[0]  # CloudCore — matches a persona
    bad_listing = {
        "title": "Unscoreable role",
        "company_name": "Nowhere Inc",
        "location": "Nowhere",
        "description": "Completely unrelated gibberish that matches no known persona at all.",
        "job_url": "https://example.com/jobs/unscoreable-1",
    }
    fake_serpapi.listings = [good_listing, bad_listing]
    resume_id = upload_resume(client, dataset, key="asha").json()["resume_id"]

    response = run_radar_search(client, resume_id)
    assert response.status_code == 200
    body = response.json()

    assert len(body["results"]) == 1
    assert body["results"][0]["company"] == "CloudCore"
    assert body["skipped_count"] == 1


def test_unknown_resume_returns_404(client, fake_serpapi):
    fake_serpapi.listings = load_serpapi_listings()
    response = run_radar_search(client, "00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


def test_past_search_replays_without_new_serpapi_or_gemini_calls(
    client, dataset, fake_serpapi, fake_gemini
):
    fake_serpapi.listings = load_serpapi_listings()
    resume_id = upload_resume(client, dataset, key="asha").json()["resume_id"]
    search_id = run_radar_search(client, resume_id).json()["search_id"]

    calls_before_serpapi = len(fake_serpapi.calls)
    calls_before_gemini = sum(fake_gemini.calls.values())

    replay = client.get(f"/api/job-radar/{search_id}?resume_id={resume_id}")
    assert replay.status_code == 200
    assert len(fake_serpapi.calls) == calls_before_serpapi
    assert sum(fake_gemini.calls.values()) == calls_before_gemini

    body = replay.json()
    assert body["search_id"] == search_id
    assert len(body["results"]) == 2


def test_list_past_searches(client, dataset, fake_serpapi):
    fake_serpapi.listings = load_serpapi_listings()
    resume_id = upload_resume(client, dataset, key="asha").json()["resume_id"]
    run_radar_search(client, resume_id, role="backend engineer", location="Remote")
    run_radar_search(client, resume_id, role="data analyst", location="Pune")

    listing = client.get(f"/api/job-radar?resume_id={resume_id}")
    assert listing.status_code == 200
    rows = listing.json()
    assert len(rows) == 2
    assert {row["role"] for row in rows} == {"backend engineer", "data analyst"}

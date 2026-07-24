"""Analytics dashboard — cross-run match-percentage distribution endpoint."""

from tests.test_gap_module import create_gap_report
from tests.test_resume_module import upload_resume


def test_gap_distribution_lists_the_users_reports(client, dataset):
    resume_id = upload_resume(client, dataset).json()["resume_id"]
    gap = create_gap_report(client, dataset, resume_id).json()

    response = client.get("/api/analytics/gap-distribution")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1
    assert items[0]["match_percentage"] == gap["match_percentage"]
    assert items[0]["jd_id"] == gap["jd_id"]
    assert "created_at" in items[0]


def test_gap_distribution_is_empty_without_reports(client):
    response = client.get("/api/analytics/gap-distribution")
    assert response.status_code == 200
    assert response.json() == []

from __future__ import annotations

from datetime import datetime


def test_projects_timeline_returns_sorted_list(client):
    response = client.get("/projects/timeline")

    assert response.status_code == 200
    data = response.json()

    assert len(data) == 4

    names = [item["project_name"] for item in data]
    # Sorted by first_commit ascending
    assert names == [
        "Platform Core Services",
        "Legacy Data Pipeline",
        "Analytics Dashboard",
        "Mobile Experience",
    ]

    first_commits = [datetime.fromisoformat(item["first_commit"]) for item in data]
    assert first_commits == sorted(first_commits)

    legacy = next(item for item in data if item["project_name"] == "Legacy Data Pipeline")
    assert legacy["duration_days"] == 228
    assert legacy["was_active"] is False


def test_projects_timeline_active_only_filter(client):
    response = client.get("/projects/timeline", params={"active_only": True})

    assert response.status_code == 200
    data = response.json()

    names = {item["project_name"] for item in data}
    assert names == {"Platform Core Services", "Mobile Experience"}
    assert all(item["was_active"] for item in data)


def test_projects_timeline_date_filtering(client):
    response = client.get("/projects/timeline", params={"end_date": "2021-01-01"})

    assert response.status_code == 200
    data = response.json()

    names = {item["project_name"] for item in data}
    assert names == {"Platform Core Services", "Legacy Data Pipeline"}

    end_date = datetime.fromisoformat("2021-01-01").date()
    for item in data:
        first_commit = datetime.fromisoformat(item["first_commit"]).date()
        assert first_commit <= end_date

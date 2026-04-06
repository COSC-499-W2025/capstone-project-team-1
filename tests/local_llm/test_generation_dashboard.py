from __future__ import annotations

from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from artifactminer.local_llm.generation import service
from artifactminer.local_llm.generation.schemas import (
    ProjectFacts,
    ResumeOutputModel,
    ResumeProjectModel,
    ResumeProjectPeriod,
)


def _fact(
    *,
    name: str,
    project_type: str,
    technologies: list[str],
    contribution_pct: float | None,
    first_commit: str | None,
    last_commit: str | None,
    commit_breakdown: dict[str, int],
) -> ProjectFacts:
    return ProjectFacts.model_validate(
        {
            "project_name": name,
            "project_type": project_type,
            "summary": f"{name} summary",
            "technologies": technologies,
            "highlights": [],
            "evidence": [],
            "contribution_pct": contribution_pct,
            "first_commit": first_commit,
            "last_commit": last_commit,
            "commit_breakdown": commit_breakdown,
        }
    )


def _output_with_project(name: str, project_type: str) -> ResumeOutputModel:
    return ResumeOutputModel(
        professional_summary="Summary",
        skills_section="Skills",
        developer_profile="Profile",
        projects=[
            ResumeProjectModel(
                name=name,
                type=project_type,
                period=ResumeProjectPeriod(),
            )
        ],
    )


def test_build_snapshot_includes_daily_commits(monkeypatch) -> None:
    monkeypatch.setattr(
        service,
        "getRepoStats",
        lambda _: SimpleNamespace(
            project_name="demo",
            primary_language="Python",
            Languages=["Python"],
            language_percentages=[100],
            frameworks=["FastAPI"],
            health_score=92.0,
            is_collaborative=False,
            total_commits=15,
            first_commit=datetime(2024, 1, 1, 12, 0, 0),
            last_commit=datetime(2025, 1, 1, 12, 0, 0),
        ),
    )
    monkeypatch.setattr(
        service,
        "getUserRepoStats",
        lambda *_: SimpleNamespace(
            userStatspercentages=73.5,
            total_commits=11,
            commitFrequency=1.4,
            commitActivities={
                "feature": {"commits": 8, "percentage": 72, "lines_added": 210}
            },
        ),
    )
    monkeypatch.setattr(service, "collect_user_additions", lambda **_: ["added line"])
    monkeypatch.setattr(
        service,
        "get_daily_commit_counts",
        lambda *_: {"2025-01-02": 3, "2025-01-03": 2},
    )
    monkeypatch.setattr(service, "_read_readme", lambda *_: "README")
    monkeypatch.setattr(service, "_recent_commit_messages", lambda *_: ["feat: x"])
    monkeypatch.setattr(service, "_sample_files", lambda *_: ["main.py"])

    snapshot = service._build_snapshot(Path("/tmp/demo"), "demo@example.com")

    assert snapshot["daily_commits"] == {"2025-01-02": 3, "2025-01-03": 2}
    assert snapshot["activity_breakdown"] == {
        "feature": {"commits": 8, "lines_added": 210, "percentage": 72}
    }


def test_skills_timeline_orders_by_first_seen_then_depth() -> None:
    facts = [
        _fact(
            name="project-a",
            project_type="api",
            technologies=["Python", "FastAPI"],
            contribution_pct=70,
            first_commit="2024-01-01T00:00:00",
            last_commit="2024-06-01T00:00:00",
            commit_breakdown={"feature": 3},
        ),
        _fact(
            name="project-b",
            project_type="web",
            technologies=["Python", "React"],
            contribution_pct=80,
            first_commit="2024-02-01T00:00:00",
            last_commit="2025-01-01T00:00:00",
            commit_breakdown={"feature": 5},
        ),
    ]
    snapshots = [
        {"project_name": "project-a", "user_total_commits": 4},
        {"project_name": "project-b", "user_total_commits": 9},
    ]

    timeline = service._build_skills_timeline(facts, snapshots)

    assert [row["skill"] for row in timeline] == ["Python", "FastAPI", "React"]
    assert timeline[0] == {
        "skill": "Python",
        "first_seen": "2024-01-01T00:00:00",
        "last_seen": "2025-01-01T00:00:00",
        "projects_count": 2,
        "depth_score": 3.912,
    }


def test_activity_heatmap_aggregates_daily_commits() -> None:
    snapshots = [
        {"project_name": "project-a", "daily_commits": {"2025-01-01": 1, "2025-01-02": 2}},
        {"project_name": "project-b", "daily_commits": {"2025-01-02": 3, "2025-01-04": 1}},
    ]

    heatmap = service._build_activity_heatmap(snapshots)

    assert heatmap == {
        "daily_activity": {
            "2025-01-01": 1,
            "2025-01-02": 5,
            "2025-01-04": 1,
        },
        "total_days_active": 3,
        "max_daily_commits": 5,
        "date_range": {"start": "2025-01-01", "end": "2025-01-04"},
    }


def test_top_projects_uses_weighted_scoring_and_deterministic_ties() -> None:
    facts = [
        _fact(
            name="alpha-core",
            project_type="api",
            technologies=["Python"],
            contribution_pct=90,
            first_commit="2024-01-01T00:00:00",
            last_commit="2025-01-01T00:00:00",
            commit_breakdown={"feature": 20},
        ),
        _fact(
            name="zeta-core",
            project_type="api",
            technologies=["Python"],
            contribution_pct=90,
            first_commit="2024-01-01T00:00:00",
            last_commit="2025-01-01T00:00:00",
            commit_breakdown={"feature": 20},
        ),
        _fact(
            name="beta-ui",
            project_type="web",
            technologies=["TypeScript"],
            contribution_pct=80,
            first_commit="2024-01-01T00:00:00",
            last_commit="2025-01-01T00:00:00",
            commit_breakdown={"feature": 20},
        ),
        _fact(
            name="gamma-old",
            project_type="cli",
            technologies=["Rust"],
            contribution_pct=90,
            first_commit="2022-01-01T00:00:00",
            last_commit="2022-06-01T00:00:00",
            commit_breakdown={"feature": 10},
        ),
    ]
    snapshots = [
        {
            "project_name": "alpha-core",
            "user_total_commits": 20,
            "activity_breakdown": {"feature": {"percentage": 60, "commits": 12}},
            "recent_commit_messages": ["feat: add ranking panel"],
        },
        {
            "project_name": "zeta-core",
            "user_total_commits": 20,
            "activity_breakdown": {"feature": {"percentage": 58, "commits": 10}},
            "recent_commit_messages": ["feat: add dashboard mode"],
        },
        {"project_name": "beta-ui", "user_total_commits": 20},
        {"project_name": "gamma-old", "user_total_commits": 10},
    ]

    top_projects = service._build_top_projects(
        facts,
        snapshots,
        now=datetime(2025, 1, 1, 0, 0, 0),
    )

    assert len(top_projects) == 3
    assert [item["project_name"] for item in top_projects] == [
        "alpha-core",
        "zeta-core",
        "beta-ui",
    ]
    assert top_projects[0]["score"] >= top_projects[1]["score"] >= top_projects[2]["score"]


def test_finalize_output_includes_dashboard_and_supports_override() -> None:
    facts = [
        _fact(
            name="artifact-miner",
            project_type="tui",
            technologies=["TypeScript"],
            contribution_pct=78,
            first_commit="2024-01-01T00:00:00",
            last_commit="2025-01-01T00:00:00",
            commit_breakdown={"feature": 12},
        )
    ]
    snapshots = [
        {
            "project_name": "artifact-miner",
            "user_total_commits": 12,
            "daily_commits": {"2025-01-01": 3},
            "recent_commit_messages": ["feat: add dashboard tab"],
            "activity_breakdown": {"feature": {"percentage": 70, "commits": 8}},
        }
    ]

    payload = service.finalize_output(
        _output_with_project("artifact-miner", "tui"),
        facts=facts,
        snapshots=snapshots,
        stage="draft",
        models_used=["local-model"],
        generation_time_seconds=4.2,
        errors=[],
    )

    assert "portfolio_dashboard" in payload
    assert payload["portfolio_dashboard"]["skills_timeline"][0]["skill"] == "TypeScript"
    assert payload["portfolio_dashboard"]["activity_heatmap"]["daily_activity"] == {
        "2025-01-01": 3
    }

    dashboard_override = {
        "skills_timeline": [],
        "activity_heatmap": {
            "daily_activity": {},
            "total_days_active": 0,
            "max_daily_commits": 0,
            "date_range": {"start": None, "end": None},
        },
        "top_projects": [
            {
                "project_name": "override-project",
                "project_type": "api",
                "score": 1.0,
                "contribution_pct": 100.0,
                "commit_total": 10,
                "first_commit": "2025-01-01T00:00:00",
                "last_commit": "2025-01-01T00:00:00",
                "recency_score": 1.0,
                "activity_focus": None,
                "latest_change": None,
                "evolution_note": "override",
            }
        ],
    }
    override_payload = service.finalize_output(
        _output_with_project("artifact-miner", "tui"),
        facts=facts,
        portfolio_dashboard=dashboard_override,
        stage="polish",
        models_used=["local-model"],
        generation_time_seconds=5.0,
        errors=[],
    )

    assert override_payload["portfolio_dashboard"] == dashboard_override

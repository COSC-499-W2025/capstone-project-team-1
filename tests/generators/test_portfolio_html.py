import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from artifactminer.db import (
    Base,
    Consent,
    ProjectEvidence,
    ProjectSkill,
    Question,
    RepoStat,
    RepresentationPrefs,
    ResumeItem,
    Skill,
    UploadedZip,
    UserAIntelligenceSummary,
    UserAnswer,
    UserProjectSkill,
    UserRepoStat,
)
from artifactminer.generators import portfolio_html


@pytest.fixture
def db_session(tmp_path, monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()

    now = datetime.now(UTC).replace(tzinfo=None)
    today = datetime.now(UTC).date()
    old_day = (today - timedelta(days=500)).isoformat()
    day_4 = (today - timedelta(days=4)).isoformat()
    day_3 = (today - timedelta(days=3)).isoformat()
    day_2 = (today - timedelta(days=2)).isoformat()
    day_1 = (today - timedelta(days=1)).isoformat()

    db.add(Question(id=1, key="email", question_text="Email?", order=1, required=True))
    db.add(UserAnswer(question_id=1, answer_text="builder@example.com", answered_at=now))
    db.add(Consent(id=1, consent_level="local", accepted_at=now))

    db.add_all(
        [
            UploadedZip(
                id=10,
                filename="portfolio-a.zip",
                path="/uploads/a.zip",
                portfolio_id="portfolio-123",
                extraction_path="/extracted/10",
            ),
            UploadedZip(
                id=11,
                filename="portfolio-b.zip",
                path="/uploads/b.zip",
                portfolio_id="portfolio-123",
                extraction_path="/extracted/11",
            ),
            RepoStat(
                id=1,
                project_name="Alpha",
                project_path="/extracted/10/alpha",
                languages=["Python", "SQL"],
                frameworks=["FastAPI"],
                first_commit=now - timedelta(days=200),
                last_commit=now - timedelta(days=10),
                ranking_score=80.0,
                health_score=91.0,
            ),
            RepoStat(
                id=2,
                project_name="Beta",
                project_path="/extracted/10/beta",
                languages=["TypeScript"],
                frameworks=["Next.js"],
                first_commit=now - timedelta(days=180),
                last_commit=now - timedelta(days=8),
                ranking_score=70.0,
                health_score=84.0,
            ),
            RepoStat(
                id=3,
                project_name="Gamma",
                project_path="/extracted/11/gamma",
                languages=["Go"],
                frameworks=["Gin"],
                first_commit=now - timedelta(days=150),
                last_commit=now - timedelta(days=5),
                ranking_score=90.0,
                health_score=89.0,
            ),
            RepoStat(
                id=4,
                project_name="Delta",
                project_path="/extracted/11/delta",
                languages=["Rust"],
                frameworks=["Axum"],
                first_commit=now - timedelta(days=120),
                last_commit=now - timedelta(days=3),
                ranking_score=60.0,
                health_score=86.0,
            ),
            RepoStat(
                id=5,
                project_name="Outside",
                project_path="/outside/omega",
                languages=["Python"],
                frameworks=["Flask"],
                first_commit=now - timedelta(days=40),
                last_commit=now - timedelta(days=1),
                ranking_score=99.0,
                health_score=99.0,
            ),
            RepresentationPrefs(
                portfolio_id="portfolio-123",
                prefs_json=json.dumps(
                    {
                        "showcase_project_ids": [3, 1, 2, 4],
                        "project_order": [3, 1, 2, 4],
                    }
                ),
            ),
            Skill(id=1, name="Python", category="Programming Languages"),
            Skill(id=2, name="FastAPI", category="Frameworks & Libraries"),
            Skill(id=3, name="Go", category="Programming Languages"),
            Skill(id=4, name="Next.js", category="Frameworks & Libraries"),
            Skill(id=5, name="Rust", category="Programming Languages"),
            ProjectSkill(repo_stat_id=1, skill_id=1, proficiency=0.8),
            ProjectSkill(repo_stat_id=1, skill_id=2, proficiency=0.6),
            ProjectSkill(repo_stat_id=2, skill_id=4, proficiency=0.55),
            ProjectSkill(repo_stat_id=3, skill_id=3, proficiency=0.9),
            UserProjectSkill(
                repo_stat_id=4,
                skill_id=5,
                user_email="builder@example.com",
                proficiency=None,
            ),
            UserRepoStat(
                id=1,
                project_name="Alpha",
                project_path="/extracted/10/alpha",
                total_commits=5,
                daily_commits={old_day: 7},
                userStatspercentages=10.0,
                activity_breakdown={"code": {"percentage": 100}},
                user_role="Contributor",
            ),
            UserRepoStat(
                id=2,
                project_name="Alpha",
                project_path="/extracted/10/alpha",
                total_commits=22,
                daily_commits={day_4: 2},
                userStatspercentages=55.0,
                activity_breakdown={
                    "code": {"percentage": 70},
                    "docs": {"percentage": 10},
                    "config": {"percentage": 20},
                },
                user_role="Lead Developer",
            ),
            UserRepoStat(
                id=3,
                project_name="Beta",
                project_path="/extracted/10/beta",
                total_commits=12,
                daily_commits={day_3: 3},
                userStatspercentages=25.0,
                activity_breakdown={
                    "code": {"percentage": 60},
                    "test": {"percentage": 40},
                },
                user_role="Contributor",
            ),
            UserRepoStat(
                id=4,
                project_name="Gamma",
                project_path="/extracted/11/gamma",
                total_commits=30,
                daily_commits={day_2: 4},
                userStatspercentages=80.0,
                activity_breakdown={
                    "code": {"percentage": 50},
                    "design": {"percentage": 50},
                },
                user_role="Architect",
            ),
            UserRepoStat(
                id=5,
                project_name="Delta",
                project_path="/extracted/11/delta",
                total_commits=8,
                daily_commits={day_1: 1},
                userStatspercentages=35.0,
                activity_breakdown=None,
                user_role="Maintainer",
            ),
            UserRepoStat(
                id=6,
                project_name="Outside",
                project_path="/outside/omega",
                total_commits=99,
                daily_commits={day_1: 20},
                userStatspercentages=99.0,
                activity_breakdown={"code": {"percentage": 100}},
                user_role="Ignored",
            ),
            ResumeItem(id=1, title="Alpha 1", content="Alpha resume 1", category="Backend", repo_stat_id=1),
            ResumeItem(id=2, title="Alpha 2", content="Alpha resume 2", category="Backend", repo_stat_id=1),
            ResumeItem(id=3, title="Gamma 1", content="Gamma resume 1", category="Backend", repo_stat_id=3),
            ResumeItem(id=4, title="Gamma 2", content="Gamma resume 2", category="Backend", repo_stat_id=3),
            ResumeItem(id=5, title="Gamma 3", content="Gamma resume 3", category="Backend", repo_stat_id=3),
            ResumeItem(id=6, title="Gamma 4", content="Gamma resume 4", category="Backend", repo_stat_id=3),
            ProjectEvidence(id=1, repo_stat_id=1, type="metric", content="Alpha metric", date=(today - timedelta(days=10))),
            ProjectEvidence(id=2, repo_stat_id=1, type="feedback", content="Alpha feedback", date=(today - timedelta(days=8))),
            ProjectEvidence(id=3, repo_stat_id=1, type="custom", content="Alpha custom", date=(today - timedelta(days=6))),
            ProjectEvidence(id=4, repo_stat_id=1, type="custom", content="Alpha extra", date=(today - timedelta(days=4))),
            ProjectEvidence(id=5, repo_stat_id=3, type="metric", content="Gamma metric", date=(today - timedelta(days=5))),
            UserAIntelligenceSummary(
                id=1,
                repo_path="/extracted/10/alpha",
                user_email="builder@example.com",
                summary_text="Old alpha summary",
                generated_at=now - timedelta(days=4),
            ),
            UserAIntelligenceSummary(
                id=2,
                repo_path="/extracted/10/alpha",
                user_email="builder@example.com",
                summary_text="Latest alpha summary",
                generated_at=now - timedelta(days=1),
            ),
            UserAIntelligenceSummary(
                id=3,
                repo_path="/extracted/11/gamma",
                user_email="builder@example.com",
                summary_text="Gamma summary",
                generated_at=now - timedelta(days=2),
            ),
        ]
    )
    db.commit()

    output_path = tmp_path / ".artifactminer" / "output" / "portfolio.html"
    monkeypatch.setattr(portfolio_html, "OUTPUT_PATH", output_path)

    yield db, output_path, {"old_day": old_day, "day_4": day_4, "day_3": day_3, "day_2": day_2, "day_1": day_1}

    db.close()


def test_build_portfolio_dashboard_data_returns_exact_top_level_keys(db_session):
    db, _, _ = db_session
    data = portfolio_html.build_portfolio_dashboard_data(db, "portfolio-123")

    assert list(data.keys()) == [
        "meta",
        "preferences",
        "stats",
        "filters",
        "skills_timeline",
        "heatmap",
        "projects",
        "top_projects",
    ]


def test_selected_projects_are_portfolio_scoped_and_ordered_by_preferences(db_session):
    db, _, _ = db_session
    data = portfolio_html.build_portfolio_dashboard_data(db, "portfolio-123")

    assert [project["id"] for project in data["projects"]] == [3, 1, 2, 4]
    assert all(project["project_path"].startswith("/extracted/") for project in data["projects"])


def test_top_projects_slice_and_latest_user_repo_stat_wins(db_session):
    db, _, _ = db_session
    data = portfolio_html.build_portfolio_dashboard_data(db, "portfolio-123")

    assert [project["id"] for project in data["top_projects"]] == [3, 1, 2]

    alpha = next(project for project in data["projects"] if project["id"] == 1)
    assert alpha["user_role"] == "Lead Developer"
    assert alpha["contribution_pct"] == 55.0
    assert alpha["activity_breakdown"] == {
        "code": 70,
        "test": 0,
        "docs": 10,
        "config": 20,
        "other": 0,
    }
    assert alpha["summary_text"] == "Latest alpha summary"
    assert len(alpha["resume_items"]) == 2
    assert len(alpha["evidence"]) == 3


def test_heatmap_is_trimmed_to_last_364_days(db_session):
    db, _, days = db_session
    data = portfolio_html.build_portfolio_dashboard_data(db, "portfolio-123")

    assert days["old_day"] not in data["heatmap"]["daily_activity"]
    assert data["heatmap"]["daily_activity"] == {
        days["day_4"]: 2,
        days["day_3"]: 3,
        days["day_2"]: 4,
        days["day_1"]: 1,
    }


def test_rendered_html_contains_required_sections_and_chart_dependency(db_session):
    db, output_path, _ = db_session
    path = portfolio_html.generate_portfolio_html(db, "portfolio-123")
    html = Path(path).read_text(encoding="utf-8")

    assert path == output_path.resolve()
    assert path.exists()
    assert "const DATA =" in html
    assert "Skills Timeline" in html
    assert "Activity Heatmap" in html
    assert "Top Project Showcase" in html
    assert "https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js" in html

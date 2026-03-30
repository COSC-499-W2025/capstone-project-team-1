import json
from datetime import UTC, datetime, timedelta

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
from artifactminer.generators.portfolio_html import (
    build_portfolio_dashboard_data,
    generate_portfolio_html,
)


@pytest.fixture
def db_session(tmp_path, monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = Session()

    monkeypatch.setattr(
        portfolio_html,
        "_output_path",
        lambda: tmp_path / ".artifactminer" / "output" / "portfolio.html",
    )

    now = datetime.now(UTC).replace(tzinfo=None)
    today = datetime.now(UTC).date()
    recent_3 = (today - timedelta(days=3)).isoformat()
    recent_2 = (today - timedelta(days=2)).isoformat()
    recent_1 = (today - timedelta(days=1)).isoformat()
    old_day = (today - timedelta(days=400)).isoformat()

    db.add(Question(id=1, key="email", question_text="Email?", order=1, required=True))
    db.add(UserAnswer(question_id=1, answer_text="dev@example.com", answered_at=now))
    db.add(Consent(id=1, consent_level="local", accepted_at=now))

    db.add_all(
        [
            UploadedZip(
                id=10,
                filename="portfolio-a.zip",
                path="/uploads/portfolio-a.zip",
                portfolio_id="portfolio-511",
                extraction_path="/extracted/10",
            ),
            UploadedZip(
                id=11,
                filename="portfolio-b.zip",
                path="/uploads/portfolio-b.zip",
                portfolio_id="portfolio-511",
                extraction_path="/extracted/11",
            ),
            RepoStat(
                id=1,
                project_name="Alpha",
                project_path="/extracted/10/alpha",
                ranking_score=82.0,
                health_score=90.0,
                languages=["Python"],
                frameworks=["FastAPI"],
                total_commits=50,
                thumbnail_url="https://example.com/alpha.png",
                first_commit=now - timedelta(days=220),
                last_commit=now - timedelta(days=12),
            ),
            RepoStat(
                id=2,
                project_name="Beta",
                project_path="/extracted/10/beta",
                ranking_score=58.0,
                health_score=80.0,
                languages=["TypeScript"],
                frameworks=["React"],
                total_commits=21,
                first_commit=now - timedelta(days=200),
                last_commit=now - timedelta(days=30),
            ),
            RepoStat(
                id=3,
                project_name="Gamma",
                project_path="/extracted/11/gamma",
                ranking_score=97.0,
                health_score=95.0,
                languages=["Go"],
                frameworks=["Gin"],
                total_commits=30,
                first_commit=now - timedelta(days=180),
                last_commit=now - timedelta(days=4),
            ),
            RepoStat(
                id=4,
                project_name="Delta",
                project_path="/extracted/11/delta",
                ranking_score=71.0,
                health_score=76.0,
                languages=["Python", "TypeScript"],
                frameworks=["Next.js"],
                total_commits=17,
                first_commit=now - timedelta(days=160),
                last_commit=now - timedelta(days=6),
            ),
            RepoStat(
                id=5,
                project_name="Outside",
                project_path="/outside/omega",
                ranking_score=100.0,
                health_score=99.0,
                languages=["Rust"],
                frameworks=["Rocket"],
                total_commits=99,
                first_commit=now - timedelta(days=90),
                last_commit=now - timedelta(days=1),
            ),
            RepresentationPrefs(
                portfolio_id="portfolio-511",
                prefs_json=json.dumps(
                    {
                        "showcase_project_ids": [3, 1, 4, 2],
                        "project_order": [3, 1, 4, 2],
                    }
                ),
            ),
            UserRepoStat(
                id=1,
                project_name="Alpha",
                project_path="/extracted/10/alpha",
                total_commits=10,
                userStatspercentages=12.5,
                activity_breakdown={"code": 1},
                user_role="Contributor",
                daily_commits={old_day: 9},
            ),
            UserRepoStat(
                id=2,
                project_name="Alpha",
                project_path="/extracted/10/alpha",
                total_commits=44,
                userStatspercentages=64.0,
                activity_breakdown={"code": 70, "docs": 10, "misc": 5},
                user_role="Lead Developer",
                daily_commits={recent_3: 2, old_day: 9},
            ),
            UserRepoStat(
                id=3,
                project_name="Beta",
                project_path="/extracted/10/beta",
                total_commits=8,
                userStatspercentages=30.0,
                activity_breakdown={"tests": 6, "config": 2},
                user_role="Contributor",
                daily_commits={recent_2: 4},
            ),
            UserRepoStat(
                id=4,
                project_name="Gamma",
                project_path="/extracted/11/gamma",
                total_commits=15,
                userStatspercentages=88.0,
                activity_breakdown={"code": 9, "documentation": 1},
                user_role="Maintainer",
                daily_commits={recent_1: 3},
            ),
            ResumeItem(
                id=1,
                title="Gamma launch",
                content="Delivered the primary service release.",
                category="Launch",
                repo_stat_id=3,
            ),
            ResumeItem(
                id=2,
                title="Alpha backend",
                content="Designed API boundaries.",
                category="Backend",
                repo_stat_id=1,
            ),
            ResumeItem(
                id=3,
                title="Alpha observability",
                content="Added structured tracing.",
                category="Backend",
                repo_stat_id=1,
            ),
            ProjectEvidence(
                id=1,
                repo_stat_id=1,
                type="metric",
                content="Improved reliability",
                source="CI",
                date=today - timedelta(days=20),
            ),
            ProjectEvidence(
                id=2,
                repo_stat_id=1,
                type="testing",
                content="Expanded test coverage",
                source="pytest",
                date=today - timedelta(days=10),
            ),
            ProjectEvidence(
                id=3,
                repo_stat_id=3,
                type="feedback",
                content="Strong release quality",
                source="QA",
                date=today - timedelta(days=8),
            ),
            UserAIntelligenceSummary(
                id=1,
                repo_path="/extracted/10/alpha",
                user_email="dev@example.com",
                summary_text="Old alpha summary",
                generated_at=now - timedelta(days=7),
            ),
            UserAIntelligenceSummary(
                id=2,
                repo_path="/extracted/10/alpha",
                user_email="dev@example.com",
                summary_text="Newest alpha summary",
                generated_at=now - timedelta(days=1),
            ),
            UserAIntelligenceSummary(
                id=3,
                repo_path="/extracted/11/gamma",
                user_email="dev@example.com",
                summary_text="Gamma summary",
                generated_at=now - timedelta(days=2),
            ),
            Skill(id=1, name="Python", category="Languages"),
            Skill(id=2, name="FastAPI", category="Frameworks"),
            Skill(id=3, name="Go", category="Languages"),
            Skill(id=4, name="Testing", category="Practices"),
            ProjectSkill(repo_stat_id=1, skill_id=1, proficiency=0.6),
            ProjectSkill(repo_stat_id=1, skill_id=2, proficiency=None),
            ProjectSkill(repo_stat_id=3, skill_id=3, proficiency=0.9),
            ProjectSkill(repo_stat_id=2, skill_id=4, proficiency=0.55),
            UserProjectSkill(
                repo_stat_id=1,
                skill_id=1,
                user_email="dev@example.com",
                proficiency=0.8,
            ),
        ]
    )
    db.commit()

    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_build_portfolio_dashboard_data_returns_exact_top_level_keys(db_session):
    data = build_portfolio_dashboard_data(db_session, "portfolio-511")

    assert set(data.keys()) == {
        "meta",
        "preferences",
        "stats",
        "filters",
        "skills_timeline",
        "heatmap",
        "projects",
        "top_projects",
    }


def test_selected_projects_are_portfolio_scoped_and_preference_ordered(db_session):
    data = build_portfolio_dashboard_data(db_session, "portfolio-511")

    assert [project["id"] for project in data["projects"]] == [3, 1, 4, 2]
    assert all(not project["project_path"].startswith("/outside") for project in data["projects"])


def test_top_three_project_slicing_is_correct(db_session):
    data = build_portfolio_dashboard_data(db_session, "portfolio-511")

    assert [project["id"] for project in data["top_projects"]] == [3, 1, 4]


def test_heatmap_trims_data_to_last_364_days(db_session):
    data = build_portfolio_dashboard_data(db_session, "portfolio-511")

    old_day = (datetime.now(UTC).date() - timedelta(days=400)).isoformat()
    assert old_day not in data["heatmap"]["daily_activity"]


def test_newest_user_repo_stat_row_wins_for_role_contribution_and_activity(db_session):
    data = build_portfolio_dashboard_data(db_session, "portfolio-511")
    alpha = next(project for project in data["projects"] if project["project_name"] == "Alpha")

    assert alpha["user_role"] == "Lead Developer"
    assert alpha["contribution_pct"] == 64.0
    assert alpha["activity_breakdown"] == {
        "code": 70,
        "test": 0,
        "docs": 10,
        "config": 0,
        "other": 5,
    }
    assert alpha["summary_text"] == "Newest alpha summary"


def test_rendered_html_contains_data_and_required_sections(db_session):
    output_path = generate_portfolio_html(db_session, "portfolio-511")
    html = output_path.read_text(encoding="utf-8")

    assert "const DATA =" in html
    assert "Top Projects" in html
    assert "Skills Timeline" in html
    assert "Activity Heatmap" in html
    assert "https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js" in html


def test_output_file_is_written_to_fixed_portfolio_path(db_session, tmp_path):
    output_path = generate_portfolio_html(db_session, "portfolio-511")

    assert output_path == tmp_path / ".artifactminer" / "output" / "portfolio.html"
    assert output_path.is_file()

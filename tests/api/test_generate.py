import json
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from artifactminer.api.app import create_app
from artifactminer.api.schemas import GeneratedArtifactResponse
from artifactminer.db import (
    Base,
    Consent,
    ProjectSkill,
    Question,
    RepoStat,
    RepresentationPrefs,
    Skill,
    UploadedZip,
    UserAIntelligenceSummary,
    UserAnswer,
    UserRepoStat,
    get_db,
)
from artifactminer.generators import portfolio_html


@pytest.fixture
def client(tmp_path, monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db

    output_path = tmp_path / ".artifactminer" / "output" / "portfolio.html"
    monkeypatch.setattr(portfolio_html, "OUTPUT_PATH", output_path)

    now = datetime.now(UTC).replace(tzinfo=None)
    today = datetime.now(UTC).date()
    db = TestingSessionLocal()
    db.add(Question(id=1, key="email", question_text="Email?", order=1, required=True))
    db.add(UserAnswer(question_id=1, answer_text="student@example.com", answered_at=now))
    db.add(Consent(id=1, consent_level="local", accepted_at=now))
    db.add_all(
        [
            UploadedZip(
                id=10,
                filename="portfolio.zip",
                path="/uploads/portfolio.zip",
                portfolio_id="portfolio-123",
                extraction_path="/extracted/10",
            ),
            RepoStat(
                id=1,
                project_name="Alpha",
                project_path="/extracted/10/alpha",
                languages=["Python"],
                frameworks=["FastAPI"],
                first_commit=now - timedelta(days=50),
                last_commit=now - timedelta(days=1),
                ranking_score=88.0,
                health_score=93.0,
            ),
            RepresentationPrefs(
                portfolio_id="portfolio-123",
                prefs_json=json.dumps({"showcase_project_ids": [1], "project_order": [1]}),
            ),
            Skill(id=1, name="Python", category="Programming Languages"),
            ProjectSkill(repo_stat_id=1, skill_id=1, proficiency=0.9),
            UserRepoStat(
                id=1,
                project_name="Alpha",
                project_path="/extracted/10/alpha",
                total_commits=12,
                daily_commits={(today - timedelta(days=1)).isoformat(): 2},
                userStatspercentages=65.0,
                activity_breakdown={"code": {"percentage": 100}},
                user_role="Lead Developer",
            ),
            UserAIntelligenceSummary(
                id=1,
                repo_path="/extracted/10/alpha",
                user_email="student@example.com",
                summary_text="Alpha summary",
                generated_at=now - timedelta(days=1),
            ),
        ]
    )
    db.commit()
    db.close()

    yield TestClient(app), output_path
    app.dependency_overrides.clear()


def test_post_generate_portfolio_returns_generated_artifact_response(client):
    test_client, output_path = client

    response = test_client.post("/generate/portfolio", json={"portfolio_id": "portfolio-123"})
    assert response.status_code == 200

    payload = response.json()
    parsed = GeneratedArtifactResponse.model_validate(payload)

    assert payload["success"] is True
    assert payload["artifact"] == "portfolio"
    assert payload["path"] == str(output_path.resolve())
    assert output_path.exists()
    assert isinstance(payload["warnings"], list)
    assert parsed.artifact == "portfolio"

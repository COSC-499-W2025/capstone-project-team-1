"""Tests for POST /portfolio/generate endpoint."""

import json
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from artifactminer.api.app import create_app
from artifactminer.db import (
    Base,
    Consent,
    ProjectEvidence,
    Question,
    RepoStat,
    RepresentationPrefs,
    ResumeItem,
    UploadedZip,
    UserAIntelligenceSummary,
    UserAnswer,
    UserRepoStat,
    get_db,
)


@pytest.fixture(scope="function")
def client_with_portfolio_data():
    """Test client seeded with analyzed portfolio data."""
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

    now = datetime.now(UTC).replace(tzinfo=None)
    db = TestingSessionLocal()
    db.add(Question(id=1, key="email", question_text="Email?", order=1, required=True))
    db.add(UserAnswer(question_id=1, answer_text="student@example.com", answered_at=now))
    db.add(Consent(id=1, consent_level="no_llm", accepted_at=now))

    db.add_all(
        [
            UploadedZip(
                id=10,
                filename="portfolio-a.zip",
                path="/uploads/portfolio-a.zip",
                portfolio_id="portfolio-123",
                extraction_path="/extracted/10",
            ),
            UploadedZip(
                id=11,
                filename="portfolio-b.zip",
                path="/uploads/portfolio-b.zip",
                portfolio_id="portfolio-123",
                extraction_path="/extracted/11",
            ),
            RepoStat(
                id=1,
                project_name="Alpha",
                project_path="/extracted/10/alpha",
                ranking_score=88.0,
                first_commit=now - timedelta(days=100),
                last_commit=now - timedelta(days=1),
            ),
            RepoStat(
                id=2,
                project_name="Beta",
                project_path="/extracted/11/beta",
                ranking_score=91.0,
                first_commit=now - timedelta(days=80),
                last_commit=now - timedelta(days=2),
            ),
            RepoStat(
                id=3,
                project_name="OutsidePortfolio",
                project_path="/different/77/outside",
                ranking_score=99.0,
                first_commit=now - timedelta(days=40),
                last_commit=now - timedelta(days=1),
            ),
            ResumeItem(
                id=1,
                title="Built Alpha API",
                content="Designed service boundaries and CI checks.",
                category="Backend",
                repo_stat_id=1,
            ),
            ResumeItem(
                id=2,
                title="Built Beta UI",
                content="Implemented dashboard workflow and state handling.",
                category="Frontend",
                repo_stat_id=2,
            ),
            UserAIntelligenceSummary(
                id=1,
                repo_path="/extracted/10/alpha",
                user_email="student@example.com",
                summary_text="Alpha summary",
                generated_at=now - timedelta(days=3),
            ),
            UserAIntelligenceSummary(
                id=2,
                repo_path="/extracted/11/beta",
                user_email="student@example.com",
                summary_text="Beta summary",
                generated_at=now - timedelta(days=2),
            ),
            UserAIntelligenceSummary(
                id=3,
                repo_path="/extracted/11/beta",
                user_email="other@example.com",
                summary_text="Wrong user summary",
                generated_at=now - timedelta(days=1),
            ),
            RepresentationPrefs(
                portfolio_id="portfolio-123",
                prefs_json=json.dumps(
                    {
                        "showcase_project_ids": ["2", "1"],
                        "project_order": ["2", "1"],
                    }
                ),
            ),
        ]
    )
    db.commit()
    db.close()

    yield TestClient(app)
    app.dependency_overrides.clear()


def test_portfolio_generate_happy_path(client_with_portfolio_data):
    """POST /portfolio/generate returns assembled, ordered portfolio payload."""
    resp = client_with_portfolio_data.post(
        "/portfolio/generate",
        json={"portfolio_id": "portfolio-123"},
    )
    assert resp.status_code == 200

    payload = resp.json()
    assert payload["success"] is True
    assert payload["portfolio_id"] == "portfolio-123"
    assert payload["consent_level"] == "no_llm"
    assert payload["errors"] == []

    # Ordered by saved project_order preference.
    assert [p["id"] for p in payload["projects"]] == [2, 1]
    assert [p["project_name"] for p in payload["projects"]] == ["Beta", "Alpha"]

    # Only selected portfolio projects are included.
    assert len(payload["resume_items"]) == 2
    assert set(item["project_name"] for item in payload["resume_items"]) == {
        "Alpha",
        "Beta",
    }

    assert len(payload["summaries"]) == 2
    assert [s["summary_text"] for s in payload["summaries"]] == [
        "Beta summary",
        "Alpha summary",
    ]


def test_portfolio_generate_missing_portfolio_returns_404(client_with_portfolio_data):
    """POST /portfolio/generate returns 404 when portfolio_id does not exist."""
    resp = client_with_portfolio_data.post(
        "/portfolio/generate",
        json={"portfolio_id": "missing-portfolio"},
    )
    assert resp.status_code == 404
    assert "Portfolio not found" in resp.json()["detail"]


def test_portfolio_generate_requires_analyzed_zips():
    """POST /portfolio/generate returns 400 if portfolio has no extraction paths."""
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

    db = TestingSessionLocal()
    now = datetime.now(UTC).replace(tzinfo=None)
    db.add(Question(id=1, key="email", question_text="Email?", order=1, required=True))
    db.add(UserAnswer(question_id=1, answer_text="student@example.com", answered_at=now))
    db.add(UploadedZip(id=50, filename="raw.zip", path="/uploads/raw.zip", portfolio_id="p0"))
    db.commit()
    db.close()

    client = TestClient(app)
    try:
        resp = client.post("/portfolio/generate", json={"portfolio_id": "p0"})
        assert resp.status_code == 400
        assert "no analyzed ZIPs" in resp.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_portfolio_generate_missing_email_returns_400():
    """POST /portfolio/generate requires configured user email."""
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

    db = TestingSessionLocal()
    now = datetime.now(UTC).replace(tzinfo=None)
    db.add(UploadedZip(id=61, filename="a.zip", path="/uploads/a.zip", portfolio_id="p1", extraction_path="/extracted/61"))
    db.add(RepoStat(id=61, project_name="A", project_path="/extracted/61/a", last_commit=now))
    db.commit()
    db.close()

    client = TestClient(app)
    try:
        resp = client.post("/portfolio/generate", json={"portfolio_id": "p1"})
        assert resp.status_code == 400
        assert "email" in resp.json()["detail"].lower()
    finally:
        app.dependency_overrides.clear()


def test_portfolio_generate_uses_strict_path_boundaries():
    """Prefix-like paths (e.g. /extracted/10) must not match /extracted/1 scope."""
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

    now = datetime.now(UTC).replace(tzinfo=None)
    db = TestingSessionLocal()
    db.add(Question(id=1, key="email", question_text="Email?", order=1, required=True))
    db.add(UserAnswer(question_id=1, answer_text="student@example.com", answered_at=now))
    db.add(Consent(id=1, consent_level="no_llm", accepted_at=now))

    db.add_all(
        [
            UploadedZip(
                id=70,
                filename="portfolio.zip",
                path="/uploads/p.zip",
                portfolio_id="p-boundary",
                extraction_path="/extracted/1",
            ),
            RepoStat(
                id=70,
                project_name="InScope",
                project_path="/extracted/1/repo",
                last_commit=now,
            ),
            RepoStat(
                id=71,
                project_name="OutOfScopePrefix",
                project_path="/extracted/10/repo",
                last_commit=now,
            ),
            ResumeItem(
                id=70,
                title="InScope item",
                content="valid",
                category="Backend",
                repo_stat_id=70,
            ),
            ResumeItem(
                id=71,
                title="OutOfScope item",
                content="invalid",
                category="Backend",
                repo_stat_id=71,
            ),
            UserAIntelligenceSummary(
                id=70,
                repo_path="/extracted/1/repo",
                user_email="student@example.com",
                summary_text="in-scope summary",
                generated_at=now,
            ),
            UserAIntelligenceSummary(
                id=71,
                repo_path="/extracted/10/repo",
                user_email="student@example.com",
                summary_text="out-of-scope summary",
                generated_at=now,
            ),
        ]
    )
    db.commit()
    db.close()

    client = TestClient(app)
    try:
        resp = client.post("/portfolio/generate", json={"portfolio_id": "p-boundary"})
        assert resp.status_code == 200
        payload = resp.json()

        assert [p["project_name"] for p in payload["projects"]] == ["InScope"]
        assert [s["summary_text"] for s in payload["summaries"]] == ["in-scope summary"]
        assert [r["title"] for r in payload["resume_items"]] == ["InScope item"]
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests for GET /portfolio/{id}
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function")
def client_with_complete_portfolio():
    """Test client with portfolio including role, thumbnail, and evidence data."""
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

    now = datetime.now(UTC).replace(tzinfo=None)
    db = TestingSessionLocal()
    
    # Set up user and consent
    db.add(Question(id=1, key="email", question_text="Email?", order=1, required=True))
    db.add(UserAnswer(question_id=1, answer_text="student@example.com", answered_at=now))
    db.add(Consent(id=1, consent_level="no_llm", accepted_at=now))

    # Portfolio with projects
    db.add_all(
        [
            UploadedZip(
                id=20,
                filename="portfolio-complete.zip",
                path="/uploads/portfolio-complete.zip",
                portfolio_id="portfolio-456",
                extraction_path="/extracted/20",
            ),
            RepoStat(
                id=100,
                project_name="ProjectAlpha",
                project_path="/extracted/20/alpha",
                ranking_score=85.0,
                health_score=92.0,
                thumbnail_url="https://example.com/alpha-thumb.png",
                first_commit=now - timedelta(days=100),
                last_commit=now - timedelta(days=5),
                languages=["Python", "JavaScript"],
                frameworks=["FastAPI", "React"],
            ),
            RepoStat(
                id=101,
                project_name="ProjectBeta",
                project_path="/extracted/20/beta",
                ranking_score=90.0,
                health_score=88.0,
                thumbnail_url="/uploads/thumbnails/beta.jpg",
                first_commit=now - timedelta(days=80),
                last_commit=now - timedelta(days=3),
                languages=["TypeScript"],
                frameworks=["Next.js"],
            ),
            # User repo stats with roles
            UserRepoStat(
                id=1,
                project_name="ProjectAlpha",
                project_path="/extracted/20/alpha",
                user_email="student@example.com",
                user_role="Lead Developer",
                total_commits=150,
            ),
            UserRepoStat(
                id=2,
                project_name="ProjectBeta",
                project_path="/extracted/20/beta",
                user_email="student@example.com",
                user_role="Contributor",
                total_commits=42,
            ),
            # Project evidence
            ProjectEvidence(
                id=1,
                repo_stat_id=100,
                type="metric",
                content="95% test coverage achieved",
                source="pytest",
                date=(now - timedelta(days=10)).date(),
            ),
            ProjectEvidence(
                id=2,
                repo_stat_id=100,
                type="award",
                content="Best API Design Award",
                source="Hackathon 2025",
                date=(now - timedelta(days=20)).date(),
            ),
            ProjectEvidence(
                id=3,
                repo_stat_id=101,
                type="feedback",
                content="Excellent user experience",
                source="User Survey",
                date=(now - timedelta(days=15)).date(),
            ),
            # Resume items
            ResumeItem(
                id=100,
                title="Built Alpha Backend",
                content="Designed RESTful API with FastAPI",
                category="Backend",
                repo_stat_id=100,
            ),
            # Summaries
            UserAIntelligenceSummary(
                id=100,
                repo_path="/extracted/20/alpha",
                user_email="student@example.com",
                summary_text="Alpha project summary",
                generated_at=now - timedelta(days=5),
            ),
            RepresentationPrefs(
                portfolio_id="portfolio-456",
                prefs_json=json.dumps(
                    {
                        "showcase_project_ids": ["100", "101"],
                        "project_order": ["100", "101"],
                    }
                ),
            ),
        ]
    )
    db.commit()
    db.close()

    yield TestClient(app)
    app.dependency_overrides.clear()


def test_get_portfolio_happy_path(client_with_complete_portfolio):
    """GET /portfolio/{id} returns complete portfolio with role, thumbnail, and evidence."""
    resp = client_with_complete_portfolio.get("/portfolio/portfolio-456")
    
    assert resp.status_code == 200
    payload = resp.json()
    
    assert payload["success"] is True
    assert payload["portfolio_id"] == "portfolio-456"
    assert payload["consent_level"] == "no_llm"
    assert len(payload["projects"]) == 2
    
    # Verify first project has complete data
    alpha = payload["projects"][0]
    assert alpha["project_name"] == "ProjectAlpha"
    assert alpha["thumbnail_url"] == "https://example.com/alpha-thumb.png"
    assert alpha["user_role"] == "Lead Developer"
    assert alpha["ranking_score"] == 85.0
    assert alpha["health_score"] == 92.0
    assert alpha["languages"] == ["Python", "JavaScript"]
    assert alpha["frameworks"] == ["FastAPI", "React"]
    
    # Verify evidence is included
    assert len(alpha["evidence"]) == 2
    evidence_contents = [e["content"] for e in alpha["evidence"]]
    assert "95% test coverage achieved" in evidence_contents
    assert "Best API Design Award" in evidence_contents
    assert alpha["evidence"][0]["type"] in ["metric", "award", "feedback", "evaluation", "custom"]
    
    # Verify second project
    beta = payload["projects"][1]
    assert beta["project_name"] == "ProjectBeta"
    assert beta["thumbnail_url"] == "/uploads/thumbnails/beta.jpg"
    assert beta["user_role"] == "Contributor"
    assert len(beta["evidence"]) == 1
    assert beta["evidence"][0]["content"] == "Excellent user experience"
    
    # Verify other aggregated data
    assert len(payload["resume_items"]) == 1
    assert payload["resume_items"][0]["title"] == "Built Alpha Backend"
    assert len(payload["summaries"]) == 1
    assert payload["summaries"][0]["summary_text"] == "Alpha project summary"


def test_get_portfolio_not_found(client_with_complete_portfolio):
    """GET /portfolio/{id} returns 404 for non-existent portfolio."""
    resp = client_with_complete_portfolio.get("/portfolio/nonexistent-portfolio")
    
    assert resp.status_code == 404
    assert "Portfolio not found" in resp.json()["detail"]


def test_get_portfolio_empty_id(client_with_complete_portfolio):
    """GET /portfolio/{id} returns 422 for empty portfolio_id."""
    resp = client_with_complete_portfolio.get("/portfolio/   ")
    
    assert resp.status_code == 422
    assert "cannot be empty" in resp.json()["detail"]


def test_get_portfolio_no_analyzed_zips():
    """GET /portfolio/{id} returns 400 when portfolio has no analyzed ZIPs."""
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

    now = datetime.now(UTC).replace(tzinfo=None)
    db = TestingSessionLocal()
    
    db.add(Question(id=1, key="email", question_text="Email?", order=1, required=True))
    db.add(UserAnswer(question_id=1, answer_text="student@example.com", answered_at=now))
    db.add(Consent(id=1, consent_level="no_llm", accepted_at=now))
    
    # Portfolio with no extraction_path (not analyzed)
    db.add(
        UploadedZip(
            id=30,
            filename="unanalyzed.zip",
            path="/uploads/unanalyzed.zip",
            portfolio_id="portfolio-789",
            extraction_path=None,
        )
    )
    db.commit()
    db.close()

    client = TestClient(app)
    try:
        resp = client.get("/portfolio/portfolio-789")
        
        assert resp.status_code == 400
        assert "no analyzed ZIPs" in resp.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_get_portfolio_respects_preferences(client_with_complete_portfolio):
    """GET /portfolio/{id} respects RepresentationPrefs ordering."""
    resp = client_with_complete_portfolio.get("/portfolio/portfolio-456")
    
    assert resp.status_code == 200
    payload = resp.json()
    
    # Verify projects are ordered according to preferences
    project_names = [p["project_name"] for p in payload["projects"]]
    assert project_names == ["ProjectAlpha", "ProjectBeta"]
    
    # Verify preferences are included in response
    assert payload["preferences"] is not None
    assert payload["preferences"]["showcase_project_ids"] == ["100", "101"]


def test_get_portfolio_without_role_and_evidence():
    """GET /portfolio/{id} handles projects without role or evidence gracefully."""
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

    now = datetime.now(UTC).replace(tzinfo=None)
    db = TestingSessionLocal()
    
    db.add(Question(id=1, key="email", question_text="Email?", order=1, required=True))
    db.add(UserAnswer(question_id=1, answer_text="student@example.com", answered_at=now))
    db.add(Consent(id=1, consent_level="no_llm", accepted_at=now))
    
    db.add_all([
        UploadedZip(
            id=40,
            filename="minimal.zip",
            path="/uploads/minimal.zip",
            portfolio_id="portfolio-minimal",
            extraction_path="/extracted/40",
        ),
        RepoStat(
            id=200,
            project_name="MinimalProject",
            project_path="/extracted/40/minimal",
            ranking_score=70.0,
            # No thumbnail_url
        ),
        # No UserRepoStat (no role)
        # No ProjectEvidence
        RepresentationPrefs(
            portfolio_id="portfolio-minimal",
            prefs_json="{}",
        ),
    ])
    db.commit()
    db.close()

    client = TestClient(app)
    try:
        resp = client.get("/portfolio/portfolio-minimal")
        
        assert resp.status_code == 200
        payload = resp.json()
        
        project = payload["projects"][0]
        assert project["project_name"] == "MinimalProject"
        assert project["user_role"] is None
        assert project["thumbnail_url"] is None
        assert project["evidence"] == []
    finally:
        app.dependency_overrides.clear()

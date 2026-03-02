"""Tests for POST /portfolio/{id}/edit endpoint."""

import json
from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from artifactminer.api.app import create_app
from artifactminer.db import (
    Base,
    Consent,
    Question,
    RepoStat,
    RepresentationPrefs,
    UploadedZip,
    UserAnswer,
    get_db,
)


@pytest.fixture(scope="function")
def client_with_portfolio_data():
    """Test client seeded with portfolio data for edit tests."""
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
    db.add(
        UserAnswer(question_id=1, answer_text="student@example.com", answered_at=now)
    )
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
                project_name="Gamma",
                project_path="/extracted/11/gamma",
                ranking_score=95.0,
                first_commit=now - timedelta(days=60),
                last_commit=now - timedelta(days=3),
            ),
        ]
    )
    db.commit()
    db.close()

    yield TestClient(app)
    app.dependency_overrides.clear()


def test_portfolio_edit_happy_path(client_with_portfolio_data):
    """POST /portfolio/{id}/edit updates portfolio preferences successfully."""
    resp = client_with_portfolio_data.post(
        "/portfolio/portfolio-123/edit",
        json={
            "showcase_project_ids": [1, 2],
            "project_order": [2, 1],
            "skills_to_highlight": [1, 2],
            "hidden_skills": [3],
            "chronology_overrides": [
                {
                    "project_id": 1,
                    "first_commit": "2023-01-15",
                    "last_commit": "2023-12-01",
                }
            ],
            "comparison_attributes": ["languages", "frameworks", "ranking_score"],
            "custom_rankings": [
                {"project_id": 1, "rank": 2},
                {"project_id": 2, "rank": 1},
            ],
        },
    )
    assert resp.status_code == 200

    payload = resp.json()
    assert payload["success"] is True
    assert payload["portfolio_id"] == "portfolio-123"
    assert "updated_at" in payload
    assert "preferences" in payload

    prefs = payload["preferences"]
    assert prefs["showcase_project_ids"] == [1, 2]
    assert prefs["project_order"] == [2, 1]
    assert prefs["skills_to_highlight"] == [1, 2]
    assert prefs["hidden_skills"] == [3]
    assert len(prefs["chronology_overrides"]) == 1
    assert prefs["chronology_overrides"][0]["project_id"] == 1
    assert prefs["chronology_overrides"][0]["first_commit"] == "2023-01-15"
    assert prefs["comparison_attributes"] == [
        "languages",
        "frameworks",
        "ranking_score",
    ]
    assert len(prefs["custom_rankings"]) == 2
    assert prefs["custom_rankings"][0]["project_id"] == 1
    assert prefs["custom_rankings"][0]["rank"] == 2


def test_portfolio_edit_full_replacement_not_partial(client_with_portfolio_data):
    """POST /portfolio/{id}/edit performs full replacement (not partial update).

    Note: This endpoint replaces ALL preferences. To change one field,
    client must send all desired values including unchanged ones.
    """
    # First, set some initial preferences
    client_with_portfolio_data.post(
        "/portfolio/portfolio-123/edit",
        json={
            "showcase_project_ids": [1, 2, 3],
            "project_order": [3, 2, 1],
        },
    )

    # Then update only project_order
    resp = client_with_portfolio_data.post(
        "/portfolio/portfolio-123/edit",
        json={
            "project_order": [1, 2, 3],
        },
    )
    assert resp.status_code == 200

    payload = resp.json()
    prefs = payload["preferences"]
    # Other fields should be reset to defaults (empty lists)
    assert prefs["project_order"] == [1, 2, 3]
    assert prefs["showcase_project_ids"] == []


def test_portfolio_edit_empty_preferences(client_with_portfolio_data):
    """POST /portfolio/{id}/edit allows clearing all preferences."""
    resp = client_with_portfolio_data.post(
        "/portfolio/portfolio-123/edit",
        json={},
    )
    assert resp.status_code == 200

    payload = resp.json()
    assert payload["success"] is True
    prefs = payload["preferences"]
    assert prefs["showcase_project_ids"] == []
    assert prefs["project_order"] == []
    assert prefs["skills_to_highlight"] == []
    assert prefs["hidden_skills"] == []


def test_portfolio_edit_missing_portfolio_returns_404(client_with_portfolio_data):
    """POST /portfolio/{id}/edit returns 404 when portfolio_id does not exist."""
    resp = client_with_portfolio_data.post(
        "/portfolio/missing-portfolio/edit",
        json={"showcase_project_ids": [1]},
    )
    assert resp.status_code == 404
    assert "Portfolio not found" in resp.json()["detail"]


def test_portfolio_edit_empty_portfolio_id_returns_422(client_with_portfolio_data):
    """POST /portfolio/{id}/edit returns 422 when portfolio_id is empty."""
    resp = client_with_portfolio_data.post(
        "/portfolio/ /edit",
        json={"showcase_project_ids": [1]},
    )
    assert resp.status_code == 422
    assert "portfolio_id cannot be empty" in resp.json()["detail"]


def test_portfolio_edit_persists_customizations(client_with_portfolio_data):
    """Edits persist and are retrievable via GET /views/{id}/prefs."""
    # Edit portfolio
    client_with_portfolio_data.post(
        "/portfolio/portfolio-123/edit",
        json={
            "showcase_project_ids": [2],
            "project_order": [2, 1],
        },
    )

    # Verify via GET endpoint
    resp = client_with_portfolio_data.get("/views/portfolio-123/prefs")
    assert resp.status_code == 200

    prefs = resp.json()
    assert prefs["showcase_project_ids"] == [2]
    assert prefs["project_order"] == [2, 1]


def test_portfolio_edit_affects_subsequent_generate(client_with_portfolio_data):
    """Edited preferences affect subsequent portfolio generation."""
    # First edit - showcase only project 2
    client_with_portfolio_data.post(
        "/portfolio/portfolio-123/edit",
        json={
            "showcase_project_ids": [2],
            "project_order": [2],
        },
    )

    # Generate portfolio
    resp = client_with_portfolio_data.post(
        "/portfolio/generate",
        json={"portfolio_id": "portfolio-123"},
    )
    assert resp.status_code == 200

    payload = resp.json()
    # Should only include project 2
    assert len(payload["projects"]) == 1
    assert payload["projects"][0]["id"] == 2
    assert payload["projects"][0]["project_name"] == "Beta"


def test_portfolio_edit_invalid_comparison_attribute(client_with_portfolio_data):
    """POST /portfolio/{id}/edit rejects invalid comparison attributes."""
    resp = client_with_portfolio_data.post(
        "/portfolio/portfolio-123/edit",
        json={
            "comparison_attributes": ["invalid_attribute"],
        },
    )
    assert resp.status_code == 422


def test_portfolio_edit_invalid_custom_ranking(client_with_portfolio_data):
    """POST /portfolio/{id}/edit rejects invalid custom rankings."""
    resp = client_with_portfolio_data.post(
        "/portfolio/portfolio-123/edit",
        json={
            "custom_rankings": [{"project_id": 1, "rank": 0}],  # rank must be >= 1
        },
    )
    assert resp.status_code == 422


def test_portfolio_edit_negative_project_ids(client_with_portfolio_data):
    """POST /portfolio/{id}/edit rejects negative project IDs."""
    resp = client_with_portfolio_data.post(
        "/portfolio/portfolio-123/edit",
        json={
            "showcase_project_ids": [-1, 2],
        },
    )
    assert resp.status_code == 422


def test_portfolio_edit_chronology_override_partial(client_with_portfolio_data):
    """POST /portfolio/{id}/edit allows partial chronology overrides."""
    resp = client_with_portfolio_data.post(
        "/portfolio/portfolio-123/edit",
        json={
            "chronology_overrides": [
                {"project_id": 1, "first_commit": "2023-01-15"},
                {"project_id": 2, "last_commit": "2023-06-30"},
            ],
        },
    )
    assert resp.status_code == 200

    payload = resp.json()
    prefs = payload["preferences"]
    assert len(prefs["chronology_overrides"]) == 2
    assert prefs["chronology_overrides"][0]["first_commit"] == "2023-01-15"
    assert prefs["chronology_overrides"][0]["last_commit"] is None
    assert prefs["chronology_overrides"][1]["first_commit"] is None
    assert prefs["chronology_overrides"][1]["last_commit"] == "2023-06-30"


def test_portfolio_edit_multiple_edits_accumulate(client_with_portfolio_data):
    """Multiple edits replace previous preferences (not accumulate)."""
    # First edit
    client_with_portfolio_data.post(
        "/portfolio/portfolio-123/edit",
        json={
            "showcase_project_ids": [1],
            "project_order": [1, 2, 3],
        },
    )

    # Second edit - should replace first
    resp = client_with_portfolio_data.post(
        "/portfolio/portfolio-123/edit",
        json={
            "showcase_project_ids": [2, 3],
            "skills_to_highlight": [5, 6],
        },
    )
    assert resp.status_code == 200

    payload = resp.json()
    prefs = payload["preferences"]
    # New values
    assert prefs["showcase_project_ids"] == [2, 3]
    assert prefs["skills_to_highlight"] == [5, 6]
    # Old values should be cleared (empty, not [1])
    assert prefs["project_order"] == []


def test_portfolio_edit_idempotency(client_with_portfolio_data):
    """Same edit twice produces same result."""
    edit_payload = {
        "showcase_project_ids": [1, 2],
        "project_order": [2, 1],
    }

    # First edit
    resp1 = client_with_portfolio_data.post(
        "/portfolio/portfolio-123/edit",
        json=edit_payload,
    )
    assert resp1.status_code == 200

    # Second edit with same data
    resp2 = client_with_portfolio_data.post(
        "/portfolio/portfolio-123/edit",
        json=edit_payload,
    )
    assert resp2.status_code == 200

    # Both responses should be equivalent
    assert resp1.json()["preferences"] == resp2.json()["preferences"]


def test_normalize_tokens_coerces_integers_to_strings():
    """_normalize_tokens converts int values to strings for matching."""
    from artifactminer.api.portfolio import _normalize_tokens

    assert _normalize_tokens([1, 2, 3]) == ["1", "2", "3"]
    assert _normalize_tokens(["alpha", "beta"]) == ["alpha", "beta"]
    assert _normalize_tokens([1, "beta", 3]) == ["1", "beta", "3"]
    assert _normalize_tokens([0]) == ["0"]
    assert _normalize_tokens([" "]) == []  # whitespace-only stripped to empty

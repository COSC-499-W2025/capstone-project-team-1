from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from artifactminer.api.app import app
from artifactminer.db import Base, get_db


engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


def setup_function():
    Base.metadata.create_all(bind=engine)


def teardown_function():
    Base.metadata.drop_all(bind=engine)


def test_get_consent_seeds_default_if_missing():
    client = TestClient(app)
    response = client.get("/consent")

    assert response.status_code == 200
    payload = response.json()
    assert payload["consent_level"] == "none"
    assert payload["accepted_at"] is None


def test_get_consent_returns_existing_state():
    client = TestClient(app)
    
    client.put("/consent", json={"consent_level": "full"})
    
    response = client.get("/consent")
    assert response.status_code == 200
    payload = response.json()
    assert payload["consent_level"] == "full"
    assert payload["accepted_at"] is not None


def test_get_consent_response_structure():
    client = TestClient(app)
    response = client.get("/consent")

    assert response.status_code == 200
    payload = response.json()
    assert "consent_level" in payload
    assert "accepted_at" in payload
    assert isinstance(payload["consent_level"], str)
    assert payload["consent_level"] in ("full", "no_llm", "none")


def test_accept_full_consent():
    client = TestClient(app)
    response = client.put("/consent", json={"consent_level": "full"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["consent_level"] == "full"
    assert payload["accepted_at"] is not None


def test_accept_no_llm_consent():
    client = TestClient(app)
    response = client.put("/consent", json={"consent_level": "no_llm"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["consent_level"] == "no_llm"
    assert payload["accepted_at"] is not None


def test_set_consent_to_none():
    client = TestClient(app)
    
    client.put("/consent", json={"consent_level": "full"})
    
    response = client.put("/consent", json={"consent_level": "none"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["consent_level"] == "none"
    assert payload["accepted_at"] is None


def test_change_consent_level():
    client = TestClient(app)
    
    client.put("/consent", json={"consent_level": "full"})
    
    response = client.put("/consent", json={"consent_level": "no_llm"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["consent_level"] == "no_llm"
    assert payload["accepted_at"] is not None


def test_accepted_at_timestamp_format():
    client = TestClient(app)
    response = client.put("/consent", json={"consent_level": "full"})

    assert response.status_code == 200
    payload = response.json()
    accepted_at = payload["accepted_at"]
    assert accepted_at is not None
    assert "T" in accepted_at
    assert isinstance(accepted_at, str)


def test_multiple_updates_timestamp():
    client = TestClient(app)
    
    response1 = client.put("/consent", json={"consent_level": "full"})
    timestamp1 = response1.json()["accepted_at"]
    
    client.put("/consent", json={"consent_level": "none"})
    
    response2 = client.put("/consent", json={"consent_level": "no_llm"})
    timestamp2 = response2.json()["accepted_at"]
    
    assert timestamp1 != timestamp2


def test_consent_persists_across_requests():
    client = TestClient(app)
    
    client.put("/consent", json={"consent_level": "full"})
    
    response = client.get("/consent")
    assert response.status_code == 200
    assert response.json()["consent_level"] == "full"
    
    response = client.get("/consent")
    assert response.status_code == 200
    assert response.json()["consent_level"] == "full"


def test_update_consent_with_missing_fields():
    client = TestClient(app)
    
    response = client.put("/consent", json={})
    assert response.status_code == 422


def test_invalid_consent_level():
    client = TestClient(app)
    response = client.put("/consent", json={"consent_level": "invalid_level"})

    assert response.status_code == 422

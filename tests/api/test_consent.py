from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from artifactminer.api.app import app
from artifactminer.api.consent import CONSENT_VERSION
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
    assert payload["accepted"] is False
    assert payload["version"] == CONSENT_VERSION
    assert payload["accepted_at"] is None


def test_get_consent_returns_existing_state():
    client = TestClient(app)
    
    client.put("/consent", json={"accepted": True, "version": CONSENT_VERSION})
    
    response = client.get("/consent")
    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted"] is True
    assert payload["version"] == CONSENT_VERSION
    assert payload["accepted_at"] is not None


def test_get_consent_response_structure():
    client = TestClient(app)
    response = client.get("/consent")

    assert response.status_code == 200
    payload = response.json()
    assert "accepted" in payload
    assert "version" in payload
    assert "accepted_at" in payload
    assert isinstance(payload["accepted"], bool)
    assert isinstance(payload["version"], str)


def test_accept_consent_with_correct_version():
    client = TestClient(app)
    response = client.put("/consent", json={"accepted": True, "version": CONSENT_VERSION})

    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted"] is True
    assert payload["version"] == CONSENT_VERSION
    assert payload["accepted_at"] is not None


def test_accept_consent_with_incorrect_version():
    client = TestClient(app)
    outdated_version = "v99"
    response = client.put("/consent", json={"accepted": True, "version": outdated_version})

    assert response.status_code == 400
    error_detail = response.json()["detail"]
    assert error_detail["code"] == "CONSENT_VERSION_MISMATCH"
    assert "message" in error_detail
    assert error_detail["server_version"] == CONSENT_VERSION


def test_revoke_consent():
    client = TestClient(app)
    
    client.put("/consent", json={"accepted": True, "version": CONSENT_VERSION})
    
    response = client.put("/consent", json={"accepted": False, "version": CONSENT_VERSION})
    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted"] is False
    assert payload["accepted_at"] is None


def test_revoke_consent_ignores_version_mismatch():
    client = TestClient(app)
    
    client.put("/consent", json={"accepted": True, "version": CONSENT_VERSION})
    
    response = client.put("/consent", json={"accepted": False, "version": "v99"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted"] is False
    assert payload["accepted_at"] is None


def test_accepted_at_timestamp_format():
    client = TestClient(app)
    response = client.put("/consent", json={"accepted": True, "version": CONSENT_VERSION})

    assert response.status_code == 200
    payload = response.json()
    accepted_at = payload["accepted_at"]
    assert accepted_at is not None
    assert "T" in accepted_at
    assert isinstance(accepted_at, str)


def test_multiple_accept_updates_timestamp():
    client = TestClient(app)
    
    response1 = client.put("/consent", json={"accepted": True, "version": CONSENT_VERSION})
    timestamp1 = response1.json()["accepted_at"]
    
    client.put("/consent", json={"accepted": False, "version": CONSENT_VERSION})
    
    response2 = client.put("/consent", json={"accepted": True, "version": CONSENT_VERSION})
    timestamp2 = response2.json()["accepted_at"]
    
    assert timestamp1 != timestamp2


def test_consent_persists_across_requests():
    client = TestClient(app)
    
    client.put("/consent", json={"accepted": True, "version": CONSENT_VERSION})
    
    response = client.get("/consent")
    assert response.status_code == 200
    assert response.json()["accepted"] is True
    
    response = client.get("/consent")
    assert response.status_code == 200
    assert response.json()["accepted"] is True


def test_update_consent_with_missing_fields():
    client = TestClient(app)
    
    response = client.put("/consent", json={"accepted": True})
    assert response.status_code == 422
    
    response = client.put("/consent", json={"version": CONSENT_VERSION})
    assert response.status_code == 422


def test_version_mismatch_error_detail_structure():
    client = TestClient(app)
    response = client.put("/consent", json={"accepted": True, "version": "old_version"})

    assert response.status_code == 400
    error = response.json()
    assert "detail" in error
    detail = error["detail"]
    assert detail["code"] == "CONSENT_VERSION_MISMATCH"
    assert "message" in detail
    assert "server_version" in detail
    assert detail["server_version"] == CONSENT_VERSION
    assert isinstance(detail["message"], str)

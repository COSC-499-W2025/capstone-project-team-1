from fastapi.testclient import TestClient

from artifactminer.api.app import app


def test_healthcheck_returns_ok_status():
    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert "timestamp" in payload

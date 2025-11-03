def test_get_consent_seeds_default_if_missing(client):
    response = client.get("/consent")

    assert response.status_code == 200
    payload = response.json()
    assert payload["consent_level"] == "none"
    assert payload["accepted_at"] is None


def test_get_consent_returns_existing_state(client):
    
    client.put("/consent", json={"consent_level": "full"})
    
    response = client.get("/consent")
    assert response.status_code == 200
    payload = response.json()
    assert payload["consent_level"] == "full"
    assert payload["accepted_at"] is not None


def test_get_consent_response_structure(client):
    response = client.get("/consent")

    assert response.status_code == 200
    payload = response.json()
    assert "consent_level" in payload
    assert "accepted_at" in payload
    assert isinstance(payload["consent_level"], str)
    assert payload["consent_level"] in ("full", "no_llm", "none")


def test_accept_full_consent(client):
    response = client.put("/consent", json={"consent_level": "full"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["consent_level"] == "full"
    assert payload["accepted_at"] is not None


def test_accept_no_llm_consent(client):
    response = client.put("/consent", json={"consent_level": "no_llm"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["consent_level"] == "no_llm"
    assert payload["accepted_at"] is not None


def test_set_consent_to_none(client):
    
    client.put("/consent", json={"consent_level": "full"})
    
    response = client.put("/consent", json={"consent_level": "none"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["consent_level"] == "none"
    assert payload["accepted_at"] is None


def test_change_consent_level(client):
    
    client.put("/consent", json={"consent_level": "full"})
    
    response = client.put("/consent", json={"consent_level": "no_llm"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["consent_level"] == "no_llm"
    assert payload["accepted_at"] is not None


def test_accepted_at_timestamp_format(client):
    response = client.put("/consent", json={"consent_level": "full"})

    assert response.status_code == 200
    payload = response.json()
    accepted_at = payload["accepted_at"]
    assert accepted_at is not None
    assert "T" in accepted_at
    assert isinstance(accepted_at, str)


def test_multiple_updates_timestamp(client):
    
    response1 = client.put("/consent", json={"consent_level": "full"})
    timestamp1 = response1.json()["accepted_at"]
    
    client.put("/consent", json={"consent_level": "none"})
    
    response2 = client.put("/consent", json={"consent_level": "no_llm"})
    timestamp2 = response2.json()["accepted_at"]
    
    assert timestamp1 != timestamp2


def test_consent_persists_across_requests(client):
    
    client.put("/consent", json={"consent_level": "full"})
    
    response = client.get("/consent")
    assert response.status_code == 200
    assert response.json()["consent_level"] == "full"
    
    response = client.get("/consent")
    assert response.status_code == 200
    assert response.json()["consent_level"] == "full"


def test_update_consent_with_missing_fields(client):
    
    response = client.put("/consent", json={})
    assert response.status_code == 422


def test_invalid_consent_level(client):
    response = client.put("/consent", json={"consent_level": "invalid_level"})

    assert response.status_code == 422

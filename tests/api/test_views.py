"""Tests for the views representation preferences API."""


def test_get_prefs_returns_defaults_for_missing_portfolio(client):
    """GET on a non-existent portfolio_id returns default preferences."""
    response = client.get("/views/9999/prefs")

    assert response.status_code == 200
    payload = response.json()
    assert payload["showcase_project_ids"] == []
    assert payload["project_order"] == []


def test_put_get_roundtrip_returns_same_payload(client):
    """PUT then GET roundtrip returns the same payload."""
    prefs = {
        "showcase_project_ids": [101, 102],
        "project_order": [102, 101, 103],
    }

    # PUT the preferences
    put_response = client.put("/views/1/prefs", json=prefs)
    assert put_response.status_code == 200
    put_payload = put_response.json()
    assert put_payload["showcase_project_ids"] == prefs["showcase_project_ids"]
    assert put_payload["project_order"] == prefs["project_order"]

    # GET should return the same preferences
    get_response = client.get("/views/1/prefs")
    assert get_response.status_code == 200
    get_payload = get_response.json()
    assert get_payload["showcase_project_ids"] == prefs["showcase_project_ids"]
    assert get_payload["project_order"] == prefs["project_order"]

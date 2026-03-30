"""Tests for Education and Award API endpoints."""

import pytest


# ============================================================================
# EDUCATION TESTS
# ============================================================================


def test_list_education_empty(client):
    """Test listing education entries when none exist."""
    response = client.get("/education/?portfolio_id=test-portfolio")
    assert response.status_code == 200
    assert response.json() == []


def test_create_education(client):
    """Test creating a new education entry."""
    payload = {
        "institution": "Stanford University",
        "degree": "Bachelor",
        "field_of_study": "Computer Science",
        "start_date": "2020-09-01",
        "end_date": "2024-05-30",
        "gpa": "3.8",
        "honors": "Magna Cum Laude",
    }
    response = client.post(
        "/education/?portfolio_id=test-portfolio",
        json=payload,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["institution"] == "Stanford University"
    assert data["degree"] == "Bachelor"
    assert data["field_of_study"] == "Computer Science"
    assert data["start_date"] == "2020-09-01"
    assert data["end_date"] == "2024-05-30"
    assert data["gpa"] == "3.8"
    assert data["honors"] == "Magna Cum Laude"
    assert data["portfolio_id"] == "test-portfolio"
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_create_education_minimal(client):
    """Test creating education entry with minimal fields."""
    payload = {
        "institution": "MIT",
        "degree": "Master",
        "start_date": "2023-09-01",
    }
    response = client.post(
        "/education/?portfolio_id=test-portfolio",
        json=payload,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["institution"] == "MIT"
    assert data["end_date"] is None
    assert data["gpa"] is None


def test_get_education(client):
    """Test retrieving a specific education entry."""
    payload = {
        "institution": "Harvard",
        "degree": "PhD",
        "start_date": "2019-01-01",
    }
    create_response = client.post(
        "/education/?portfolio_id=test-portfolio",
        json=payload,
    )
    education_id = create_response.json()["id"]

    response = client.get(f"/education/{education_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == education_id
    assert data["institution"] == "Harvard"


def test_get_education_not_found(client):
    """Test retrieving non-existent education entry."""
    response = client.get("/education/99999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_update_education(client):
    """Test updating an education entry."""
    payload = {
        "institution": "Yale",
        "degree": "Bachelor",
        "start_date": "2020-01-01",
    }
    create_response = client.post(
        "/education/?portfolio_id=test-portfolio",
        json=payload,
    )
    education_id = create_response.json()["id"]

    update_payload = {
        "institution": "Yale University",
        "degree": "Master",
        "field_of_study": "Engineering",
        "start_date": "2022-01-01",
        "end_date": "2024-05-30",
        "gpa": "3.9",
        "honors": "Summa Cum Laude",
    }
    response = client.put(
        f"/education/{education_id}",
        json=update_payload,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["institution"] == "Yale University"
    assert data["degree"] == "Master"
    assert data["gpa"] == "3.9"


def test_delete_education(client):
    """Test deleting an education entry."""
    payload = {
        "institution": "Princeton",
        "degree": "Bachelor",
        "start_date": "2020-01-01",
    }
    create_response = client.post(
        "/education/?portfolio_id=test-portfolio",
        json=payload,
    )
    education_id = create_response.json()["id"]

    response = client.delete(f"/education/{education_id}")
    assert response.status_code == 200
    assert "deleted" in response.json()["detail"].lower()

    get_response = client.get(f"/education/{education_id}")
    assert get_response.status_code == 404


def test_list_education_by_portfolio(client):
    """Test listing education entries filtered by portfolio."""
    payload1 = {
        "institution": "Stanford",
        "degree": "Bachelor",
        "start_date": "2020-01-01",
    }
    client.post("/education/?portfolio_id=portfolio1", json=payload1)

    payload2 = {
        "institution": "MIT",
        "degree": "Master",
        "start_date": "2022-01-01",
    }
    client.post("/education/?portfolio_id=portfolio2", json=payload2)

    response = client.get("/education/?portfolio_id=portfolio1")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["institution"] == "Stanford"

    response = client.get("/education/?portfolio_id=portfolio2")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["institution"] == "MIT"


# ============================================================================
# AWARD TESTS
# ============================================================================


def test_list_awards_empty(client):
    """Test listing awards when none exist."""
    response = client.get("/education/awards/?portfolio_id=test-portfolio")
    assert response.status_code == 200
    assert response.json() == []


def test_create_award(client):
    """Test creating a new award entry."""
    payload = {
        "title": "Best Developer Award",
        "issuer": "Tech Conference 2024",
        "date": "2024-06-15",
        "description": "Awarded for exceptional contribution to open source",
    }
    response = client.post(
        "/education/awards/?portfolio_id=test-portfolio",
        json=payload,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Best Developer Award"
    assert data["issuer"] == "Tech Conference 2024"
    assert data["date"] == "2024-06-15"
    assert data["description"] == "Awarded for exceptional contribution to open source"
    assert data["portfolio_id"] == "test-portfolio"
    assert "id" in data


def test_create_award_minimal(client):
    """Test creating award with minimal fields."""
    payload = {
        "title": "Developer Award",
        "issuer": "Company",
        "date": "2024-01-01",
    }
    response = client.post(
        "/education/awards/?portfolio_id=test-portfolio",
        json=payload,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["description"] is None


def test_get_award(client):
    """Test retrieving a specific award."""
    payload = {
        "title": "Innovation Award",
        "issuer": "Tech Summit",
        "date": "2023-09-01",
    }
    create_response = client.post(
        "/education/awards/?portfolio_id=test-portfolio",
        json=payload,
    )
    award_id = create_response.json()["id"]

    response = client.get(f"/education/awards/{award_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == award_id
    assert data["title"] == "Innovation Award"


def test_get_award_not_found(client):
    """Test retrieving non-existent award."""
    response = client.get("/education/awards/99999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_update_award(client):
    """Test updating an award entry."""
    payload = {
        "title": "Award",
        "issuer": "Organization",
        "date": "2024-01-01",
    }
    create_response = client.post(
        "/education/awards/?portfolio_id=test-portfolio",
        json=payload,
    )
    award_id = create_response.json()["id"]

    update_payload = {
        "title": "Excellence in Engineering Award",
        "issuer": "Engineering Society",
        "date": "2024-03-15",
        "description": "For outstanding engineering achievements",
    }
    response = client.put(
        f"/education/awards/{award_id}",
        json=update_payload,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Excellence in Engineering Award"
    assert data["description"] == "For outstanding engineering achievements"


def test_delete_award(client):
    """Test deleting an award entry."""
    payload = {
        "title": "Award",
        "issuer": "Org",
        "date": "2024-01-01",
    }
    create_response = client.post(
        "/education/awards/?portfolio_id=test-portfolio",
        json=payload,
    )
    award_id = create_response.json()["id"]

    response = client.delete(f"/education/awards/{award_id}")
    assert response.status_code == 200
    assert "deleted" in response.json()["detail"].lower()

    get_response = client.get(f"/education/awards/{award_id}")
    assert get_response.status_code == 404


def test_list_awards_by_portfolio(client):
    """Test listing awards filtered by portfolio."""
    payload1 = {
        "title": "Award 1",
        "issuer": "Org 1",
        "date": "2024-01-01",
    }
    client.post("/education/awards/?portfolio_id=portfolio1", json=payload1)

    payload2 = {
        "title": "Award 2",
        "issuer": "Org 2",
        "date": "2024-02-01",
    }
    client.post("/education/awards/?portfolio_id=portfolio2", json=payload2)

    response = client.get("/education/awards/?portfolio_id=portfolio1")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Award 1"

    response = client.get("/education/awards/?portfolio_id=portfolio2")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Award 2"

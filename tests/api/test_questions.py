from fastapi.testclient import TestClient

from artifactminer.api.app import app


def test_get_questions_returns_list():
    client = TestClient(app)
    response = client.get("/questions")

    assert response.status_code == 200
    questions = response.json()
    assert isinstance(questions, list)
    assert len(questions) > 0


def test_questions_have_required_fields():
    client = TestClient(app)
    response = client.get("/questions")

    assert response.status_code == 200
    questions = response.json()
    
    for question in questions:
        assert "id" in question
        assert "question_text" in question
        assert "order" in question
        assert isinstance(question["id"], int)
        assert isinstance(question["question_text"], str)
        assert isinstance(question["order"], int)


def test_questions_are_ordered():
    client = TestClient(app)
    response = client.get("/questions")

    assert response.status_code == 200
    questions = response.json()
    
    orders = [q["order"] for q in questions]
    assert orders == sorted(orders)

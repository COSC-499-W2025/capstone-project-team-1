def test_get_questions_returns_list(client):
    response = client.get("/questions")

    assert response.status_code == 200
    questions = response.json()
    assert isinstance(questions, list)
    assert len(questions) > 0


def test_questions_have_required_fields(client):
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


def test_questions_are_ordered(client):
    response = client.get("/questions")

    assert response.status_code == 200
    questions = response.json()

    orders = [q["order"] for q in questions]
    assert orders == sorted(orders)


def test_submit_answers_success(client):
    """Test successful answer submission with valid email."""
    answers_payload = {
        "email": "test@example.com",
        "artifacts_focus": "Focus on Python files",
        "end_goal": "Analyze code quality",
        "repository_priority": "Git repository",
        "file_patterns": "*.py"
    }

    response = client.post("/answers", json=answers_payload)
    assert response.status_code == 200

    saved_answers = response.json()
    assert isinstance(saved_answers, list)
    assert len(saved_answers) == 5

    for answer in saved_answers:
        assert "id" in answer
        assert "question_id" in answer
        assert "answer_text" in answer
        assert "answered_at" in answer


def test_submit_answers_invalid_email(client):
    """Test that invalid email is rejected."""
    answers_payload = {
        "email": "not-an-email",
        "artifacts_focus": "Focus on Python files",
        "end_goal": "Analyze code quality",
        "repository_priority": "Git repository",
        "file_patterns": "*.py"
    }

    response = client.post("/answers", json=answers_payload)
    assert response.status_code == 422  # Validation error


def test_submit_answers_empty_text(client):
    """Test answer submission with empty answer fails validation."""
    answers_payload = {
        "email": "test@example.com",
        "artifacts_focus": "",  # Empty field
        "end_goal": "Analyze code quality",
        "repository_priority": "Git repository",
        "file_patterns": "*.py"
    }

    response = client.post("/answers", json=answers_payload)
    assert response.status_code == 422  # Validation error

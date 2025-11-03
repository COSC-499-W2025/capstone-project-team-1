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
        "answers": {
            "email": "test@example.com",
            "artifacts_focus": "Focus on Python files",
            "end_goal": "Analyze code quality",
            "repository_priority": "Git repository",
            "file_patterns_include": "*.py,*.js",
            "file_patterns_exclude": "*.log,*.tmp",
        }
    }

    response = client.post("/answers", json=answers_payload)
    assert response.status_code == 200

    saved_answers = response.json()
    assert isinstance(saved_answers, list)
    assert len(saved_answers) == 6

    for answer in saved_answers:
        assert "id" in answer
        assert "question_id" in answer
        assert "answer_text" in answer
        assert "answered_at" in answer


def test_submit_answers_invalid_email(client):
    """Test that invalid email is rejected."""
    answers_payload = {
        "answers": {
            "email": "not-an-email",
            "artifacts_focus": "Focus on Python files",
            "end_goal": "Analyze code quality",
            "repository_priority": "Git repository",
            "file_patterns_include": "*.py",
            "file_patterns_exclude": "*.log",
        }
    }

    response = client.post("/answers", json=answers_payload)
    assert response.status_code == 422  # Validation error


def test_submit_answers_empty_text(client):
    """Test answer submission with empty required field fails validation."""
    answers_payload = {
        "answers": {
            "email": "test@example.com",
            "artifacts_focus": "",  # Empty required field
            "end_goal": "Analyze code quality",
            "repository_priority": "Git repository",
            "file_patterns_include": "*.py",
            "file_patterns_exclude": "*.log",
        }
    }

    response = client.post("/answers", json=answers_payload)
    assert response.status_code == 422  # Validation error


def test_submit_answers_valid_comma_separated(client):
    """Test various valid comma-separated formats."""
    test_cases = [
        "*.py,*.js",  # No spaces
        "*.py, *.js, *.ts",  # With spaces
        "*.py",  # Single value
        "*.py,*.js,*.md,*.txt",  # Multiple values
    ]

    for pattern in test_cases:
        answers_payload = {
            "answers": {
                "email": "test@example.com",
                "artifacts_focus": "Focus on files",
                "end_goal": "Analyze code",
                "repository_priority": "Git",
                "file_patterns_include": pattern,
                "file_patterns_exclude": "*.log",
            }
        }

        response = client.post("/answers", json=answers_payload)
        assert response.status_code == 200, f"Failed for pattern: {pattern}"


def test_submit_answers_invalid_comma_separated(client):
    """Test that invalid comma-separated formats are rejected."""
    invalid_patterns = [
        "*.py,,*.js",  # Double comma (empty item)
        ",*.py",  # Leading comma
        "*.py,",  # Trailing comma
        "*.py, ,*.js",  # Whitespace-only item
    ]

    for pattern in invalid_patterns:
        answers_payload = {
            "answers": {
                "email": "test@example.com",
                "artifacts_focus": "Focus on files",
                "end_goal": "Analyze code",
                "repository_priority": "Git",
                "file_patterns_include": pattern,
                "file_patterns_exclude": "*.log",
            }
        }

        response = client.post("/answers", json=answers_payload)
        assert response.status_code == 422, f"Should fail for pattern: {pattern}"


def test_submit_answers_empty_comma_separated_allowed(client):
    """Test that empty comma-separated fields are allowed (required=False)."""
    answers_payload = {
        "answers": {
            "email": "test@example.com",
            "artifacts_focus": "Focus on files",
            "end_goal": "Analyze code",
            "repository_priority": "Git",
            "file_patterns_include": "",  # Empty is allowed
            "file_patterns_exclude": "",  # Empty is allowed
        }
    }

    response = client.post("/answers", json=answers_payload)
    assert response.status_code == 200

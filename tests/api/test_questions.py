from contextlib import contextmanager

from artifactminer.db import Question, UserAnswer, get_db


def _valid_answers_payload(**overrides):
    """Return a canonical answers payload with overrides applied."""
    answers = {
        "email": "test@example.com",
        "artifacts_focus": "Focus on Python files",
        "end_goal": "Analyze code quality",
        "repository_priority": "Git repository",
        "file_patterns_include": "*.py,*.js",
        "file_patterns_exclude": "*.log,*.tmp",
    }
    answers.update(overrides)
    return {"answers": answers}


@contextmanager
def _db_session(client):
    """Yield the current test DB session from the FastAPI dependency override."""
    override = client.app.dependency_overrides[get_db]
    generator = override()
    db = next(generator)
    try:
        yield db
    finally:
        generator.close()


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
    answers_payload = _valid_answers_payload()

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
    answers_payload = _valid_answers_payload(
        file_patterns_include="",
        file_patterns_exclude="",
        artifacts_focus="Focus on files",
        end_goal="Analyze code",
        repository_priority="Git",
    )

    response = client.post("/answers", json=answers_payload)
    assert response.status_code == 200


def test_submit_answers_upsert_updates_existing_entries(client):
    """Ensure posting twice updates existing answers instead of duplicating rows."""
    initial_payload = _valid_answers_payload()
    response = client.post("/answers", json=initial_payload)
    assert response.status_code == 200

    with _db_session(client) as db:
        total_before = db.query(UserAnswer).count()
        focus_question = (
            db.query(Question).filter(Question.key == "artifacts_focus").one()
        )
        focus_question_id = focus_question.id
        focus_answer_before = (
            db.query(UserAnswer)
            .filter(UserAnswer.question_id == focus_question_id)
            .one()
        )

    updated_payload = _valid_answers_payload(
        artifacts_focus="Emphasize architecture review documents"
    )
    response = client.post("/answers", json=updated_payload)
    assert response.status_code == 200

    with _db_session(client) as db:
        total_after = db.query(UserAnswer).count()
        focus_answer_after = (
            db.query(UserAnswer)
            .filter(UserAnswer.question_id == focus_question_id)
            .one()
        )

    assert total_after == total_before
    assert (
        focus_answer_after.answer_text
        == "Emphasize architecture review documents"
    )
    assert focus_answer_after.answered_at != focus_answer_before.answered_at


def test_submit_answers_rejects_unknown_keys(client):
    """Unknown question keys should raise a validation error."""
    payload = _valid_answers_payload()
    payload["answers"]["unexpected_field"] = "extra data"

    response = client.post("/answers", json=payload)
    assert response.status_code == 422
    assert response.json()["detail"] == "Invalid field provided."


def test_submit_answers_missing_required_field_is_rejected(client):
    """Omitting a required field entirely should fail validation."""
    payload = _valid_answers_payload()
    payload["answers"].pop("email")

    response = client.post("/answers", json=payload)
    assert response.status_code == 422
    assert response.json()["detail"] == "Please fill in all required fields."


def test_submit_answers_optional_fields_can_be_omitted(client):
    """Optional comma-separated questions can be left out entirely."""
    payload = _valid_answers_payload()
    payload["answers"].pop("file_patterns_include")
    payload["answers"].pop("file_patterns_exclude")

    response = client.post("/answers", json=payload)
    assert response.status_code == 200
    assert len(response.json()) == len(payload["answers"])

from artifactminer.db import (
    get_db,
)
from conftest import get_db


def test_post_user_answer(client):
    payload = {"email": "foo@example.com"}

    response = client.post("/postanswer/1", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["id"] > 0
    assert data["question_id"] == 1
    assert data["answer_text"] == payload["email"].lower()
    assert "answered_at" in data


from artifactminer.api.user_info import user_email_to_db
from artifactminer.db.models import UserAnswer

def test_user_email_to_db(db_session):
    email = "Test@Email.com"
    answer = user_email_to_db(db_session, email)

    assert isinstance(answer, UserAnswer)
    assert answer.id is not None
    assert answer.answer_text == email.lower()
    assert answer.question_id == 1

def test_get_user_answer(client):
    # Insert a test answer directly
 
    from artifactminer.db.models import UserAnswer
    from datetime import datetime

    payload = {"email": "foo@example.com"}

    #post data...
    response = client.post("/postanswer/1", json=payload)

    responseJson = response.json()
    resId = responseJson["id"]

    input = {"id" : 1}
    response = client.get(f"/useranswer", params=input)
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == resId
    assert data["question_id"] == 1
    assert data["answer_text"] == "foo@example.com"


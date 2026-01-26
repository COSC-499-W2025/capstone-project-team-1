from datetime import datetime, UTC

from sqlalchemy.orm import Session

from artifactminer.db import Consent, Question, UserAnswer


def setup_consent(db: Session, level: str) -> None:
    """Set consent level in database."""
    consent = db.get(Consent, 1)
    if consent is None:
        consent = Consent(id=1, consent_level=level, accepted_at=datetime.now(UTC))
        db.add(consent)
    else:
        consent.consent_level = level
        if level in ("full", "no_llm"):
            consent.accepted_at = datetime.now(UTC)
    db.commit()


def setup_user_email(db: Session, email: str) -> None:
    """Set user email in database."""
    email_question = db.query(Question).filter(Question.key == "email").first()
    if not email_question:
        email_question = Question(key="email", text="What is your email?", order=1)
        db.add(email_question)
        db.commit()
        db.refresh(email_question)

    db.query(UserAnswer).filter(UserAnswer.question_id == email_question.id).delete()
    answer = UserAnswer(
        question_id=email_question.id,
        answer_text=email,
        answered_at=datetime.now(UTC),
    )
    db.add(answer)
    db.commit()


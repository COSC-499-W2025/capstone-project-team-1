from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from artifactminer.db.models import Question, UserAnswer

from .schemas import UserAnswerCreate, UserAnswerResponse
from ..db import get_db

router = APIRouter(tags=["user_info"])


@router.get("/useranswer", response_model=UserAnswerResponse, tags=["user_info"])
async def get_user_info(
    id: int,
    db: Session = Depends(get_db),
):
    try:
        answer = (
            db.query(UserAnswer)
            .filter(UserAnswer.question_id == id)
            .order_by(UserAnswer.answered_at.desc())
            .first()
        )
        if answer is None:
            raise HTTPException(status_code=404, detail="Answer not found")

        response = UserAnswerResponse(
            id=answer.id,
            question_id=answer.question_id,
            answer_text=answer.answer_text,
            answered_at=answer.answered_at,
        )

        return response

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/postanswer/",
    response_model=UserAnswerResponse,
    tags=["user_info"],
)
async def create_user_answer(
    email_payload: UserAnswerCreate,
    db: Session = Depends(get_db),
):
    answer = user_email_to_db(db, email_payload.email)

    response = UserAnswerResponse(
        id=answer.id,
        question_id=answer.question_id,
        answer_text=answer.answer_text,
        answered_at=answer.answered_at,
    )

    return response


def user_email_to_db(db: Session, email: str) -> UserAnswer:
    """
    question id 1 = user's email
    """
    email_question_id = db.query(Question).filter(Question.key == "email").first() #get correct question id...

    email_answer = db.query(UserAnswer).filter(UserAnswer.question_id == email_question_id.id).first()

    if not email_answer:
        # if answer does not exist,
        email_answer = UserAnswer(
            question_id=1,  # EMAIL QUESTION
            answer_text=email.strip().lower(),
            answered_at=datetime.now(UTC)
        )
        db.add(email_answer)
        db.commit()
        db.refresh(email_answer)
    else:
        email_answer.answer_text = email.strip().lower()
        email_answer.answered_at = datetime.now(UTC)

        db.commit()
        db.refresh(email_answer)

    return email_answer

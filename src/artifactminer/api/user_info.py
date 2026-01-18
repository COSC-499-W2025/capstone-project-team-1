"""
Consent API module: endpoints and helpers for consent state.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from artifactminer.db.models import Question, UserAnswer

from .schemas import ConsentResponse, ConsentUpdateRequest, UserAnswerCreate, UserAnswerResponse
from ..db import Consent, get_db

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

from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session
@router.post(
    "/useranswer",
    response_model=UserAnswerResponse,
    tags=["user_info"],
)
async def create_user_answer(
    payload: UserAnswerCreate,
    db: Session = Depends(get_db),
):
    # Optional: validate question exists
    question = db.query(Question).filter(Question.id == payload.question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    ua = UserAnswer(
        question_id=payload.question_id,
        answer_text=payload.answer_text.strip(),
    )

    

    db.add(ua)
    db.commit()
    db.refresh(ua)

    response = UserAnswerResponse(
    id=payload.question_id,
    question_id=payload.question_id,
    answer_text=payload.answer_text,
    answered_at=datetime.utcnow,
    )

    return response
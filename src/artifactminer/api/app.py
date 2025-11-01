"""ASGI application exposing Artifact Miner backend services."""

from datetime import UTC, datetime
from typing import List

from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from .schemas import HealthStatus, QuestionResponse, UserAnswersRequest, UserAnswerResponse
from ..db import Base, engine, SessionLocal, Question, UserAnswer, get_db, seed_questions
from .consent import router as consent_router

def create_app() -> FastAPI:
    """Construct the FastAPI instance so tests or scripts can customize it."""
    app = FastAPI(
        title="Artifact Miner API",
        description="Backend services powering the Artifact Miner TUI.",
        version="0.1.0",
    )
    
    # Create database tables on startup
    Base.metadata.create_all(bind=engine)
    
    # Seed questions
    db = SessionLocal()
    try:
        seed_questions(db)
    finally:
        db.close()

    @app.get("/health", response_model=HealthStatus, tags=["system"])
    async def healthcheck() -> HealthStatus:
        """Basic readiness probe that lets the TUI verify connectivity."""
        return HealthStatus(status="ok", timestamp=datetime.now(UTC))

    @app.get("/questions", response_model=List[QuestionResponse], tags=["questions"])
    async def get_questions(db: Session = Depends(get_db)) -> List[Question]:
        """Fetch all active questions ordered by their display order."""
        questions = db.query(Question).filter(Question.is_active == True).order_by(Question.order).all()  # noqa: E712
        return questions

    @app.post("/answers", response_model=List[UserAnswerResponse], tags=["questions"])
    async def submit_answers(
        request: UserAnswersRequest,
        db: Session = Depends(get_db)
    ) -> List[UserAnswer]:
        """Save user answers to configuration questions."""
        # Map fields to question IDs (based on order from seed.py)
        answers_data = [
            (1, request.email),
            (2, request.artifacts_focus),
            (3, request.end_goal),
            (4, request.repository_priority),
            (5, request.file_patterns),
        ]

        saved_answers = []
        for question_id, answer_text in answers_data:
            user_answer = UserAnswer(
                question_id=question_id,
                answer_text=answer_text
            )
            db.add(user_answer)
            saved_answers.append(user_answer)

        db.commit()

        for answer in saved_answers:
            db.refresh(answer)

        return saved_answers

    # Mount consent router
    app.include_router(consent_router)

    return app


# Module-level application instance for ASGI servers (e.g., uvicorn).
app = create_app()

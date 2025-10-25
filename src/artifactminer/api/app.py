"""ASGI application exposing Artifact Miner backend services."""

from datetime import UTC, datetime
from typing import List

from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from .schemas import HealthStatus, QuestionResponse
from .database import Base, engine, SessionLocal
from .models import Question


def get_db():
    """Database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def seed_questions(db: Session) -> None:
    """Populate initial questions if the table is empty."""
    existing_count = db.query(Question).count()
    if existing_count > 0:
        return
    
    questions = [
        Question(question_text="What artifacts should we focus on? (e.g., code files, documentation, configs)", order=1, is_active=True),
        Question(question_text="What is your end goal with this analysis?", order=2, is_active=True),
        Question(question_text="Should we prioritize git repository analysis or scan all file types?", order=3, is_active=True),
        Question(question_text="Any specific file patterns to include or exclude?", order=4, is_active=True),
    ]
    
    db.add_all(questions)
    db.commit()

from ..db.database import Base, engine

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
        questions = db.query(Question).filter(Question.is_active == True).order_by(Question.order).all()
        return questions

    return app


# Module-level application instance for ASGI servers (e.g., uvicorn).
app = create_app()

"""ASGI application exposing Artifact Miner backend services."""

from datetime import UTC, datetime
from typing import List

from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from .schemas import HealthStatus, QuestionResponse
from ..db import Base, engine, SessionLocal, Question, get_db, seed_questions
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

    # Mount consent router
    app.include_router(consent_router)

    return app


# Module-level application instance for ASGI servers (e.g., uvicorn).
app = create_app()

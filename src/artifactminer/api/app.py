"""ASGI application exposing Artifact Miner backend services."""

from datetime import UTC, datetime
from typing import List

from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from fastapi import HTTPException
from email_validator import validate_email, EmailNotValidError

from .schemas import (
    HealthStatus,
    QuestionResponse,
    UserAnswerResponse,
    KeyedAnswersRequest,
)
from ..db import (
    Base,
    engine,
    SessionLocal,
    Question,
    UserAnswer,
    get_db,
    seed_questions,
)
from .consent import router as consent_router
from .zip import router as zip_router
from .openai import router as openai_router
from .projects import router as projects_router
from artifactminer.RepositoryIntelligence.repo_intelligence_main import (
    getRepoStats, saveRepoStats
)
from artifactminer.RepositoryIntelligence.repo_intelligence_user import (
    getUserRepoStats, saveUserRepoStats
)


def create_app() -> FastAPI:
    """Construct the FastAPI instance so tests or scripts can customize it."""
    app = FastAPI(
        title="Artifact Miner API",
        description="Backend services powering the Artifact Miner TUI.",
        version="0.1.0",
    )

    # Create database tables on startup
    Base.metadata.create_all(bind=engine)

    # Initialize database schema and seed
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
        questions = (
            db.query(Question)
            .filter(Question.is_active == True)
            .order_by(Question.order)
            .all()
        )  # noqa: E712
        return questions

    @app.post("/answers", response_model=List[UserAnswerResponse], tags=["questions"])
    async def submit_answers(
        request: KeyedAnswersRequest, db: Session = Depends(get_db)
    ) -> List[UserAnswer]:
        """Save user answers to configuration questions using a keyed payload."""

    @app.post("/repos/analyze", tags=["repositories"])
    async def analyze_repo(
        repo_path: str,
        user_email: str,
        db: Session = Depends(get_db)
    ):
        """Analyze a single git repository and store RepoStat + UserRepoStat."""
        repo_stats = getRepoStats(repo_path)
        saveRepoStats(repo_stats)

        user_stats = getUserRepoStats(repo_path, user_email)
        saveUserRepoStats(user_stats)

        return {
            "repo_stats": repo_stats.__dict__,
            "user_stats": user_stats.__dict__
        }

    # Mount routers (unchanged)
    app.include_router(consent_router)
    app.include_router(zip_router)
    app.include_router(projects_router)
    app.include_router(openai_router)
    return app


app = create_app()

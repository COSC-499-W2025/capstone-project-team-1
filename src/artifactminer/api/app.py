"""ASGI application exposing Artifact Miner backend services."""

from datetime import UTC, datetime, date, timedelta
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
    ProjectTimelineItem,
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

        # Prefetch active questions into a mapping for lookups and validation
        questions: list[Question] = (
            db.query(Question)
            .filter(Question.is_active == True)
            .order_by(Question.order)
            .all()
        )
        key_to_q = {q.key or str(q.id): q for q in questions}

        saved_answers: list[UserAnswer] = []

        # Normalize incoming answers: coerce to str and strip whitespace
        raw_answers = request.answers or {}
        answers = {k: ("" if v is None else str(v).strip()) for k, v in raw_answers.items()}

        # Validate required fields and answer types
        required_missing = [
            k
            for k, q in key_to_q.items()
            if (
                q.required and (k not in answers or not str(answers.get(k, "")).strip())
            )
        ]
        if required_missing:
            # Generic validation error for missing required fields
            raise HTTPException(
                status_code=422, detail="Please fill in all required fields."
            )

        # Type-specific validation (email)
        for k, v in answers.items():
            q = key_to_q.get(k)
            if not q:
                # Generic error for unknown fields
                raise HTTPException(status_code=422, detail="Invalid field provided.")
            if (q.answer_type or "text") == "email":
                try:
                    # Validate format only; avoid DNS/network checks
                    validate_email(v, check_deliverability=False)
                except EmailNotValidError:
                    # Generic error for invalid email format
                    raise HTTPException(
                        status_code=422, detail="Invalid email provided."
                    )
            elif (q.answer_type or "text") == "comma_separated":
                # Allow empty string (required=False questions)
                if v.strip():
                    # Split by comma, strip whitespace from each item
                    items = [item.strip() for item in v.split(",")]
                    # Reject if any empty items (e.g., "*.py,,*.js" or ",*.py")
                    if any(not item for item in items):
                        raise HTTPException(
                            status_code=422,
                            detail="Invalid comma-separated format. Use: *.py,*.js"
                        )

        # Persist (upsert: update existing or create new)
        for k, v in answers.items():
            q = key_to_q[k]
            # Check if answer already exists for this question
            existing = db.query(UserAnswer).filter(UserAnswer.question_id == q.id).first()
            if existing:
                # Update existing answer
                existing.answer_text = str(v).strip()
                existing.answered_at = datetime.now()
                saved_answers.append(existing)
            else:
                # Create new answer
                ua = UserAnswer(question_id=q.id, answer_text=str(v).strip())
                db.add(ua)
                saved_answers.append(ua)

        db.commit()
        for ans in saved_answers:
            db.refresh(ans)
        return saved_answers

    @app.get("/projects/timeline", response_model=List[ProjectTimelineItem], tags=["projects"])
    async def get_project_timeline(
        start_date: date | None = None,
        end_date: date | None = None,
        active_only: bool | None = None,
    ) -> list[ProjectTimelineItem]:
        """Return mocked project timeline data with simple filters applied."""

        now = datetime.utcnow()
        six_months_ago = now - timedelta(days=180)

        # Mocked dataset representing different activity patterns.
        mock_projects = [
            {
                "project_name": "Legacy Data Pipeline",
                "first_commit": datetime(2020, 2, 10),
                "last_commit": datetime(2020, 9, 25),
            },
            {
                "project_name": "Mobile Experience",
                "first_commit": now - timedelta(days=60),
                "last_commit": now - timedelta(days=2),
            },
            {
                "project_name": "Platform Core Services",
                "first_commit": datetime(2018, 7, 1),
                "last_commit": now - timedelta(days=5),
            },
            {
                "project_name": "Analytics Dashboard",
                "first_commit": now - timedelta(days=400),
                "last_commit": now - timedelta(days=190),
            },
        ]

        sorted_projects = sorted(mock_projects, key=lambda proj: proj["first_commit"])

        timeline_items: list[ProjectTimelineItem] = []
        for proj in sorted_projects:
            first_commit: datetime = proj["first_commit"]
            last_commit: datetime = proj["last_commit"]
            duration_days = (last_commit - first_commit).days
            was_active = last_commit >= six_months_ago

            if start_date and first_commit.date() < start_date:
                continue
            if end_date and first_commit.date() > end_date:
                continue
            if active_only and not was_active:
                continue

            timeline_items.append(
                ProjectTimelineItem(
                    project_name=proj["project_name"],
                    first_commit=first_commit,
                    last_commit=last_commit,
                    duration_days=duration_days,
                    was_active=was_active,
                )
            )

        return timeline_items

    # Mount consent router
    app.include_router(consent_router)
    app.include_router(zip_router)

    app.include_router(openai_router)
    return app


# Module-level application instance for ASGI servers (e.g., uvicorn).
app = create_app()

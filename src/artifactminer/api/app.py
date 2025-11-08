"""ASGI application exposing Artifact Miner backend services."""

from datetime import UTC, datetime
from typing import List
from pathlib import Path
import shutil

from fastapi import FastAPI, Depends, UploadFile, File
from sqlalchemy.orm import Session

from fastapi import HTTPException
from email_validator import validate_email, EmailNotValidError

from .schemas import (
    HealthStatus,
    QuestionResponse,
    UserAnswerResponse,
    KeyedAnswersRequest,
    ZipUploadResponse,
    DirectoriesResponse,
)
from ..db import (
    Base,
    engine,
    SessionLocal,
    Question,
    UserAnswer,
    UploadedZip,
    get_db,
    seed_questions,
)
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

    @app.post("/zip/upload", response_model=ZipUploadResponse, tags=["upload"])
    async def upload_zip(
        file: UploadFile = File(...), db: Session = Depends(get_db)
    ) -> ZipUploadResponse:
        """Upload a ZIP file for artifact analysis.

        Accepts a ZIP file, saves it to the ./uploads/ directory,
        and stores metadata in the database.
        """
        # Validate file extension
        if not file.filename or not file.filename.endswith(".zip"):
            raise HTTPException(
                status_code=422, detail="Only ZIP files are allowed."
            )

        # Create uploads directory if it doesn't exist
        upload_dir = Path("./uploads")
        upload_dir.mkdir(exist_ok=True)

        # Generate unique filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{timestamp}_{file.filename}"
        file_path = upload_dir / safe_filename

        # Save file to disk
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Store metadata in database
        uploaded_zip = UploadedZip(
            filename=file.filename, path=str(file_path)
        )
        db.add(uploaded_zip)
        db.commit()
        db.refresh(uploaded_zip)

        return ZipUploadResponse(
            zip_id=uploaded_zip.id, filename=uploaded_zip.filename
        )

    @app.get(
        "/zip/{zip_id}/directories",
        response_model=DirectoriesResponse,
        tags=["upload"],
    )
    async def get_directories(
        zip_id: int, db: Session = Depends(get_db)
    ) -> DirectoriesResponse:
        """Get list of directories from an uploaded ZIP file.

        Currently returns mock data for testing purposes.
        Backend extraction logic will be added later.
        """
        # Verify ZIP exists
        uploaded_zip = (
            db.query(UploadedZip).filter(UploadedZip.id == zip_id).first()
        )

        if not uploaded_zip:
            raise HTTPException(status_code=404, detail="ZIP file not found.")

        # Mock directory list (backend extraction logic pending)
        mock_directories = [
            "cs320_project/",
            "cs540_ai_project/",
            "hackathon_2024/",
            "personal_website/",
            "senior_design/",
        ]

        return DirectoriesResponse(
            zip_id=uploaded_zip.id,
            filename=uploaded_zip.filename,
            directories=mock_directories,
        )

    # Mount consent router
    app.include_router(consent_router)

    return app


# Module-level application instance for ASGI servers (e.g., uvicorn).
app = create_app()

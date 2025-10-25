"""ASGI application exposing Artifact Miner backend services."""

from datetime import UTC, datetime

from fastapi import FastAPI

from .schemas import HealthStatus

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

    @app.get("/health", response_model=HealthStatus, tags=["system"])
    async def healthcheck() -> HealthStatus:
        """Basic readiness probe that lets the TUI verify connectivity."""
        return HealthStatus(status="ok", timestamp=datetime.now(UTC))

    return app


# Module-level application instance for ASGI servers (e.g., uvicorn).
app = create_app()

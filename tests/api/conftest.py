import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from artifactminer.api.app import create_app
from artifactminer.db import Base, get_db, seed_questions, seed_repo_stats


@pytest.fixture(scope="function")
def client():
    """Create a test client with a fresh in-memory database for each test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    
    # Seed questions for the test database
    db = TestingSessionLocal()
    try:
        seed_questions(db)
        seed_repo_stats(db)
    finally:
        db.close()
    
    yield TestClient(app)
    
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)

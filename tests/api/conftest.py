import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from artifactminer.api.app import create_app
from artifactminer.api import local_llm
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
    
    # Clear any active intakes from previous tests
    local_llm._active_intakes.clear()
    local_llm._generation_jobs.clear()
    local_llm._active_generation_id = None
    
    yield TestClient(app)
    
    # Clean up active intakes after test
    for context in local_llm._active_intakes.values():
        import shutil
        from pathlib import Path
        if hasattr(context, 'extracted_dir') and Path(context.extracted_dir).exists():
            shutil.rmtree(context.extracted_dir)
    local_llm._active_intakes.clear()
    local_llm._generation_jobs.clear()
    local_llm._active_generation_id = None
    
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session():


    """
    This code creates a mock database for testing functions that require a database
    """

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # seed initial data
    db = TestingSessionLocal()
    try:
        seed_questions(db)
        seed_repo_stats(db)
    finally:
        db.close()
    
    session = TestingSessionLocal()
    yield session
    
    session.close()
    Base.metadata.drop_all(bind=engine)

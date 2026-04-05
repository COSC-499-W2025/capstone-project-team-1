from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker, declarative_base

from artifactminer.app_paths import DATABASE_URL, ensure_app_directories


ensure_app_directories()

SQLALCHEMY_DATABASE_URL = DATABASE_URL

_url = make_url(SQLALCHEMY_DATABASE_URL)
if _url.get_backend_name() == "sqlite" and _url.database not in (None, "", ":memory:"):
    Path(_url.database).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

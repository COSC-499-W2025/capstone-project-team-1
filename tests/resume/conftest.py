"""
Shared fixtures for resume pipeline tests.

Creates a temporary git repository with realistic commit history,
file structure, and README for testing extractors.
"""

from __future__ import annotations

import os
import textwrap
from pathlib import Path

import pytest
from git import Repo


TEST_EMAIL = "dev@example.com"
TEST_NAME = "Test Developer"


@pytest.fixture()
def sample_repo(tmp_path: Path) -> Path:
    """
    Create a realistic git repo with commits, README, routes, tests, etc.

    The repo simulates a small FastAPI web API project.
    """
    repo_dir = tmp_path / "my-web-api"
    repo_dir.mkdir()

    repo = Repo.init(repo_dir)
    repo.config_writer().set_value("user", "email", TEST_EMAIL).release()
    repo.config_writer().set_value("user", "name", TEST_NAME).release()

    # --- README ---
    readme = repo_dir / "README.md"
    readme.write_text(textwrap.dedent("""\
        # My Web API

        A REST API for managing tasks and users built with FastAPI.

        ## Features
        - User authentication with JWT
        - CRUD operations for tasks
        - Real-time notifications via WebSocket
    """))
    repo.index.add(["README.md"])
    repo.index.commit("docs: add project README")

    # --- Project structure ---
    (repo_dir / "src").mkdir()
    (repo_dir / "src" / "api").mkdir(parents=True)
    (repo_dir / "src" / "models").mkdir(parents=True)
    (repo_dir / "tests").mkdir()

    # --- Source files ---
    routes = repo_dir / "src" / "api" / "routes.py"
    routes.write_text(textwrap.dedent("""\
        from fastapi import APIRouter

        router = APIRouter()

        @router.get("/api/users")
        def list_users():
            return []

        @router.post("/api/users")
        def create_user(user: dict):
            return user

        @router.get("/api/tasks")
        def list_tasks():
            return []

        @router.delete("/api/tasks/{task_id}")
        def delete_task(task_id: int):
            return {"deleted": task_id}
    """))
    repo.index.add(["src/api/routes.py"])
    repo.index.commit("feat: implement user and task API endpoints")

    models = repo_dir / "src" / "models" / "user.py"
    models.write_text(textwrap.dedent("""\
        class User:
            def __init__(self, name: str, email: str):
                self.name = name
                self.email = email

        class TaskItem:
            def __init__(self, title: str, done: bool = False):
                self.title = title
                self.done = done
    """))
    repo.index.add(["src/models/user.py"])
    repo.index.commit("feat: add User and TaskItem models")

    auth = repo_dir / "src" / "api" / "auth.py"
    auth.write_text(textwrap.dedent("""\
        def authenticate(token: str) -> bool:
            return token == "valid"

        def generate_token(user_id: int) -> str:
            return f"token-{user_id}"
    """))
    repo.index.add(["src/api/auth.py"])
    repo.index.commit("feat: add JWT authentication helpers")

    # --- Tests ---
    test_file = repo_dir / "tests" / "test_routes.py"
    test_file.write_text(textwrap.dedent("""\
        def test_list_users():
            assert True

        def test_create_user():
            assert True

        def test_delete_task():
            assert True
    """))
    repo.index.add(["tests/test_routes.py"])
    repo.index.commit("test: add route handler tests")

    # --- Bug fix commit ---
    routes.write_text(routes.read_text() + "\n# Fixed null check\n")
    repo.index.add(["src/api/routes.py"])
    repo.index.commit("fix: handle null user in create endpoint")

    # --- Refactor commit ---
    models.write_text(models.read_text().replace("TaskItem", "Task"))
    repo.index.add(["src/models/user.py"])
    repo.index.commit("refactor: rename TaskItem to Task for consistency")

    # --- Config file ---
    pyproject = repo_dir / "pyproject.toml"
    pyproject.write_text('[project]\nname = "my-web-api"\n')
    repo.index.add(["pyproject.toml"])
    repo.index.commit("chore: add pyproject.toml")

    return repo_dir

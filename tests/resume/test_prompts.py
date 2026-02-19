"""Tests for the v3 prompt builders and assembler."""

from __future__ import annotations

from artifactminer.resume.models import (
    ProjectDataBundle,
    PortfolioDataBundle,
    ResumeOutput,
    ProjectSection,
    CommitGroup,
    CodeConstructs,
)
from artifactminer.resume.queries.runner import (
    _normalize_skills_section,
)
from artifactminer.resume.assembler import assemble_markdown, assemble_json


def _make_bundle() -> ProjectDataBundle:
    """Create a sample ProjectDataBundle for testing."""
    return ProjectDataBundle(
        project_name="my-web-api",
        project_path="/tmp/my-web-api",
        project_type="Web API",
        languages=["Python", "JavaScript"],
        language_percentages=[72.0, 28.0],
        primary_language="Python",
        frameworks=["FastAPI", "SQLAlchemy"],
        user_contribution_pct=100.0,
        user_total_commits=45,
        total_commits=45,
        first_commit="2024-01-15",
        last_commit="2024-06-20",
        readme_text="A REST API for managing tasks and users built with FastAPI.",
        commit_groups=[
            CommitGroup(
                category="feature",
                messages=[
                    "feat: implement user registration endpoint",
                    "feat: add task CRUD operations",
                    "feat: add JWT authentication",
                ],
            ),
            CommitGroup(
                category="bugfix",
                messages=[
                    "fix: handle null user in create endpoint",
                ],
            ),
            CommitGroup(
                category="test",
                messages=[
                    "test: add route handler tests",
                ],
            ),
        ],
        directory_overview=["src", "tests", "docs"],
        module_groups={"src": ["src/api/routes.py", "src/models/user.py"]},
        constructs=CodeConstructs(
            routes=["GET /api/users", "POST /api/users", "GET /api/tasks"],
            classes=["User", "TaskItem"],
            test_functions=["test_list_users", "test_create_user"],
            key_functions=["authenticate", "generate_token"],
        ),
        detected_skills=["REST API Design", "Authentication"],
    )


def _make_portfolio() -> PortfolioDataBundle:
    """Create a sample PortfolioDataBundle for testing."""
    bundle = _make_bundle()
    return PortfolioDataBundle(
        user_email="dev@example.com",
        projects=[bundle],
        total_projects=1,
        total_commits=45,
        languages_used=["Python", "JavaScript"],
        frameworks_used=["FastAPI", "SQLAlchemy"],
        earliest_commit="2024-01-15",
        latest_commit="2024-06-20",
        project_types={"Web API": 1},
        top_skills=["REST API Design", "Authentication"],
    )


class TestNormalizeSkillsSection:
    """Tests for skills section cleanup and normalization."""

    def test_moves_languages_out_of_other_categories(self) -> None:
        """Languages should not be duplicated under frameworks/practices."""
        portfolio = _make_portfolio()
        portfolio.top_skills = ["Testing", "CI/CD"]

        raw = (
            "Languages: Python, JavaScript\n"
            "Frameworks & Libraries: FastAPI, TypeScript, SQLAlchemy\n"
            "Practices: Python, Testing, CI/CD"
        )

        normalized = _normalize_skills_section(raw, portfolio)
        assert "Languages: Python, JavaScript, TypeScript" in normalized
        assert "Frameworks & Libraries: FastAPI, SQLAlchemy" in normalized
        assert "Tools & Infrastructure: CI/CD" in normalized
        assert "Practices: Testing" in normalized


# ── Assembler ─────────────────────────────────────────────────────────


class TestAssembleMarkdown:
    """Tests for the markdown assembler."""

    def test_produces_valid_markdown(self) -> None:
        """Should output markdown with expected headers."""
        output = ResumeOutput(
            project_sections={
                "my-web-api": ProjectSection(
                    description="A task management API.",
                    bullets=["Built user auth", "Added task CRUD"],
                    narrative="Solo-developed the entire API.",
                ),
            },
            professional_summary="Full-stack developer with API experience.",
            skills_section="Languages: Python, JavaScript",
            developer_profile="Focused on backend services.",
            portfolio_data=_make_portfolio(),
            model_used="qwen2.5-coder-3b-q4",
            generation_time_seconds=120.0,
        )
        md = assemble_markdown(output)
        assert "# Technical Resume" in md
        assert "## Professional Summary" in md
        assert "### my-web-api" in md
        assert "- Built user auth" in md
        assert "> Solo-developed" in md
        assert "qwen2.5-coder-3b-q4" in md

    def test_handles_empty_output(self) -> None:
        """Should produce valid markdown even with no data."""
        output = ResumeOutput()
        md = assemble_markdown(output)
        assert "# Technical Resume" in md


class TestAssembleJson:
    """Tests for the JSON assembler."""

    def test_produces_valid_json(self) -> None:
        """Should output parseable JSON."""
        import json

        output = ResumeOutput(
            project_sections={
                "my-web-api": ProjectSection(
                    description="A task management API.",
                    bullets=["Built user auth"],
                ),
            },
            professional_summary="Developer summary.",
            portfolio_data=_make_portfolio(),
            model_used="qwen2.5-coder-3b-q4",
        )
        json_str = assemble_json(output)
        data = json.loads(json_str)
        assert data["professional_summary"] == "Developer summary."
        assert len(data["projects"]) == 1
        assert data["projects"][0]["name"] == "my-web-api"

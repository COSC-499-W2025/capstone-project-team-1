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
from artifactminer.resume.queries.prompts import (
    build_project_prompt,
    build_summary_prompt,
    build_skills_prompt,
    build_profile_prompt,
)
from artifactminer.resume.queries.runner import _parse_project_response
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
            CommitGroup(category="feature", messages=[
                "feat: implement user registration endpoint",
                "feat: add task CRUD operations",
                "feat: add JWT authentication",
            ]),
            CommitGroup(category="bugfix", messages=[
                "fix: handle null user in create endpoint",
            ]),
            CommitGroup(category="test", messages=[
                "test: add route handler tests",
            ]),
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


# ── Prompt construction ───────────────────────────────────────────────


class TestBuildProjectPrompt:
    """Tests for the per-project prompt builder."""

    def test_includes_project_name(self) -> None:
        """Prompt should contain the project name."""
        prompt = build_project_prompt(_make_bundle())
        assert "my-web-api" in prompt

    def test_includes_commit_messages(self) -> None:
        """Prompt should include actual commit messages."""
        prompt = build_project_prompt(_make_bundle())
        assert "implement user registration endpoint" in prompt

    def test_includes_code_constructs(self) -> None:
        """Prompt should reference routes and classes."""
        prompt = build_project_prompt(_make_bundle())
        assert "/api/users" in prompt
        assert "User" in prompt

    def test_includes_readme_excerpt(self) -> None:
        """Prompt should contain the README excerpt."""
        prompt = build_project_prompt(_make_bundle())
        assert "REST API for managing tasks" in prompt

    def test_solo_project_hint(self) -> None:
        """100% contribution should trigger solo project language."""
        prompt = build_project_prompt(_make_bundle())
        assert "SOLO project" in prompt

    def test_no_solo_hint_for_team_projects(self) -> None:
        """Team projects should not get solo language."""
        bundle = _make_bundle()
        bundle.user_contribution_pct = 30.0
        prompt = build_project_prompt(bundle)
        assert "SOLO project" not in prompt

    def test_output_format_instructions(self) -> None:
        """Prompt should request DESCRIPTION/BULLETS/NARRATIVE format."""
        prompt = build_project_prompt(_make_bundle())
        assert "DESCRIPTION:" in prompt
        assert "BULLETS:" in prompt
        assert "NARRATIVE:" in prompt


class TestBuildPortfolioPrompts:
    """Tests for the portfolio-level prompt builders."""

    def test_summary_includes_project_count(self) -> None:
        """Summary prompt should mention number of projects."""
        prompt = build_summary_prompt(_make_portfolio())
        assert "1" in prompt

    def test_skills_includes_languages(self) -> None:
        """Skills prompt should list languages."""
        prompt = build_skills_prompt(_make_portfolio())
        assert "Python" in prompt
        assert "JavaScript" in prompt

    def test_profile_includes_project_types(self) -> None:
        """Profile prompt should mention project types."""
        prompt = build_profile_prompt(_make_portfolio())
        assert "Web API" in prompt


# ── Response parsing ──────────────────────────────────────────────────


class TestParseProjectResponse:
    """Tests for parsing the structured LLM response."""

    def test_parses_structured_response(self) -> None:
        """Should parse DESCRIPTION/BULLETS/NARRATIVE format."""
        text = (
            "DESCRIPTION: A FastAPI web service for task management.\n"
            "BULLETS:\n"
            "- Implemented user registration with JWT authentication\n"
            "- Built CRUD endpoints for task management\n"
            "- Added comprehensive route handler tests\n"
            "NARRATIVE: The developer independently architected a full REST API."
        )
        section = _parse_project_response(text)
        assert "FastAPI" in section.description
        assert len(section.bullets) == 3
        assert "JWT" in section.bullets[0]
        assert "independently" in section.narrative.lower()

    def test_handles_bullet_style_only(self) -> None:
        """Should fallback to parsing bullets when no structure markers."""
        text = (
            "- Built user authentication system\n"
            "- Implemented task CRUD operations\n"
        )
        section = _parse_project_response(text)
        assert len(section.bullets) == 2

    def test_handles_empty_response_gracefully(self) -> None:
        """Should not crash on empty sections."""
        text = "DESCRIPTION: \nBULLETS:\nNARRATIVE: "
        section = _parse_project_response(text)
        assert isinstance(section, ProjectSection)


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

"""Tests for Strategy B: Multi-stage pipeline with specialized models."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from artifactminer.resume.models import (
    CodeConstructs,
    CommitGroup,
    PortfolioDataBundle,
    ProjectDataBundle,
    ProjectSection,
    RawProjectFacts,
    ResumeOutput,
    UserFeedback,
)
from artifactminer.resume.queries.prompts import (
    DRAFT_SYSTEM,
    EXTRACTION_SYSTEM,
    POLISH_SYSTEM,
    build_draft_prompt,
    build_extraction_prompt,
    build_polish_prompt,
)
from artifactminer.resume.queries.runner import (
    _apply_citation_gate,
    _parse_draft_response,
    _parse_extraction_response,
    run_draft_queries,
    run_extraction_query,
    run_polish_query,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_bundle(**overrides) -> ProjectDataBundle:
    """Create a sample ProjectDataBundle for testing."""
    defaults = dict(
        project_name="my-web-api",
        project_path="/tmp/my-web-api",
        project_type="Web API",
        languages=["Python", "JavaScript"],
        language_percentages=[72.0, 28.0],
        primary_language="Python",
        frameworks=["FastAPI", "SQLAlchemy"],
        user_contribution_pct=85.0,
        user_total_commits=45,
        total_commits=53,
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
                messages=["fix: handle null user in create endpoint"],
            ),
        ],
        constructs=CodeConstructs(
            routes=["GET /api/users", "POST /api/users", "GET /api/tasks"],
            classes=["User", "TaskItem"],
            test_functions=["test_list_users"],
            key_functions=["authenticate", "generate_token"],
        ),
    )
    defaults.update(overrides)
    return ProjectDataBundle(**defaults)


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


def _make_raw_facts() -> dict[str, RawProjectFacts]:
    """Create sample extracted facts."""
    return {
        "my-web-api": RawProjectFacts(
            project_name="my-web-api",
            summary="A REST API for managing tasks and users with authentication.",
            facts=[
                "Built user registration endpoint with email validation",
                "Implemented JWT-based authentication with token refresh",
                "Created CRUD endpoints for task management",
                "Added null-safety checks in user creation flow",
            ],
            role="Contributed 85% of the codebase, focusing on backend API development.",
        ),
    }


def _make_draft_output() -> ResumeOutput:
    """Create a sample draft output for polish testing."""
    return ResumeOutput(
        stage="draft",
        project_sections={
            "my-web-api": ProjectSection(
                description="A REST API for task management with JWT authentication.",
                bullets=[
                    "Built user registration with email validation",
                    "Implemented JWT authentication with token refresh",
                    "Created CRUD endpoints for task lifecycle",
                ],
                narrative="Contributed 85% of the backend codebase.",
            ),
        },
        professional_summary="Software developer with experience building REST APIs.",
        skills_section="Languages: Python, JavaScript",
        developer_profile="Backend-focused developer with API expertise.",
        portfolio_data=_make_portfolio(),
        raw_project_facts=_make_raw_facts(),
    )


@pytest.fixture(autouse=True)
def _disable_structured_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep unit tests deterministic by forcing legacy text parser mode."""
    monkeypatch.setattr(
        "artifactminer.resume.queries.runner._should_use_structured_json",
        lambda _model: False,
    )


# ---------------------------------------------------------------------------
# Model types
# ---------------------------------------------------------------------------


class TestNewDataclasses:
    """Tests for Strategy B dataclasses."""

    def test_raw_project_facts_defaults(self) -> None:
        """RawProjectFacts should have sensible defaults."""
        facts = RawProjectFacts()
        assert facts.project_name == ""
        assert facts.summary == ""
        assert facts.facts == []
        assert facts.role == ""

    def test_user_feedback_defaults(self) -> None:
        """UserFeedback should have sensible defaults."""
        fb = UserFeedback()
        assert fb.section_edits == {}
        assert fb.additions == []
        assert fb.removals == []
        assert fb.tone == ""
        assert fb.general_notes == ""

    def test_resume_output_multistage_fields(self) -> None:
        """ResumeOutput should have multi-stage tracking fields."""
        output = ResumeOutput()
        assert output.raw_project_facts == {}
        assert output.stage == "single"
        assert output.models_used == []

    def test_user_feedback_with_content(self) -> None:
        """UserFeedback should accept all fields."""
        fb = UserFeedback(
            section_edits={"summary": "Updated summary text"},
            additions=["Mention Docker experience"],
            removals=["Remove Java reference"],
            tone="more technical",
            general_notes="Emphasize backend work",
        )
        assert "summary" in fb.section_edits
        assert len(fb.additions) == 1
        assert len(fb.removals) == 1
        assert fb.tone == "more technical"


# ---------------------------------------------------------------------------
# Stage 1: Extraction prompts and parsing
# ---------------------------------------------------------------------------


class TestExtractionPrompt:
    """Tests for Stage 1 extraction prompt."""

    def test_extraction_prompt_contains_format(self) -> None:
        """Extraction prompt should specify JSON schema fields."""
        prompt = build_extraction_prompt(_make_bundle())
        assert '"project_summary"' in prompt
        assert '"facts"' in prompt
        assert '"role"' in prompt
        assert '"fact_id"' in prompt
        assert '"evidence_keys"' in prompt

    def test_extraction_prompt_contains_project_data(self) -> None:
        """Extraction prompt should include project context."""
        prompt = build_extraction_prompt(_make_bundle())
        assert "my-web-api" in prompt
        assert "implement user registration endpoint" in prompt

    def test_extraction_prompt_format_before_data(self) -> None:
        """Output format should appear before project data."""
        prompt = build_extraction_prompt(_make_bundle())
        format_pos = prompt.index('"project_summary"')
        data_pos = prompt.index("Project data:")
        assert format_pos < data_pos


class TestParseExtractionResponse:
    """Tests for parsing Stage 1 extraction responses."""

    def test_parses_complete_response(self) -> None:
        """Should parse a well-formed extraction response."""
        text = (
            "PROJECT_SUMMARY: A task management REST API with authentication.\n"
            "FACTS:\n"
            "- Built user registration with email validation\n"
            "- Implemented JWT authentication\n"
            "- Created CRUD endpoints for tasks\n"
            "ROLE: Contributed 85% of the backend code."
        )
        facts = _parse_extraction_response(text, "my-api")
        assert facts.project_name == "my-api"
        assert "task management" in facts.summary.lower()
        assert len(facts.facts) == 3
        assert "JWT" in facts.facts[1]
        assert "85%" in facts.role

    def test_handles_empty_response(self) -> None:
        """Should return empty facts on empty response."""
        facts = _parse_extraction_response("", "my-api")
        assert facts.project_name == "my-api"
        assert facts.summary == ""
        assert facts.facts == []

    def test_parses_inline_summary(self) -> None:
        """Should handle PROJECT_SUMMARY on the same line."""
        text = "PROJECT_SUMMARY: A web application.\nFACTS:\n- Built API\nROLE: Lead developer"
        facts = _parse_extraction_response(text, "proj")
        assert "web application" in facts.summary.lower()
        assert len(facts.facts) == 1
        assert "Lead developer" in facts.role


# ---------------------------------------------------------------------------
# Stage 2: Draft prompts and parsing
# ---------------------------------------------------------------------------


class TestDraftPrompt:
    """Tests for Stage 2 draft prompt."""

    def test_draft_prompt_contains_format(self) -> None:
        """Draft prompt should specify full JSON output contract."""
        prompt = build_draft_prompt(_make_raw_facts(), _make_portfolio())
        assert '"professional_summary"' in prompt
        assert '"skills"' in prompt
        assert '"project_name"' in prompt
        assert '"bullets"' in prompt
        assert '"developer_profile"' in prompt
        assert '"fact_ids"' in prompt

    def test_draft_prompt_contains_extracted_facts(self) -> None:
        """Draft prompt should include the extracted facts."""
        prompt = build_draft_prompt(_make_raw_facts(), _make_portfolio())
        assert "JWT-based authentication" in prompt
        assert "my-web-api" in prompt

    def test_draft_prompt_contains_portfolio_context(self) -> None:
        """Draft prompt should include portfolio context."""
        prompt = build_draft_prompt(_make_raw_facts(), _make_portfolio())
        assert "Python" in prompt
        assert "FastAPI" in prompt


class TestParseDraftResponse:
    """Tests for parsing Stage 2 draft responses."""

    def test_parses_complete_draft(self) -> None:
        """Should parse a well-formed draft response."""
        text = (
            "PROFESSIONAL_SUMMARY: Experienced backend developer.\n"
            "SKILLS:\n"
            "Languages: Python, JavaScript\n"
            "PROJECT: my-web-api\n"
            "DESCRIPTION: A task management API.\n"
            "BULLETS:\n"
            "- Built user registration\n"
            "- Implemented JWT auth\n"
            "NARRATIVE: Contributed 85% of the codebase.\n"
            "DEVELOPER_PROFILE: Backend-focused developer with API expertise."
        )
        output = _parse_draft_response(text)
        assert output.stage == "draft"
        assert "backend developer" in output.professional_summary.lower()
        assert "my-web-api" in output.project_sections
        section = output.project_sections["my-web-api"]
        assert "task management" in section.description.lower()
        assert len(section.bullets) == 2
        assert "Backend-focused" in output.developer_profile

    def test_handles_empty_draft(self) -> None:
        """Should return empty output on empty response."""
        output = _parse_draft_response("")
        assert output.stage == "draft"
        assert output.professional_summary == ""
        assert output.project_sections == {}

    def test_parses_minimal_draft(self) -> None:
        """Should handle a draft with only some sections."""
        text = (
            "PROFESSIONAL_SUMMARY: A developer.\n"
            "DEVELOPER_PROFILE: Full-stack developer."
        )
        output = _parse_draft_response(text)
        assert "developer" in output.professional_summary.lower()
        assert "Full-stack" in output.developer_profile


# ---------------------------------------------------------------------------
# Stage 3: Polish prompt
# ---------------------------------------------------------------------------


class TestPolishPrompt:
    """Tests for Stage 3 polish prompt."""

    def test_polish_prompt_contains_draft(self) -> None:
        """Polish prompt should include the draft resume text."""
        draft = _make_draft_output()
        feedback = UserFeedback(tone="more technical")
        prompt = build_polish_prompt(draft, feedback)
        assert "task management" in prompt.lower()
        assert "85%" in prompt

    def test_polish_prompt_contains_feedback(self) -> None:
        """Polish prompt should include user feedback."""
        draft = _make_draft_output()
        feedback = UserFeedback(
            tone="formal",
            general_notes="Emphasize Python expertise",
            additions=["Mention Docker experience"],
            removals=["Remove JWT reference"],
        )
        prompt = build_polish_prompt(draft, feedback)
        assert "formal" in prompt
        assert "Emphasize Python expertise" in prompt
        assert "Docker" in prompt
        assert "JWT reference" in prompt

    def test_polish_prompt_no_feedback(self) -> None:
        """Polish prompt should handle empty feedback gracefully."""
        draft = _make_draft_output()
        feedback = UserFeedback()
        prompt = build_polish_prompt(draft, feedback)
        assert "Polish for clarity" in prompt


# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------


class TestMultistageSystemPrompts:
    """Tests for multi-stage system prompts."""

    def test_extraction_system_is_defined(self) -> None:
        """EXTRACTION_SYSTEM should be a non-empty string."""
        assert isinstance(EXTRACTION_SYSTEM, str)
        assert len(EXTRACTION_SYSTEM) > 20

    def test_draft_system_is_defined(self) -> None:
        """DRAFT_SYSTEM should be a non-empty string."""
        assert isinstance(DRAFT_SYSTEM, str)
        assert len(DRAFT_SYSTEM) > 20

    def test_polish_system_is_defined(self) -> None:
        """POLISH_SYSTEM should be a non-empty string."""
        assert isinstance(POLISH_SYSTEM, str)
        assert len(POLISH_SYSTEM) > 20


# ---------------------------------------------------------------------------
# Runner integration with mocked LLM
# ---------------------------------------------------------------------------


class TestRunExtractionQuery:
    """Tests for run_extraction_query with mocked LLM."""

    @patch("artifactminer.resume.queries.runner._query")
    def test_returns_parsed_facts(self, mock_query: MagicMock) -> None:
        """Should return RawProjectFacts from LLM response."""
        mock_query.return_value = (
            "PROJECT_SUMMARY: A task management API.\n"
            "FACTS:\n"
            "- Built registration endpoint\n"
            "- Added JWT auth\n"
            "- Created task CRUD\n"
            "ROLE: Contributed 85% of the code."
        )
        bundle = _make_bundle()
        facts = run_extraction_query(bundle, "lfm2.5-1.2b-q4")

        assert facts.project_name == "my-web-api"
        assert "task management" in facts.summary.lower()
        assert len(facts.facts) == 3
        assert "85%" in facts.role

        # Verify the query was called with correct system prompt
        mock_query.assert_called_once()
        call_args = mock_query.call_args
        assert call_args[0][2] == EXTRACTION_SYSTEM  # system prompt

    @patch("artifactminer.resume.queries.runner._query")
    def test_raises_on_empty_response(self, mock_query: MagicMock) -> None:
        """Should raise RuntimeError on empty LLM response."""
        mock_query.return_value = ""
        bundle = _make_bundle()
        with pytest.raises(RuntimeError, match="empty response"):
            run_extraction_query(bundle, "lfm2.5-1.2b-q4")


class TestRunDraftQueries:
    """Tests for run_draft_queries with mocked LLM."""

    @patch("artifactminer.resume.queries.runner._query")
    def test_returns_draft_output(self, mock_query: MagicMock) -> None:
        """Should return ResumeOutput with stage='draft'."""
        mock_query.return_value = (
            "PROFESSIONAL_SUMMARY: Experienced developer.\n"
            "SKILLS:\n"
            "Languages: Python, JavaScript\n"
            "PROJECT: my-web-api\n"
            "DESCRIPTION: A task API.\n"
            "BULLETS:\n"
            "- Built registration\n"
            "- Added auth\n"
            "NARRATIVE: Key contributor.\n"
            "DEVELOPER_PROFILE: Backend developer."
        )
        raw_facts = _make_raw_facts()
        portfolio = _make_portfolio()
        output = run_draft_queries(raw_facts, portfolio, "qwen3-1.7b-q8")

        assert output.stage == "draft"
        assert output.professional_summary
        assert output.portfolio_data is portfolio

        mock_query.assert_called_once()
        call_args = mock_query.call_args
        assert call_args[0][2] == DRAFT_SYSTEM

    @patch("artifactminer.resume.queries.runner._query")
    def test_raises_on_empty_response(self, mock_query: MagicMock) -> None:
        """Should raise RuntimeError on empty LLM response."""
        mock_query.return_value = ""
        with pytest.raises(RuntimeError, match="empty response"):
            run_draft_queries(_make_raw_facts(), _make_portfolio(), "qwen3-1.7b-q8")


class TestRunPolishQuery:
    """Tests for run_polish_query with mocked LLM."""

    @patch("artifactminer.resume.queries.runner._query")
    def test_returns_polished_output(self, mock_query: MagicMock) -> None:
        """Should return ResumeOutput with stage='polish'."""
        mock_query.return_value = (
            "PROFESSIONAL_SUMMARY: Seasoned backend engineer.\n"
            "SKILLS:\n"
            "Languages: Python, JavaScript\n"
            "PROJECT: my-web-api\n"
            "DESCRIPTION: A polished task management API.\n"
            "BULLETS:\n"
            "- Designed user registration with validation\n"
            "- Engineered JWT-based authentication\n"
            "NARRATIVE: Primary architect of the backend.\n"
            "DEVELOPER_PROFILE: Expert backend developer."
        )
        draft = _make_draft_output()
        feedback = UserFeedback(tone="more technical")
        output = run_polish_query(draft, feedback, "qwen3-4b-q4")

        assert output.stage == "polish"
        assert "engineer" in output.professional_summary.lower()

        mock_query.assert_called_once()
        call_args = mock_query.call_args
        assert call_args[0][2] == POLISH_SYSTEM

    @patch("artifactminer.resume.queries.runner._query")
    def test_falls_back_to_draft_on_empty(self, mock_query: MagicMock) -> None:
        """Should fall back to draft if polish returns empty."""
        mock_query.return_value = ""
        draft = _make_draft_output()
        feedback = UserFeedback()
        output = run_polish_query(draft, feedback, "qwen3-4b-q4")

        assert output.stage == "polish"
        # Should have draft content preserved
        assert output.professional_summary == draft.professional_summary

    @patch("artifactminer.resume.queries.runner._query")
    def test_preserves_draft_sections_on_partial_polish(
        self, mock_query: MagicMock
    ) -> None:
        """Should preserve draft sections not returned by polish."""
        mock_query.return_value = "PROFESSIONAL_SUMMARY: Updated summary."
        draft = _make_draft_output()
        feedback = UserFeedback()
        output = run_polish_query(draft, feedback, "qwen3-4b-q4")

        assert output.stage == "polish"
        assert "Updated summary" in output.professional_summary
        # Draft sections should be preserved
        assert output.developer_profile == draft.developer_profile
        assert output.skills_section  # should be preserved from draft


class TestCitationGate:
    """Tests for fact citation validation and auto-repair behavior."""

    def test_repairs_invalid_bullets_using_stage1_facts(self) -> None:
        """Bullets with missing/invalid citations should be repaired conservatively."""
        output = ResumeOutput(
            stage="draft",
            project_sections={
                "my-web-api": ProjectSection(
                    description="Task API",
                    bullets=["Did some backend work", "Improved reliability"],
                    bullet_fact_ids=[[], ["F99"]],
                    narrative="Contributed significantly.",
                )
            },
        )

        raw_facts = _make_raw_facts()
        metrics = _apply_citation_gate(output, raw_facts)

        section = output.project_sections["my-web-api"]
        assert metrics["repaired_bullets"] >= 1
        assert metrics["citation_precision"] == 1.0
        assert len(section.bullets) == 2
        assert all(ids for ids in section.bullet_fact_ids)

    def test_synthesizes_bullets_when_missing(self) -> None:
        """If a project has no bullets, gate should synthesize from facts."""
        output = ResumeOutput(
            stage="draft",
            project_sections={
                "my-web-api": ProjectSection(
                    description="Task API",
                    bullets=[],
                    bullet_fact_ids=[],
                    narrative="Contributed significantly.",
                )
            },
        )

        raw_facts = _make_raw_facts()
        metrics = _apply_citation_gate(output, raw_facts)

        section = output.project_sections["my-web-api"]
        assert section.bullets
        assert metrics["repaired_bullets"] >= 1
        assert metrics["fact_coverage"] > 0


# ---------------------------------------------------------------------------
# Model switching verification
# ---------------------------------------------------------------------------


class TestModelSwitching:
    """Tests verifying model switching between stages."""

    @patch("artifactminer.resume.queries.runner._query")
    def test_extraction_uses_correct_model(self, mock_query: MagicMock) -> None:
        """Stage 1 should use the specified extraction model."""
        mock_query.return_value = (
            "PROJECT_SUMMARY: An app.\nFACTS:\n- Built it\nROLE: Developer"
        )
        run_extraction_query(_make_bundle(), "lfm2.5-1.2b-q4")
        call_args = mock_query.call_args
        assert call_args[0][1] == "lfm2.5-1.2b-q4"  # model arg

    @patch("artifactminer.resume.queries.runner._query")
    def test_draft_uses_correct_model(self, mock_query: MagicMock) -> None:
        """Stage 2 should use the specified draft model."""
        mock_query.return_value = "PROFESSIONAL_SUMMARY: Developer."
        run_draft_queries(_make_raw_facts(), _make_portfolio(), "qwen3-1.7b-q8")
        call_args = mock_query.call_args
        assert call_args[0][1] == "qwen3-1.7b-q8"

    @patch("artifactminer.resume.queries.runner._query")
    def test_polish_uses_correct_model(self, mock_query: MagicMock) -> None:
        """Stage 3 should use the specified polish model."""
        mock_query.return_value = "PROFESSIONAL_SUMMARY: Senior developer."
        run_polish_query(_make_draft_output(), UserFeedback(), "qwen3-4b-q4")
        call_args = mock_query.call_args
        assert call_args[0][1] == "qwen3-4b-q4"


# ---------------------------------------------------------------------------
# Assembler multi-stage support
# ---------------------------------------------------------------------------


class TestAssemblerMultistage:
    """Tests for assembler multi-stage metadata support."""

    def test_markdown_shows_multi_model_footer(self) -> None:
        """Markdown footer should list all models when multi-stage."""
        from artifactminer.resume.assembler import assemble_markdown

        output = ResumeOutput(
            models_used=["lfm2.5-1.2b-q4", "qwen3-1.7b-q8", "qwen3-4b-q4"],
            stage="polish",
            generation_time_seconds=30.0,
        )
        md = assemble_markdown(output)
        assert "multi-stage pipeline" in md
        assert "lfm2.5-1.2b-q4" in md
        assert "qwen3-4b-q4" in md

    def test_json_includes_stage_metadata(self) -> None:
        """JSON output should include stage and models_used in metadata."""
        import json
        from artifactminer.resume.assembler import assemble_json

        output = ResumeOutput(
            models_used=["lfm2.5-1.2b-q4", "qwen3-1.7b-q8"],
            stage="draft",
            model_used="qwen3-1.7b-q8",
            generation_time_seconds=20.0,
        )
        data = json.loads(assemble_json(output))
        assert data["metadata"]["stage"] == "draft"
        assert "lfm2.5-1.2b-q4" in data["metadata"]["models_used"]

    def test_single_stage_footer_unchanged(self) -> None:
        """Single-stage output should use the original footer format."""
        from artifactminer.resume.assembler import assemble_markdown

        output = ResumeOutput(
            model_used="qwen2.5-coder-3b-q4",
            generation_time_seconds=120.0,
        )
        md = assemble_markdown(output)
        assert "qwen2.5-coder-3b-q4" in md
        assert "multi-stage" not in md


# ---------------------------------------------------------------------------
# Integration: enriched extraction → distillation (Phase 5)
# ---------------------------------------------------------------------------


class TestEnrichedExtractDistill:
    """Integration tests verifying enriched fields flow through distillation."""

    def test_enriched_bundle_distills_under_budget(self) -> None:
        """A fully-populated bundle should distill to ≤3500 tokens."""
        from artifactminer.resume.distill import distill_project_context
        from artifactminer.resume.models import (
            EnrichedClass,
            EnrichedConstructs,
            EnrichedFunction,
            GitStats,
            ImportGraph,
            ConfigFingerprint,
            ChurnComplexityHotspot,
            TestRatio,
            CommitQuality,
            ModuleBreadth,
        )
        from artifactminer.resume.analysis.developer_style import StyleMetrics
        from artifactminer.resume.analysis.skill_timeline import SkillAppearance

        bundle = _make_bundle(
            git_stats=GitStats(
                lines_added=3000,
                lines_deleted=500,
                net_lines=2500,
                files_touched=40,
                file_hotspots=[("src/api/routes.py", 15), ("src/models/user.py", 10)],
                active_days=60,
                active_span_days=180,
                avg_commit_size=50.0,
            ),
            test_ratio=TestRatio(
                test_files=5,
                source_files=12,
                test_ratio=0.42,
                has_ci=True,
            ),
            commit_quality=CommitQuality(
                conventional_pct=80.0,
                avg_message_length=45.0,
                type_diversity=4,
                longest_streak=7,
            ),
            module_breadth=ModuleBreadth(
                modules_touched=3,
                total_modules=4,
                breadth_pct=75.0,
                deepest_path="src/api/v2/routes.py",
            ),
            style_metrics=StyleMetrics(
                avg_function_length=15.0,
                max_function_length=45,
                total_functions=20,
                naming_convention="snake_case",
                type_annotation_ratio=0.7,
                comment_density=5.0,
                docstring_coverage=0.4,
                avg_imports_per_file=4.0,
                files_analyzed=8,
            ),
            file_complexity=[],
            skill_appearances=[
                SkillAppearance(
                    skill_name="Python",
                    first_date="2024-01-15",
                    project_name="my-web-api",
                    evidence="src/api/routes.py",
                ),
                SkillAppearance(
                    skill_name="Testing",
                    first_date="2024-02-10",
                    project_name="my-web-api",
                    evidence="tests/test_routes.py",
                ),
            ],
            enriched_constructs=EnrichedConstructs(
                classes=[
                    EnrichedClass(
                        name="User", method_count=3, total_loc=25, parent_class=""
                    ),
                    EnrichedClass(
                        name="TaskItem",
                        method_count=2,
                        total_loc=15,
                        parent_class="BaseModel",
                    ),
                ],
                functions=[
                    EnrichedFunction(
                        name="authenticate",
                        param_count=1,
                        loc=5,
                        has_return_type=True,
                    ),
                    EnrichedFunction(
                        name="generate_token",
                        param_count=1,
                        loc=3,
                        has_return_type=True,
                    ),
                ],
                routes=["GET /api/users", "POST /api/users", "GET /api/tasks"],
                test_functions=["test_list_users", "test_create_user"],
            ),
            import_graph=ImportGraph(
                imports_map={"src.api.routes": ["fastapi"], "src.api.auth": ["src.models.user"]},
                layer_detection=["presentation", "data"],
                circular_deps=[],
                external_deps=["fastapi", "sqlalchemy"],
            ),
            config_fingerprint=ConfigFingerprint(
                linters=["ruff", "mypy"],
                formatters=["black"],
                test_frameworks=["pytest"],
                build_tools=[],
                deployment_tools=["GitHub Actions"],
                package_managers=["uv"],
                pre_commit_hooks=["ruff", "mypy"],
            ),
            churn_complexity_hotspots=[
                ChurnComplexityHotspot(
                    filepath="src/api/routes.py",
                    edit_count=15,
                    cyclomatic_complexity=12,
                    max_nesting_depth=3,
                    risk_score=1.0,
                ),
            ],
        )

        ctx = distill_project_context(bundle)
        assert ctx.token_estimate <= 3500
        assert "ARCHITECTURE:" in ctx.text
        assert "CODE STYLE:" in ctx.text
        assert "Class User:" in ctx.text
        assert "SKILL TIMELINE:" in ctx.text

    def test_evidence_catalog_includes_new_fields(self) -> None:
        """Evidence catalog should include import graph and config items."""
        from artifactminer.resume.queries.prompts import (
            build_extraction_evidence_catalog,
        )
        from artifactminer.resume.models import (
            ImportGraph,
            ConfigFingerprint,
            ChurnComplexityHotspot,
        )

        bundle = _make_bundle(
            import_graph=ImportGraph(
                layer_detection=["presentation", "data"],
                external_deps=["fastapi"],
            ),
            config_fingerprint=ConfigFingerprint(
                linters=["ruff"],
                test_frameworks=["pytest"],
                deployment_tools=["GitHub Actions"],
                package_managers=["uv"],
            ),
            churn_complexity_hotspots=[
                ChurnComplexityHotspot(
                    filepath="src/api/routes.py",
                    edit_count=10,
                    cyclomatic_complexity=8,
                    max_nesting_depth=2,
                    risk_score=0.9,
                ),
            ],
        )

        catalog = build_extraction_evidence_catalog(bundle, max_items=36)
        values = list(catalog.values())
        values_str = " ".join(values)
        assert "arch_layer:" in values_str
        assert "external_dep:" in values_str
        assert "linter:" in values_str
        assert "hotspot:" in values_str

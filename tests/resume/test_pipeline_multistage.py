"""Tests for Strategy B: Multi-stage pipeline with specialized models."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from artifactminer.resume.models import (
    CodeConstructs,
    CommitGroup,
    EnrichedClass,
    EnrichedConstructs,
    EnrichedFunction,
    EvidenceLinkedFact,
    GitStats,
    ImportGraph,
    PortfolioDataBundle,
    ProjectDataBundle,
    ProjectSection,
    RawProjectFacts,
    ResumeOutput,
    TestRatio,
    UserFeedback,
)
from artifactminer.resume.queries.prompts import (
    BULLET_SYSTEM,
    MICRO_POLISH_SYSTEM,
)
from artifactminer.resume.queries.runner import (
    _apply_citation_gate,
    _build_data_card_context,
    _build_skills_deterministic,
    _clean_evidence_artifacts,
    _clean_llm_artifacts,
    _clean_summary_or_profile,
    _parse_bullet_response,
    compile_project_data_card,
    run_draft_queries,
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
        git_stats=GitStats(
            lines_added=3000,
            lines_deleted=500,
            net_lines=2500,
            files_touched=40,
            active_days=60,
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
                imports_map={
                    "src.api.routes": ["fastapi"],
                    "src.api.auth": ["src.models.user"],
                },
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


# ---------------------------------------------------------------------------
# v2 helpers
# ---------------------------------------------------------------------------


def _make_raw_facts_with_evidence() -> dict[str, RawProjectFacts]:
    """Create sample extracted facts with evidence-linked items."""
    return {
        "my-web-api": RawProjectFacts(
            project_name="my-web-api",
            summary="commit:feature:A REST API for managing tasks and users.",
            facts=[
                "commit:feat:Built user registration endpoint with email validation",
                "Implemented JWT-based authentication (E2) with token refresh",
                "Created CRUD endpoints [feature] for task management",
                "Added null-safety checks | evidence: E1, E4",
            ],
            fact_items=[
                EvidenceLinkedFact(
                    fact_id="F1",
                    text="commit:feat:Built user registration endpoint with email validation",
                    evidence_keys=["E1"],
                ),
                EvidenceLinkedFact(
                    fact_id="F2",
                    text="Implemented JWT-based authentication (E2) with token refresh",
                    evidence_keys=["E2"],
                ),
                EvidenceLinkedFact(
                    fact_id="F3",
                    text="Created CRUD endpoints [feature] for task management",
                    evidence_keys=["E3"],
                ),
            ],
            role="feat: Contributed 85% of the backend code.",
        ),
    }


# ---------------------------------------------------------------------------
# Step 2: Evidence artifact cleanup
# ---------------------------------------------------------------------------


class TestCleanEvidenceArtifacts:
    """Tests for _clean_evidence_artifacts stripping."""

    def test_strips_commit_prefix(self) -> None:
        """Should remove commit:feature: and commit:feat: prefixes."""
        assert _clean_evidence_artifacts("commit:feature:Added login") == "Added login"
        assert _clean_evidence_artifacts("commit:feat:Added login") == "Added login"

    def test_strips_inline_evidence_keys(self) -> None:
        """Should remove (E1), (E2) markers from inline text."""
        result = _clean_evidence_artifacts("Built API (E2) with auth")
        assert "(E2)" not in result
        assert "Built API" in result

    def test_strips_bracket_markers(self) -> None:
        """Should remove [feature], [docs] bracket markers."""
        result = _clean_evidence_artifacts("Added endpoint [feature] for users")
        assert "[feature]" not in result
        assert "Added endpoint" in result

    def test_strips_evidence_suffix(self) -> None:
        """Should remove | evidence: E1, E4 suffixes."""
        result = _clean_evidence_artifacts("Built API | evidence: E1, E4")
        assert "evidence:" not in result
        assert "Built API" in result

    def test_strips_conventional_commit_prefix(self) -> None:
        """Should remove feat:, fix: etc. prefixes."""
        assert _clean_evidence_artifacts("feat: added login") == "added login"
        assert _clean_evidence_artifacts("fix(auth): resolved bug") == "resolved bug"

    def test_handles_empty_input(self) -> None:
        """Should return empty string for empty input."""
        assert _clean_evidence_artifacts("") == ""
        assert _clean_evidence_artifacts(None) == ""


class TestCleanLlmArtifacts:
    """Tests for _clean_llm_artifacts stripping think tags, emoji, and mid-text prefixes."""

    def test_strips_think_tags(self) -> None:
        """Should remove </think> tags from LLM output."""
        result = _clean_llm_artifacts("Built user registration.</think>")
        assert "</think>" not in result
        assert "Built user registration." in result

    def test_strips_emoji_garbage(self) -> None:
        """Should remove long runs of emoji characters."""
        result = _clean_llm_artifacts(
            "Built API.\n\u2705\ufe0f\U0001f525\U0001f525\U0001f525\U0001f525"
        )
        assert "\U0001f525" not in result
        assert "Built API." in result

    def test_strips_midtext_conventional_prefix(self) -> None:
        """Should remove 'feat: ' appearing mid-text."""
        result = _clean_llm_artifacts("Implemented via feat: save results to JSON file")
        assert "feat:" not in result
        assert "save results" in result

    def test_preserves_clean_text(self) -> None:
        """Should not alter text that has no artifacts."""
        text = "Built user registration with email validation."
        assert _clean_llm_artifacts(text) == text

    def test_strips_note_parenthetical(self) -> None:
        """Should remove leaked editorial note parentheticals."""
        result = _clean_llm_artifacts(
            'Implemented result mapping. (Note: Since "map outputs" is vague, I rephrased it)'
        )
        assert "(Note:" not in result
        assert "Implemented result mapping." in result


class TestCleanSummaryOrProfile:
    """Tests for summary/profile cleanup helpers."""

    def test_strips_meta_preamble(self) -> None:
        """Should remove lead-in text like 'Here is a ...'."""
        text = (
            "Here is a 2-sentence professional summary for a software engineer's resume:\n\n"
            "Backend engineer with experience in APIs and tooling."
        )
        cleaned = _clean_summary_or_profile(text)
        assert "Here is" not in cleaned
        assert cleaned.startswith("Backend engineer")


class TestParseBulletResponse:
    """Tests for _parse_bullet_response with artifact cleanup."""

    def test_strips_think_tags_from_bullets(self) -> None:
        """Should produce clean bullets with no think tags."""
        text = (
            "- Built user registration.</think>\n- Added JWT auth.\n- Created CRUD.\n"
        )
        bullets = _parse_bullet_response(text)
        assert len(bullets) == 3
        for b in bullets:
            assert "</think>" not in b

    def test_strips_emoji_garbage_from_bullets(self) -> None:
        """Should remove emoji garbage appended to bullets."""
        text = (
            "- Built API.\n"
            "- Added auth.\n"
            "- Created CRUD.\n"
            "\u2705\ufe0f\U0001f525\U0001f525\U0001f525\U0001f525\U0001f525"
        )
        bullets = _parse_bullet_response(text)
        assert len(bullets) == 3
        for b in bullets:
            assert "\U0001f525" not in b


# ---------------------------------------------------------------------------
# Step 3: Deterministic skills
# ---------------------------------------------------------------------------


class TestBuildSkillsDeterministic:
    """Tests for _build_skills_deterministic capitalization and categorization."""

    def test_capitalizes_known_skills(self) -> None:
        """Should apply proper capitalization for known skill names."""
        portfolio = _make_portfolio()
        portfolio.languages_used = ["python", "javascript"]
        portfolio.frameworks_used = ["fastapi", "sqlalchemy"]
        skills = _build_skills_deterministic(portfolio)
        assert "Python" in skills
        assert "JavaScript" in skills
        assert "FastAPI" in skills

    def test_categorizes_tools_separately(self) -> None:
        """Should put tool-like items in Tools & Infrastructure."""
        portfolio = _make_portfolio()
        portfolio.frameworks_used = ["Docker", "FastAPI", "Kubernetes"]
        skills = _build_skills_deterministic(portfolio)
        assert "Tools & Infrastructure:" in skills
        assert "Docker" in skills.split("Tools & Infrastructure:")[1]

    def test_deduplicates_across_categories(self) -> None:
        """Should not list the same skill in multiple categories."""
        portfolio = _make_portfolio()
        portfolio.languages_used = ["Python"]
        portfolio.frameworks_used = ["Python"]  # duplicate
        portfolio.top_skills = ["Python"]  # triple
        skills = _build_skills_deterministic(portfolio)
        assert skills.count("Python") == 1


# ---------------------------------------------------------------------------
# Step 7: run_draft_queries
# ---------------------------------------------------------------------------


class TestRunDraftQueries:
    """Tests for run_draft_queries with mocked LLM."""

    @patch("artifactminer.resume.queries.runner._query")
    def test_returns_draft_with_micro_prompts(self, mock_query: MagicMock) -> None:
        """Should return a ResumeOutput built from per-section micro-prompts."""
        # Mock returns for bullet query, summary query, profile query
        mock_query.side_effect = [
            "- Designed user registration with email validation\n"
            "- Implemented JWT authentication with token refresh\n"
            "- Built CRUD endpoints for task management\n",
            "Experienced developer with 1 project using Python. Builds REST APIs and backend systems.",
            "Backend-focused developer with API and authentication expertise. Delivers reliable web services.",
        ]
        raw_facts = _make_raw_facts_with_evidence()
        portfolio = _make_portfolio()
        output = run_draft_queries(raw_facts, portfolio, "qwen3-1.7b-q8")

        assert output.stage == "draft"
        assert "my-web-api" in output.project_sections
        section = output.project_sections["my-web-api"]
        assert len(section.bullets) > 0
        assert output.professional_summary
        assert output.developer_profile
        assert output.skills_section

    @patch("artifactminer.resume.queries.runner._query")
    def test_uses_deterministic_skills(self, mock_query: MagicMock) -> None:
        """Skills section should be built deterministically without LLM call."""
        mock_query.side_effect = [
            "- Built registration\n- Added auth\n- Created CRUD\n",
            "Developer with projects.",
            "Backend developer.",
        ]
        raw_facts = _make_raw_facts_with_evidence()
        portfolio = _make_portfolio()
        output = run_draft_queries(raw_facts, portfolio, "qwen3-1.7b-q8")

        # 3 calls: 1 bullet + 1 summary + 1 profile (no skills LLM call)
        assert mock_query.call_count == 3
        assert "Languages:" in output.skills_section

    @patch("artifactminer.resume.queries.runner._query")
    def test_cleans_evidence_artifacts(self, mock_query: MagicMock) -> None:
        """Descriptions and narratives should be free of evidence artifacts."""
        mock_query.side_effect = [
            "- Built endpoint\n- Added auth\n- Created CRUD\n",
            "Summary text.",
            "Profile text.",
        ]
        raw_facts = _make_raw_facts_with_evidence()
        portfolio = _make_portfolio()
        output = run_draft_queries(raw_facts, portfolio, "qwen3-1.7b-q8")

        section = output.project_sections["my-web-api"]
        assert "commit:" not in section.description
        assert "(E" not in section.description


# ---------------------------------------------------------------------------
# Step 8: run_polish_query
# ---------------------------------------------------------------------------


class TestRunPolishQuery:
    """Tests for run_polish_query with mocked LLM."""

    @patch("artifactminer.resume.queries.runner._query")
    def test_polishes_bullets_with_feedback(self, mock_query: MagicMock) -> None:
        """Should polish bullets when feedback is provided."""
        mock_query.side_effect = [
            "- Engineered user registration with email validation\n"
            "- Architected JWT authentication system\n"
            "- Developed CRUD endpoints for task management\n",
            "Seasoned backend engineer with REST API expertise.",
            "Expert developer specializing in authentication systems.",
        ]
        draft = _make_draft_output()
        feedback = UserFeedback(
            tone="more technical", general_notes="Use stronger verbs"
        )
        output = run_polish_query(draft, feedback, "qwen3-1.7b-q8")

        assert output.stage == "polish"
        assert "my-web-api" in output.project_sections
        # Should have polished bullets (3 calls: bullets + summary + profile)
        assert mock_query.call_count == 3

    @patch("artifactminer.resume.queries.runner._query")
    def test_preserves_draft_without_feedback(self, mock_query: MagicMock) -> None:
        """Should preserve draft content when no feedback is provided."""
        draft = _make_draft_output()
        feedback = UserFeedback()
        output = run_polish_query(draft, feedback, "qwen3-1.7b-q8")

        assert output.stage == "polish"
        # No LLM calls should be made
        mock_query.assert_not_called()
        assert output.professional_summary == draft.professional_summary
        assert output.developer_profile == draft.developer_profile

    @patch("artifactminer.resume.queries.runner._query")
    def test_applies_direct_section_edits(self, mock_query: MagicMock) -> None:
        """Should apply section_edits directly without LLM."""
        draft = _make_draft_output()
        feedback = UserFeedback(
            section_edits={"summary": "Custom summary text."},
        )
        output = run_polish_query(draft, feedback, "qwen3-1.7b-q8")

        assert output.professional_summary == "Custom summary text."
        mock_query.assert_not_called()


# ---------------------------------------------------------------------------
# Assembler metrics line
# ---------------------------------------------------------------------------


class TestAssemblerMetricsLine:
    """Tests for the metrics line in assembled markdown."""

    def test_metrics_line_in_markdown(self) -> None:
        """Markdown should include a metrics line when git_stats are available."""
        from artifactminer.resume.assembler import assemble_markdown

        bundle = _make_bundle(
            git_stats=GitStats(
                lines_added=3000,
                files_touched=40,
                active_days=60,
            ),
        )
        portfolio = _make_portfolio()
        portfolio.projects = [bundle]

        output = ResumeOutput(
            stage="draft",
            portfolio_data=portfolio,
            project_sections={
                "my-web-api": ProjectSection(
                    description="A REST API.",
                    bullets=["Built registration endpoint"],
                ),
            },
        )
        md = assemble_markdown(output)
        assert "3,000 lines added" in md
        assert "40 files" in md
        assert "60 active days" in md


# ---------------------------------------------------------------------------
# Deterministic data card compilation (replaces Stage 1 LLM)
# ---------------------------------------------------------------------------


def _make_bundle_for_data_card(**overrides) -> ProjectDataBundle:
    """Create a ProjectDataBundle with enriched fields for data card tests."""
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
        readme_text="A REST API for managing tasks and users built with FastAPI. It supports authentication and CRUD operations.",
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
        git_stats=GitStats(
            lines_added=3000,
            lines_deleted=500,
            net_lines=2500,
            files_touched=40,
            active_days=60,
        ),
        test_ratio=TestRatio(
            test_files=5,
            source_files=12,
            test_ratio=0.42,
            has_ci=True,
        ),
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
                    name="authenticate", param_count=1, loc=5, has_return_type=True
                ),
            ],
            routes=["GET /api/users", "POST /api/users", "GET /api/tasks"],
            test_functions=["test_list_users", "test_create_user"],
        ),
    )
    defaults.update(overrides)
    return ProjectDataBundle(**defaults)


class TestCompileProjectDataCard:
    """Tests for compile_project_data_card deterministic fact compilation."""

    def test_produces_facts_from_feature_commits(self) -> None:
        """Should produce facts from feature commits with evidence links."""
        bundle = _make_bundle_for_data_card()
        result = compile_project_data_card(bundle)

        assert result.project_name == "my-web-api"
        assert result.source_format == "data_card"
        assert len(result.facts) >= 1
        assert len(result.fact_items) >= 1
        # At least one fact should come from a commit
        fact_texts = " ".join(result.facts)
        assert (
            "registration" in fact_texts or "CRUD" in fact_texts or "JWT" in fact_texts
        )

    def test_summary_derived_from_readme(self) -> None:
        """Summary should come from the first sentence of the README."""
        bundle = _make_bundle_for_data_card()
        result = compile_project_data_card(bundle)

        assert "REST API" in result.summary or "tasks" in result.summary.lower()

    def test_summary_fallback_when_no_readme(self) -> None:
        """Should fall back to project type when README is empty."""
        bundle = _make_bundle_for_data_card(readme_text="")
        result = compile_project_data_card(bundle)

        assert "web api" in result.summary.lower() or "python" in result.summary.lower()

    def test_filters_note_like_commit_facts(self) -> None:
        """Note/todo style commit messages should not become resume facts."""
        bundle = _make_bundle_for_data_card(
            commit_groups=[
                CommitGroup(
                    category="feature",
                    messages=[
                        "feat: notes: add ridge idea",
                        "feat: implement login endpoint",
                    ],
                )
            ]
        )
        result = compile_project_data_card(bundle)
        facts_text = " ".join(result.facts).lower()
        assert "notes" not in facts_text
        assert "todo" not in facts_text

    def test_skips_trivial_class_fact(self) -> None:
        """Trivial class metadata should be excluded from fact list."""
        bundle = _make_bundle_for_data_card(
            commit_groups=[
                CommitGroup(category="feature", messages=["feat: add auth endpoint"])
            ],
            enriched_constructs=EnrichedConstructs(
                classes=[
                    EnrichedClass(
                        name="SensorReading",
                        method_count=0,
                        total_loc=4,
                        parent_class="BaseModel",
                    )
                ],
                functions=[],
                routes=["GET /health", "POST /alerts"],
                test_functions=[],
            ),
            test_ratio=TestRatio(
                test_files=1, source_files=8, test_ratio=0.12, has_ci=False
            ),
        )
        result = compile_project_data_card(bundle)
        assert all("0 methods" not in fact for fact in result.facts)

    def test_role_reflects_contribution_pct(self) -> None:
        """Role should reflect the contribution percentage."""
        # Sole developer
        bundle_sole = _make_bundle_for_data_card(user_contribution_pct=100.0)
        result_sole = compile_project_data_card(bundle_sole)
        assert "Sole developer" in result_sole.role

        # Lead developer
        bundle_lead = _make_bundle_for_data_card(user_contribution_pct=75.0)
        result_lead = compile_project_data_card(bundle_lead)
        assert "Led development" in result_lead.role

        # Team contributor
        bundle_team = _make_bundle_for_data_card(user_contribution_pct=30.0)
        result_team = compile_project_data_card(bundle_team)
        assert "Contributed" in result_team.role

    def test_deduplicates_near_identical_commits(self) -> None:
        """Near-duplicate commits should be collapsed."""
        bundle = _make_bundle_for_data_card(
            commit_groups=[
                CommitGroup(
                    category="feature",
                    messages=[
                        "feat: add user authentication",
                        "feat(auth): add user authentication",
                        "feat: implement payment gateway",
                    ],
                ),
            ],
        )
        result = compile_project_data_card(bundle)

        # Should not have two facts about "user authentication"
        auth_facts = [f for f in result.facts if "authentication" in f.lower()]
        assert len(auth_facts) <= 1

    def test_supplements_with_construct_facts(self) -> None:
        """Should include construct-derived facts when commits are sparse."""
        bundle = _make_bundle_for_data_card(
            commit_groups=[
                CommitGroup(category="feature", messages=["feat: initial commit"]),
            ],
        )
        result = compile_project_data_card(bundle)

        # Should have route or class facts
        all_text = " ".join(result.facts)
        has_constructs = (
            "endpoint" in all_text.lower()
            or "class" in all_text.lower()
            or "User" in all_text
        )
        assert has_constructs

    def test_includes_test_coverage_fact(self) -> None:
        """Should include a test coverage fact when test files exist."""
        bundle = _make_bundle_for_data_card(
            commit_groups=[
                CommitGroup(
                    category="feature",
                    messages=["feat: add login endpoint"],
                ),
            ],
        )
        result = compile_project_data_card(bundle)

        test_facts = [f for f in result.facts if "test" in f.lower()]
        assert len(test_facts) >= 1

    def test_never_calls_llm(self) -> None:
        """compile_project_data_card should never invoke the LLM."""
        bundle = _make_bundle_for_data_card()
        # No mock needed — if it tried to call _query it would fail
        # since there's no server running. Just verify it returns cleanly.
        result = compile_project_data_card(bundle)
        assert result.source_format == "data_card"
        assert result.evidence_catalog  # should have an evidence catalog

    def test_evidence_catalog_populated(self) -> None:
        """Evidence catalog should be populated from bundle data."""
        bundle = _make_bundle_for_data_card()
        result = compile_project_data_card(bundle)

        assert len(result.evidence_catalog) > 0
        values = list(result.evidence_catalog.values())
        values_str = " ".join(values)
        assert "commit:" in values_str

    def test_max_facts_respected(self) -> None:
        """Should not produce more facts than max_facts."""
        bundle = _make_bundle_for_data_card(
            commit_groups=[
                CommitGroup(
                    category="feature",
                    messages=[f"feat: feature {i}" for i in range(10)],
                ),
            ],
        )
        result = compile_project_data_card(bundle, max_facts=3)

        assert len(result.facts) <= 3
        assert len(result.fact_items) <= 3


class TestBuildDataCardContext:
    """Tests for _build_data_card_context structured text block."""

    def test_contains_project_identity(self) -> None:
        """Context should include project type, language, and frameworks."""
        bundle = _make_bundle_for_data_card()
        context = _build_data_card_context(bundle)

        assert "Web API" in context
        assert "Python" in context
        assert "FastAPI" in context

    def test_contains_impact_metrics(self) -> None:
        """Context should include lines added, files, and active days."""
        bundle = _make_bundle_for_data_card()
        context = _build_data_card_context(bundle)

        assert "3,000" in context
        assert "40 files" in context
        assert "60 active days" in context

    def test_contains_constructs(self) -> None:
        """Context should include enriched class info and routes."""
        bundle = _make_bundle_for_data_card()
        context = _build_data_card_context(bundle)

        assert "User" in context
        assert "3 methods" in context
        assert "3 endpoints" in context

    def test_contains_contribution_pct(self) -> None:
        """Context should include contribution percentage."""
        bundle = _make_bundle_for_data_card()
        context = _build_data_card_context(bundle)

        assert "85%" in context

    def test_contains_test_ratio(self) -> None:
        """Context should include test ratio information."""
        bundle = _make_bundle_for_data_card()
        context = _build_data_card_context(bundle)

        assert "test" in context.lower()
        assert "42%" in context

    def test_handles_minimal_bundle(self) -> None:
        """Should not crash on a bundle with minimal data."""
        bundle = ProjectDataBundle(
            project_name="minimal",
            project_path="/tmp/minimal",
        )
        context = _build_data_card_context(bundle)

        assert "Software Project" in context

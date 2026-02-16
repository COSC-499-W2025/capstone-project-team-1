"""Tests for Strategy C prompt optimizations: few-shot, positive instructions, front-loaded format."""

from __future__ import annotations

import re

import pytest

from artifactminer.resume.llm_client import (
    MODEL_REGISTRY,
    MODEL_SAMPLING_DEFAULTS,
    get_sampling_params,
)
from artifactminer.resume.models import (
    CommitGroup,
    CodeConstructs,
    PortfolioDataBundle,
    ProjectDataBundle,
)
from artifactminer.resume.queries.prompts import (
    PROJECT_SYSTEM,
    SUMMARY_SYSTEM,
    _PROJECT_FEW_SHOT,
    build_profile_prompt,
    build_project_prompt,
    build_skills_prompt,
    build_summary_prompt,
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
                messages=["fix: handle null user in create endpoint"],
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


# ---------------------------------------------------------------------------
# C1: Few-shot example
# ---------------------------------------------------------------------------


class TestFewShotExample:
    """Tests that the few-shot example is present and well-formed."""

    def test_project_prompt_contains_few_shot(self) -> None:
        """build_project_prompt should include the few-shot example."""
        prompt = build_project_prompt(_make_bundle())
        assert "EXAMPLE INPUT:" in prompt
        assert "EXAMPLE OUTPUT:" in prompt

    def test_few_shot_contains_example_project(self) -> None:
        """Few-shot example should reference a realistic project name."""
        assert "TaskTracker" in _PROJECT_FEW_SHOT

    def test_few_shot_contains_all_output_sections(self) -> None:
        """Few-shot output should demonstrate DESCRIPTION/BULLETS/NARRATIVE."""
        assert "DESCRIPTION:" in _PROJECT_FEW_SHOT
        assert "BULLETS:" in _PROJECT_FEW_SHOT
        assert "NARRATIVE:" in _PROJECT_FEW_SHOT

    def test_few_shot_token_budget(self) -> None:
        """Few-shot example should be approximately 200-350 tokens (~4 chars/token)."""
        char_count = len(_PROJECT_FEW_SHOT)
        estimated_tokens = char_count / 4
        assert 150 <= estimated_tokens <= 400, (
            f"Few-shot is ~{estimated_tokens:.0f} tokens, expected 150-400"
        )


# ---------------------------------------------------------------------------
# C2: Positive-only instructions (no negatives)
# ---------------------------------------------------------------------------

_NEGATIVE_PATTERNS = [
    r"\bNever\b",
    r"\bDo not\b",
    r"\bDo NOT\b",
    r"\bDon't\b",
    r"\bdon't\b",
    r"\bAvoid\b",
]


class TestPositiveInstructions:
    """All prompt instructions should use positive framing."""

    def test_project_system_no_negatives(self) -> None:
        """PROJECT_SYSTEM should contain only positive instructions."""
        for pattern in _NEGATIVE_PATTERNS:
            assert not re.search(pattern, PROJECT_SYSTEM), (
                f"PROJECT_SYSTEM contains negative instruction matching: {pattern}"
            )

    def test_summary_system_no_negatives(self) -> None:
        """SUMMARY_SYSTEM should contain only positive instructions."""
        for pattern in _NEGATIVE_PATTERNS:
            assert not re.search(pattern, SUMMARY_SYSTEM), (
                f"SUMMARY_SYSTEM contains negative instruction matching: {pattern}"
            )

    def test_project_prompt_no_negatives(self) -> None:
        """build_project_prompt output should avoid negative instructions."""
        prompt = build_project_prompt(_make_bundle())
        for pattern in _NEGATIVE_PATTERNS:
            assert not re.search(pattern, prompt), (
                f"Project prompt contains negative instruction matching: {pattern}"
            )

    def test_summary_prompt_no_negatives(self) -> None:
        """build_summary_prompt output should avoid negative instructions."""
        prompt = build_summary_prompt(_make_portfolio())
        for pattern in _NEGATIVE_PATTERNS:
            assert not re.search(pattern, prompt), (
                f"Summary prompt contains negative instruction matching: {pattern}"
            )

    def test_skills_prompt_no_negatives(self) -> None:
        """build_skills_prompt output should avoid negative instructions."""
        prompt = build_skills_prompt(_make_portfolio())
        for pattern in _NEGATIVE_PATTERNS:
            assert not re.search(pattern, prompt), (
                f"Skills prompt contains negative instruction matching: {pattern}"
            )

    def test_profile_prompt_no_negatives(self) -> None:
        """build_profile_prompt output should avoid negative instructions."""
        prompt = build_profile_prompt(_make_portfolio())
        for pattern in _NEGATIVE_PATTERNS:
            assert not re.search(pattern, prompt), (
                f"Profile prompt contains negative instruction matching: {pattern}"
            )


# ---------------------------------------------------------------------------
# C3: Front-loaded output format
# ---------------------------------------------------------------------------


class TestFrontLoadedFormat:
    """Output format should appear before the project data in prompts."""

    def test_project_prompt_format_before_data(self) -> None:
        """Format spec should appear before project context data."""
        prompt = build_project_prompt(_make_bundle())
        format_pos = prompt.index("DESCRIPTION:")
        data_pos = prompt.index("PROJECT: my-web-api")
        assert format_pos < data_pos, "Format spec should come before project data"

    def test_summary_prompt_rules_before_data(self) -> None:
        """Rules should appear before portfolio data in summary prompt."""
        prompt = build_summary_prompt(_make_portfolio())
        rules_pos = prompt.index("Rules:")
        data_pos = prompt.index("Portfolio data:")
        assert rules_pos < data_pos, "Rules should come before portfolio data"

    def test_skills_prompt_format_before_data(self) -> None:
        """Format block should appear before skill listings."""
        prompt = build_skills_prompt(_make_portfolio())
        format_pos = prompt.index("Format:")
        data_pos = prompt.index("Languages: Python")
        assert format_pos < data_pos, "Format should come before data"

    def test_profile_prompt_rules_before_data(self) -> None:
        """Rules should appear before project data in profile prompt."""
        prompt = build_profile_prompt(_make_portfolio())
        rules_pos = prompt.index("Rules:")
        data_pos = prompt.index("Project data:")
        assert rules_pos < data_pos, "Rules should come before project data"


# ---------------------------------------------------------------------------
# C4: Per-model sampling parameters
# ---------------------------------------------------------------------------


class TestModelSamplingConfig:
    """Tests for per-model sampling parameter configuration."""

    def test_lfm25_sampling_params(self) -> None:
        """LFM2.5 models should use low temperature and top_p."""
        params = get_sampling_params("lfm2.5-1.2b-q4")
        assert params["temperature"] == 0.1
        assert params["top_p"] == 0.1
        assert params["repetition_penalty"] == 1.05

    def test_qwen25_coder_sampling_params(self) -> None:
        """Qwen2.5-Coder models should have their own temperature."""
        params = get_sampling_params("qwen2.5-coder-3b-q4")
        assert params["temperature"] == 0.15
        assert params["top_p"] == 0.9

    def test_qwen3_sampling_params(self) -> None:
        """Qwen3 models should have their own temperature."""
        params = get_sampling_params("qwen3-4b-q4")
        assert params["temperature"] == 0.2
        assert params["top_p"] == 0.9

    def test_unknown_model_gets_default(self) -> None:
        """Unknown model names should get default sampling params."""
        params = get_sampling_params("unknown-model-7b")
        assert params["temperature"] == 0.2
        assert params["top_p"] == 0.9

    def test_default_has_no_repetition_penalty(self) -> None:
        """Default params should not include repetition_penalty."""
        params = get_sampling_params("unknown-model-7b")
        assert "repetition_penalty" not in params

    def test_get_sampling_params_returns_copy(self) -> None:
        """get_sampling_params should return a copy, not the original dict."""
        params1 = get_sampling_params("qwen3-4b-q4")
        params1["temperature"] = 999
        params2 = get_sampling_params("qwen3-4b-q4")
        assert params2["temperature"] == 0.2


# ---------------------------------------------------------------------------
# C6: MODEL_REGISTRY fixes
# ---------------------------------------------------------------------------


class TestModelRegistryFixes:
    """Verify MODEL_REGISTRY entries point to correct repos."""

    def test_lfm2_repo(self) -> None:
        """lfm2-2.6b-q8 should reference LiquidAI repo."""
        repo_id, filename, ctx = MODEL_REGISTRY["lfm2-2.6b-q8"]
        assert repo_id == "LiquidAI/LFM2-2.6B-GGUF"
        assert filename == "LFM2-2.6B-Q8_0.gguf"
        assert ctx == 20480

    def test_lfm25_q4_repo(self) -> None:
        """lfm2.5-1.2b-q4 should reference LiquidAI repo."""
        repo_id, filename, ctx = MODEL_REGISTRY["lfm2.5-1.2b-q4"]
        assert repo_id == "LiquidAI/LFM2.5-1.2B-Instruct-GGUF"
        assert filename == "LFM2.5-1.2B-Instruct-Q4_K_M.gguf"
        assert ctx == 32768

    def test_lfm25_bf16_repo(self) -> None:
        """lfm2.5-1.2b-bf16 should reference LiquidAI repo."""
        repo_id, filename, ctx = MODEL_REGISTRY["lfm2.5-1.2b-bf16"]
        assert repo_id == "LiquidAI/LFM2.5-1.2B-Instruct-GGUF"
        assert filename == "LFM2.5-1.2B-Instruct-BF16.gguf"
        assert ctx == 32768


# ---------------------------------------------------------------------------
# Commit deduplication in to_prompt_context
# ---------------------------------------------------------------------------


class TestCommitDedup:
    """Tests for commit message deduplication in to_prompt_context."""

    def test_exact_duplicates_removed(self) -> None:
        """Exact duplicate commit messages should be collapsed."""
        bundle = _make_bundle(
            commit_groups=[
                CommitGroup(
                    category="feature",
                    messages=[
                        "feat: add login endpoint",
                        "feat: add login endpoint",
                        "feat: add logout endpoint",
                    ],
                ),
            ]
        )
        context = bundle.to_prompt_context()
        # Should appear only once
        assert context.count("add login endpoint") == 1
        assert "add logout endpoint" in context

    def test_near_duplicate_commits_collapsed(self) -> None:
        """Near-identical commits (same words, different prefix) should be collapsed."""
        bundle = _make_bundle(
            commit_groups=[
                CommitGroup(
                    category="feature",
                    messages=[
                        "feat: add user authentication",
                        "feat(auth): add user authentication",
                        "feat: implement payment gateway",
                    ],
                ),
            ]
        )
        context = bundle.to_prompt_context()
        # "add user authentication" appears in two near-identical messages
        lines = [l.strip() for l in context.split("\n") if "authentication" in l.lower()]
        assert len(lines) == 1, f"Expected 1 auth line, got {len(lines)}: {lines}"
        assert "payment gateway" in context

    def test_distinct_commits_preserved(self) -> None:
        """Genuinely different commit messages should all be kept."""
        bundle = _make_bundle(
            commit_groups=[
                CommitGroup(
                    category="feature",
                    messages=[
                        "feat: add REST API with CRUD endpoints",
                        "feat: implement WebSocket notifications",
                        "feat: build CI/CD pipeline with GitHub Actions",
                    ],
                ),
            ]
        )
        context = bundle.to_prompt_context()
        assert "REST API" in context
        assert "WebSocket" in context
        assert "CI/CD" in context

    def test_normalize_strips_ticket_numbers(self) -> None:
        """Normalization should strip ticket numbers like #123 or PROJ-456."""
        normalized = ProjectDataBundle._normalize_commit_msg(
            "feat: add login page #123"
        )
        assert "#123" not in normalized
        assert "login page" in normalized

        normalized2 = ProjectDataBundle._normalize_commit_msg(
            "fix(PROJ-789): resolve null pointer"
        )
        assert "PROJ-789" not in normalized2
        assert "resolve null pointer" in normalized2

    def test_empty_messages_handled(self) -> None:
        """Empty message lists should not cause errors."""
        result = ProjectDataBundle._dedup_commit_messages([])
        assert result == []

    def test_single_message_unchanged(self) -> None:
        """A single message should pass through unchanged."""
        result = ProjectDataBundle._dedup_commit_messages(["feat: add feature"])
        assert result == ["feat: add feature"]


# ---------------------------------------------------------------------------
# Prompt builder parameterized checks
# ---------------------------------------------------------------------------


class TestPromptBuildersParameterized:
    """Parameterized tests for prompt builder structural properties."""

    @pytest.mark.parametrize("contribution,expected_hint", [
        (100.0, "SOLO project"),
        (95.0, "SOLO project"),
        (94.0, "TEAM project"),
        (50.0, "TEAM project"),
        (None, ""),
    ])
    def test_ownership_hint(self, contribution, expected_hint) -> None:
        """Ownership hint should match contribution percentage."""
        bundle = _make_bundle(user_contribution_pct=contribution)
        prompt = build_project_prompt(bundle)
        if expected_hint:
            assert expected_hint in prompt
        else:
            assert "SOLO project" not in prompt
            assert "TEAM project" not in prompt

    @pytest.mark.parametrize("builder,required_markers", [
        (
            lambda: build_project_prompt(_make_bundle()),
            ["DESCRIPTION:", "BULLETS:", "NARRATIVE:"],
        ),
        (
            lambda: build_summary_prompt(_make_portfolio()),
            ["Rules:", "Portfolio data:"],
        ),
        (
            lambda: build_skills_prompt(_make_portfolio()),
            ["Format:", "Rules:", "Languages:"],
        ),
        (
            lambda: build_profile_prompt(_make_portfolio()),
            ["Rules:", "Project data:"],
        ),
    ])
    def test_required_markers_present(self, builder, required_markers) -> None:
        """Each prompt should contain its expected structural markers."""
        prompt = builder()
        for marker in required_markers:
            assert marker in prompt, f"Missing marker: {marker}"

"""Tests for the distillation stage (distill.py)."""

from __future__ import annotations

from artifactminer.resume.distill import (
    distill_project_context,
    distill_portfolio_context,
    _deduplicate_messages,
    _estimate_tokens,
    _truncate_to_tokens,
)
from artifactminer.resume.models import (
    CommitGroup,
    CodeConstructs,
    GitStats,
    TestRatio,
    CommitQuality,
    ModuleBreadth,
    ProjectDataBundle,
    PortfolioDataBundle,
)


# ── Helpers ──────────────────────────────────────────────────────────


def _make_bundle(**overrides) -> ProjectDataBundle:
    """Create a ProjectDataBundle with sensible defaults for testing."""
    defaults = dict(
        project_name="TestProject",
        project_path="/tmp/test-project",
        project_type="Web API",
        languages=["Python", "JavaScript"],
        language_percentages=[72.0, 28.0],
        primary_language="Python",
        frameworks=["FastAPI"],
        user_contribution_pct=85.0,
        user_total_commits=45,
        total_commits=53,
        first_commit="2025-01-01",
        last_commit="2025-06-15",
        readme_text="A REST API for managing tasks and users.",
        commit_groups=[
            CommitGroup(
                category="feature",
                messages=[
                    "feat: add user registration endpoint",
                    "feat: implement JWT authentication",
                    "feat: add task CRUD operations",
                ],
            ),
            CommitGroup(
                category="bugfix",
                messages=[
                    "fix: resolve null pointer in auth",
                    "fix: handle empty task list",
                ],
            ),
            CommitGroup(
                category="refactor",
                messages=["refactor: extract auth middleware"],
            ),
        ],
        directory_overview=["src", "tests", "docs"],
        module_groups={
            "src": ["src/api/routes.py", "src/models/user.py"],
            "tests": ["tests/test_routes.py"],
        },
        constructs=CodeConstructs(
            routes=["GET /api/users", "POST /api/users", "GET /api/tasks"],
            classes=["User", "TaskItem", "AuthMiddleware"],
            test_functions=["test_list_users", "test_create_user"],
            key_functions=["authenticate", "validate_token"],
        ),
        git_stats=GitStats(
            lines_added=2400,
            lines_deleted=350,
            net_lines=2050,
            files_touched=34,
            file_hotspots=[("src/api/routes.py", 12), ("src/models/user.py", 8)],
            active_days=45,
            active_span_days=165,
            avg_commit_size=55.0,
        ),
        test_ratio=TestRatio(
            test_files=3,
            source_files=8,
            test_ratio=0.38,
            has_ci=True,
        ),
        commit_quality=CommitQuality(
            conventional_pct=72.0,
            avg_message_length=38.0,
            type_diversity=3,
            longest_streak=5,
        ),
        module_breadth=ModuleBreadth(
            modules_touched=2,
            total_modules=3,
            breadth_pct=66.7,
            deepest_path="src/api/v2/routes.py",
        ),
    )
    defaults.update(overrides)
    return ProjectDataBundle(**defaults)


def _make_portfolio(bundles=None) -> PortfolioDataBundle:
    """Create a PortfolioDataBundle for testing."""
    if bundles is None:
        bundles = [_make_bundle()]
    return PortfolioDataBundle(
        user_email="dev@example.com",
        projects=bundles,
        total_projects=len(bundles),
        total_commits=sum(b.user_total_commits or 0 for b in bundles),
        languages_used=["Python", "JavaScript"],
        frameworks_used=["FastAPI"],
        earliest_commit="2025-01-01",
        latest_commit="2025-06-15",
        project_types={"Web API": len(bundles)},
        top_skills=["REST APIs", "Authentication", "Testing"],
    )


# ── Token utilities ──────────────────────────────────────────────────


class TestTokenUtilities:
    """Tests for token estimation and truncation helpers."""

    def test_estimate_tokens(self) -> None:
        """Should estimate ~1 token per 4 chars."""
        text = "Hello world, this is a test."
        tokens = _estimate_tokens(text)
        assert tokens == len(text) // 4

    def test_truncate_at_sentence_boundary(self) -> None:
        """Should truncate at a sentence boundary when possible."""
        text = "First sentence. Second sentence. Third sentence."
        result = _truncate_to_tokens(text, 5)  # ~20 chars
        assert result.endswith(".")
        assert len(result) < len(text)

    def test_truncate_preserves_short_text(self) -> None:
        """Should not truncate text shorter than the budget."""
        text = "Short text."
        result = _truncate_to_tokens(text, 1000)
        assert result == text


# ── Commit deduplication ─────────────────────────────────────────────


class TestCommitDeduplication:
    """Tests for the commit message deduplication logic."""

    def test_removes_near_duplicates(self) -> None:
        """Should cluster and keep the best representative."""
        messages = [
            "feat: add user login",
            "feat: add user login flow",
            "feat: implement authentication",
        ]
        result = _deduplicate_messages(messages)
        # "add user login" and "add user login flow" should cluster
        assert len(result) < len(messages)
        assert any("authentication" in m for m in result)

    def test_keeps_unique_messages(self) -> None:
        """Should keep messages that are sufficiently different."""
        messages = [
            "feat: add user registration",
            "fix: resolve database connection issue",
            "refactor: extract auth middleware",
        ]
        result = _deduplicate_messages(messages)
        assert len(result) == 3

    def test_empty_input(self) -> None:
        """Should handle empty input."""
        assert _deduplicate_messages([]) == []

    def test_single_message(self) -> None:
        """Should handle single message."""
        result = _deduplicate_messages(["feat: add login"])
        assert result == ["feat: add login"]

    def test_keeps_longest_representative(self) -> None:
        """Should keep the longest message as cluster representative."""
        messages = [
            "add user login page",
            "add user login page with validation",
        ]
        result = _deduplicate_messages(messages)
        assert len(result) == 1
        assert "validation" in result[0]


# ── Project distillation ─────────────────────────────────────────────


class TestDistillProjectContext:
    """Tests for project-level distillation."""

    def test_produces_nonempty_text(self) -> None:
        """Should produce a non-empty distilled context."""
        bundle = _make_bundle()
        ctx = distill_project_context(bundle)
        assert len(ctx.text) > 0
        assert ctx.token_estimate > 0

    def test_contains_project_name(self) -> None:
        """Should include the project name."""
        bundle = _make_bundle()
        ctx = distill_project_context(bundle)
        assert "TestProject" in ctx.text

    def test_contains_impact_section(self) -> None:
        """Should include quantitative impact signals."""
        bundle = _make_bundle()
        ctx = distill_project_context(bundle)
        assert "IMPACT:" in ctx.text
        assert "2,400" in ctx.text  # lines added

    def test_contains_commit_highlights(self) -> None:
        """Should include commit highlights."""
        bundle = _make_bundle()
        ctx = distill_project_context(bundle)
        assert "KEY WORK" in ctx.text

    def test_contains_code_constructs(self) -> None:
        """Should include code constructs."""
        bundle = _make_bundle()
        ctx = distill_project_context(bundle)
        assert "CODE CONSTRUCTS:" in ctx.text
        assert "/api/users" in ctx.text

    def test_contains_readme_summary(self) -> None:
        """Should include README excerpt."""
        bundle = _make_bundle()
        ctx = distill_project_context(bundle)
        assert "README SUMMARY:" in ctx.text

    def test_respects_token_budget(self) -> None:
        """Should stay within token budget."""
        bundle = _make_bundle()
        ctx = distill_project_context(bundle, token_budget=2500)
        assert ctx.token_estimate <= 2500

    def test_handles_empty_bundle(self) -> None:
        """Should handle a minimal bundle without crashing."""
        bundle = ProjectDataBundle(
            project_name="Empty",
            project_path="/tmp/empty",
        )
        ctx = distill_project_context(bundle)
        assert "Empty" in ctx.text

    def test_features_ranked_before_chores(self) -> None:
        """Should rank feature commits before chore commits."""
        bundle = _make_bundle()
        ctx = distill_project_context(bundle)
        feature_pos = ctx.text.find("[feature]")
        bugfix_pos = ctx.text.find("[bugfix]")
        # Features should appear before bugfixes
        if feature_pos >= 0 and bugfix_pos >= 0:
            assert feature_pos < bugfix_pos

    def test_tight_budget_still_produces_output(self) -> None:
        """Should produce output even with a very tight token budget."""
        bundle = _make_bundle()
        ctx = distill_project_context(bundle, token_budget=300)
        assert len(ctx.text) > 0
        assert "TestProject" in ctx.text


# ── Portfolio distillation ───────────────────────────────────────────


class TestDistillPortfolioContext:
    """Tests for portfolio-level distillation."""

    def test_produces_nonempty_text(self) -> None:
        """Should produce a non-empty distilled portfolio context."""
        portfolio = _make_portfolio()
        ctx = distill_portfolio_context(portfolio)
        assert len(ctx.text) > 0
        assert ctx.token_estimate > 0

    def test_contains_overview(self) -> None:
        """Should include portfolio overview."""
        portfolio = _make_portfolio()
        ctx = distill_portfolio_context(portfolio)
        assert "PORTFOLIO OVERVIEW" in ctx.text

    def test_contains_project_summaries(self) -> None:
        """Should include per-project summaries."""
        portfolio = _make_portfolio()
        ctx = distill_portfolio_context(portfolio)
        assert "TestProject" in ctx.text

    def test_respects_token_budget(self) -> None:
        """Should stay within token budget."""
        portfolio = _make_portfolio()
        ctx = distill_portfolio_context(portfolio, token_budget=2000)
        assert ctx.token_estimate <= 2000

    def test_multi_project_portfolio(self) -> None:
        """Should include summaries for multiple projects."""
        bundles = [
            _make_bundle(project_name="ProjectA"),
            _make_bundle(project_name="ProjectB"),
        ]
        portfolio = _make_portfolio(bundles)
        ctx = distill_portfolio_context(portfolio)
        assert "ProjectA" in ctx.text
        assert "ProjectB" in ctx.text

    def test_handles_empty_portfolio(self) -> None:
        """Should handle a portfolio with no projects."""
        portfolio = PortfolioDataBundle(
            user_email="dev@example.com",
            total_projects=0,
        )
        ctx = distill_portfolio_context(portfolio)
        assert "PORTFOLIO OVERVIEW" in ctx.text

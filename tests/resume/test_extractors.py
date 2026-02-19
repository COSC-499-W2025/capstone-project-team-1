"""Tests for the v3 resume pipeline extractors."""

from __future__ import annotations

from pathlib import Path

from artifactminer.resume.extractors.readme import extract_readme
from artifactminer.resume.extractors.commits import (
    extract_and_classify_commits,
    _classify_static,
)
from artifactminer.resume.extractors.structure import extract_structure
from artifactminer.resume.extractors.constructs import extract_constructs
from artifactminer.resume.extractors.project_type import infer_project_type
from artifactminer.resume.extractors.enriched_constructs import (
    extract_enriched_constructs,
)
from artifactminer.resume.extractors.imports import extract_import_graph
from artifactminer.resume.extractors.config_fingerprint import (
    extract_config_fingerprint,
)
from artifactminer.resume.extractors.llm_reasoning import (
    extract_llm_project_understanding,
)
from artifactminer.resume.models import CommitGroup


TEST_EMAIL = "dev@example.com"


# ── README extractor ──────────────────────────────────────────────────


class TestExtractReadme:
    """Tests for the README extractor."""

    def test_extracts_readme_content(self, sample_repo: Path) -> None:
        """Should return the README text."""
        text = extract_readme(str(sample_repo))
        assert "My Web API" in text
        assert "FastAPI" in text

    def test_respects_max_chars(self, sample_repo: Path) -> None:
        """Should truncate to max_chars."""
        text = extract_readme(str(sample_repo), max_chars=30)
        assert len(text) <= 30

    def test_returns_empty_for_missing_readme(self, tmp_path: Path) -> None:
        """Should return empty string when no README exists."""
        text = extract_readme(str(tmp_path))
        assert text == ""


# ── Commit classifier (static regex) ─────────────────────────────────


class TestClassifyStatic:
    """Tests for the regex-based commit classifier."""

    def test_conventional_feat(self) -> None:
        """Should classify 'feat: ...' as feature."""
        assert _classify_static("feat: add login page") == "feature"

    def test_conventional_fix(self) -> None:
        """Should classify 'fix: ...' as bugfix."""
        assert _classify_static("fix: resolve null pointer") == "bugfix"

    def test_conventional_with_scope(self) -> None:
        """Should handle scope in conventional commits."""
        assert _classify_static("feat(auth): add JWT support") == "feature"

    def test_conventional_test(self) -> None:
        """Should classify 'test: ...' as test."""
        assert _classify_static("test: add unit tests for auth") == "test"

    def test_conventional_docs(self) -> None:
        """Should classify 'docs: ...' as docs."""
        assert _classify_static("docs: update README") == "docs"

    def test_conventional_chore(self) -> None:
        """Should classify 'chore: ...' as chore."""
        assert _classify_static("chore: bump version") == "chore"

    def test_keyword_add(self) -> None:
        """Should classify 'Add ...' via keyword heuristic."""
        assert _classify_static("Add user registration flow") == "feature"

    def test_keyword_fix(self) -> None:
        """Should classify 'Fix ...' via keyword heuristic."""
        assert _classify_static("Fix crash on empty input") == "bugfix"

    def test_keyword_refactor(self) -> None:
        """Should classify refactoring commits."""
        assert _classify_static("Refactor database connection pool") == "refactor"

    def test_unclassifiable_returns_none(self) -> None:
        """Should return None for ambiguous messages."""
        assert _classify_static("Update thing") is None


# ── Commit extractor (full pipeline, no LLM) ─────────────────────────


class TestExtractAndClassifyCommits:
    """Tests for the full commit extraction pipeline."""

    def test_extracts_commits_from_repo(self, sample_repo: Path) -> None:
        """Should return CommitGroup objects with messages."""
        groups = extract_and_classify_commits(str(sample_repo), TEST_EMAIL)
        assert len(groups) > 0
        assert all(isinstance(g, CommitGroup) for g in groups)

    def test_groups_have_correct_categories(self, sample_repo: Path) -> None:
        """Should classify commits into known categories."""
        groups = extract_and_classify_commits(str(sample_repo), TEST_EMAIL)
        categories = {g.category for g in groups}
        # Our sample repo has feat, fix, refactor, test, docs, chore commits
        assert "feature" in categories
        assert "bugfix" in categories

    def test_commit_messages_are_populated(self, sample_repo: Path) -> None:
        """Each group should contain actual commit messages."""
        groups = extract_and_classify_commits(str(sample_repo), TEST_EMAIL)
        total_msgs = sum(g.count for g in groups)
        assert total_msgs >= 5  # we made 7 commits in the fixture

    def test_filters_by_user_email(self, sample_repo: Path) -> None:
        """Should return empty for an email with no commits."""
        groups = extract_and_classify_commits(str(sample_repo), "nobody@example.com")
        total = sum(g.count for g in groups)
        assert total == 0


# ── Structure extractor ───────────────────────────────────────────────


class TestExtractStructure:
    """Tests for the directory structure extractor."""

    def test_returns_top_level_dirs(self, sample_repo: Path) -> None:
        """Should list top-level directories."""
        dirs, _ = extract_structure(str(sample_repo), TEST_EMAIL)
        assert "src" in dirs
        assert "tests" in dirs

    def test_excludes_hidden_dirs(self, sample_repo: Path) -> None:
        """Should not include .git or other hidden directories."""
        dirs, _ = extract_structure(str(sample_repo), TEST_EMAIL)
        assert ".git" not in dirs

    def test_module_groups_populated(self, sample_repo: Path) -> None:
        """Should group user-touched files by module."""
        _, modules = extract_structure(str(sample_repo), TEST_EMAIL)
        assert len(modules) > 0
        # src/ should have files
        assert "src" in modules
        assert len(modules["src"]) > 0


# ── Constructs extractor ──────────────────────────────────────────────


class TestExtractConstructs:
    """Tests for the code construct extractor."""

    def test_finds_routes(self, sample_repo: Path) -> None:
        """Should detect FastAPI route definitions."""
        constructs = extract_constructs(str(sample_repo))
        assert len(constructs.routes) > 0
        route_strs = " ".join(constructs.routes)
        assert "/api/users" in route_strs

    def test_finds_classes(self, sample_repo: Path) -> None:
        """Should detect class definitions."""
        constructs = extract_constructs(str(sample_repo))
        class_names = constructs.classes
        assert "User" in class_names

    def test_finds_test_functions(self, sample_repo: Path) -> None:
        """Should detect test function names."""
        constructs = extract_constructs(str(sample_repo))
        assert len(constructs.test_functions) > 0
        assert "test_list_users" in constructs.test_functions

    def test_finds_key_functions(self, sample_repo: Path) -> None:
        """Should detect non-test, non-dunder functions."""
        constructs = extract_constructs(str(sample_repo))
        func_names = constructs.key_functions
        assert "authenticate" in func_names

    def test_scoped_to_touched_files(self, sample_repo: Path) -> None:
        """Should only scan provided files when touched_files is set."""
        constructs = extract_constructs(
            str(sample_repo),
            touched_files={"src/api/auth.py"},
        )
        # Should find auth functions but not route decorators
        assert "authenticate" in constructs.key_functions
        assert len(constructs.routes) == 0


# ── Project type inference ────────────────────────────────────────────


class TestInferProjectType:
    """Tests for project type inference."""

    def test_detects_web_api_from_frameworks(self, sample_repo: Path) -> None:
        """Should identify a FastAPI project as Web API."""
        ptype = infer_project_type(
            str(sample_repo),
            frameworks=["FastAPI"],
            readme_text="A REST API built with FastAPI",
        )
        assert ptype == "Web API"

    def test_detects_cli_tool(self, tmp_path: Path) -> None:
        """Should identify CLI tool from frameworks."""
        ptype = infer_project_type(
            str(tmp_path),
            frameworks=["Typer", "Click"],
        )
        assert ptype == "CLI Tool"

    def test_fallback_to_software_project(self, tmp_path: Path) -> None:
        """Should return generic type when no signals match."""
        ptype = infer_project_type(str(tmp_path))
        assert ptype == "Software Project"

    def test_readme_keywords_boost_scores(self, tmp_path: Path) -> None:
        """README keywords should contribute to type scoring."""
        ptype = infer_project_type(
            str(tmp_path),
            readme_text="This is a command-line CLI tool for data processing",
        )
        assert ptype == "CLI Tool"


# ── Analysis module wiring (Phase 1) ─────────────────────────────────


class TestAnalysisModuleWiring:
    """Tests that analysis modules produce data from the sample_repo fixture."""

    def test_style_metrics_returns_data(self, sample_repo: Path) -> None:
        """compute_style_metrics should return StyleMetrics for the sample repo."""
        from artifactminer.resume.analysis.developer_style import (
            compute_style_metrics,
        )

        metrics = compute_style_metrics(str(sample_repo), TEST_EMAIL, "Python")
        assert metrics is not None
        assert metrics.total_functions > 0
        assert metrics.files_analyzed > 0

    def test_complexity_metrics_returns_data(self, sample_repo: Path) -> None:
        """compute_complexity_metrics should return FileComplexity list."""
        from artifactminer.resume.analysis.complexity_narrative import (
            compute_complexity_metrics,
        )

        results = compute_complexity_metrics(str(sample_repo), TEST_EMAIL)
        assert isinstance(results, list)
        assert len(results) > 0
        assert results[0].filepath

    def test_skill_appearances_returns_data(self, sample_repo: Path) -> None:
        """compute_skill_first_appearances should find skills from the fixture."""
        from artifactminer.resume.analysis.skill_timeline import (
            compute_skill_first_appearances,
        )

        appearances = compute_skill_first_appearances(
            str(sample_repo), TEST_EMAIL, ["Python", "Testing", "REST API Design"]
        )
        assert isinstance(appearances, list)
        assert len(appearances) > 0
        skill_names = {a.skill_name for a in appearances}
        assert "Python" in skill_names


# ── Enriched constructs extractor (Phase 2) ──────────────────────────


class TestEnrichedConstructs:
    """Tests for the enriched code construct extractor."""

    def test_finds_classes_with_metadata(self, sample_repo: Path) -> None:
        """Should detect classes with method count and LOC."""
        ec = extract_enriched_constructs(str(sample_repo))
        assert len(ec.classes) > 0
        user_cls = next((c for c in ec.classes if c.name == "User"), None)
        assert user_cls is not None
        assert user_cls.total_loc > 0

    def test_finds_functions_with_metadata(self, sample_repo: Path) -> None:
        """Should detect functions with param count and return type info."""
        ec = extract_enriched_constructs(str(sample_repo))
        assert len(ec.functions) > 0
        auth_fn = next((f for f in ec.functions if f.name == "authenticate"), None)
        assert auth_fn is not None
        assert auth_fn.param_count >= 1
        assert auth_fn.has_return_type is True

    def test_finds_routes(self, sample_repo: Path) -> None:
        """Should detect FastAPI routes."""
        ec = extract_enriched_constructs(str(sample_repo))
        assert len(ec.routes) > 0
        route_strs = " ".join(ec.routes)
        assert "/api/users" in route_strs

    def test_finds_test_functions(self, sample_repo: Path) -> None:
        """Should detect test function names."""
        ec = extract_enriched_constructs(str(sample_repo))
        assert len(ec.test_functions) > 0
        assert "test_list_users" in ec.test_functions

    def test_scoped_to_touched_files(self, sample_repo: Path) -> None:
        """Should only scan provided files when touched_files is set."""
        ec = extract_enriched_constructs(
            str(sample_repo),
            touched_files={"src/api/auth.py"},
        )
        assert any(f.name == "authenticate" for f in ec.functions)
        assert len(ec.routes) == 0


# ── Import graph extractor (Phase 3) ─────────────────────────────────


class TestImportGraph:
    """Tests for the import graph analyzer."""

    def test_detects_imports(self, sample_repo: Path) -> None:
        """Should detect import statements in Python files."""
        ig = extract_import_graph(str(sample_repo))
        assert isinstance(ig.imports_map, dict)
        # auth.py imports from src.models.user
        has_import = any(
            any("models" in dep or "user" in dep for dep in deps)
            for deps in ig.imports_map.values()
        )
        assert has_import

    def test_detects_external_deps(self, sample_repo: Path) -> None:
        """Should identify external dependencies."""
        ig = extract_import_graph(str(sample_repo))
        assert isinstance(ig.external_deps, list)
        # fastapi is imported in routes.py
        assert "fastapi" in ig.external_deps

    def test_detects_layers(self, sample_repo: Path) -> None:
        """Should detect architectural layers from directory structure."""
        ig = extract_import_graph(str(sample_repo))
        assert isinstance(ig.layer_detection, list)
        # src/api → presentation, src/models → data
        assert "presentation" in ig.layer_detection or "data" in ig.layer_detection

    def test_scoped_to_touched_files(self, sample_repo: Path) -> None:
        """Should only scan provided files when touched_files is set."""
        ig = extract_import_graph(
            str(sample_repo),
            touched_files={"src/api/auth.py"},
        )
        assert len(ig.imports_map) <= 1


# ── LLM semantic extractor (Phase 4) ─────────────────────────────────


class TestLLMProjectUnderstanding:
    """Tests for optional LLM semantic project understanding."""

    def test_extracts_semantic_understanding(
        self,
        sample_repo: Path,
        monkeypatch,
    ) -> None:
        """Should map LLM JSON output into bundle-friendly understanding fields."""

        class _FakePayload:
            project_purpose = "A REST API for managing tasks and users."
            user_value = "Lets teams track work and automate task workflows."
            architecture_summary = (
                "FastAPI endpoints with auth helpers and model modules."
            )
            key_capabilities = [
                "Implements user and task CRUD endpoints",
                "Supports token-based authentication flows",
            ]
            implementation_highlights = [
                "Organizes API handlers in src/api modules",
            ]

        monkeypatch.setattr(
            "artifactminer.resume.extractors.llm_reasoning.query_llm",
            lambda *args, **kwargs: _FakePayload(),
        )

        understanding = extract_llm_project_understanding(
            str(sample_repo),
            model="qwen3-1.7b-q8",
            project_name="my-web-api",
            project_type="Web API",
            primary_language="Python",
            frameworks=["FastAPI"],
            readme_text="A REST API for managing tasks and users built with FastAPI.",
            commit_groups=[
                CommitGroup(category="feature", messages=["feat: add task CRUD"]),
            ],
            module_groups={"src": ["src/api/routes.py", "src/api/auth.py"]},
            routes=["GET /api/users", "POST /api/users"],
        )

        assert understanding is not None
        assert "REST API" in understanding.project_purpose
        assert len(understanding.key_capabilities) >= 1

    def test_returns_none_on_llm_failure(self, sample_repo: Path, monkeypatch) -> None:
        """Should degrade gracefully when LLM inference fails."""

        def _raise(*_args, **_kwargs):
            raise RuntimeError("llm unavailable")

        monkeypatch.setattr(
            "artifactminer.resume.extractors.llm_reasoning.query_llm",
            _raise,
        )

        understanding = extract_llm_project_understanding(
            str(sample_repo),
            model="qwen3-1.7b-q8",
            project_name="my-web-api",
            project_type="Web API",
            readme_text="A REST API for managing tasks and users built with FastAPI.",
        )

        assert understanding is None


# ── Config fingerprint extractor (Phase 3) ───────────────────────────


class TestConfigFingerprint:
    """Tests for the config/infra fingerprint extractor."""

    def test_detects_pyproject_tools(self, sample_repo: Path) -> None:
        """Should detect tools from pyproject.toml [tool.X] sections."""
        fp = extract_config_fingerprint(str(sample_repo))
        assert "ruff" in fp.linters
        assert "pytest" in fp.test_frameworks
        assert "mypy" in fp.linters

    def test_detects_pre_commit_hooks(self, sample_repo: Path) -> None:
        """Should extract hook IDs from .pre-commit-config.yaml."""
        fp = extract_config_fingerprint(str(sample_repo))
        assert len(fp.pre_commit_hooks) > 0
        assert "ruff" in fp.pre_commit_hooks

    def test_empty_repo_returns_empty_fingerprint(self, tmp_path: Path) -> None:
        """Should return an empty fingerprint for a repo with no config."""
        fp = extract_config_fingerprint(str(tmp_path))
        assert fp.linters == []
        assert fp.formatters == []
        assert fp.test_frameworks == []


# ── Churn-complexity cross-reference (Phase 3) ───────────────────────


class TestChurnComplexity:
    """Tests for the churn-complexity hotspot cross-reference."""

    def test_computes_hotspots(self) -> None:
        """Should intersect file hotspots with complexity metrics."""
        from artifactminer.resume.pipeline import _compute_churn_complexity
        from artifactminer.resume.models import GitStats
        from artifactminer.resume.analysis.complexity_narrative import FileComplexity

        git_stats = GitStats(
            file_hotspots=[
                ("src/api/routes.py", 12),
                ("src/models/user.py", 8),
                ("src/api/auth.py", 5),
            ],
        )
        file_complexity = [
            FileComplexity(
                filepath="src/api/routes.py",
                cyclomatic_complexity=15,
                max_nesting_depth=3,
                loc=100,
                function_count=5,
            ),
            FileComplexity(
                filepath="src/models/user.py",
                cyclomatic_complexity=3,
                max_nesting_depth=1,
                loc=30,
                function_count=2,
            ),
        ]

        hotspots = _compute_churn_complexity(git_stats, file_complexity)
        assert len(hotspots) == 2
        # routes.py should be ranked first (12*15 > 8*3)
        assert hotspots[0].filepath == "src/api/routes.py"
        assert hotspots[0].risk_score == 1.0
        assert 0 < hotspots[1].risk_score < 1.0

    def test_empty_inputs(self) -> None:
        """Should return empty list when no overlap exists."""
        from artifactminer.resume.pipeline import _compute_churn_complexity
        from artifactminer.resume.models import GitStats

        git_stats = GitStats(file_hotspots=[])
        result = _compute_churn_complexity(git_stats, [])
        assert result == []

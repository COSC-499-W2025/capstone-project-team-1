"""Tests for repo_quality_bridge extractor."""

from datetime import date

from artifactminer.evidence.extractors.repo_quality_bridge import (
    repo_quality_to_evidence,
)
from artifactminer.skills.deep_analysis import RepoQualityResult


def test_repo_quality_to_evidence_returns_empty_for_no_signals():
    quality = RepoQualityResult()
    result = repo_quality_to_evidence(quality)
    assert result == []


def test_repo_quality_to_evidence_converts_testing_signals():
    quality = RepoQualityResult(
        test_file_count=5,
        has_tests=True,
        test_frameworks=["pytest"],
    )
    result = repo_quality_to_evidence(quality)

    test_item = next((i for i in result if i.type == "testing"), None)
    assert test_item is not None
    assert "5 test files" in test_item.content
    assert test_item.source == "repo_quality_signals"


def test_repo_quality_to_evidence_converts_docs_signals():
    quality = RepoQualityResult(
        has_readme=True,
        has_changelog=True,
        has_docs_dir=True,
    )
    result = repo_quality_to_evidence(quality)

    docs_item = next((i for i in result if i.type == "documentation"), None)
    assert docs_item is not None
    assert "README" in docs_item.content


def test_repo_quality_to_evidence_converts_quality_signals():
    quality = RepoQualityResult(
        has_lint_config=True,
        has_precommit=True,
        has_type_check=True,
        quality_tools=["ruff", "mypy", "pre-commit"],
    )
    result = repo_quality_to_evidence(quality)

    quality_item = next((i for i in result if i.type == "code_quality"), None)
    assert quality_item is not None
    assert "ruff" in quality_item.content or "mypy" in quality_item.content


def test_repo_quality_to_evidence_uses_evidence_date():
    quality = RepoQualityResult(has_readme=True)
    evidence_date = date(2024, 6, 1)
    result = repo_quality_to_evidence(quality, evidence_date=evidence_date)

    assert all(item.date == evidence_date for item in result)


def test_repo_quality_to_evidence_combines_all_signals():
    quality = RepoQualityResult(
        test_file_count=3,
        has_tests=True,
        has_readme=True,
        has_changelog=True,
        has_lint_config=True,
        has_precommit=True,
    )
    result = repo_quality_to_evidence(quality)

    types = {item.type for item in result}
    assert "testing" in types
    assert "documentation" in types
    assert "code_quality" in types

"""Tests for repo_quality_bridge extractor."""

from datetime import date

from artifactminer.evidence.extractors.repo_quality_bridge import (
    repo_quality_to_evidence,
)
from artifactminer.skills.deep_analysis import RepoQualityResult


def test_repo_quality_to_evidence_returns_negative_for_bare_defaults():
    quality = RepoQualityResult()
    result = repo_quality_to_evidence(quality)
    types = {item.type for item in result}
    # No tests and no docs → negative signals
    assert "test_coverage" in types
    assert "documentation" in types


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
        has_contributing=True,
        has_docs_dir=True,
    )
    result = repo_quality_to_evidence(quality)

    docs_item = next((i for i in result if i.type == "documentation"), None)
    assert docs_item is not None
    assert "README" in docs_item.content
    assert "CONTRIBUTING" in docs_item.content


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


def test_repo_quality_to_evidence_negative_coverage():
    """No tests → negative test_coverage evidence."""
    quality = RepoQualityResult(has_tests=False, has_readme=True)
    result = repo_quality_to_evidence(quality)

    cov_item = next((i for i in result if i.type == "test_coverage"), None)
    assert cov_item is not None
    assert cov_item.content == "No test files detected in repository"
    assert cov_item.source == "repo_quality_signals"


def test_repo_quality_to_evidence_negative_docs():
    """No docs → negative documentation evidence."""
    quality = RepoQualityResult(has_tests=True, test_file_count=1, has_readme=False, has_docs_dir=False)
    result = repo_quality_to_evidence(quality)

    docs_item = next((i for i in result if i.type == "documentation"), None)
    assert docs_item is not None
    assert "missing" in docs_item.content.lower()
    assert docs_item.source == "docs_signals"


def test_repo_quality_to_evidence_changelog_counts_as_docs():
    quality = RepoQualityResult(has_tests=True, test_file_count=1, has_changelog=True)
    result = repo_quality_to_evidence(quality)

    docs_items = [i for i in result if i.type == "documentation"]
    assert docs_items
    assert any("CHANGELOG" in i.content for i in docs_items)
    assert all("missing" not in i.content.lower() for i in docs_items)


def test_repo_quality_to_evidence_contributing_counts_as_docs():
    quality = RepoQualityResult(has_tests=True, test_file_count=1, has_contributing=True)
    result = repo_quality_to_evidence(quality)

    docs_items = [i for i in result if i.type == "documentation"]
    assert docs_items
    assert any("CONTRIBUTING" in i.content for i in docs_items)
    assert all("missing" not in i.content.lower() for i in docs_items)


def test_repo_quality_to_evidence_no_negative_when_present():
    """Has tests and docs → no negative signals."""
    quality = RepoQualityResult(
        test_file_count=3,
        has_tests=True,
        has_readme=True,
    )
    result = repo_quality_to_evidence(quality)

    assert not any(i.type == "test_coverage" for i in result)
    # Should have positive documentation, not negative
    doc_items = [i for i in result if i.type == "documentation"]
    assert all("missing" not in i.content.lower() for i in doc_items)

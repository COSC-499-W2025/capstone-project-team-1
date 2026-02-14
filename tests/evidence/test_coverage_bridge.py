"""Tests for coverage_bridge extractor."""

from artifactminer.evidence.extractors.coverage_bridge import coverage_to_evidence


def test_coverage_to_evidence_below_threshold():
    result = coverage_to_evidence({"percent": 50.0})
    assert len(result) == 1
    assert result[0].type == "test_coverage"
    assert result[0].source == "test_coverage_signals"
    assert "50.0%" in result[0].content


def test_coverage_to_evidence_above_threshold():
    result = coverage_to_evidence({"percent": 85.0})
    assert result == []


def test_coverage_to_evidence_exactly_80():
    result = coverage_to_evidence({"percent": 80.0})
    assert result == []


def test_coverage_to_evidence_missing_key():
    # defaults to 100.0, so no evidence
    result = coverage_to_evidence({})
    assert result == []


def test_coverage_to_evidence_zero_percent():
    result = coverage_to_evidence({"percent": 0.0})
    assert len(result) == 1
    assert "0.0%" in result[0].content

"""Tests for coverage_bridge extractor."""

from artifactminer.evidence.extractors.coverage_bridge import coverage_to_evidence


def test_coverage_to_evidence_below_threshold():
    coverage_data = {"percent": 50.0, "test_count": 10}
    result = coverage_to_evidence(coverage_data)
    assert len(result) >= 1
    assert result[0].type == "test_coverage"
    assert result[0].source == "test_coverage_signals"


def test_coverage_to_evidence_above_threshold():
    coverage_data = {"percent": 85.0, "test_count": 20}
    result = coverage_to_evidence(coverage_data)
    # Above 80% threshold, no evidence items
    assert result == []

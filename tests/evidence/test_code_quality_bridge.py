"""Tests for code_quality_bridge extractor."""

from artifactminer.evidence.extractors.code_quality_bridge import quality_to_evidence


def test_quality_to_evidence_with_issues():
    quality_data = {"issues": 5, "has_type_hints": True}
    result = quality_to_evidence(quality_data)
    assert len(result) >= 1
    assert result[0].type == "code_quality"
    assert result[0].source == "code_quality_signals"


def test_quality_to_evidence_no_issues():
    quality_data = {"issues": 0, "has_type_hints": True}
    result = quality_to_evidence(quality_data)
    # No issues, no evidence items
    assert result == []

"""Tests for code_quality_bridge extractor."""

from artifactminer.evidence.extractors.code_quality_bridge import quality_to_evidence


def test_quality_to_evidence_with_issues():
    result = quality_to_evidence({"issues": 5})
    assert len(result) == 1
    assert result[0].type == "code_quality"
    assert result[0].source == "code_quality_signals"
    assert "5 issues" in result[0].content


def test_quality_to_evidence_no_issues():
    result = quality_to_evidence({"issues": 0})
    assert result == []


def test_quality_to_evidence_missing_key():
    result = quality_to_evidence({})
    assert result == []


def test_quality_to_evidence_empty_dict():
    result = quality_to_evidence({})
    assert result == []


def test_quality_to_evidence_none_value():
    # .get() returns 0 default, but if someone passes None explicitly
    result = quality_to_evidence({"issues": None})
    # None > 0 is False in Python, so no evidence
    assert result == []

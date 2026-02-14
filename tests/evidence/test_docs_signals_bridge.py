"""Tests for docs_signals_bridge extractor."""

from artifactminer.evidence.extractors.docs_signals_bridge import docs_to_evidence


def test_docs_to_evidence_missing_docs():
    result = docs_to_evidence({"has_docs": False})
    assert len(result) == 1
    assert result[0].type == "documentation"
    assert result[0].source == "docs_signals"


def test_docs_to_evidence_has_docs():
    result = docs_to_evidence({"has_docs": True})
    assert result == []


def test_docs_to_evidence_missing_key():
    # defaults to True (assume docs present), so no evidence
    result = docs_to_evidence({})
    assert result == []


def test_docs_to_evidence_empty_dict():
    result = docs_to_evidence({})
    assert result == []

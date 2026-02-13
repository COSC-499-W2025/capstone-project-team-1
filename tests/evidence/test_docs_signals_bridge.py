"""Tests for docs_signals_bridge extractor."""

from artifactminer.evidence.extractors.docs_signals_bridge import docs_to_evidence


def test_docs_to_evidence_missing_docs():
    doc_data = {"has_docs": False, "readme_exists": False}
    result = docs_to_evidence(doc_data)
    assert len(result) >= 1
    assert result[0].type == "documentation"
    assert result[0].source == "docs_signals"


def test_docs_to_evidence_has_docs():
    doc_data = {"has_docs": True, "readme_exists": True}
    result = docs_to_evidence(doc_data)
    # Has docs, no evidence items
    assert result == []

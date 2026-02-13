"""Bridge for documentation signals into evidence items."""

from __future__ import annotations
from typing import List
from artifactminer.evidence.models import EvidenceItem
from artifactminer.skills.signals.docs_signals import DocsSignals


def docs_to_evidence(doc_data: dict) -> List[EvidenceItem]:
    signals = DocsSignals(doc_data)
    return signals.to_evidence()

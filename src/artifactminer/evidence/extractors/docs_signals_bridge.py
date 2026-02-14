"""Bridge for documentation signals into evidence items."""

from __future__ import annotations

from typing import List

from artifactminer.evidence.models import EvidenceItem
from artifactminer.skills.signals.docs_signals import docs_dict_to_evidence


def docs_to_evidence(doc_data: dict) -> List[EvidenceItem]:
    return docs_dict_to_evidence(doc_data)

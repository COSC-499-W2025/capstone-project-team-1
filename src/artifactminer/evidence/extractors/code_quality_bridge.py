"""Bridge for code quality signals into evidence items."""

from __future__ import annotations

from typing import List

from artifactminer.evidence.models import EvidenceItem
from artifactminer.skills.signals.code_quality_signals import quality_dict_to_evidence


def quality_to_evidence(quality_data: dict) -> List[EvidenceItem]:
    return quality_dict_to_evidence(quality_data)

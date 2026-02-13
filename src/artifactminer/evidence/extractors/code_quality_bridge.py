"""Bridge for code quality signals into evidence items."""

from __future__ import annotations
from typing import List
from artifactminer.evidence.models import EvidenceItem
from artifactminer.skills.signals.code_quality_signals import CodeQualitySignals


def quality_to_evidence(quality_data: dict) -> List[EvidenceItem]:
    signals = CodeQualitySignals(quality_data)
    return signals.to_evidence()

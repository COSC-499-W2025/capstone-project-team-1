"""Bridge for test coverage data into evidence items."""

from __future__ import annotations

from typing import List

from artifactminer.evidence.models import EvidenceItem
from artifactminer.skills.signals.test_coverage_signals import coverage_dict_to_evidence


def coverage_to_evidence(coverage_data: dict) -> List[EvidenceItem]:
    return coverage_dict_to_evidence(coverage_data)

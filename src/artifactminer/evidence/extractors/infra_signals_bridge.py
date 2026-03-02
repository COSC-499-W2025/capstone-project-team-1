"""Bridge infra signals into evidence items."""

from __future__ import annotations

from datetime import date
from typing import List

from artifactminer.evidence.models import EvidenceItem
from artifactminer.skills.models import InfraSignalsResult


def infra_signals_to_evidence(
    infra_signals: InfraSignalsResult,
    *,
    evidence_date: date | None = None,
) -> List[EvidenceItem]:
    """Convert infrastructure signals to evidence items."""
    if not infra_signals or not infra_signals.all_tools:
        return []

    items: List[EvidenceItem] = []
    _CATEGORIES = [
        (infra_signals.ci_cd_tools, "CI/CD"),
        (infra_signals.docker_tools, "Containerization"),
        (infra_signals.env_build_tools, "Build/Deploy tools"),
    ]

    for tools, label in _CATEGORIES:
        if tools:
            items.append(EvidenceItem(
                type="metric",
                content=f"{label}: {', '.join(sorted(set(tools)))}",
                source="infra_signals",
                date=evidence_date,
            ))

    return items

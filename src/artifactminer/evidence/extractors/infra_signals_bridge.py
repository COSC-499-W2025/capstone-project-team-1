"""Bridge infra signals into evidence items."""

from __future__ import annotations

from datetime import date
from typing import List

from artifactminer.evidence.models import EvidenceItem
from artifactminer.skills.deep_analysis import InfraSignalsResult


def infra_signals_to_evidence(
    infra_signals: InfraSignalsResult,
    *,
    evidence_date: date | None = None,
) -> List[EvidenceItem]:
    """Convert infrastructure signals to evidence items."""
    items: List[EvidenceItem] = []

    if not infra_signals or not infra_signals.all_tools:
        return items

    if infra_signals.ci_cd_tools:
        tools_str = ", ".join(sorted(set(infra_signals.ci_cd_tools)))
        items.append(
            EvidenceItem(
                type="metric",
                content=f"CI/CD: {tools_str}",
                source="infra_signals",
                date=evidence_date,
            )
        )

    if infra_signals.docker_tools:
        tools_str = ", ".join(sorted(set(infra_signals.docker_tools)))
        items.append(
            EvidenceItem(
                type="metric",
                content=f"Containerization: {tools_str}",
                source="infra_signals",
                date=evidence_date,
            )
        )

    env_build = infra_signals.env_build_tools
    if env_build:
        tools_str = ", ".join(sorted(set(env_build)))
        items.append(
            EvidenceItem(
                type="metric",
                content=f"Build/Deploy tools: {tools_str}",
                source="infra_signals",
                date=evidence_date,
            )
        )

    return items

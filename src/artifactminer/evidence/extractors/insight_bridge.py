"""Bridge DeepRepoAnalyzer insights into evidence items."""

from __future__ import annotations

from datetime import date, datetime
from typing import Iterable

from artifactminer.evidence.models import EvidenceItem
from artifactminer.evidence.utils import coerce_date
from artifactminer.skills.models import Insight


def insights_to_evidence(
    insights: Iterable[Insight],
    *,
    repo_last_commit: date | datetime | None = None,
) -> list[EvidenceItem]:
    """Map insights to evidence rows used by the ProjectEvidence table."""
    converted: list[EvidenceItem] = []
    evidence_date = coerce_date(repo_last_commit)

    for insight in insights:
        title = (insight.title or "").strip()
        why = (insight.why_it_matters or "").strip()
        if not title and not why:
            continue

        if title and why:
            content = f"{title}: {why}"
        else:
            content = title or why

        source_chunks = [item.strip() for item in (insight.evidence or []) if item and item.strip()]
        source = "; ".join(source_chunks[:5]) if source_chunks else None

        converted.append(
            EvidenceItem(
                type="evaluation",
                content=content,
                source=source,
                date=evidence_date,
            )
        )

    return converted

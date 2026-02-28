"""Evidence extractors."""

from artifactminer.evidence.extractors.git_stats_bridge import git_stats_to_evidence
from artifactminer.evidence.extractors.infra_signals_bridge import (
    infra_signals_to_evidence,
)
from artifactminer.evidence.extractors.insight_bridge import insights_to_evidence

__all__ = [
    "git_stats_to_evidence",
    "infra_signals_to_evidence",
    "insights_to_evidence",
]

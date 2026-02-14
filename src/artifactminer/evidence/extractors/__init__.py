"""Evidence extractors."""

from artifactminer.evidence.extractors.git_stats_bridge import git_stats_to_evidence
from artifactminer.evidence.extractors.infra_signals_bridge import (
    infra_signals_to_evidence,
)
from artifactminer.evidence.extractors.insight_bridge import insights_to_evidence
from artifactminer.evidence.extractors.repo_quality_bridge import (
    repo_quality_to_evidence,
)

from artifactminer.evidence.extractors.coverage_bridge import coverage_to_evidence
from artifactminer.evidence.extractors.docs_signals_bridge import docs_to_evidence
from artifactminer.evidence.extractors.code_quality_bridge import quality_to_evidence

__all__ = [
    "git_stats_to_evidence",
    "infra_signals_to_evidence",
    "insights_to_evidence",
    "repo_quality_to_evidence",
    "coverage_to_evidence",
    "docs_to_evidence",
    "quality_to_evidence",
]

"""
Data models for the v3 resume pipeline.

Three bundles flow through the pipeline:
  1. ProjectDataBundle — per-repo extraction output (EXTRACT phase)
  2. PortfolioDataBundle — aggregated across repos (EXTRACT phase)
  3. ResumeOutput — final sections after LLM + assembly (QUERY/ASSEMBLE phase)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Supporting types
# ---------------------------------------------------------------------------


@dataclass
class CommitGroup:
    """Commits grouped by semantic type (feature, bugfix, etc.)."""

    category: str  # feature | bugfix | refactor | test | docs | chore
    messages: List[str] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.messages)


@dataclass
class CodeConstructs:
    """Concrete code constructs found via regex scanning."""

    routes: List[str] = field(default_factory=list)       # e.g. "GET /api/users"
    classes: List[str] = field(default_factory=list)       # e.g. "UserService"
    test_functions: List[str] = field(default_factory=list)  # e.g. "test_login"
    key_functions: List[str] = field(default_factory=list)  # e.g. "authenticate"


@dataclass
class ProjectSection:
    """LLM-generated content for one project."""

    description: str = ""
    bullets: List[str] = field(default_factory=list)
    narrative: str = ""


# ---------------------------------------------------------------------------
# EXTRACT phase outputs
# ---------------------------------------------------------------------------


@dataclass
class ProjectDataBundle:
    """
    Rich data bundle for a single project — replaces ProjectFacts.

    Produced entirely by static extractors (no LLM).
    """

    # Identity
    project_name: str
    project_path: str
    project_type: str = "Software Project"  # e.g. "Web API", "CLI Tool", "Library"

    # Languages & frameworks
    languages: List[str] = field(default_factory=list)
    language_percentages: List[float] = field(default_factory=list)
    primary_language: Optional[str] = None
    frameworks: List[str] = field(default_factory=list)

    # User contribution metrics
    user_contribution_pct: Optional[float] = None
    user_total_commits: Optional[int] = None
    total_commits: Optional[int] = None
    first_commit: Optional[str] = None
    last_commit: Optional[str] = None

    # README (best source for "what is this project?")
    readme_text: str = ""

    # Commits grouped by type with actual message text
    commit_groups: List[CommitGroup] = field(default_factory=list)

    # Directory overview
    directory_overview: List[str] = field(default_factory=list)

    # User-touched files grouped by module (dir → files)
    module_groups: Dict[str, List[str]] = field(default_factory=dict)

    # Code constructs
    constructs: CodeConstructs = field(default_factory=CodeConstructs)

    # Skills (from existing DeepRepoAnalyzer)
    detected_skills: List[str] = field(default_factory=list)
    skill_evidence: Dict[str, List[str]] = field(default_factory=dict)

    # Insights (from existing DeepRepoAnalyzer)
    insights: List[Dict[str, Any]] = field(default_factory=list)

    def all_commit_messages(self) -> List[str]:
        """Flat list of all commit messages across groups."""
        msgs: List[str] = []
        for g in self.commit_groups:
            msgs.extend(g.messages)
        return msgs

    def commit_count_by_type(self) -> Dict[str, int]:
        """Breakdown dict: {"feature": 15, "bugfix": 8, ...}."""
        return {g.category: g.count for g in self.commit_groups if g.count > 0}

    def to_prompt_context(self) -> str:
        """Compact text for LLM prompt inclusion."""
        lines: List[str] = []

        lines.append(f"PROJECT: {self.project_name}")
        lines.append(f"Type: {self.project_type}")

        # Stack
        if self.languages:
            lang_str = ", ".join(
                f"{lang} ({pct:.0f}%)"
                for lang, pct in zip(self.languages[:4], self.language_percentages[:4])
            )
            lines.append(f"Stack: {lang_str}")
        if self.frameworks:
            lines.append(f"Frameworks: {', '.join(self.frameworks)}")

        # Contribution
        if self.user_contribution_pct is not None:
            contrib = f"{self.user_contribution_pct:.0f}%"
            if self.user_total_commits and self.total_commits:
                contrib += f" ({self.user_total_commits}/{self.total_commits} commits)"
            lines.append(f"Contribution: {contrib}")

        # Period
        if self.first_commit and self.last_commit:
            lines.append(f"Period: {self.first_commit[:10]} to {self.last_commit[:10]}")

        # README excerpt
        if self.readme_text:
            excerpt = self.readme_text[:600].strip()
            lines.append(f"\nREADME excerpt:\n{excerpt}")

        # Commit messages by type
        for group in self.commit_groups:
            if group.messages:
                lines.append(f"\n{group.category.upper()} commits ({group.count}):")
                for msg in group.messages[:10]:
                    lines.append(f"  - {msg}")

        # Code constructs
        c = self.constructs
        if c.routes:
            lines.append(f"\nRoutes: {', '.join(c.routes[:8])}")
        if c.classes:
            lines.append(f"Classes: {', '.join(c.classes[:8])}")
        if c.test_functions:
            lines.append(f"Tests: {len(c.test_functions)} test functions")
        if c.key_functions:
            lines.append(f"Key functions: {', '.join(c.key_functions[:8])}")

        # Modules worked on
        if self.module_groups:
            lines.append("\nModules worked on:")
            for mod, files in sorted(self.module_groups.items())[:6]:
                lines.append(f"  {mod}/ ({len(files)} files)")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Portfolio-level bundle
# ---------------------------------------------------------------------------


@dataclass
class PortfolioDataBundle:
    """Aggregated data across all projects — replaces PortfolioFacts."""

    user_email: str
    projects: List[ProjectDataBundle] = field(default_factory=list)

    # Aggregated stats
    total_projects: int = 0
    total_commits: int = 0
    languages_used: List[str] = field(default_factory=list)
    frameworks_used: List[str] = field(default_factory=list)
    earliest_commit: Optional[str] = None
    latest_commit: Optional[str] = None

    # Project type distribution
    project_types: Dict[str, int] = field(default_factory=dict)

    # Top skills across all projects (deduplicated, sorted by frequency)
    top_skills: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# ASSEMBLE phase output
# ---------------------------------------------------------------------------


@dataclass
class ResumeOutput:
    """Final resume output — replaces ResumeContent + GenerationResult."""

    # Per-project sections
    project_sections: Dict[str, ProjectSection] = field(default_factory=dict)

    # Portfolio-level sections (LLM-generated strings)
    professional_summary: str = ""
    skills_section: str = ""
    developer_profile: str = ""

    # Metadata
    portfolio_data: Optional[PortfolioDataBundle] = None
    model_used: str = ""
    generation_time_seconds: float = 0.0
    errors: List[str] = field(default_factory=list)

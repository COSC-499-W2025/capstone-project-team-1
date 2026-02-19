"""
Data models for the v3 resume pipeline.

Three bundles flow through the pipeline:
  1. ProjectDataBundle — per-repo extraction output (EXTRACT phase)
  2. PortfolioDataBundle — aggregated across repos (EXTRACT phase)
  3. ResumeOutput — final sections after LLM + assembly (QUERY/ASSEMBLE phase)
"""

from __future__ import annotations

import re
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

    routes: List[str] = field(default_factory=list)  # e.g. "GET /api/users"
    classes: List[str] = field(default_factory=list)  # e.g. "UserService"
    test_functions: List[str] = field(default_factory=list)  # e.g. "test_login"
    key_functions: List[str] = field(default_factory=list)  # e.g. "authenticate"


@dataclass
class ProjectSection:
    """LLM-generated content for one project."""

    description: str = ""
    bullets: List[str] = field(default_factory=list)
    bullet_fact_ids: List[List[str]] = field(
        default_factory=list
    )  # one list per bullet
    narrative: str = ""


@dataclass
class GitStats:
    """Quantitative impact signals per user per repo."""

    lines_added: int = 0
    lines_deleted: int = 0
    net_lines: int = 0
    files_touched: int = 0
    file_hotspots: List[tuple] = field(default_factory=list)  # (filename, edit_count)
    active_days: int = 0
    active_span_days: int = 0
    avg_commit_size: float = 0.0


@dataclass
class TestRatio:
    """Test-to-source file ratio for a repo."""

    test_files: int = 0
    source_files: int = 0
    test_ratio: float = 0.0
    has_ci: bool = False


@dataclass
class CommitQuality:
    """Overall commit quality metrics."""

    conventional_pct: float = 0.0
    avg_message_length: float = 0.0
    type_diversity: int = 0
    longest_streak: int = 0


@dataclass
class ModuleBreadth:
    """Breadth of contribution across the codebase."""

    modules_touched: int = 0
    total_modules: int = 0
    breadth_pct: float = 0.0
    deepest_path: str = ""


@dataclass
class EnrichedClass:
    """A class with structural metadata beyond just its name."""

    name: str
    method_count: int = 0
    total_loc: int = 0
    parent_class: str = ""


@dataclass
class EnrichedFunction:
    """A function with structural metadata beyond just its name."""

    name: str
    param_count: int = 0
    loc: int = 0
    has_return_type: bool = False


@dataclass
class EnrichedConstructs:
    """Code constructs with structural metadata (sizes, params, inheritance)."""

    classes: List[EnrichedClass] = field(default_factory=list)
    functions: List[EnrichedFunction] = field(default_factory=list)
    routes: List[str] = field(default_factory=list)
    test_functions: List[str] = field(default_factory=list)


@dataclass
class ImportGraph:
    """Import/dependency relationships across the codebase."""

    imports_map: Dict[str, List[str]] = field(default_factory=dict)
    layer_detection: List[str] = field(default_factory=list)
    circular_deps: List[tuple] = field(default_factory=list)
    external_deps: List[str] = field(default_factory=list)


@dataclass
class ConfigFingerprint:
    """Toolchain and infrastructure configuration signals."""

    linters: List[str] = field(default_factory=list)
    formatters: List[str] = field(default_factory=list)
    test_frameworks: List[str] = field(default_factory=list)
    build_tools: List[str] = field(default_factory=list)
    deployment_tools: List[str] = field(default_factory=list)
    package_managers: List[str] = field(default_factory=list)
    pre_commit_hooks: List[str] = field(default_factory=list)


@dataclass
class ChurnComplexityHotspot:
    """A file that is both frequently edited and complex — high-risk zone."""

    filepath: str
    edit_count: int
    cyclomatic_complexity: int
    max_nesting_depth: int
    risk_score: float  # normalized 0-1


@dataclass
class DistilledContext:
    """Token-budgeted, ranked context block ready for the LLM."""

    text: str = ""
    token_estimate: int = 0


@dataclass
class LLMProjectUnderstanding:
    """LLM-derived semantic understanding of the project from raw code snippets."""

    project_purpose: str = ""
    user_value: str = ""
    architecture_summary: str = ""
    key_capabilities: List[str] = field(default_factory=list)
    implementation_highlights: List[str] = field(default_factory=list)


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

    # New Strategy A extractors
    git_stats: GitStats = field(default_factory=GitStats)
    test_ratio: TestRatio = field(default_factory=TestRatio)
    commit_quality: CommitQuality = field(default_factory=CommitQuality)
    module_breadth: ModuleBreadth = field(default_factory=ModuleBreadth)

    # Analysis modules (from analysis/)
    style_metrics: Optional[Any] = None
    file_complexity: List[Any] = field(default_factory=list)
    skill_appearances: List[Any] = field(default_factory=list)

    # Enriched constructs (Phase 2)
    enriched_constructs: Optional[EnrichedConstructs] = None

    # Import graph, config fingerprint, churn-complexity (Phase 3)
    import_graph: Optional[ImportGraph] = None
    config_fingerprint: Optional[ConfigFingerprint] = None
    churn_complexity_hotspots: List[ChurnComplexityHotspot] = field(
        default_factory=list
    )

    # Distilled context (set by distill_project_context, used by to_prompt_context)
    distilled_context: Optional[DistilledContext] = None

    # LLM semantic understanding from raw repo snippets
    llm_understanding: Optional[LLMProjectUnderstanding] = None

    def all_commit_messages(self) -> List[str]:
        """Flat list of all commit messages across groups."""
        msgs: List[str] = []
        for g in self.commit_groups:
            msgs.extend(g.messages)
        return msgs

    def commit_count_by_type(self) -> Dict[str, int]:
        """Breakdown dict: {"feature": 15, "bugfix": 8, ...}."""
        return {g.category: g.count for g in self.commit_groups if g.count > 0}

    @staticmethod
    def _normalize_commit_msg(msg: str) -> str:
        """Normalize a commit message for dedup comparison."""
        text = msg.lower().strip()
        # Strip conventional commit prefix (feat: fix: etc.)
        text = re.sub(
            r"^(feat|fix|refactor|test|docs|chore|style|perf|ci|build)(\(.+?\))?:\s*",
            "",
            text,
        )
        # Strip ticket numbers like PROJ-123, #456
        text = re.sub(r"(#\d+|\b[A-Z]+-\d+\b)", "", text)
        # Collapse whitespace
        text = re.sub(r"\s+", " ", text).strip()
        return text

    @staticmethod
    def _dedup_commit_messages(messages: List[str]) -> List[str]:
        """Deduplicate near-identical commit messages using word-level Jaccard."""
        if len(messages) <= 1:
            return list(messages)

        normalized = [
            (msg, set(ProjectDataBundle._normalize_commit_msg(msg).split()))
            for msg in messages
        ]

        kept: List[str] = []
        kept_word_sets: List[set] = []

        for msg, words in normalized:
            if not words:
                continue
            is_dup = False
            for existing_words in kept_word_sets:
                intersection = len(words & existing_words)
                union = len(words | existing_words)
                if union > 0 and intersection / union >= 0.6:
                    is_dup = True
                    break
            if not is_dup:
                kept.append(msg)
                kept_word_sets.append(words)

        return kept

    def to_prompt_context(self) -> str:
        """Compact text for LLM prompt inclusion with commit dedup.

        If a distilled context has been set (via distill_project_context),
        returns that instead of building from raw fields.
        """
        if self.distilled_context is not None:
            return self.distilled_context.text

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

        # LLM semantic understanding
        if self.llm_understanding is not None:
            if self.llm_understanding.project_purpose:
                lines.append(f"\nLLM purpose: {self.llm_understanding.project_purpose}")
            if self.llm_understanding.user_value:
                lines.append(f"LLM user value: {self.llm_understanding.user_value}")
            if self.llm_understanding.architecture_summary:
                lines.append(
                    f"LLM architecture: {self.llm_understanding.architecture_summary}"
                )
            if self.llm_understanding.key_capabilities:
                lines.append(
                    "LLM capabilities: "
                    f"{', '.join(self.llm_understanding.key_capabilities[:5])}"
                )

        # Commit messages by type — deduplicated
        for group in self.commit_groups:
            if group.messages:
                deduped = self._dedup_commit_messages(group.messages[:10])
                lines.append(f"\n{group.category.upper()} commits ({group.count}):")
                for msg in deduped:
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
# Multi-stage pipeline types (Strategy B)
# ---------------------------------------------------------------------------


@dataclass
class RawProjectFacts:
    """Stage 1 output — structured facts extracted by LFM2.5-1.2B."""

    project_name: str = ""
    summary: str = ""  # 1 sentence: what the project does
    facts: List[str] = field(default_factory=list)  # 3-5 bullet facts
    fact_items: List["EvidenceLinkedFact"] = field(default_factory=list)
    evidence_catalog: Dict[str, str] = field(default_factory=dict)
    role: str = ""  # developer's specific contribution
    source_format: str = "text"  # "json" | "text"


@dataclass
class EvidenceLinkedFact:
    """A Stage 1 fact tied to deterministic evidence keys."""

    fact_id: str
    text: str
    evidence_keys: List[str] = field(default_factory=list)


@dataclass
class UserFeedback:
    """User corrections/preferences between draft and polish stages."""

    section_edits: Dict[str, str] = field(
        default_factory=dict
    )  # section_name -> corrected text
    additions: List[str] = field(default_factory=list)  # additional info to include
    removals: List[str] = field(default_factory=list)  # claims to remove
    tone: str = ""  # e.g. "more technical", "formal"
    general_notes: str = ""  # free-form instructions


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

    # Multi-stage raw material (Strategy B)
    raw_project_facts: Dict[str, RawProjectFacts] = field(default_factory=dict)
    stage: str = "single"  # "single" | "extract" | "draft" | "polish"

    # Metadata
    portfolio_data: Optional[PortfolioDataBundle] = None
    model_used: str = ""
    models_used: List[str] = field(
        default_factory=list
    )  # multi-stage tracks all models
    generation_time_seconds: float = 0.0
    errors: List[str] = field(default_factory=list)
    quality_metrics: Dict[str, Any] = field(default_factory=dict)

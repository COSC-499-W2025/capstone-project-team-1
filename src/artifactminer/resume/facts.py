"""
Facts Bundle Builder - Aggregates all static analysis signals into a structured format.

This module is the bridge between the rich static analysis infrastructure and
the optional LLM enhancement. It produces a lightweight, structured representation
of a user's contributions that can be:
1. Used directly to generate template-based resume bullets
2. Fed to a small LLM for prose polishing (without raw code)

The key insight: LLMs don't need to see code. They need pre-digested facts.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional
import json

# Extension to language name mapping (import from skill_patterns for single source of truth)
from ..skills.skill_patterns import LANGUAGE_EXTENSIONS

# File extensions that are NOT programming languages (filter these out)
JUNK_EXTENSIONS = {
    ".zip", ".tar", ".gz", ".rar", ".7z",  # Archives
    ".lock", ".log", ".tmp", ".cache",      # Generated files
    ".gitignore", ".gitattributes", ".gitmodules",  # Git files
    ".env", ".env.example", ".env.local",   # Env files
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp",  # Images
    ".mp4", ".avi", ".mov", ".webm",        # Videos
    ".mp3", ".wav", ".ogg",                 # Audio
    ".pdf", ".doc", ".docx",                # Documents
    ".csv", ".xlsx",                        # Data files
    ".txt", ".example", ".sample",          # Misc text
    ".mako", ".jinja", ".jinja2",           # Templates (not primary languages)
    ".ini", ".cfg", ".conf",                # Config files
    ".yml", ".yaml",                        # YAML (usually config)
    ".xml",                                 # XML (usually config/data)
    ".woff", ".woff2", ".ttf", ".eot",      # Fonts
}


def extension_to_language(ext: str) -> Optional[str]:
    """Convert file extension to human-readable language name."""
    if ext in LANGUAGE_EXTENSIONS:
        return LANGUAGE_EXTENSIONS[ext][0]  # Returns "Python", "JavaScript", etc.
    return None


NON_LANGUAGE_EXTENSIONS = {
    ".md", ".markdown", ".rst", ".txt",  # Documentation (not a language)
    ".json", ".toml",                    # Data/config (not a language)
}


def is_programming_language(ext: str) -> bool:
    """Check if extension represents a programming language."""
    ext_lower = ext.lower()
    if ext_lower in JUNK_EXTENSIONS or ext_lower in NON_LANGUAGE_EXTENSIONS:
        return False
    # Known programming languages
    if ext_lower in LANGUAGE_EXTENSIONS:
        return True
    # Additional code extensions not in LANGUAGE_EXTENSIONS
    code_extensions = {".html", ".css", ".scss", ".sass", ".less", ".vue", ".svelte"}
    return ext_lower in code_extensions


def clean_skill_evidence(evidence_list: List[str]) -> List[str]:
    """
    Clean skill evidence for resume presentation.

    Removes debug-style evidence like "366 user-touched *.py files detected"
    and keeps only meaningful evidence.
    """
    cleaned = []
    for evidence in evidence_list:
        # Skip file count evidence (not resume-appropriate)
        if "files detected" in evidence.lower():
            continue
        # Skip "Detected via repo stats" internal messages
        if "detected via repo stats" in evidence.lower():
            continue
        # Skip "Detected framework" internal messages
        if evidence.lower().startswith("detected framework"):
            continue
        # Keep meaningful evidence (pattern matches, etc.)
        cleaned.append(evidence)
    return cleaned


@dataclass
class ProjectFacts:
    """All facts about a single project, extracted via static analysis."""

    # Basic info
    project_name: str
    project_path: str

    # Languages & frameworks
    languages: List[str] = field(default_factory=list)
    language_percentages: List[float] = field(default_factory=list)
    primary_language: Optional[str] = None
    frameworks: List[str] = field(default_factory=list)

    # User contribution metrics
    user_contribution_pct: Optional[float] = None
    user_total_commits: Optional[int] = None
    total_commits: Optional[int] = None
    commit_frequency: Optional[str] = None  # e.g., "2.3 commits/week"
    first_commit: Optional[str] = None  # ISO date string
    last_commit: Optional[str] = None   # ISO date string

    # Activity breakdown (what kind of work did the user do?)
    activity_breakdown: Dict[str, float] = field(default_factory=dict)
    # e.g., {"code": 78.0, "tests": 12.0, "docs": 8.0, "config": 2.0}

    # Detected skills (from SkillExtractor)
    detected_skills: List[str] = field(default_factory=list)
    skill_evidence: Dict[str, List[str]] = field(default_factory=dict)
    # e.g., {"REST API Design": ["@router.get in api/routes.py", "FastAPI dependency injection"]}

    # Strategic insights (from DeepRepoAnalyzer)
    insights: List[Dict[str, Any]] = field(default_factory=list)
    # e.g., [{"title": "API Design", "why": "...", "evidence": [...]}]

    # Repository health
    health_score: Optional[float] = None
    is_collaborative: bool = False

    # --- NEW: LLM-enhanced analysis fields ---

    # Commit classification (feature/bugfix/refactor/test/docs/chore counts)
    commit_breakdown: Dict[str, int] = field(default_factory=dict)

    # Skill first-appearance dates (skill_name → ISO date)
    skill_first_appearances: Dict[str, str] = field(default_factory=dict)

    # Code style metrics
    style_metrics: Optional[Dict[str, Any]] = None

    # Complexity highlights (top complex files)
    complexity_highlights: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    def to_llm_context(self, max_skills: int = 10, max_evidence: int = 3) -> str:
        """
        Generate a compact text representation for LLM consumption.

        This is the key method - it produces a token-efficient summary
        that gives the LLM everything it needs without any raw code.
        """
        lines = []

        # Project header
        lines.append(f"PROJECT: {self.project_name}")

        # Languages & frameworks
        lang_str = ", ".join(
            f"{lang} ({pct:.0f}%)"
            for lang, pct in zip(self.languages[:3], self.language_percentages[:3])
        ) if self.languages else "Unknown"
        lines.append(f"Stack: {lang_str}")

        if self.frameworks:
            lines.append(f"Frameworks: {', '.join(self.frameworks)}")

        # User contribution
        if self.user_contribution_pct is not None:
            contrib = f"{self.user_contribution_pct:.0f}% of commits"
            if self.user_total_commits and self.total_commits:
                contrib += f" ({self.user_total_commits}/{self.total_commits})"
            lines.append(f"Contribution: {contrib}")

        # Time period
        if self.first_commit and self.last_commit:
            lines.append(f"Period: {self.first_commit[:10]} to {self.last_commit[:10]}")

        # Activity breakdown
        if self.activity_breakdown:
            activities = [f"{k}: {v:.0f}%" for k, v in self.activity_breakdown.items() if v > 0]
            if activities:
                lines.append(f"Work breakdown: {', '.join(activities)}")

        # Skills with evidence
        if self.detected_skills:
            lines.append(f"Skills demonstrated: {', '.join(self.detected_skills[:max_skills])}")

            # Add evidence for top skills
            for skill in self.detected_skills[:5]:
                if skill in self.skill_evidence:
                    evidence = self.skill_evidence[skill][:max_evidence]
                    if evidence:
                        lines.append(f"  - {skill}: {'; '.join(evidence)}")

        # Insights
        if self.insights:
            lines.append("Key insights:")
            for insight in self.insights:
                lines.append(f"  - {insight.get('title', 'Unknown')}: {insight.get('why', '')}")

        # Commit breakdown
        if self.commit_breakdown:
            parts = [f"{k}: {v}" for k, v in self.commit_breakdown.items() if v > 0]
            if parts:
                lines.append(f"Commit types: {', '.join(parts)}")

        return "\n".join(lines)


@dataclass
class PortfolioFacts:
    """Aggregated facts across all projects in a user's portfolio."""

    user_email: str
    projects: List[ProjectFacts] = field(default_factory=list)

    # Aggregated skills (deduplicated, sorted by frequency)
    top_skills: List[str] = field(default_factory=list)

    # Overall stats
    total_projects: int = 0
    total_commits: int = 0
    languages_used: List[str] = field(default_factory=list)
    frameworks_used: List[str] = field(default_factory=list)

    # Date range across all projects
    earliest_commit: Optional[str] = None
    latest_commit: Optional[str] = None

    # --- NEW: LLM-enhanced analysis fields ---

    # Aggregated commit breakdown across all projects
    total_commit_breakdown: Dict[str, int] = field(default_factory=dict)

    # Skill timeline (aggregated across projects, sorted by date)
    skill_timeline: List[Dict[str, str]] = field(default_factory=list)

    # LLM-generated narratives (populated after LLM calls)
    skill_evolution_narrative: Optional[str] = None
    developer_fingerprint: Optional[str] = None
    complexity_narrative: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        d = asdict(self)
        d["projects"] = [p.to_dict() for p in self.projects]
        return d

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)

    def to_llm_context(self) -> str:
        """
        Generate a compact portfolio summary for LLM consumption.
        """
        lines = []

        lines.append("PORTFOLIO SUMMARY")
        lines.append(f"Projects: {self.total_projects}")
        lines.append(f"Total commits: {self.total_commits}")

        if self.languages_used:
            lines.append(f"Languages: {', '.join(self.languages_used[:5])}")

        if self.frameworks_used:
            lines.append(f"Frameworks: {', '.join(self.frameworks_used[:8])}")

        if self.top_skills:
            lines.append(f"Top skills: {', '.join(self.top_skills[:10])}")

        if self.earliest_commit and self.latest_commit:
            lines.append(f"Active period: {self.earliest_commit[:10]} to {self.latest_commit[:10]}")

        lines.append("")
        lines.append("=" * 50)
        lines.append("")

        # Add each project's context
        for project in self.projects:
            lines.append(project.to_llm_context())
            lines.append("")
            lines.append("-" * 30)
            lines.append("")

        return "\n".join(lines)


def build_project_facts(
    repo_path: str,
    repo_stats: Any,  # RepoStats dataclass
    user_stats: Any | None,  # UserRepoStats dataclass
    deep_result: Any | None,  # DeepAnalysisResult
    activity_data: Dict[str, Any] | None = None,
) -> ProjectFacts:
    """
    Build a ProjectFacts bundle from the outputs of various static analyzers.

    This is the integration point that combines:
    - getRepoStats() output
    - getUserRepoStats() output
    - DeepRepoAnalyzer.analyze() output
    - Activity classification data

    Args:
        repo_path: Path to the repository
        repo_stats: Output from getRepoStats()
        user_stats: Output from getUserRepoStats() (may be None if user has no commits)
        deep_result: Output from DeepRepoAnalyzer.analyze()
        activity_data: Optional activity breakdown from classify_commit_activities()

    Returns:
        ProjectFacts with all relevant signals aggregated
    """
    # Clean up languages: filter junk, map to proper names, deduplicate
    raw_languages = repo_stats.Languages or []
    raw_percentages = repo_stats.language_percentages or []

    # First pass: collect and aggregate by language name
    lang_totals: Dict[str, float] = {}
    for ext, pct in zip(raw_languages, raw_percentages):
        if is_programming_language(ext):
            lang_name = extension_to_language(ext) or ext.lstrip(".")
            lang_totals[lang_name] = lang_totals.get(lang_name, 0) + pct

    # Sort by percentage descending
    sorted_langs = sorted(lang_totals.items(), key=lambda x: -x[1])
    clean_languages = [lang for lang, _ in sorted_langs]
    clean_percentages = [pct for _, pct in sorted_langs]

    # Determine primary language (map from extension to name)
    primary_lang = repo_stats.primary_language
    if primary_lang:
        primary_lang = extension_to_language(primary_lang) or primary_lang.lstrip(".")

    facts = ProjectFacts(
        project_name=repo_stats.project_name,
        project_path=str(repo_path),
        languages=clean_languages,
        language_percentages=clean_percentages,
        primary_language=primary_lang,
        frameworks=repo_stats.frameworks or [],
        total_commits=repo_stats.total_commits,
        health_score=repo_stats.health_score,
        is_collaborative=repo_stats.is_collaborative,
    )

    # Add user-specific stats if available
    if user_stats:
        facts.user_contribution_pct = getattr(user_stats, 'userStatspercentages', None)
        facts.user_total_commits = getattr(user_stats, 'total_commits', None)
        facts.commit_frequency = str(getattr(user_stats, 'commitFrequency', ''))

        first = getattr(user_stats, 'first_commit', None)
        last = getattr(user_stats, 'last_commit', None)
        if first:
            facts.first_commit = first.isoformat() if isinstance(first, datetime) else str(first)
        if last:
            facts.last_commit = last.isoformat() if isinstance(last, datetime) else str(last)

    # Add activity breakdown if available
    if activity_data:
        # Normalize to percentages
        total = sum(activity_data.values()) if activity_data.values() else 1
        facts.activity_breakdown = {
            k: (v / total * 100) if total > 0 else 0
            for k, v in activity_data.items()
        }

    # Add skills and insights from deep analysis
    if deep_result:
        # Extract skill names and evidence (cleaned for resume)
        for skill in deep_result.skills:
            facts.detected_skills.append(skill.skill)
            if skill.evidence:
                # Clean evidence: remove debug strings, keep meaningful content
                cleaned = clean_skill_evidence(skill.evidence[:5])
                if cleaned:
                    facts.skill_evidence[skill.skill] = cleaned

        # Extract insights
        for insight in deep_result.insights:
            # Clean insight evidence too
            cleaned_evidence = clean_skill_evidence(insight.evidence[:3]) if insight.evidence else []
            facts.insights.append({
                "title": insight.title,
                "why": insight.why_it_matters,
                "evidence": cleaned_evidence,
            })

    return facts


def build_portfolio_facts(
    user_email: str,
    project_facts_list: List[ProjectFacts],
) -> PortfolioFacts:
    """
    Build a PortfolioFacts bundle aggregating all projects.

    Args:
        user_email: The user's email
        project_facts_list: List of ProjectFacts for each analyzed repo

    Returns:
        PortfolioFacts with aggregated statistics and top skills
    """
    portfolio = PortfolioFacts(
        user_email=user_email,
        projects=project_facts_list,
        total_projects=len(project_facts_list),
    )

    # Aggregate commits
    portfolio.total_commits = sum(
        p.user_total_commits or 0 for p in project_facts_list
    )

    # Collect all languages (deduplicated, ordered by frequency)
    # Languages are already cleaned in build_project_facts
    lang_counter: Dict[str, int] = {}
    for p in project_facts_list:
        for lang in p.languages:
            lang_counter[lang] = lang_counter.get(lang, 0) + 1
    portfolio.languages_used = sorted(lang_counter.keys(), key=lambda x: -lang_counter[x])

    # Collect all frameworks (deduplicated)
    frameworks_seen: set = set()
    for p in project_facts_list:
        frameworks_seen.update(p.frameworks)
    portfolio.frameworks_used = sorted(frameworks_seen)

    # Collect all skills (sorted by frequency across projects)
    skill_counter: Dict[str, int] = {}
    for p in project_facts_list:
        for skill in p.detected_skills:
            skill_counter[skill] = skill_counter.get(skill, 0) + 1
    portfolio.top_skills = sorted(skill_counter.keys(), key=lambda x: -skill_counter[x])

    # Find date range
    all_firsts = [p.first_commit for p in project_facts_list if p.first_commit]
    all_lasts = [p.last_commit for p in project_facts_list if p.last_commit]
    if all_firsts:
        portfolio.earliest_commit = min(all_firsts)
    if all_lasts:
        portfolio.latest_commit = max(all_lasts)

    # Aggregate commit breakdowns
    for p in project_facts_list:
        for cat, count in p.commit_breakdown.items():
            portfolio.total_commit_breakdown[cat] = (
                portfolio.total_commit_breakdown.get(cat, 0) + count
            )

    # Aggregate skill timeline (sorted by date across all projects)
    for p in project_facts_list:
        for skill, date in p.skill_first_appearances.items():
            portfolio.skill_timeline.append({
                "skill": skill,
                "first_seen": date,
                "project": p.project_name,
            })
    portfolio.skill_timeline.sort(key=lambda x: x.get("first_seen", ""))

    return portfolio

"""
Resume Generation Orchestrator - Main entry point for the new architecture.

This module orchestrates the full pipeline:
1. Extract ZIP and discover git repos (existing infrastructure)
2. Run static analysis on each repo (existing: getRepoStats, getUserRepoStats, DeepRepoAnalyzer)
3. Build facts bundles from analysis outputs (facts.py)
4. Optionally enhance with LLM (enhance.py)
5. Output resume content (JSON + Markdown)

The key design principle: Static analysis does 90% of the work.
The LLM (if enabled) just polishes the prose.
"""

from __future__ import annotations

import json
import shutil
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Optional

from .facts import (
    ProjectFacts,
    PortfolioFacts,
    build_project_facts,
    build_portfolio_facts,
)
from .enhance import (
    ResumeContent,
    enhance_with_llm,
)


@dataclass
class GenerationResult:
    """Final output of the resume generation pipeline."""

    portfolio_facts: PortfolioFacts
    resume_content: ResumeContent
    generation_time_seconds: float
    errors: List[str]

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON."""
        return json.dumps(
            {
                "portfolio": self.portfolio_facts.to_dict(),
                "resume": {
                    "project_bullets": self.resume_content.project_bullets,
                    "professional_summary": self.resume_content.professional_summary,
                    "skills_section": self.resume_content.skills_section,
                    "skill_evolution": self.resume_content.skill_evolution,
                    "developer_profile": self.resume_content.developer_profile,
                    "complexity_highlights": self.resume_content.complexity_highlights,
                    "work_breakdown": self.resume_content.work_breakdown,
                    "llm_enhanced": self.resume_content.llm_enhanced,
                    "model_used": self.resume_content.model_used,
                },
                "metadata": {
                    "generation_time_seconds": self.generation_time_seconds,
                    "errors": self.errors,
                },
            },
            indent=indent,
            default=str,
        )

    def to_markdown(self) -> str:
        """Generate human-readable markdown output."""
        lines = []

        # Header
        lines.append("# Resume Content")
        lines.append("")

        # Professional Summary
        if self.resume_content.professional_summary:
            lines.append("## Professional Summary")
            lines.append("")
            lines.append(self.resume_content.professional_summary)
            lines.append("")

        # Skills
        if self.resume_content.skills_section:
            lines.append("## Technical Skills")
            lines.append("")
            lines.append(self.resume_content.skills_section)
            lines.append("")

        # Projects
        lines.append("## Projects")
        lines.append("")

        for project in self.portfolio_facts.projects:
            lines.append(f"### {project.project_name}")
            lines.append("")

            # Project metadata
            if project.frameworks:
                lines.append(f"**Technologies:** {', '.join(project.frameworks)}")
            if project.primary_language:
                lines.append(f"**Primary Language:** {project.primary_language}")
            if project.user_contribution_pct:
                lines.append(f"**Contribution:** {project.user_contribution_pct:.0f}%")
            lines.append("")

            # Bullets
            bullets = self.resume_content.project_bullets.get(project.project_name, [])
            for bullet in bullets:
                lines.append(f"- {bullet}")
            lines.append("")

        # Skill Evolution
        if self.resume_content.skill_evolution:
            lines.append("## Skill Evolution")
            lines.append("")
            lines.append(self.resume_content.skill_evolution)
            lines.append("")

        # Developer Profile
        if self.resume_content.developer_profile:
            lines.append("## Developer Profile")
            lines.append("")
            lines.append(self.resume_content.developer_profile)
            lines.append("")

        # Complexity Highlights
        if self.resume_content.complexity_highlights:
            lines.append("## Complexity Highlights")
            lines.append("")
            lines.append(self.resume_content.complexity_highlights)
            lines.append("")

        # Work Breakdown
        if self.resume_content.work_breakdown:
            lines.append("## Work Breakdown")
            lines.append("")
            total = sum(self.resume_content.work_breakdown.values())
            for cat, count in sorted(
                self.resume_content.work_breakdown.items(),
                key=lambda x: -x[1],
            ):
                pct = (count / total * 100) if total > 0 else 0
                lines.append(f"- **{cat.title()}**: {count} commits ({pct:.0f}%)")
            lines.append("")

        # Footer
        lines.append("---")
        enhanced = (
            "LLM-enhanced" if self.resume_content.llm_enhanced else "Template-generated"
        )
        model = (
            f" ({self.resume_content.model_used})"
            if self.resume_content.model_used
            else ""
        )
        lines.append(f"*{enhanced}{model} in {self.generation_time_seconds:.1f}s*")

        return "\n".join(lines)


def extract_zip(zip_path: str, extract_to: Optional[str] = None) -> Path:
    """
    Extract ZIP file to a directory.

    Args:
        zip_path: Path to the ZIP file
        extract_to: Optional extraction directory. If None, extracts next to ZIP.

    Returns:
        Path to extraction directory
    """
    zip_file = Path(zip_path)
    if not zip_file.exists():
        raise FileNotFoundError(f"ZIP file not found: {zip_file}")

    if extract_to:
        extract_dir = Path(extract_to)
    else:
        extract_dir = zip_file.parent / f"{zip_file.stem}_extracted"

    # Clean up previous extraction
    if extract_dir.exists():
        shutil.rmtree(extract_dir)

    extract_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_file, "r") as zf:
        zf.extractall(extract_dir)

    return extract_dir


def discover_git_repos(base_path: Path) -> List[Path]:
    """
    Find all git repositories under a base path.

    Args:
        base_path: Directory to search

    Returns:
        List of paths to git repositories
    """
    repos = []

    def is_macos_metadata(path: Path) -> bool:
        try:
            parts = path.relative_to(base_path).parts
        except ValueError:
            parts = path.parts
        return any(part == "__MACOSX" or part.startswith("._") for part in parts)

    def is_git_repo(path: Path) -> bool:
        git_dir = path / ".git"
        return git_dir.is_dir() and (git_dir / "HEAD").is_file()

    if is_git_repo(base_path) and not is_macos_metadata(base_path):
        repos.append(base_path)

    for path in base_path.rglob("*"):
        if not path.is_dir() or is_macos_metadata(path):
            continue

        if is_git_repo(path):
            # Avoid nested repos
            is_nested = any(
                is_git_repo(parent)
                for parent in path.parents
                if parent != base_path and str(parent).startswith(str(base_path))
            )
            if not is_nested:
                repos.append(path)

    return repos


def generate_resume(
    zip_path: str,
    user_email: str,
    llm_model: Optional[str] = None,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> GenerationResult:
    """
    Main entry point: Generate resume content from a ZIP of git repositories.

    Args:
        zip_path: Absolute path to the ZIP file containing git repos
        user_email: User's email for attribution in git history
        llm_model: Local GGUF model to use (default: qwen3-1.7b)
        progress_callback: Optional callback for progress updates

    Returns:
        GenerationResult with portfolio facts and resume content

    Raises:
        RuntimeError: If model is not available or LLM fails
    """
    start_time = datetime.now()
    errors: List[str] = []

    def log(msg: str):
        if progress_callback:
            progress_callback(msg)
        print(f"[resume] {msg}")

    # Ensure the LLM model is available before starting analysis
    model = llm_model or "qwen3-1.7b"
    from .llm_client import ensure_model_available

    log(f"Ensuring model '{model}' is available...")
    ensure_model_available(model)

    # Import existing analysis infrastructure
    # (Deferred import to avoid circular dependencies)
    from ..RepositoryIntelligence.repo_intelligence_main import getRepoStats
    from ..RepositoryIntelligence.repo_intelligence_user import (
        getUserRepoStats,
        collect_user_additions,
    )
    from ..skills.deep_analysis import DeepRepoAnalyzer

    # Step 1: Extract ZIP
    log(f"Extracting {zip_path}...")
    try:
        extract_dir = extract_zip(zip_path)
        log(f"Extracted to {extract_dir}")
    except Exception as e:
        raise RuntimeError(f"Failed to extract ZIP: {e}")

    # Step 2: Discover git repositories
    log("Discovering git repositories...")
    repos = discover_git_repos(extract_dir)
    if not repos:
        raise RuntimeError("No git repositories found in ZIP")
    log(f"Found {len(repos)} repositories")

    # Step 3: Analyze each repository
    analyzer = DeepRepoAnalyzer(enable_llm=False)  # Static analysis only
    project_facts_list: List[ProjectFacts] = []

    for i, repo_path in enumerate(repos):
        repo_name = repo_path.name
        log(f"Analyzing [{i + 1}/{len(repos)}]: {repo_name}")

        try:
            # Get repository stats (existing function)
            repo_stats = getRepoStats(repo_path)

            # Get user-specific stats (existing function)
            user_stats = None
            additions_text = ""
            try:
                user_stats = getUserRepoStats(repo_path, user_email)
                user_additions = collect_user_additions(
                    repo_path=str(repo_path),
                    user_email=user_email,
                    max_commits=500,
                )
                additions_text = "\n".join(user_additions)
            except ValueError as e:
                log(f"  Note: {e}")
                # User has no commits, but we can still analyze the repo

            # Run deep analysis (existing function)
            deep_result = analyzer.analyze(
                repo_path=str(repo_path),
                repo_stat=repo_stats,  # Pass the stats object
                user_email=user_email,
                user_contributions={"additions": additions_text},
                consent_level="full",  # We're doing local analysis
            )

            # Build facts bundle from analysis outputs
            facts = build_project_facts(
                repo_path=str(repo_path),
                repo_stats=repo_stats,
                user_stats=user_stats,
                deep_result=deep_result,
            )

            # --- NEW: LLM-enhanced analysis per repo ---
            from .analysis.commit_classifier import (
                extract_commit_messages,
                classify_commits,
            )
            from .analysis.skill_timeline import compute_skill_first_appearances
            from .analysis.developer_style import compute_style_metrics
            from .analysis.complexity_narrative import compute_complexity_metrics

            # 3b: Commit message classification
            try:
                commit_msgs = extract_commit_messages(
                    str(repo_path), user_email, max_commits=200
                )
                if commit_msgs:
                    log(f"  Classifying {len(commit_msgs)} commits...")
                    facts.commit_breakdown = classify_commits(commit_msgs, model=model)
                    facts.commit_subjects = [c.message for c in commit_msgs]
            except Exception as e:
                log(f"  Note: commit classification skipped: {e}")

            # 3c: Skill first-appearances
            try:
                appearances = compute_skill_first_appearances(
                    str(repo_path), user_email, facts.detected_skills
                )
                facts.skill_first_appearances = {
                    a.skill_name: a.first_date for a in appearances
                }
            except Exception as e:
                log(f"  Note: skill timeline skipped: {e}")

            # 3d: Style metrics
            try:
                style = compute_style_metrics(
                    str(repo_path), user_email, facts.primary_language
                )
                if style:
                    from dataclasses import asdict as _asdict

                    facts.style_metrics = _asdict(style)
            except Exception as e:
                log(f"  Note: style metrics skipped: {e}")

            # 3e: Complexity metrics
            try:
                complexity = compute_complexity_metrics(str(repo_path), user_email)
                if complexity:
                    from dataclasses import asdict as _asdict2

                    facts.complexity_highlights = [_asdict2(c) for c in complexity[:5]]
            except Exception as e:
                log(f"  Note: complexity metrics skipped: {e}")

            project_facts_list.append(facts)
            log(
                f"  ✓ {len(facts.detected_skills)} skills, {len(facts.insights)} insights"
            )

        except Exception as e:
            error_msg = f"Error analyzing {repo_name}: {e}"
            log(f"  ✗ {error_msg}")
            errors.append(error_msg)

    if not project_facts_list:
        raise RuntimeError("No repositories could be analyzed")

    # Step 4: Build portfolio facts
    log("Building portfolio summary...")
    portfolio = build_portfolio_facts(user_email, project_facts_list)
    log(
        f"Portfolio: {portfolio.total_projects} projects, {len(portfolio.top_skills)} skills"
    )

    # Step 5: LLM narrative generation for new analysis features

    # 5a: Skill evolution narrative
    if portfolio.skill_timeline:
        try:
            from .analysis.skill_timeline import (
                SkillAppearance,
                generate_skill_timeline_narrative,
            )

            appearances = [
                SkillAppearance(
                    skill_name=s["skill"],
                    first_date=s["first_seen"],
                    project_name=s.get("project", ""),
                    evidence="",
                )
                for s in portfolio.skill_timeline
            ]
            log("Generating skill evolution narrative...")
            result = generate_skill_timeline_narrative(appearances, model)
            if result:
                portfolio.skill_evolution_narrative = result.narrative
        except Exception as e:
            log(f"  Note: skill timeline narrative skipped: {e}")

    # 5b: Developer style fingerprint
    all_style_metrics = [p.style_metrics for p in project_facts_list if p.style_metrics]
    if all_style_metrics:
        try:
            from .analysis.developer_style import (
                StyleMetrics,
                generate_style_fingerprint,
            )

            # Use the first project's metrics (or aggregate later)
            m = all_style_metrics[0]
            metrics = StyleMetrics(**m)
            log("Generating developer profile...")
            fingerprint = generate_style_fingerprint(metrics, model)
            if fingerprint:
                portfolio.developer_fingerprint = fingerprint.narrative
        except Exception as e:
            log(f"  Note: developer fingerprint skipped: {e}")

    # 5c: Complexity narrative
    all_complexity = []
    for p in project_facts_list:
        all_complexity.extend(p.complexity_highlights)
    if all_complexity:
        try:
            from .analysis.complexity_narrative import (
                FileComplexity,
                generate_complexity_narrative,
            )

            metrics_list = [FileComplexity(**c) for c in all_complexity]
            log("Generating complexity narrative...")
            narrative = generate_complexity_narrative(metrics_list, model)
            if narrative:
                portfolio.complexity_narrative = narrative.narrative
        except Exception as e:
            log(f"  Note: complexity narrative skipped: {e}")

    # Step 6: Generate resume content with LLM (existing prose polish)
    log(f"Enhancing with LLM ({model})...")
    resume_content = enhance_with_llm(portfolio, model=model)

    # Done
    elapsed = (datetime.now() - start_time).total_seconds()
    log(f"Generation complete in {elapsed:.1f}s")

    return GenerationResult(
        portfolio_facts=portfolio,
        resume_content=resume_content,
        generation_time_seconds=elapsed,
        errors=errors,
    )

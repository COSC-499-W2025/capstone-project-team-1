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
        return json.dumps({
            "portfolio": self.portfolio_facts.to_dict(),
            "resume": {
                "project_bullets": self.resume_content.project_bullets,
                "professional_summary": self.resume_content.professional_summary,
                "skills_section": self.resume_content.skills_section,
                "llm_enhanced": self.resume_content.llm_enhanced,
                "model_used": self.resume_content.model_used,
            },
            "metadata": {
                "generation_time_seconds": self.generation_time_seconds,
                "errors": self.errors,
            }
        }, indent=indent, default=str)

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

        # Footer
        lines.append("---")
        enhanced = "LLM-enhanced" if self.resume_content.llm_enhanced else "Template-generated"
        model = f" ({self.resume_content.model_used})" if self.resume_content.model_used else ""
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
    zip_path = Path(zip_path)
    if not zip_path.exists():
        raise FileNotFoundError(f"ZIP file not found: {zip_path}")

    if extract_to:
        extract_dir = Path(extract_to)
    else:
        extract_dir = zip_path.parent / f"{zip_path.stem}_extracted"

    # Clean up previous extraction
    if extract_dir.exists():
        shutil.rmtree(extract_dir)

    extract_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zf:
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

    def is_git_repo(path: Path) -> bool:
        return (path / ".git").is_dir()

    if is_git_repo(base_path):
        repos.append(base_path)

    for path in base_path.rglob("*"):
        if path.is_dir() and is_git_repo(path):
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
        llm_model: Ollama model to use (default: qwen3:1.7b)
        progress_callback: Optional callback for progress updates

    Returns:
        GenerationResult with portfolio facts and resume content

    Raises:
        RuntimeError: If Ollama is not available or LLM fails
    """
    start_time = datetime.now()
    errors: List[str] = []

    def log(msg: str):
        if progress_callback:
            progress_callback(msg)
        print(f"[resume] {msg}")

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
        log(f"Analyzing [{i+1}/{len(repos)}]: {repo_name}")

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

            project_facts_list.append(facts)
            log(f"  ✓ {len(facts.detected_skills)} skills, {len(facts.insights)} insights")

        except Exception as e:
            error_msg = f"Error analyzing {repo_name}: {e}"
            log(f"  ✗ {error_msg}")
            errors.append(error_msg)

    if not project_facts_list:
        raise RuntimeError("No repositories could be analyzed")

    # Step 4: Build portfolio facts
    log("Building portfolio summary...")
    portfolio = build_portfolio_facts(user_email, project_facts_list)
    log(f"Portfolio: {portfolio.total_projects} projects, {len(portfolio.top_skills)} skills")

    # Step 5: Generate resume content with LLM
    model = llm_model or "qwen3:1.7b"
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

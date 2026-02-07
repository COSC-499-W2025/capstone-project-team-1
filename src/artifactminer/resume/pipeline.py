"""
v3 Resume Pipeline Orchestrator.

Three clean phases:
  1. EXTRACT — static data gathering into ProjectDataBundle / PortfolioDataBundle
  2. QUERY  — focused LLM calls (1 per project + 3 portfolio)
  3. ASSEMBLE — stitch into final markdown + JSON

Replaces generate.generate_resume as the main entry point.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Optional

from .models import (
    ProjectDataBundle,
    PortfolioDataBundle,
    ResumeOutput,
)
from .extractors import (
    extract_readme,
    extract_and_classify_commits,
    extract_structure,
    extract_constructs,
    infer_project_type,
)
from .queries.runner import run_project_query, run_portfolio_queries
from .assembler import assemble_markdown, assemble_json

# Reuse existing infrastructure
from .generate import extract_zip, discover_git_repos
from .facts import (
    build_project_facts,
    build_portfolio_facts,
    is_programming_language,
    extension_to_language,
)

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Phase 1: EXTRACT
# ---------------------------------------------------------------------------


def _extract_project(
    repo_path: Path,
    user_email: str,
    *,
    llm_model: Optional[str] = None,
    progress: Optional[Callable[[str], None]] = None,
) -> ProjectDataBundle:
    """Run all extractors on a single repo, returning a ProjectDataBundle."""
    from ..RepositoryIntelligence.repo_intelligence_main import getRepoStats
    from ..RepositoryIntelligence.repo_intelligence_user import getUserRepoStats
    from ..skills.deep_analysis import DeepRepoAnalyzer
    from ..RepositoryIntelligence.repo_intelligence_user import collect_user_additions

    repo_name = repo_path.name

    # --- Existing static analysis ---
    repo_stats = getRepoStats(repo_path)

    user_stats = None
    try:
        user_stats = getUserRepoStats(repo_path, user_email)
    except ValueError:
        pass

    # Deep analysis for skills/insights
    additions_text = ""
    try:
        user_additions = collect_user_additions(
            repo_path=str(repo_path),
            user_email=user_email,
            max_commits=500,
        )
        additions_text = "\n".join(user_additions)
    except Exception:
        pass

    analyzer = DeepRepoAnalyzer(enable_llm=False)
    deep_result = analyzer.analyze(
        repo_path=str(repo_path),
        repo_stat=repo_stats,
        user_email=user_email,
        user_contributions={"additions": additions_text},
        consent_level="full",
    )

    # Build intermediate ProjectFacts (reuse existing builder)
    facts = build_project_facts(
        repo_path=str(repo_path),
        repo_stats=repo_stats,
        user_stats=user_stats,
        deep_result=deep_result,
    )

    # --- New v3 extractors ---
    if progress:
        progress(f"  Extracting README...")
    readme_text = extract_readme(str(repo_path))

    if progress:
        progress(f"  Classifying commits...")
    commit_groups = extract_and_classify_commits(
        str(repo_path),
        user_email,
        llm_model=llm_model,
    )

    if progress:
        progress(f"  Extracting structure...")
    directory_overview, module_groups = extract_structure(str(repo_path), user_email)

    # Collect user-touched files for construct scanning
    touched_files: set[str] = set()
    for files in module_groups.values():
        touched_files.update(files)

    if progress:
        progress(f"  Extracting code constructs...")
    constructs = extract_constructs(str(repo_path), touched_files or None)

    if progress:
        progress(f"  Inferring project type...")
    project_type = infer_project_type(
        str(repo_path),
        frameworks=facts.frameworks,
        readme_text=readme_text,
    )

    # --- Assemble ProjectDataBundle ---
    # Clean up languages (reuse facts.py logic already applied)
    raw_langs = repo_stats.Languages or []
    raw_pcts = repo_stats.language_percentages or []
    lang_totals: dict[str, float] = {}
    for ext, pct in zip(raw_langs, raw_pcts):
        if is_programming_language(ext):
            name = extension_to_language(ext) or ext.lstrip(".")
            lang_totals[name] = lang_totals.get(name, 0) + pct
    sorted_langs = sorted(lang_totals.items(), key=lambda x: -x[1])

    primary_lang = repo_stats.primary_language
    if primary_lang:
        primary_lang = extension_to_language(primary_lang) or primary_lang.lstrip(".")

    bundle = ProjectDataBundle(
        project_name=repo_stats.project_name,
        project_path=str(repo_path),
        project_type=project_type,
        languages=[lang for lang, _ in sorted_langs],
        language_percentages=[pct for _, pct in sorted_langs],
        primary_language=primary_lang,
        frameworks=repo_stats.frameworks or [],
        total_commits=repo_stats.total_commits,
        readme_text=readme_text,
        commit_groups=commit_groups,
        directory_overview=directory_overview,
        module_groups=module_groups,
        constructs=constructs,
        detected_skills=facts.detected_skills,
        skill_evidence=facts.skill_evidence,
        insights=facts.insights,
    )

    # User-specific stats
    if user_stats:
        bundle.user_contribution_pct = getattr(user_stats, "userStatspercentages", None)
        bundle.user_total_commits = getattr(user_stats, "total_commits", None)
        first = getattr(user_stats, "first_commit", None)
        last = getattr(user_stats, "last_commit", None)
        if first:
            bundle.first_commit = first.isoformat() if hasattr(first, "isoformat") else str(first)
        if last:
            bundle.last_commit = last.isoformat() if hasattr(last, "isoformat") else str(last)

    return bundle


def _build_portfolio(
    user_email: str,
    bundles: List[ProjectDataBundle],
) -> PortfolioDataBundle:
    """Aggregate project bundles into a portfolio bundle."""
    portfolio = PortfolioDataBundle(
        user_email=user_email,
        projects=bundles,
        total_projects=len(bundles),
    )

    portfolio.total_commits = sum(p.user_total_commits or 0 for p in bundles)

    # Languages (sorted by frequency)
    lang_counter: dict[str, int] = {}
    for p in bundles:
        for lang in p.languages:
            lang_counter[lang] = lang_counter.get(lang, 0) + 1
    portfolio.languages_used = sorted(lang_counter, key=lambda x: -lang_counter[x])

    # Frameworks (deduplicated)
    fw_seen: set[str] = set()
    for p in bundles:
        fw_seen.update(p.frameworks)
    portfolio.frameworks_used = sorted(fw_seen)

    # Date range
    firsts = [p.first_commit for p in bundles if p.first_commit]
    lasts = [p.last_commit for p in bundles if p.last_commit]
    if firsts:
        portfolio.earliest_commit = min(firsts)
    if lasts:
        portfolio.latest_commit = max(lasts)

    # Project type distribution
    for p in bundles:
        portfolio.project_types[p.project_type] = (
            portfolio.project_types.get(p.project_type, 0) + 1
        )

    # Skills (sorted by frequency)
    skill_counter: dict[str, int] = {}
    for p in bundles:
        for skill in p.detected_skills:
            skill_counter[skill] = skill_counter.get(skill, 0) + 1
    portfolio.top_skills = sorted(skill_counter, key=lambda x: -skill_counter[x])

    return portfolio


# ---------------------------------------------------------------------------
# Phase 2 + 3: QUERY + ASSEMBLE
# ---------------------------------------------------------------------------


def generate_resume_v3(
    zip_path: str,
    user_email: str,
    *,
    llm_model: str = "qwen2.5-coder-3b-q4",
    progress_callback: Optional[Callable[[str], None]] = None,
) -> ResumeOutput:
    """
    Main v3 pipeline entry point.

    Args:
        zip_path: Path to ZIP file containing git repositories
        user_email: User's git email for attribution
        llm_model: GGUF model name (default: qwen2.5-coder-3b-q4)
        progress_callback: Optional callback for progress messages

    Returns:
        ResumeOutput with all sections populated
    """
    start_time = datetime.now()
    errors: list[str] = []

    def prog(msg: str) -> None:
        if progress_callback:
            progress_callback(msg)
        log.info(msg)

    # Ensure model is available
    from .llm_client import ensure_model_available
    prog(f"Ensuring model '{llm_model}' is available...")
    ensure_model_available(llm_model)

    # ── PHASE 1: EXTRACT ──────────────────────────────────────────────
    prog(f"Extracting {zip_path}...")
    extract_dir = extract_zip(zip_path)
    prog(f"Extracted to {extract_dir}")

    repos = discover_git_repos(extract_dir)
    if not repos:
        raise RuntimeError("No git repositories found in ZIP")
    prog(f"Found {len(repos)} repositories")

    bundles: List[ProjectDataBundle] = []
    for i, repo_path in enumerate(repos):
        prog(f"Analyzing [{i+1}/{len(repos)}]: {repo_path.name}")
        try:
            bundle = _extract_project(
                repo_path,
                user_email,
                llm_model=llm_model,
                progress=prog,
            )
            bundles.append(bundle)

            # Report extraction results
            n_commits = sum(g.count for g in bundle.commit_groups)
            prog(
                f"  Done: {bundle.project_type}, {n_commits} commits, "
                f"{len(bundle.detected_skills)} skills, "
                f"{len(bundle.constructs.routes)} routes"
            )
        except Exception as e:
            error_msg = f"Error analyzing {repo_path.name}: {e}"
            prog(f"  ERROR: {error_msg}")
            errors.append(error_msg)

    if not bundles:
        raise RuntimeError("No repositories could be analyzed")

    portfolio = _build_portfolio(user_email, bundles)
    prog(
        f"Portfolio: {portfolio.total_projects} projects, "
        f"{len(portfolio.top_skills)} skills, "
        f"{len(portfolio.languages_used)} languages"
    )

    # ── PHASE 2: QUERY ────────────────────────────────────────────────
    output = ResumeOutput(
        portfolio_data=portfolio,
        model_used=llm_model,
        errors=errors,
    )

    # Per-project LLM queries
    for bundle in bundles:
        try:
            section = run_project_query(bundle, llm_model, progress=prog)
            output.project_sections[bundle.project_name] = section
        except Exception as e:
            prog(f"  LLM query failed for {bundle.project_name}: {e}")
            errors.append(f"LLM failed for {bundle.project_name}: {e}")

    # Portfolio-level LLM queries
    try:
        summary, skills, profile = run_portfolio_queries(
            portfolio, llm_model, progress=prog
        )
        output.professional_summary = summary
        output.skills_section = skills
        output.developer_profile = profile
    except Exception as e:
        prog(f"Portfolio LLM queries failed: {e}")
        errors.append(f"Portfolio LLM failed: {e}")

    # ── PHASE 3: ASSEMBLE ─────────────────────────────────────────────
    elapsed = (datetime.now() - start_time).total_seconds()
    output.generation_time_seconds = elapsed
    prog(f"Generation complete in {elapsed:.1f}s")

    return output

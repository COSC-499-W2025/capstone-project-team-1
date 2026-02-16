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
    RawProjectFacts,
    ResumeOutput,
    UserFeedback,
)
from .extractors import (
    extract_readme,
    extract_and_classify_commits,
    extract_structure,
    extract_constructs,
    infer_project_type,
    extract_git_stats,
    extract_test_ratio,
    extract_commit_quality,
    extract_cross_module_breadth,
)
from .distill import distill_project_context, distill_portfolio_context
from .queries.runner import (
    run_project_query,
    run_portfolio_queries,
    run_extraction_query,
    run_draft_queries,
    run_polish_query,
)
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

    # --- New Strategy A extractors ---
    if progress:
        progress(f"  Extracting git stats...")
    git_stats = extract_git_stats(str(repo_path), user_email)

    if progress:
        progress(f"  Computing test ratio...")
    test_ratio = extract_test_ratio(str(repo_path), module_groups)

    if progress:
        progress(f"  Scoring commit quality...")
    commit_quality = extract_commit_quality(commit_groups)

    if progress:
        progress(f"  Measuring module breadth...")
    module_breadth = extract_cross_module_breadth(module_groups, directory_overview)

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
        git_stats=git_stats,
        test_ratio=test_ratio,
        commit_quality=commit_quality,
        module_breadth=module_breadth,
    )

    # User-specific stats
    if user_stats:
        bundle.user_contribution_pct = getattr(user_stats, "userStatspercentages", None)
        bundle.user_total_commits = getattr(user_stats, "total_commits", None)
        first = getattr(user_stats, "first_commit", None)
        last = getattr(user_stats, "last_commit", None)
        if first:
            bundle.first_commit = (
                first.isoformat() if hasattr(first, "isoformat") else str(first)
            )
        if last:
            bundle.last_commit = (
                last.isoformat() if hasattr(last, "isoformat") else str(last)
            )

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
        prog(f"Analyzing [{i + 1}/{len(repos)}]: {repo_path.name}")
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

    # ── PHASE 1.5: DISTILL ───────────────────────────────────────────
    prog("Distilling project contexts...")
    for bundle in bundles:
        bundle.distilled_context = distill_project_context(bundle)
        prog(
            f"  Distilled {bundle.project_name}: "
            f"~{bundle.distilled_context.token_estimate} tokens"
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


# ---------------------------------------------------------------------------
# Multi-stage pipeline — stage-by-stage API
# ---------------------------------------------------------------------------


def extract_and_distill(
    zip_path: str,
    user_email: str,
    *,
    llm_model: str = "lfm2-2.6b-q8",
    progress_callback: Optional[Callable[[str], None]] = None,
) -> tuple[List[ProjectDataBundle], PortfolioDataBundle, list[str]]:
    """
    Run EXTRACT + DISTILL phases (deterministic, no LLM inference needed).

    Returns (bundles, portfolio, errors).
    """
    errors: list[str] = []

    def prog(msg: str) -> None:
        if progress_callback:
            progress_callback(msg)
        log.info(msg)

    prog(f"Extracting {zip_path}...")
    extract_dir = extract_zip(zip_path)

    repos = discover_git_repos(extract_dir)
    if not repos:
        raise RuntimeError("No git repositories found in ZIP")
    prog(f"Found {len(repos)} repositories")

    bundles: List[ProjectDataBundle] = []
    for i, repo_path in enumerate(repos):
        prog(f"Analyzing [{i + 1}/{len(repos)}]: {repo_path.name}")
        try:
            bundle = _extract_project(
                repo_path,
                user_email,
                llm_model=llm_model,
                progress=prog,
            )
            bundles.append(bundle)
        except Exception as e:
            error_msg = f"Error analyzing {repo_path.name}: {e}"
            prog(f"  ERROR: {error_msg}")
            errors.append(error_msg)

    if not bundles:
        raise RuntimeError("No repositories could be analyzed")

    portfolio = _build_portfolio(user_email, bundles)
    prog(
        f"Portfolio: {portfolio.total_projects} projects, "
        f"{len(portfolio.top_skills)} skills"
    )

    # Distill contexts
    prog("Distilling project contexts...")
    for bundle in bundles:
        bundle.distilled_context = distill_project_context(bundle)
        prog(
            f"  Distilled {bundle.project_name}: "
            f"~{bundle.distilled_context.token_estimate} tokens"
        )

    return bundles, portfolio, errors


# ---------------------------------------------------------------------------
# Multi-stage pipeline — monolithic entry point (kept for non-interactive use)
# ---------------------------------------------------------------------------


def generate_resume_v3_multistage(
    zip_path: str,
    user_email: str,
    *,
    stage1_model: str = "lfm2-2.6b-q8",
    stage2_model: str = "qwen3-1.7b-q8",
    stage3_model: str = "qwen3-1.7b-q8",
    user_feedback: Optional[UserFeedback] = None,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> ResumeOutput:
    """
    Multi-stage pipeline entry point.

    Stage 1: LFM2-2.6B extracts structured facts per project (with distilled context)
    Stage 2: Qwen3-1.7B generates a first-draft resume
    Stage 3: Qwen3-1.7B (or custom) polishes with user feedback (skipped if no feedback)

    Model switching uses _restart_server() (~4-6s per switch on M2).

    Args:
        zip_path: Path to ZIP file containing git repositories
        user_email: User's git email for attribution
        stage1_model: Model for fact extraction (default: lfm2-2.6b-q8)
        stage2_model: Model for draft generation (default: qwen3-1.7b-q8)
        stage3_model: Model for polish/refinement (default: qwen3-1.7b-q8)
        user_feedback: Optional feedback to apply in Stage 3
        progress_callback: Optional callback for progress messages

    Returns:
        ResumeOutput with all sections populated
    """
    start_time = datetime.now()
    errors: list[str] = []
    models_used: list[str] = []
    quality_metrics: dict[str, dict] = {
        "schema": {
            "stage1_total": 0,
            "stage1_json": 0,
            "stage1_text_fallback": 0,
            "stage2_json": 0,
            "stage2_text_fallback": 0,
            "stage3_json": 0,
            "stage3_text_fallback": 0,
        },
        "citations": {},
    }

    def merge_quality_metrics(source: dict) -> None:
        for key, value in source.items():
            if isinstance(value, dict):
                target = quality_metrics.setdefault(key, {})
                if isinstance(target, dict):
                    target.update(value)
            else:
                quality_metrics[key] = value

    def prog(msg: str) -> None:
        if progress_callback:
            progress_callback(msg)
        log.info(msg)

    # Ensure all stage models are available
    from .llm_client import ensure_model_available

    for model_name in [stage1_model, stage2_model, stage3_model]:
        prog(f"Checking model '{model_name}'...")
        ensure_model_available(model_name)

    # ── PHASE 1: EXTRACT + DISTILL ───────────────────────────────────
    prog(f"Extracting {zip_path}...")
    extract_dir = extract_zip(zip_path)
    prog(f"Extracted to {extract_dir}")

    repos = discover_git_repos(extract_dir)
    if not repos:
        raise RuntimeError("No git repositories found in ZIP")
    prog(f"Found {len(repos)} repositories")

    bundles: List[ProjectDataBundle] = []
    for i, repo_path in enumerate(repos):
        prog(f"Analyzing [{i + 1}/{len(repos)}]: {repo_path.name}")
        try:
            bundle = _extract_project(
                repo_path,
                user_email,
                llm_model=stage1_model,
                progress=prog,
            )
            bundles.append(bundle)
        except Exception as e:
            error_msg = f"Error analyzing {repo_path.name}: {e}"
            prog(f"  ERROR: {error_msg}")
            errors.append(error_msg)

    if not bundles:
        raise RuntimeError("No repositories could be analyzed")

    portfolio = _build_portfolio(user_email, bundles)
    prog(
        f"Portfolio: {portfolio.total_projects} projects, "
        f"{len(portfolio.top_skills)} skills"
    )

    # Distill contexts
    prog("Distilling project contexts...")
    for bundle in bundles:
        bundle.distilled_context = distill_project_context(bundle)
        prog(
            f"  Distilled {bundle.project_name}: "
            f"~{bundle.distilled_context.token_estimate} tokens"
        )

    # ── STAGE 1: EXTRACTION (structured facts) ───────────────────────
    prog(f"Stage 1: Extracting facts with {stage1_model}...")
    models_used.append(stage1_model)
    raw_facts: dict[str, RawProjectFacts] = {}

    for bundle in bundles:
        quality_metrics["schema"]["stage1_total"] += 1
        try:
            facts = run_extraction_query(bundle, stage1_model, progress=prog)
            raw_facts[bundle.project_name] = facts
            if facts.source_format == "json":
                quality_metrics["schema"]["stage1_json"] += 1
            else:
                quality_metrics["schema"]["stage1_text_fallback"] += 1
            prog(f"  Extracted {bundle.project_name}: {len(facts.facts)} facts")
        except Exception as e:
            prog(f"  Extraction failed for {bundle.project_name}: {e}")
            errors.append(f"Stage 1 failed for {bundle.project_name}: {e}")

    if not raw_facts:
        raise RuntimeError("Stage 1 extraction produced no results")

    # ── STAGE 2: DRAFT (Qwen3-1.7B) ─────────────────────────────────
    prog(f"Stage 2: Generating draft with {stage2_model}...")
    models_used.append(stage2_model)

    try:
        draft_output = run_draft_queries(
            raw_facts, portfolio, stage2_model, progress=prog
        )
        merge_quality_metrics(draft_output.quality_metrics)
        schema = quality_metrics.get("schema", {})
        schema["stage2_json"] = int(schema.get("draft_json", 0))
        schema["stage2_text_fallback"] = int(schema.get("draft_text_fallback", 0))
        prog(
            f"  Draft generated: {len(draft_output.project_sections)} projects, "
            f"summary={'yes' if draft_output.professional_summary else 'no'}"
        )
    except Exception as e:
        prog(f"Stage 2 draft failed: {e}")
        errors.append(f"Stage 2 draft failed: {e}")
        # Build a minimal output from extracted facts
        draft_output = ResumeOutput(
            stage="draft",
            portfolio_data=portfolio,
            raw_project_facts=raw_facts,
            errors=errors,
        )
        quality_metrics["schema"]["stage2_text_fallback"] = 1

    # ── STAGE 3: POLISH (feedback-guided refinement) ────────────────
    if user_feedback is not None:
        prog(f"Stage 3: Polishing with {stage3_model}...")
        models_used.append(stage3_model)

        try:
            final_output = run_polish_query(
                draft_output, user_feedback, stage3_model, progress=prog
            )
            merge_quality_metrics(final_output.quality_metrics)
            schema = quality_metrics.get("schema", {})
            schema["stage3_json"] = int(schema.get("polish_json", 0))
            schema["stage3_text_fallback"] = int(schema.get("polish_text_fallback", 0))
            prog("  Polish complete")
        except Exception as e:
            prog(f"Stage 3 polish failed, using draft: {e}")
            errors.append(f"Stage 3 polish failed: {e}")
            final_output = draft_output
            final_output.stage = "polish"
            quality_metrics["schema"]["stage3_text_fallback"] = 1
    else:
        prog("Stage 3: Skipped (no user feedback provided)")
        final_output = draft_output

    # ── FINALIZE ─────────────────────────────────────────────────────
    elapsed = (datetime.now() - start_time).total_seconds()
    final_output.generation_time_seconds = elapsed
    final_output.model_used = stage2_model  # primary model
    final_output.models_used = models_used
    final_output.portfolio_data = portfolio
    final_output.raw_project_facts = raw_facts
    final_output.errors = errors
    final_output.quality_metrics = quality_metrics

    prog(
        f"Multi-stage generation complete in {elapsed:.1f}s "
        f"(models: {', '.join(models_used)})"
    )

    return final_output

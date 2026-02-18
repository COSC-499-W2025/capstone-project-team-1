"""
Resume Pipeline Orchestrator.

Multi-stage pipeline:
  Phase 1: EXTRACT + DISTILL — static data gathering + token-budgeted compression
  Stage 1: Fact extraction (Qwen2.5-Coder-3B) — structured facts per project
  Stage 2: Draft generation (LFM2.5-1.2B) — first-draft resume
  Stage 3: Polish (LFM2.5-1.2B) — refine with user feedback
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Optional

from .models import (
    ChurnComplexityHotspot,
    GitStats,
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
    extract_enriched_constructs,
    extract_import_graph,
    extract_config_fingerprint,
    extract_llm_project_understanding,
)
from .queries.runner import (
    compile_project_data_card,
    run_draft_queries_v2,
    run_polish_query_v2,
)

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
# Churn-complexity cross-reference helper
# ---------------------------------------------------------------------------


def _compute_churn_complexity(
    git_stats: GitStats,
    file_complexity: list,
) -> list[ChurnComplexityHotspot]:
    """Cross-reference file hotspots with complexity metrics.

    Returns the top 5 files ranked by combined edit_frequency × complexity,
    normalized to a 0-1 risk score.
    """
    if not git_stats.file_hotspots or not file_complexity:
        return []

    # Index complexity by filepath
    complexity_map: dict[str, tuple[int, int]] = {}
    for fc in file_complexity:
        complexity_map[fc.filepath] = (fc.cyclomatic_complexity, fc.max_nesting_depth)

    candidates: list[tuple[str, int, int, int, float]] = []
    for filepath, edit_count in git_stats.file_hotspots:
        if filepath in complexity_map:
            cc, depth = complexity_map[filepath]
            raw_score = edit_count * cc
            candidates.append((filepath, edit_count, cc, depth, raw_score))

    if not candidates:
        return []

    # Normalize scores to 0-1
    max_score = max(c[4] for c in candidates)
    if max_score == 0:
        max_score = 1.0

    candidates.sort(key=lambda c: c[4], reverse=True)

    return [
        ChurnComplexityHotspot(
            filepath=filepath,
            edit_count=edit_count,
            cyclomatic_complexity=cc,
            max_nesting_depth=depth,
            risk_score=round(raw_score / max_score, 3),
        )
        for filepath, edit_count, cc, depth, raw_score in candidates[:5]
    ]


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

    # --- Compute primary_lang early (needed by analysis modules) ---
    primary_lang = repo_stats.primary_language
    if primary_lang:
        primary_lang = extension_to_language(primary_lang) or primary_lang.lstrip(".")

    # --- Phase 1: Analysis modules ---
    style_metrics = None
    try:
        from ..resume.analysis.developer_style import compute_style_metrics

        if progress:
            progress(f"  Computing style metrics...")
        style_metrics = compute_style_metrics(str(repo_path), user_email, primary_lang)
    except Exception:
        pass

    file_complexity: list = []
    try:
        from ..resume.analysis.complexity_narrative import compute_complexity_metrics

        if progress:
            progress(f"  Computing complexity metrics...")
        file_complexity = compute_complexity_metrics(str(repo_path), user_email)
    except Exception:
        pass

    skill_appearances: list = []
    try:
        from ..resume.analysis.skill_timeline import compute_skill_first_appearances

        if progress:
            progress(f"  Computing skill timeline...")
        skill_appearances = compute_skill_first_appearances(
            str(repo_path), user_email, facts.detected_skills
        )
    except Exception:
        pass

    # --- Phase 2: Enriched constructs ---
    enriched_constructs = None
    try:
        if progress:
            progress(f"  Extracting enriched constructs...")
        enriched_constructs = extract_enriched_constructs(
            str(repo_path), touched_files or None
        )
    except Exception:
        pass

    # --- Phase 3: Import graph, config fingerprint ---
    import_graph = None
    try:
        if progress:
            progress(f"  Analyzing import graph...")
        import_graph = extract_import_graph(str(repo_path), touched_files or None)
    except Exception:
        pass

    config_fingerprint = None
    try:
        infra_signals = getattr(deep_result, "infra_signals", None)
        if progress:
            progress(f"  Extracting config fingerprint...")
        config_fingerprint = extract_config_fingerprint(
            str(repo_path), infra_signals=infra_signals
        )
    except Exception:
        pass

    # --- Phase 4: LLM semantic understanding over raw code snippets ---
    llm_understanding = None
    if llm_model:
        try:
            if progress:
                progress("  Inferring project purpose with LLM...")

            route_context = []
            if enriched_constructs and enriched_constructs.routes:
                route_context = enriched_constructs.routes
            elif constructs.routes:
                route_context = constructs.routes

            llm_understanding = extract_llm_project_understanding(
                str(repo_path),
                model=llm_model,
                project_name=repo_stats.project_name,
                project_type=project_type,
                primary_language=primary_lang,
                frameworks=repo_stats.frameworks or [],
                readme_text=readme_text,
                commit_groups=commit_groups,
                module_groups=module_groups,
                routes=route_context,
            )
        except Exception:
            # Graceful degradation: keep deterministic path if LLM reasoning fails.
            llm_understanding = None

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

    # --- Churn-complexity cross-reference (Phase 3) ---
    churn_complexity_hotspots = _compute_churn_complexity(git_stats, file_complexity)

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
        style_metrics=style_metrics,
        file_complexity=file_complexity,
        skill_appearances=skill_appearances,
        enriched_constructs=enriched_constructs,
        import_graph=import_graph,
        config_fingerprint=config_fingerprint,
        churn_complexity_hotspots=churn_complexity_hotspots,
        llm_understanding=llm_understanding,
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
# Shared EXTRACT + DISTILL phase
# ---------------------------------------------------------------------------


def extract_and_distill(
    zip_path: str,
    user_email: str,
    *,
    llm_model: str = "qwen2.5-coder-3b-q4",
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

    # Skip distillation - give raw context to LLM for better output quality
    # Removing distillation allows the LLM to see more context

    return bundles, portfolio, errors


# ---------------------------------------------------------------------------
# Multi-stage pipeline — programmatic entry point
# ---------------------------------------------------------------------------


def generate_resume_v3_multistage(
    zip_path: str,
    user_email: str,
    *,
    stage1_model: str = "qwen2.5-coder-3b-q4",
    stage2_model: str = "lfm2.5-1.2b-bf16",
    stage3_model: str = "lfm2.5-1.2b-bf16",
    user_feedback: Optional[UserFeedback] = None,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> ResumeOutput:
    """
    Multi-stage pipeline entry point.

    Stage 1: Qwen2.5-Coder-3B extracts structured facts per project (with distilled context)
    Stage 2: LFM2.5-1.2B generates a first-draft resume
    Stage 3: LFM2.5-1.2B (or custom) polishes with user feedback (skipped if no feedback)

    Model switching uses _restart_server() (~4-6s per switch on M2).

    Args:
        zip_path: Path to ZIP file containing git repositories
        user_email: User's git email for attribution
        stage1_model: Model for fact extraction (default: qwen2.5-coder-3b-q4)
        stage2_model: Model for draft generation (default: lfm2.5-1.2b-bf16)
        stage3_model: Model for polish/refinement (default: lfm2.5-1.2b-bf16)
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
        "prose": {},
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

    # Skip distillation - give raw context to LLM for better output quality
    # Removing distillation allows the LLM to see more context

    # ── STAGE 1: DATA CARD COMPILATION (deterministic) ────────────────
    prog("Stage 1: Compiling data cards (deterministic)...")
    raw_facts: dict[str, RawProjectFacts] = {}

    for bundle in bundles:
        quality_metrics["schema"]["stage1_total"] += 1
        try:
            facts = compile_project_data_card(bundle, progress=prog)
            raw_facts[bundle.project_name] = facts
            quality_metrics["schema"]["stage1_json"] += 1
            prog(f"  Compiled {bundle.project_name}: {len(facts.facts)} facts")
        except Exception as e:
            prog(f"  Compilation failed for {bundle.project_name}: {e}")
            errors.append(f"Stage 1 failed for {bundle.project_name}: {e}")

    if not raw_facts:
        raise RuntimeError("Stage 1 extraction produced no results")

    # ── STAGE 2: DRAFT (Qwen3-1.7B) ─────────────────────────────────
    prog(f"Stage 2: Generating draft with {stage2_model}...")
    models_used.append(stage2_model)

    try:
        draft_output = run_draft_queries_v2(
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
            final_output = run_polish_query_v2(
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

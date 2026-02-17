"""
Distillation stage — compress extracted data into token-budgeted context.

Sits between EXTRACT and QUERY. Takes a ProjectDataBundle and produces
a DistilledContext — a ranked, deduplicated text block ready for the LLM.

Token budget target: 2-3K tokens per project, ~2K per portfolio.
"""

from __future__ import annotations

import re
from typing import Dict, List, Set

from .models import (
    DistilledContext,
    ProjectDataBundle,
    PortfolioDataBundle,
    CommitGroup,
)


# ---------------------------------------------------------------------------
# Token estimation (rough: 1 token ~ 4 chars for English text)
# ---------------------------------------------------------------------------

_CHARS_PER_TOKEN = 4


def _estimate_tokens(text: str) -> int:
    """Rough token count estimate."""
    return len(text) // _CHARS_PER_TOKEN


def _truncate_to_tokens(text: str, max_tokens: int) -> str:
    """Truncate text to approximately max_tokens at a sentence boundary."""
    max_chars = max_tokens * _CHARS_PER_TOKEN
    if len(text) <= max_chars:
        return text

    # Try to cut at sentence boundary
    truncated = text[:max_chars]
    for sep in (". ", ".\n", "! ", "? "):
        last = truncated.rfind(sep)
        if last > max_chars // 2:
            return truncated[: last + 1]

    return truncated.rstrip()


# ---------------------------------------------------------------------------
# Commit deduplication
# ---------------------------------------------------------------------------

_TICKET_RE = re.compile(r"\b[A-Z]+-\d+\b")
_CONVENTIONAL_PREFIX_RE = re.compile(r"^[a-z]+(?:\([^)]*\))?[!]?:\s*", re.I)


def _normalize_message(msg: str) -> str:
    """Normalize a commit message for deduplication comparison."""
    msg = msg.lower().strip()
    msg = _CONVENTIONAL_PREFIX_RE.sub("", msg)
    msg = _TICKET_RE.sub("", msg)
    return msg.strip()


def _jaccard_similarity(a: str, b: str) -> float:
    """Word-level Jaccard similarity between two strings."""
    words_a = set(a.split())
    words_b = set(b.split())
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)


def _deduplicate_messages(messages: List[str], threshold: float = 0.6) -> List[str]:
    """
    Cluster near-duplicate messages and keep the best representative.

    Uses word-level Jaccard similarity. Keeps the longest (most specific)
    message per cluster.
    """
    if not messages:
        return []

    normalized = [_normalize_message(m) for m in messages]
    clusters: List[List[int]] = []
    assigned: Set[int] = set()

    for i in range(len(messages)):
        if i in assigned:
            continue
        cluster = [i]
        assigned.add(i)
        for j in range(i + 1, len(messages)):
            if j in assigned:
                continue
            if _jaccard_similarity(normalized[i], normalized[j]) >= threshold:
                cluster.append(j)
                assigned.add(j)
        clusters.append(cluster)

    # Pick best representative per cluster (longest original message)
    result: List[str] = []
    for cluster in clusters:
        best_idx = max(cluster, key=lambda idx: len(messages[idx]))
        result.append(messages[best_idx])

    return result


# ---------------------------------------------------------------------------
# Signal ranking weights (for commit category ordering)
# ---------------------------------------------------------------------------

_COMMIT_CATEGORY_PRIORITY = {
    "feature": 0,
    "bugfix": 1,
    "refactor": 2,
    "test": 3,
    "docs": 4,
    "chore": 5,
}


def _rank_commit_groups(groups: List[CommitGroup]) -> List[CommitGroup]:
    """Sort commit groups by resume relevance."""
    return sorted(
        groups,
        key=lambda g: _COMMIT_CATEGORY_PRIORITY.get(g.category, 99),
    )


# ---------------------------------------------------------------------------
# Project-level distillation
# ---------------------------------------------------------------------------


def distill_project_context(
    bundle: ProjectDataBundle,
    token_budget: int = 3500,
) -> DistilledContext:
    """
    Distill a ProjectDataBundle into a token-budgeted context block.

    Section priority (highest resume-signal first, trimmed from back):
      1. Identity + stack: ~200 tokens
      2. Quantitative impact: ~400 tokens (incl. churn-complexity hotspots)
      3. Architecture signal: ~400 tokens (from import_graph)
      4. Code style profile: ~300 tokens (from style_metrics + file_complexity)
      5. Enriched constructs: ~600 tokens (replaces basic constructs)
      6. Cherry-picked commits: ~600 tokens (reduced from 800)
      7. Skill timeline: ~200 tokens (from skill_appearances)
      8. README excerpt: ~400 tokens (expanded from 300)
      9. Config/infra: ~200 tokens (from config_fingerprint)
     10. File hotspots: ~200 tokens (trim buffer)

    Sections 1-5 are protected during back-trimming.
    """
    sections: List[str] = []

    # ── 1. Identity block (~200 tokens) ─────────────────────────────
    identity_lines = [f"PROJECT: {bundle.project_name}"]
    parts = []
    parts.append(f"Type: {bundle.project_type}")
    if bundle.languages:
        lang_str = ", ".join(
            f"{lang} ({pct:.0f}%)"
            for lang, pct in zip(bundle.languages[:4], bundle.language_percentages[:4])
        )
        parts.append(f"Stack: {lang_str}")
    if bundle.user_contribution_pct is not None:
        parts.append(f"Contribution: {bundle.user_contribution_pct:.0f}%")
    identity_lines.append(" | ".join(parts))
    if bundle.frameworks:
        identity_lines.append(f"Frameworks: {', '.join(bundle.frameworks)}")
    sections.append("\n".join(identity_lines))

    # ── 2. Quantitative impact (~400 tokens) ────────────────────────
    gs = bundle.git_stats
    tr = bundle.test_ratio
    mb = bundle.module_breadth
    impact_lines = ["IMPACT:"]
    if gs.lines_added > 0:
        impact_lines.append(
            f"- Added {gs.lines_added:,} lines, deleted {gs.lines_deleted:,} lines "
            f"across {gs.files_touched} files over {gs.active_days} active days"
        )
    if gs.active_span_days > 0:
        impact_lines.append(
            f"- Active span: {gs.active_span_days} days, "
            f"avg commit size: {gs.avg_commit_size:.0f} lines"
        )
    if mb.modules_touched > 0:
        impact_lines.append(
            f"- Touched {mb.modules_touched}/{mb.total_modules} modules "
            f"({mb.breadth_pct:.0f}% breadth)"
        )
    if tr.source_files > 0:
        ci_note = " (CI configured)" if tr.has_ci else ""
        impact_lines.append(
            f"- Test ratio: {tr.test_files} test / {tr.source_files} source "
            f"files ({tr.test_ratio:.2f}){ci_note}"
        )
    cq = bundle.commit_quality
    if cq.conventional_pct > 0:
        impact_lines.append(
            f"- Commit quality: {cq.conventional_pct:.0f}% conventional, "
            f"{cq.type_diversity} categories, "
            f"avg {cq.avg_message_length:.0f} chars/message"
        )
    # Churn-complexity hotspots
    if bundle.churn_complexity_hotspots:
        impact_lines.append("- Churn-complexity hotspots:")
        for hs in bundle.churn_complexity_hotspots[:3]:
            impact_lines.append(
                f"  {hs.filepath} (edits={hs.edit_count}, "
                f"complexity={hs.cyclomatic_complexity}, risk={hs.risk_score:.2f})"
            )
    if len(impact_lines) > 1:
        sections.append("\n".join(impact_lines))

    # ── 3. Architecture signal (~400 tokens) ────────────────────────
    ig = bundle.import_graph
    if ig is not None:
        arch_lines = ["ARCHITECTURE:"]
        if ig.layer_detection:
            arch_lines.append(f"- Layers: {' → '.join(ig.layer_detection)}")
        if ig.external_deps:
            arch_lines.append(f"- External deps: {', '.join(ig.external_deps[:12])}")
        if ig.circular_deps:
            arch_lines.append(f"- Circular deps: {len(ig.circular_deps)} detected")
        if ig.imports_map:
            arch_lines.append(f"- Internal modules: {len(ig.imports_map)}")
        if len(arch_lines) > 1:
            sections.append("\n".join(arch_lines))

    # ── 4. Code style profile (~300 tokens) ─────────────────────────
    sm = bundle.style_metrics
    if sm is not None:
        style_lines = ["CODE STYLE:"]
        style_lines.append(
            f"- Avg function length: {sm.avg_function_length:.1f} lines "
            f"({sm.total_functions} functions)"
        )
        style_lines.append(f"- Naming: {sm.naming_convention}")
        style_lines.append(f"- Type annotations: {sm.type_annotation_ratio:.0%}")
        style_lines.append(f"- Docstring coverage: {sm.docstring_coverage:.0%}")
        style_lines.append(
            f"- Comment density: {sm.comment_density:.1f} per 100 lines"
        )
        sections.append("\n".join(style_lines))

    # ── 5. Enriched constructs (~600 tokens) ────────────────────────
    ec = bundle.enriched_constructs
    if ec is not None and (ec.classes or ec.functions or ec.routes):
        construct_lines = ["CODE CONSTRUCTS:"]
        if ec.routes:
            construct_lines.append(f"- Routes: {', '.join(ec.routes[:10])}")
        for cls in ec.classes[:8]:
            parent_str = f" extends {cls.parent_class}" if cls.parent_class else ""
            construct_lines.append(
                f"- Class {cls.name}: {cls.method_count} methods, "
                f"{cls.total_loc} LOC{parent_str}"
            )
        for fn in ec.functions[:8]:
            ret_str = " (typed)" if fn.has_return_type else ""
            construct_lines.append(
                f"- Fn {fn.name}({fn.param_count} params, {fn.loc} LOC){ret_str}"
            )
        if ec.test_functions:
            construct_lines.append(
                f"- Tests: {len(ec.test_functions)} test functions"
            )
        sections.append("\n".join(construct_lines))
    else:
        # Fallback to basic constructs
        c = bundle.constructs
        construct_lines = ["CODE CONSTRUCTS:"]
        if c.routes:
            construct_lines.append(f"- Routes: {', '.join(c.routes[:10])}")
        if c.classes:
            construct_lines.append(f"- Classes: {', '.join(c.classes[:10])}")
        if c.key_functions:
            construct_lines.append(
                f"- Key functions: {', '.join(c.key_functions[:10])}"
            )
        if c.test_functions:
            construct_lines.append(
                f"- Tests: {len(c.test_functions)} test functions"
            )
        if len(construct_lines) > 1:
            sections.append("\n".join(construct_lines))

    # ── 6. Cherry-picked commits (~600 tokens) ──────────────────────
    ranked_groups = _rank_commit_groups(bundle.commit_groups)
    commit_lines = ["KEY WORK (from commits):"]
    commit_token_budget = 600
    commit_chars = 0
    max_commit_chars = commit_token_budget * _CHARS_PER_TOKEN

    for group in ranked_groups:
        if commit_chars >= max_commit_chars:
            break
        deduped = _deduplicate_messages(group.messages)
        for msg in deduped:
            if commit_chars >= max_commit_chars:
                break
            line = f"- [{group.category}] {msg}"
            commit_lines.append(line)
            commit_chars += len(line)

    if len(commit_lines) > 1:
        sections.append("\n".join(commit_lines))

    # ── 7. Skill timeline (~200 tokens) ─────────────────────────────
    if bundle.skill_appearances:
        timeline_lines = ["SKILL TIMELINE:"]
        for sa in bundle.skill_appearances[:8]:
            date_str = sa.first_date[:10] if sa.first_date else "unknown"
            timeline_lines.append(f"- {sa.skill_name}: first seen {date_str}")
        sections.append("\n".join(timeline_lines))

    # ── 8. README excerpt (~400 tokens) ─────────────────────────────
    if bundle.readme_text:
        excerpt = _truncate_to_tokens(bundle.readme_text, 400)
        sections.append(f"README SUMMARY:\n{excerpt}")

    # ── 9. Config/infra (~200 tokens) ───────────────────────────────
    cfp = bundle.config_fingerprint
    if cfp is not None:
        config_lines = ["TOOLCHAIN:"]
        if cfp.linters:
            config_lines.append(f"- Linters: {', '.join(cfp.linters)}")
        if cfp.formatters:
            config_lines.append(f"- Formatters: {', '.join(cfp.formatters)}")
        if cfp.test_frameworks:
            config_lines.append(
                f"- Test frameworks: {', '.join(cfp.test_frameworks)}"
            )
        if cfp.build_tools:
            config_lines.append(f"- Build tools: {', '.join(cfp.build_tools)}")
        if cfp.deployment_tools:
            config_lines.append(
                f"- Deployment: {', '.join(cfp.deployment_tools)}"
            )
        if cfp.package_managers:
            config_lines.append(
                f"- Package managers: {', '.join(cfp.package_managers)}"
            )
        if cfp.pre_commit_hooks:
            config_lines.append(
                f"- Pre-commit hooks: {', '.join(cfp.pre_commit_hooks[:6])}"
            )
        if len(config_lines) > 1:
            sections.append("\n".join(config_lines))

    # ── 10. File hotspots (~200 tokens) ─────────────────────────────
    if gs.file_hotspots:
        hotspot_lines = ["FILE HOTSPOTS:"]
        for fname, count in gs.file_hotspots[:5]:
            hotspot_lines.append(f"- {fname} ({count} edits)")
        sections.append("\n".join(hotspot_lines))

    # ── Assemble and enforce budget ─────────────────────────────────
    # Protected sections: first 5 (identity, impact, architecture, style, constructs)
    min_protected = 5
    full_text = "\n\n".join(sections)
    estimated = _estimate_tokens(full_text)

    # Back-trim from section 10 → 9 → 8 → 7 → 6, preserving 1-5
    if estimated > token_budget and len(sections) > min_protected:
        while (
            _estimate_tokens("\n\n".join(sections)) > token_budget
            and len(sections) > min_protected
        ):
            sections.pop()
        full_text = "\n\n".join(sections)
        estimated = _estimate_tokens(full_text)

    return DistilledContext(text=full_text, token_estimate=estimated)


# ---------------------------------------------------------------------------
# Portfolio-level distillation
# ---------------------------------------------------------------------------


def distill_portfolio_context(
    portfolio: PortfolioDataBundle,
    token_budget: int = 2000,
) -> DistilledContext:
    """
    Distill a PortfolioDataBundle into a token-budgeted context block.

    Provides a cross-project summary for portfolio-level LLM queries.
    """
    sections: List[str] = []

    # ── Overview ────────────────────────────────────────────────────
    overview_lines = [
        f"PORTFOLIO OVERVIEW ({portfolio.total_projects} projects):",
        f"- Total commits: {portfolio.total_commits}",
        f"- Languages: {', '.join(portfolio.languages_used[:8])}",
    ]
    if portfolio.frameworks_used:
        overview_lines.append(f"- Frameworks: {', '.join(portfolio.frameworks_used[:8])}")
    if portfolio.earliest_commit and portfolio.latest_commit:
        overview_lines.append(
            f"- Active period: {portfolio.earliest_commit[:10]} to {portfolio.latest_commit[:10]}"
        )
    if portfolio.project_types:
        type_parts = [f"{t} ({c})" for t, c in portfolio.project_types.items()]
        overview_lines.append(f"- Project types: {', '.join(type_parts)}")
    if portfolio.top_skills:
        overview_lines.append(f"- Top skills: {', '.join(portfolio.top_skills[:10])}")
    sections.append("\n".join(overview_lines))

    # ── Per-project summaries ───────────────────────────────────────
    per_project_budget = (
        (token_budget - 300) // len(portfolio.projects)
        if portfolio.projects
        else 0
    )
    per_project_budget = max(per_project_budget, 150)

    for bundle in portfolio.projects:
        proj_lines = [f"PROJECT: {bundle.project_name}"]
        parts = [f"Type: {bundle.project_type}"]
        if bundle.languages:
            parts.append(f"Stack: {', '.join(bundle.languages[:3])}")
        if bundle.user_contribution_pct is not None:
            parts.append(f"Contribution: {bundle.user_contribution_pct:.0f}%")
        proj_lines.append(" | ".join(parts))

        # Key metrics
        gs = bundle.git_stats
        if gs.lines_added > 0:
            proj_lines.append(
                f"- {gs.lines_added:,} lines added across {gs.files_touched} files"
            )

        # Top commit types
        type_counts = bundle.commit_count_by_type()
        if type_counts:
            top_types = sorted(type_counts.items(), key=lambda x: -x[1])[:3]
            proj_lines.append(
                "- Commits: " + ", ".join(f"{c} {t}" for t, c in top_types)
            )

        proj_text = "\n".join(proj_lines)
        proj_text = _truncate_to_tokens(proj_text, per_project_budget)
        sections.append(proj_text)

    # ── Assemble and enforce budget ─────────────────────────────────
    full_text = "\n\n".join(sections)
    estimated = _estimate_tokens(full_text)

    # Trim last project summaries if over budget
    while estimated > token_budget and len(sections) > 1:
        sections.pop()
        full_text = "\n\n".join(sections)
        estimated = _estimate_tokens(full_text)

    return DistilledContext(text=full_text, token_estimate=estimated)

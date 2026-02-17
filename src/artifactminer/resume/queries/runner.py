"""
LLM query runner — executes prompts and parses structured responses.

Handles:
  - Calling query_llm_text with the right system prompt
  - Parsing DESCRIPTION/BULLETS/NARRATIVE output format
  - Progress reporting via callback
"""

from __future__ import annotations

import logging
import re
from typing import Callable, Optional

from ..models import (
    EvidenceLinkedFact,
    ProjectDataBundle,
    PortfolioDataBundle,
    ProjectSection,
    RawProjectFacts,
    ResumeOutput,
    UserFeedback,
)
from .prompts import (
    PROJECT_SYSTEM,
    SUMMARY_SYSTEM,
    EXTRACTION_SYSTEM,
    DRAFT_SYSTEM,
    POLISH_SYSTEM,
    BULLET_SYSTEM,
    MICRO_POLISH_SYSTEM,
    build_project_prompt,
    build_summary_prompt,
    build_skills_prompt,
    build_profile_prompt,
    build_extraction_prompt,
    build_extraction_evidence_catalog,
    build_draft_prompt,
    build_polish_prompt,
    build_bullets_prompt,
    build_micro_summary_prompt,
    build_micro_profile_prompt,
    build_bullet_polish_prompt,
    build_text_polish_prompt,
)
from .schemas import Stage1ExtractionResponse, StageDraftResponse

log = logging.getLogger(__name__)


_SECTION_HEADER_LINE_RE = re.compile(
    r"^\s*(?:[#>\-]+\s*)?(?:\*\*)?\s*"
    r"(DESCRIPTION|BULLETS|NARRATIVE)\s*"
    r"(?:\*\*)?\s*:\s*(?:\*\*)?\s*(.*)$",
    re.I,
)

_BULLET_LINE_RE = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+(.+)$")

_SKILLS_HEADER_RE = re.compile(
    r"^\s*(?:[-*•]\s*)?"
    r"(Languages|Frameworks\s*&\s*Libraries|Frameworks|"
    r"Tools\s*&\s*Infrastructure|Infrastructure|Practices)"
    r"\s*:\s*(.*)$",
    re.I,
)

_COMMON_LANGUAGES = {
    "python",
    "javascript",
    "typescript",
    "java",
    "go",
    "rust",
    "c",
    "c++",
    "c#",
    "kotlin",
    "swift",
    "php",
    "ruby",
    "scala",
    "r",
    "dart",
    "tf",
}

_TOOL_KEYWORDS = {
    "terraform",
    "docker",
    "kubernetes",
    "helm",
    "aws",
    "gcp",
    "azure",
    "ansible",
    "jenkins",
    "github actions",
    "gitlab ci",
    "linux",
    "bash",
    "shell",
    "prometheus",
    "grafana",
    "nginx",
    "vpc",
    "s3",
    "ec2",
    "lambda",
    "cloudformation",
    "ci/cd",
    "ci cd",
}


# ---------------------------------------------------------------------------
# Capitalization map for deterministic skill normalization
# ---------------------------------------------------------------------------

_CAPITALIZATION_MAP: dict[str, str] = {
    "html": "HTML",
    "css": "CSS",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "python": "Python",
    "java": "Java",
    "c++": "C++",
    "c#": "C#",
    "sql": "SQL",
    "nosql": "NoSQL",
    "mongodb": "MongoDB",
    "postgresql": "PostgreSQL",
    "mysql": "MySQL",
    "graphql": "GraphQL",
    "rest": "REST",
    "api": "API",
    "aws": "AWS",
    "gcp": "GCP",
    "azure": "Azure",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "react": "React",
    "vue": "Vue",
    "angular": "Angular",
    "fastapi": "FastAPI",
    "flask": "Flask",
    "django": "Django",
    "express": "Express",
    "nodejs": "Node.js",
    "node.js": "Node.js",
    "git": "Git",
    "ci/cd": "CI/CD",
    "github actions": "GitHub Actions",
    "gitlab ci": "GitLab CI",
    "terraform": "Terraform",
    "nginx": "Nginx",
    "redis": "Redis",
    "kafka": "Kafka",
    "rabbitmq": "RabbitMQ",
    "pytest": "pytest",
    "junit": "JUnit",
    "jest": "Jest",
    "webpack": "webpack",
    "vite": "Vite",
    "sqlalchemy": "SQLAlchemy",
    "pandas": "pandas",
    "numpy": "NumPy",
    "pytorch": "PyTorch",
    "tensorflow": "TensorFlow",
    "linux": "Linux",
    "bash": "Bash",
    "go": "Go",
    "rust": "Rust",
    "ruby": "Ruby",
    "swift": "Swift",
    "kotlin": "Kotlin",
    "php": "PHP",
    "r": "R",
    "dart": "Dart",
    "scala": "Scala",
    "tf": "Terraform",
}


# ---------------------------------------------------------------------------
# Evidence artifact cleanup (Step 2)
# ---------------------------------------------------------------------------

_EVIDENCE_ARTIFACT_RE = re.compile(
    r"commit:(?:feature|feat|bugfix|fix|refactor|test|docs|chore):"
    r"|\(E\d+\)"
    r"|\[(?:feature|bugfix|fix|refactor|test|docs|chore)\]"
    r"|\|\s*evidence:\s*[EF]\d+(?:,\s*[EF]\d+)*",
    re.I,
)

# Matches conventional commit prefixes at start of line
_CONVENTIONAL_PREFIX_RE = re.compile(
    r"^(?:feat|fix|refactor|test|docs|chore|style|perf|ci|build)"
    r"(?:\([^)]*\))?:\s*",
    re.I,
)

# Matches conventional commit prefixes appearing mid-text (e.g. "via feat: add ...")
_CONVENTIONAL_MIDTEXT_RE = re.compile(
    r"\b(?:feat|fix|refactor|test|docs|chore|style|perf|ci|build)"
    r"(?:\([^)]*\))?:\s+",
    re.I,
)

# Qwen3 thinking tag leakage
_THINK_TAG_RE = re.compile(r"</?think>", re.I)

# Emoji garbage runs (3+ consecutive emoji/variation-selector/ZWJ chars)
_EMOJI_GARBAGE_RE = re.compile(
    r"[\U0001F300-\U0001FAFF\u2600-\u27BF\u200D\uFE0F\u2705\u274C]{3,}",
)


def _clean_evidence_artifacts(text: str) -> str:
    """Strip evidence markers and conventional commit prefixes from text."""
    if not text:
        return ""
    cleaned = _EVIDENCE_ARTIFACT_RE.sub("", text)
    cleaned = _CONVENTIONAL_PREFIX_RE.sub("", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _clean_llm_artifacts(text: str) -> str:
    """Strip LLM generation artifacts: think tags, emoji garbage, mid-text commit prefixes."""
    if not text:
        return ""
    cleaned = _THINK_TAG_RE.sub("", text)
    cleaned = _EMOJI_GARBAGE_RE.sub("", cleaned)
    cleaned = _CONVENTIONAL_MIDTEXT_RE.sub("", cleaned)
    cleaned = _EVIDENCE_ARTIFACT_RE.sub("", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _clean_all_facts(
    raw_facts: dict[str, RawProjectFacts],
) -> dict[str, RawProjectFacts]:
    """Apply artifact cleanup to all Stage 1 facts in-place."""
    for facts in raw_facts.values():
        facts.summary = _clean_evidence_artifacts(facts.summary)
        facts.role = _clean_evidence_artifacts(facts.role)
        facts.facts = [
            _clean_evidence_artifacts(f)
            for f in facts.facts
            if _clean_evidence_artifacts(f)
        ]
        for item in facts.fact_items:
            item.text = _clean_evidence_artifacts(item.text)
    return raw_facts


# ---------------------------------------------------------------------------
# Deterministic data card compilation (replaces Stage 1 LLM)
# ---------------------------------------------------------------------------


def _find_evidence_key(
    catalog: dict[str, str], prefix: str
) -> str | None:
    """Find the first evidence catalog entry whose value starts with *prefix*."""
    for key, value in catalog.items():
        if value.startswith(prefix):
            return key
    return None


def _build_data_card_context(bundle: ProjectDataBundle) -> str:
    """Build a ~400-600 token structured text block from a ProjectDataBundle.

    This context block is injected into the Stage 2 bullet prompt so the LLM
    has rich quantitative data alongside the cherry-picked facts.
    """
    lines: list[str] = []

    # --- Identity ---
    lines.append(f"Type: {bundle.project_type}")
    if bundle.primary_language:
        lines.append(f"Language: {bundle.primary_language}")
    if bundle.frameworks:
        lines.append(f"Frameworks: {', '.join(bundle.frameworks[:6])}")
    if bundle.user_contribution_pct is not None:
        lines.append(f"Contribution: {bundle.user_contribution_pct:.0f}%")

    # --- Impact metrics ---
    gs = bundle.git_stats
    if gs.lines_added:
        lines.append(
            f"Impact: {gs.lines_added:,} lines added, "
            f"{gs.files_touched} files, "
            f"{gs.active_days} active days"
        )
    tr = bundle.test_ratio
    if tr.test_files > 0:
        lines.append(
            f"Testing: {tr.test_files} test files / {tr.source_files} source "
            f"({tr.test_ratio:.0%} ratio)"
            + (", CI configured" if tr.has_ci else "")
        )
    cq = bundle.commit_quality
    if cq.type_diversity > 0:
        lines.append(
            f"Commit quality: {cq.conventional_pct:.0f}% conventional, "
            f"{cq.type_diversity} types, "
            f"longest streak {cq.longest_streak}"
        )
    mb = bundle.module_breadth
    if mb.modules_touched > 0:
        lines.append(
            f"Module breadth: {mb.modules_touched}/{mb.total_modules} modules "
            f"({mb.breadth_pct:.0f}%)"
        )

    # --- Key constructs ---
    ec = bundle.enriched_constructs
    if ec:
        for cls in ec.classes[:4]:
            lines.append(
                f"Class {cls.name}: {cls.method_count} methods, {cls.total_loc} LOC"
                + (f" (extends {cls.parent_class})" if cls.parent_class else "")
            )
        if ec.routes:
            lines.append(f"Routes: {len(ec.routes)} endpoints")
        if ec.test_functions:
            lines.append(f"Tests: {len(ec.test_functions)} test functions")

    # --- Architecture ---
    ig = bundle.import_graph
    if ig:
        if ig.layer_detection:
            lines.append(f"Layers: {', '.join(ig.layer_detection)}")
        if ig.external_deps:
            lines.append(f"Dependencies: {', '.join(ig.external_deps[:6])}")

    # --- Style ---
    sm = bundle.style_metrics
    if sm is not None:
        parts: list[str] = []
        if hasattr(sm, "naming_convention") and sm.naming_convention:
            parts.append(sm.naming_convention)
        if hasattr(sm, "type_annotation_ratio") and sm.type_annotation_ratio:
            parts.append(f"{sm.type_annotation_ratio:.0%} typed")
        if hasattr(sm, "docstring_coverage") and sm.docstring_coverage:
            parts.append(f"{sm.docstring_coverage:.0%} docstring coverage")
        if parts:
            lines.append(f"Style: {', '.join(parts)}")

    # --- Churn-complexity hotspots ---
    for hs in bundle.churn_complexity_hotspots[:2]:
        lines.append(
            f"Hotspot: {hs.filepath} "
            f"(edits={hs.edit_count}, complexity={hs.cyclomatic_complexity})"
        )

    return "\n".join(lines)


def compile_project_data_card(
    bundle: ProjectDataBundle,
    *,
    max_facts: int = 5,
    progress: Optional[Callable[[str], None]] = None,
) -> RawProjectFacts:
    """Deterministic Stage 1 replacement: compile a data card from a bundle.

    Builds summary, role, and cherry-picked facts entirely from static data —
    no LLM call required.  Returns a ``RawProjectFacts`` with
    ``source_format="data_card"``.
    """
    if progress:
        progress(f"  [Stage 1] Compiling data card for {bundle.project_name}...")

    evidence_catalog = build_extraction_evidence_catalog(bundle)

    # --- Summary: first sentence of README, fallback to project type ---
    summary = ""
    if bundle.readme_text:
        # Take the first sentence (up to first period followed by space or end)
        first_sentence = bundle.readme_text.strip().split("\n")[0].strip()
        # Strip markdown heading markers
        first_sentence = first_sentence.lstrip("#").strip()
        if first_sentence:
            # Truncate at first sentence boundary if long
            dot_pos = first_sentence.find(". ")
            if dot_pos > 0 and dot_pos < 200:
                first_sentence = first_sentence[: dot_pos + 1]
            elif len(first_sentence) > 200:
                first_sentence = first_sentence[:200].rsplit(" ", 1)[0] + "..."
            summary = _clean_inline_text(first_sentence)
    if not summary:
        lang_part = f" {bundle.primary_language}" if bundle.primary_language else ""
        summary = f"A {bundle.project_type.lower()}{lang_part} project."

    # --- Role: deterministic from contribution % + git stats ---
    role = ""
    pct = bundle.user_contribution_pct
    gs = bundle.git_stats
    lines_added = gs.lines_added
    files = gs.files_touched
    active_days = gs.active_days

    if pct is not None and pct >= 95:
        role = (
            f"Sole developer, adding {lines_added:,} lines "
            f"across {files} files over {active_days} active days."
        )
    elif pct is not None and pct >= 50:
        role = (
            f"Led development ({pct:.0f}% of codebase), "
            f"adding {lines_added:,} lines across {files} files."
        )
    elif pct is not None:
        role = (
            f"Contributed {pct:.0f}% of the codebase, "
            f"adding {lines_added:,} lines across {files} files "
            f"over {active_days} active days."
        )
    elif lines_added > 0:
        role = (
            f"Added {lines_added:,} lines across {files} files "
            f"over {active_days} active days."
        )

    # --- Facts: cherry-pick from commits, constructs, tests ---
    fact_items: list[EvidenceLinkedFact] = []
    fact_texts: list[str] = []
    fact_idx = 1

    # 1. Top feature/bugfix/refactor commits (deduped)
    ordered_categories = ["feature", "bugfix", "refactor"]
    by_category = {g.category: g.messages for g in bundle.commit_groups}
    commit_pool: list[tuple[str, str]] = []  # (category, message)
    for category in ordered_categories:
        for msg in by_category.get(category, [])[:6]:
            commit_pool.append((category, msg))

    all_commit_msgs = [msg for _, msg in commit_pool]
    deduped_msgs = ProjectDataBundle._dedup_commit_messages(all_commit_msgs)
    deduped_set = set(deduped_msgs)

    for category, msg in commit_pool:
        if len(fact_items) >= max_facts:
            break
        if msg not in deduped_set:
            continue
        deduped_set.discard(msg)  # consume it so we don't repeat

        cleaned = _clean_evidence_artifacts(msg)
        if not cleaned:
            continue

        evidence_key = _find_evidence_key(
            evidence_catalog, f"commit:{category}:"
        )
        evidence_keys = [evidence_key] if evidence_key else []

        fact_id = f"F{fact_idx}"
        fact_items.append(
            EvidenceLinkedFact(
                fact_id=fact_id,
                text=cleaned,
                evidence_keys=evidence_keys,
            )
        )
        fact_texts.append(cleaned)
        fact_idx += 1

    # 2. Construct-derived facts (routes count, key classes)
    ec = bundle.enriched_constructs
    if ec and len(fact_items) < max_facts:
        if ec.routes and len(ec.routes) >= 2:
            route_text = f"Defined {len(ec.routes)} API endpoints"
            evidence_key = _find_evidence_key(evidence_catalog, "route:")
            fact_items.append(
                EvidenceLinkedFact(
                    fact_id=f"F{fact_idx}",
                    text=route_text,
                    evidence_keys=[evidence_key] if evidence_key else [],
                )
            )
            fact_texts.append(route_text)
            fact_idx += 1

        for cls in ec.classes[:2]:
            if len(fact_items) >= max_facts:
                break
            cls_text = (
                f"Implemented {cls.name} class "
                f"({cls.method_count} methods, {cls.total_loc} LOC)"
            )
            evidence_key = _find_evidence_key(evidence_catalog, f"class:{cls.name}")
            fact_items.append(
                EvidenceLinkedFact(
                    fact_id=f"F{fact_idx}",
                    text=cls_text,
                    evidence_keys=[evidence_key] if evidence_key else [],
                )
            )
            fact_texts.append(cls_text)
            fact_idx += 1

    # 3. Test coverage fact
    tr = bundle.test_ratio
    if tr.test_files > 0 and len(fact_items) < max_facts:
        test_text = (
            f"Maintained {tr.test_files} test files "
            f"({tr.test_ratio:.0%} test-to-source ratio)"
        )
        evidence_key = _find_evidence_key(evidence_catalog, "test_framework:")
        fact_items.append(
            EvidenceLinkedFact(
                fact_id=f"F{fact_idx}",
                text=test_text,
                evidence_keys=[evidence_key] if evidence_key else [],
            )
        )
        fact_texts.append(test_text)
        fact_idx += 1

    return RawProjectFacts(
        project_name=bundle.project_name,
        summary=summary,
        facts=fact_texts,
        fact_items=fact_items,
        evidence_catalog=evidence_catalog,
        role=role,
        source_format="data_card",
    )


# ---------------------------------------------------------------------------
# Deterministic skills builder (Step 3)
# ---------------------------------------------------------------------------


def _capitalize_skill(name: str) -> str:
    """Apply proper capitalization to a skill name."""
    return _CAPITALIZATION_MAP.get(name.lower().strip(), name)


def _build_skills_deterministic(portfolio: PortfolioDataBundle) -> str:
    """Build skills section deterministically from portfolio data (no LLM)."""
    categories: dict[str, list[str]] = {
        "languages": [],
        "frameworks": [],
        "tools": [],
        "practices": [],
    }

    for lang in portfolio.languages_used[:8]:
        categories["languages"].append(_capitalize_skill(lang))

    for fw in portfolio.frameworks_used[:10]:
        capitalized = _capitalize_skill(fw)
        if _looks_like_tool(fw):
            categories["tools"].append(capitalized)
        else:
            categories["frameworks"].append(capitalized)

    language_tokens = {_normalize_token(n) for n in categories["languages"]}
    framework_tokens = {_normalize_token(n) for n in categories["frameworks"]}
    tool_tokens = {_normalize_token(n) for n in categories["tools"]}

    for skill in portfolio.top_skills[:15]:
        capitalized = _capitalize_skill(skill)
        token = _normalize_token(capitalized)
        if token in language_tokens or token in framework_tokens or token in tool_tokens:
            continue
        if _normalize_token(skill) in _COMMON_LANGUAGES:
            categories["languages"].append(capitalized)
        elif _looks_like_tool(skill):
            categories["tools"].append(capitalized)
        else:
            categories["practices"].append(capitalized)

    seen: set[str] = set()
    deduped: dict[str, list[str]] = {k: [] for k in categories}
    for cat in ["languages", "frameworks", "tools", "practices"]:
        for item in categories[cat]:
            key = item.casefold()
            if key in seen:
                continue
            seen.add(key)
            deduped[cat].append(item)

    lines: list[str] = []
    if deduped["languages"]:
        lines.append(f"Languages: {', '.join(deduped['languages'])}")
    if deduped["frameworks"]:
        lines.append(f"Frameworks & Libraries: {', '.join(deduped['frameworks'])}")
    if deduped["tools"]:
        lines.append(f"Tools & Infrastructure: {', '.join(deduped['tools'])}")
    if deduped["practices"]:
        lines.append(f"Practices: {', '.join(deduped['practices'])}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Deterministic descriptions + narratives (Step 4)
# ---------------------------------------------------------------------------


def _build_descriptions_deterministic(
    raw_facts: dict[str, RawProjectFacts],
    portfolio: Optional[PortfolioDataBundle] = None,
) -> dict[str, tuple[str, str]]:
    """Build descriptions and narratives from Stage 1 data without LLM.

    Returns ``{project_name: (description, narrative)}``.
    """
    bundle_map: dict[str, ProjectDataBundle] = {}
    if portfolio:
        for b in portfolio.projects:
            bundle_map[b.project_name] = b

    result: dict[str, tuple[str, str]] = {}
    for project_name, facts in raw_facts.items():
        description = _clean_evidence_artifacts(facts.summary) if facts.summary else ""

        bundle = bundle_map.get(project_name)
        narrative = ""
        if bundle:
            pct = bundle.user_contribution_pct
            gs = bundle.git_stats
            lines_added = gs.lines_added
            files = gs.files_touched
            active_days = gs.active_days

            if pct is not None and pct >= 95:
                narrative = (
                    f"Sole developer, adding {lines_added:,} lines "
                    f"across {files} files over {active_days} active days."
                )
            elif pct is not None and pct >= 50:
                narrative = (
                    f"Led development ({pct:.0f}% of codebase), "
                    f"adding {lines_added:,} lines across {files} files."
                )
            elif pct is not None:
                narrative = (
                    f"Contributed {pct:.0f}% of the codebase, "
                    f"adding {lines_added:,} lines across {files} files "
                    f"over {active_days} active days."
                )
            elif lines_added > 0:
                narrative = (
                    f"Added {lines_added:,} lines across {files} files "
                    f"over {active_days} active days."
                )

        if not narrative:
            narrative = _clean_evidence_artifacts(facts.role) if facts.role else ""

        result[project_name] = (description, narrative)

    return result


def _query(
    prompt: str,
    model: str,
    system: str,
    *,
    temperature: float | None = None,
    max_tokens: int = 1024,
    top_p: float | None = None,
    repetition_penalty: float | None = None,
    grammar: str | None = None,
) -> str:
    """Execute a single LLM query with per-model sampling defaults."""
    from ..llm_client import get_sampling_params, query_llm_text

    # Merge per-model defaults with explicit overrides
    sampling = get_sampling_params(model)
    effective_temp = (
        temperature if temperature is not None else sampling.get("temperature", 0.2)
    )
    effective_top_p = top_p if top_p is not None else sampling.get("top_p")
    effective_rep_pen = (
        repetition_penalty
        if repetition_penalty is not None
        else sampling.get("repetition_penalty")
    )

    return query_llm_text(
        prompt=prompt,
        model=model,
        system=system,
        temperature=effective_temp,
        max_tokens=max_tokens,
        top_p=effective_top_p,
        repetition_penalty=effective_rep_pen,
        grammar=grammar,
    )


def _query_structured(
    prompt: str,
    model: str,
    system: str,
    schema: type,
    *,
    temperature: float = 0.1,
) -> object:
    """Execute a structured JSON query using constrained decoding."""
    from ..llm_client import query_llm

    return query_llm(
        prompt=prompt,
        schema=schema,
        model=model,
        system=system,
        temperature=temperature,
    )


def _should_use_structured_json(model: str) -> bool:
    """Gate structured JSON mode by local model availability."""
    from ..llm_client import check_llm_available

    return check_llm_available(model)


def _normalize_fact_id(raw: str, fallback_index: int) -> str:
    """Normalize fact ids to F<N> shape."""
    text = (raw or "").strip().upper()
    digits = "".join(ch for ch in text if ch.isdigit())
    if digits:
        return f"F{int(digits)}"
    return f"F{fallback_index}"


def _format_skills_from_structured(skills: object) -> str:
    """Render structured skills payload into stable text categories."""
    if not hasattr(skills, "languages"):
        return ""

    lines: list[str] = []
    languages = getattr(skills, "languages", []) or []
    frameworks = getattr(skills, "frameworks_libraries", []) or []
    tools = getattr(skills, "tools_infrastructure", []) or []
    practices = getattr(skills, "practices", []) or []

    if languages:
        lines.append(f"Languages: {', '.join(languages)}")
    if frameworks:
        lines.append(f"Frameworks & Libraries: {', '.join(frameworks)}")
    if tools:
        lines.append(f"Tools & Infrastructure: {', '.join(tools)}")
    if practices:
        lines.append(f"Practices: {', '.join(practices)}")

    return "\n".join(lines)


def _fact_pool_by_project(
    raw_facts: dict[str, RawProjectFacts],
) -> dict[str, dict[str, str]]:
    """Build {project -> {fact_id -> fact_text}} with backwards compatibility."""
    pool: dict[str, dict[str, str]] = {}
    for project_name, facts in raw_facts.items():
        fact_map: dict[str, str] = {}
        if facts.fact_items:
            for idx, item in enumerate(facts.fact_items, start=1):
                fid = _normalize_fact_id(item.fact_id, idx)
                text = _clean_inline_text(item.text)
                if text:
                    fact_map[fid] = text
        if not fact_map and facts.facts:
            for idx, text in enumerate(facts.facts, start=1):
                cleaned = _clean_inline_text(text)
                if cleaned:
                    fact_map[f"F{idx}"] = cleaned
        pool[project_name] = fact_map
    return pool


def _fact_to_repair_bullet(fact_text: str) -> str:
    """Convert a short fact into a conservative resume bullet sentence."""
    cleaned = _clean_inline_text(fact_text)
    if not cleaned:
        return ""
    if cleaned[-1] in ".!?":
        return cleaned
    return f"{cleaned}."


def _synthesize_sections_from_raw_facts(
    raw_facts: dict[str, RawProjectFacts],
) -> dict[str, ProjectSection]:
    """Create minimal project sections from Stage-1 facts when generation is sparse."""
    sections: dict[str, ProjectSection] = {}
    for project_name, fact_map in _fact_pool_by_project(raw_facts).items():
        if not fact_map:
            continue
        fact_ids = list(fact_map.keys())
        bullets = [_fact_to_repair_bullet(fact_map[fid]) for fid in fact_ids[:3]]
        bullet_fact_ids = [[fid] for fid in fact_ids[:3]]

        source = raw_facts.get(project_name)
        description = _clean_inline_text(source.summary if source else "")
        if not description:
            description = _clean_inline_text(bullets[0])
        narrative = _clean_inline_text(source.role if source else "")

        sections[project_name] = ProjectSection(
            description=description,
            bullets=bullets,
            bullet_fact_ids=bullet_fact_ids,
            narrative=narrative,
        )

    return sections


def _apply_citation_gate(
    output: ResumeOutput,
    raw_facts: dict[str, RawProjectFacts],
) -> dict[str, float | int]:
    """Validate bullet citations and auto-repair unsupported bullets."""
    fact_pool = _fact_pool_by_project(raw_facts)

    total_bullets = 0
    valid_bullets = 0
    repaired_bullets = 0
    unresolved_bullets = 0

    all_fact_ids: set[tuple[str, str]] = set()
    cited_fact_ids: set[tuple[str, str]] = set()

    for project_name, facts in fact_pool.items():
        for fact_id in facts:
            all_fact_ids.add((project_name, fact_id))

    for project_name, section in output.project_sections.items():
        facts = fact_pool.get(project_name, {})
        available_fact_ids = list(facts.keys())
        used_fact_ids: set[str] = set()

        bullet_ids = list(section.bullet_fact_ids or [])
        while len(bullet_ids) < len(section.bullets):
            bullet_ids.append([])

        repaired_texts: list[str] = []
        repaired_ids: list[list[str]] = []

        for idx, bullet in enumerate(section.bullets):
            total_bullets += 1
            raw_ids = bullet_ids[idx]
            normalized_ids = [
                _normalize_fact_id(fid, i + 1)
                for i, fid in enumerate(raw_ids)
                if str(fid).strip()
            ]
            valid_ids = [fid for fid in normalized_ids if fid in facts]

            if valid_ids:
                valid_bullets += 1
                repaired_texts.append(_clean_inline_text(bullet))
                repaired_ids.append(valid_ids)
                for fid in valid_ids:
                    used_fact_ids.add(fid)
                    cited_fact_ids.add((project_name, fid))
                continue

            # Hybrid repair strategy:
            # 1) Prefer an unused fact, 2) otherwise reuse the first available.
            chosen_fact_id: str | None = None
            for fid in available_fact_ids:
                if fid not in used_fact_ids:
                    chosen_fact_id = fid
                    break
            if chosen_fact_id is None and available_fact_ids:
                chosen_fact_id = available_fact_ids[0]

            if chosen_fact_id:
                repaired_texts.append(_fact_to_repair_bullet(facts[chosen_fact_id]))
                repaired_ids.append([chosen_fact_id])
                valid_bullets += 1
                repaired_bullets += 1
                used_fact_ids.add(chosen_fact_id)
                cited_fact_ids.add((project_name, chosen_fact_id))
            else:
                repaired_texts.append(_clean_inline_text(bullet))
                repaired_ids.append([])
                unresolved_bullets += 1

        # If project has no bullets, synthesize up to 3 from facts.
        if not repaired_texts and available_fact_ids:
            for fid in available_fact_ids[:3]:
                total_bullets += 1
                valid_bullets += 1
                repaired_bullets += 1
                repaired_texts.append(_fact_to_repair_bullet(facts[fid]))
                repaired_ids.append([fid])
                cited_fact_ids.add((project_name, fid))

        section.bullets = [text for text in repaired_texts if text]
        section.bullet_fact_ids = repaired_ids[: len(section.bullets)]

    citation_precision = (valid_bullets / total_bullets) if total_bullets else 0.0
    fact_coverage = len(cited_fact_ids) / len(all_fact_ids) if all_fact_ids else 0.0

    return {
        "total_bullets": total_bullets,
        "valid_bullets": valid_bullets,
        "repaired_bullets": repaired_bullets,
        "unresolved_bullets": unresolved_bullets,
        "citation_precision": round(citation_precision, 4),
        "fact_coverage": round(fact_coverage, 4),
    }


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------


def _parse_project_response(text: str) -> ProjectSection:
    """
    Parse the structured DESCRIPTION/BULLETS/NARRATIVE response.

    Falls back gracefully if the model doesn't follow the format exactly.
    """
    section = ProjectSection()

    if not text or not text.strip():
        return section

    raw_lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    parsed_sections = {"description": [], "bullets": [], "narrative": []}

    current_key: str | None = None
    found_structured_markers = False
    for raw_line in raw_lines:
        line = raw_line.rstrip()
        marker = _SECTION_HEADER_LINE_RE.match(line)
        if marker:
            found_structured_markers = True
            current_key = marker.group(1).lower()
            tail = marker.group(2).strip()
            if tail and current_key in parsed_sections:
                key = str(current_key)
                parsed_sections[key].append(tail)
            continue
        if current_key in parsed_sections:
            key = str(current_key)
            parsed_sections[key].append(line)

    if found_structured_markers:
        section.description = _clean_text_block(
            parsed_sections["description"],
            drop_bullets=True,
        )
        section.bullets = _extract_bullets(parsed_sections["bullets"])
        section.narrative = _clean_text_block(
            parsed_sections["narrative"],
            drop_bullets=True,
        )

    # Fallback: extract bullets from the whole response
    if not section.bullets:
        section.bullets = _extract_bullets(raw_lines)

    # Fallback: derive description from non-bullet lines
    if not section.description:
        non_bullet_lines = [
            line
            for line in raw_lines
            if not _BULLET_LINE_RE.match(line.strip())
            and not _SECTION_HEADER_LINE_RE.match(line.strip())
        ]
        section.description = _clean_text_block(non_bullet_lines, drop_bullets=True)

    # Last resort: use a trimmed version of the response
    if not section.bullets and not section.description:
        section.description = _clean_text_block([text])[:500]

    return section


def _clean_text_block(lines: list[str], *, drop_bullets: bool = False) -> str:
    """Normalize a generated text block by stripping markdown noise."""
    cleaned: list[str] = []

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            if cleaned and cleaned[-1] != "":
                cleaned.append("")
            continue

        line = re.sub(r"^>\s*", "", line)

        if _SECTION_HEADER_LINE_RE.match(line):
            continue
        if drop_bullets and _BULLET_LINE_RE.match(line):
            continue
        if re.fullmatch(r"[\s*_`#>\-]+", line):
            continue

        line = _clean_inline_text(line)
        if line:
            cleaned.append(line)

    text = "\n".join(cleaned).strip()
    return re.sub(r"\n{3,}", "\n\n", text)


def _clean_inline_text(text: str) -> str:
    """Normalize markdown-heavy inline text to plain resume prose."""
    value = text.strip()
    value = value.replace("**", "")
    value = value.replace("__", "")
    value = value.replace("`", "")
    value = re.sub(r"\s+", " ", value).strip()
    value = re.sub(r"\s+([,.;:!?])", r"\1", value)
    return value.strip(" -*")


def _extract_bullets(lines: list[str]) -> list[str]:
    """Extract and deduplicate bullet lines from model output."""
    bullets: list[str] = []
    seen: set[str] = set()

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        match = _BULLET_LINE_RE.match(line)
        if not match:
            continue

        bullet = _clean_inline_text(match.group(1))
        if not bullet:
            continue
        if _SECTION_HEADER_LINE_RE.match(bullet):
            continue
        if re.match(r"^(DESCRIPTION|BULLETS|NARRATIVE)\s*:", bullet, re.I):
            continue

        key = bullet.casefold()
        if key in seen:
            continue
        seen.add(key)
        bullets.append(bullet)

    return bullets


def _clean_summary_or_profile(text: str) -> str:
    """Strip optional section labels and LLM artifacts from summary/profile responses."""
    # Strip think tags and emoji garbage first
    text = _THINK_TAG_RE.sub("", text) if text else ""
    text = _EMOJI_GARBAGE_RE.sub("", text)
    cleaned = _clean_text_block(text.splitlines())
    cleaned = re.sub(
        r"^(SUMMARY|PROFILE|DEVELOPER PROFILE)\s*:\s*", "", cleaned, flags=re.I
    )
    return cleaned.strip()


def _normalize_skills_section(raw: str, portfolio: PortfolioDataBundle) -> str:
    """Parse, clean, and normalize the skills section into stable categories."""
    categories: dict[str, list[str]] = {
        "languages": [],
        "frameworks": [],
        "tools": [],
        "practices": [],
    }

    current_category: str | None = None
    for raw_line in raw.splitlines():
        line = raw_line.strip()
        if not line:
            current_category = None
            continue

        header = _SKILLS_HEADER_RE.match(line)
        if header:
            current_category = _normalize_category_name(header.group(1))
            if current_category in categories:
                categories[current_category].extend(_split_skills(header.group(2)))
            continue

        if current_category in categories and (
            line.startswith(("-", "*", "•")) or "," in line
        ):
            categories[current_category].extend(_split_skills(line))

    # Fill gaps with deterministic portfolio data
    if not categories["languages"]:
        categories["languages"].extend(portfolio.languages_used[:8])
    if not categories["frameworks"]:
        categories["frameworks"].extend(portfolio.frameworks_used[:10])
    if not categories["practices"]:
        categories["practices"].extend(portfolio.top_skills[:15])

    if not categories["tools"]:
        tool_candidates = portfolio.frameworks_used + portfolio.top_skills
        categories["tools"].extend(
            item for item in tool_candidates if _looks_like_tool(item)
        )

    language_tokens = {
        _normalize_token(name)
        for name in (_COMMON_LANGUAGES | set(portfolio.languages_used))
    }

    # Ensure languages are only listed under Languages
    for cat in ("frameworks", "tools", "practices"):
        keep: list[str] = []
        for item in categories[cat]:
            cleaned = _clean_inline_text(item)
            if not cleaned:
                continue
            if _normalize_token(cleaned) in language_tokens:
                categories["languages"].append(cleaned)
            else:
                keep.append(cleaned)
        categories[cat] = keep

    ordered = ["languages", "frameworks", "tools", "practices"]
    deduped: dict[str, list[str]] = {k: [] for k in ordered}
    seen_global: set[str] = set()

    for cat in ordered:
        for item in categories[cat]:
            cleaned = _clean_inline_text(item)
            if not cleaned:
                continue
            key = cleaned.casefold()
            if key in seen_global:
                continue
            seen_global.add(key)
            deduped[cat].append(cleaned)

    lines: list[str] = []
    if deduped["languages"]:
        lines.append(f"Languages: {', '.join(deduped['languages'])}")
    if deduped["frameworks"]:
        lines.append(f"Frameworks & Libraries: {', '.join(deduped['frameworks'])}")
    if deduped["tools"]:
        lines.append(f"Tools & Infrastructure: {', '.join(deduped['tools'])}")
    if deduped["practices"]:
        lines.append(f"Practices: {', '.join(deduped['practices'])}")

    if lines:
        return "\n".join(lines)

    # Last-resort fallback
    return _clean_text_block(raw.splitlines())


def _normalize_category_name(raw: str) -> str:
    """Map category headers to canonical keys."""
    key = raw.strip().casefold()
    if "language" in key:
        return "languages"
    if "framework" in key:
        return "frameworks"
    if "tool" in key or "infrastructure" in key:
        return "tools"
    return "practices"


def _split_skills(raw: str) -> list[str]:
    """Split a skills line into individual items."""
    text = _clean_inline_text(raw)
    if not text:
        return []

    text = re.sub(r"^[-*•]\s*", "", text)
    parts = [segment.strip() for segment in re.split(r"[,;|]", text)]
    items: list[str] = []
    for part in parts:
        cleaned = _clean_inline_text(part)
        if cleaned:
            items.append(cleaned)
    return items


def _normalize_token(text: str) -> str:
    """Normalize an item for case-insensitive matching."""
    return re.sub(r"[^a-z0-9#+]+", "", text.casefold())


def _looks_like_tool(item: str) -> bool:
    """Heuristic for infra/tooling skill names."""
    lowered = item.casefold()
    return any(keyword in lowered for keyword in _TOOL_KEYWORDS)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_project_query(
    bundle: ProjectDataBundle,
    model: str,
    *,
    progress: Optional[Callable[[str], None]] = None,
    use_grammar: bool = True,
) -> ProjectSection:
    """
    Run the LLM query for a single project and return parsed sections.

    When ``use_grammar`` is True (default), uses GBNF grammar-constrained
    decoding to enforce the DESCRIPTION/BULLETS/NARRATIVE format.

    Raises RuntimeError if the LLM returns an empty response.
    """
    from .grammars import PROJECT_SECTION_GRAMMAR

    if progress:
        progress(f"  Querying LLM for {bundle.project_name}...")

    prompt = build_project_prompt(bundle)
    grammar = PROJECT_SECTION_GRAMMAR if use_grammar else None

    response = _query(
        prompt,
        model,
        PROJECT_SYSTEM,
        max_tokens=768,
        grammar=grammar,
    )

    if not response.strip():
        raise RuntimeError(
            f"LLM returned empty response for project {bundle.project_name}"
        )

    return _parse_project_response(response)


def run_portfolio_queries(
    portfolio: PortfolioDataBundle,
    model: str,
    *,
    progress: Optional[Callable[[str], None]] = None,
    use_grammar: bool = True,
) -> tuple[str, str, str]:
    """
    Run the three portfolio-level LLM queries.

    When ``use_grammar`` is True (default), uses GBNF grammar-constrained
    decoding for skills and summary/profile outputs.

    Returns (professional_summary, skills_section, developer_profile).
    """
    from .grammars import SKILLS_SECTION_GRAMMAR, SUMMARY_GRAMMAR

    # 1. Professional summary
    if progress:
        progress("Generating professional summary...")
    summary_prompt = build_summary_prompt(portfolio)
    summary = _clean_summary_or_profile(
        _query(
            summary_prompt,
            model,
            SUMMARY_SYSTEM,
            max_tokens=256,
            grammar=SUMMARY_GRAMMAR if use_grammar else None,
        )
    )

    # 2. Skills section
    if progress:
        progress("Generating skills section...")
    skills_prompt = build_skills_prompt(portfolio)
    raw_skills = _query(
        skills_prompt,
        model,
        SUMMARY_SYSTEM,
        max_tokens=320,
        grammar=SKILLS_SECTION_GRAMMAR if use_grammar else None,
    )
    skills = _normalize_skills_section(raw_skills, portfolio)

    # 3. Developer profile
    if progress:
        progress("Generating developer profile...")
    profile_prompt = build_profile_prompt(portfolio)
    profile = _clean_summary_or_profile(
        _query(
            profile_prompt,
            model,
            SUMMARY_SYSTEM,
            max_tokens=320,
            grammar=SUMMARY_GRAMMAR if use_grammar else None,
        )
    )

    return summary, skills, profile


# ---------------------------------------------------------------------------
# Multi-stage pipeline queries (Strategy B)
# ---------------------------------------------------------------------------

_FACTS_SECTION_RE = re.compile(
    r"^\s*(?:[-*•]|\d+[.)])\s+(.+)$",
)

_EXTRACTION_HEADER_RE = re.compile(
    r"^\s*(PROJECT_SUMMARY|FACTS|ROLE)\s*:\s*(.*)$",
    re.I,
)


def _parse_extraction_response(text: str, project_name: str) -> RawProjectFacts:
    """Parse the structured PROJECT_SUMMARY/FACTS/ROLE response from Stage 1."""
    facts = RawProjectFacts(project_name=project_name)

    if not text or not text.strip():
        return facts

    current_section: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        header = _EXTRACTION_HEADER_RE.match(line)
        if header:
            current_section = header.group(1).upper()
            tail = header.group(2).strip()
            if current_section == "PROJECT_SUMMARY" and tail:
                facts.summary = _clean_inline_text(tail)
            elif current_section == "ROLE" and tail:
                facts.role = _clean_inline_text(tail)
            continue

        if current_section == "FACTS":
            bullet = _FACTS_SECTION_RE.match(line)
            if bullet:
                cleaned = _clean_inline_text(bullet.group(1))
                if cleaned:
                    facts.facts.append(cleaned)
        elif current_section == "PROJECT_SUMMARY" and not facts.summary:
            facts.summary = _clean_inline_text(line)
        elif current_section == "ROLE" and not facts.role:
            facts.role = _clean_inline_text(line)

    return facts


def _parse_draft_response(text: str) -> ResumeOutput:
    """Parse the complete draft resume from Stage 2 into a ResumeOutput."""
    output = ResumeOutput(stage="draft")

    if not text or not text.strip():
        return output

    current_section: str | None = None
    current_project: str | None = None
    project_lines: dict[str, dict[str, list[str]]] = {}

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        # Check for top-level markers
        if line.upper().startswith("PROFESSIONAL_SUMMARY:"):
            current_section = "summary"
            tail = line.split(":", 1)[1].strip()
            if tail:
                output.professional_summary = _clean_inline_text(tail)
            continue

        if line.upper().startswith("DEVELOPER_PROFILE:"):
            current_section = "profile"
            tail = line.split(":", 1)[1].strip()
            if tail:
                output.developer_profile = _clean_inline_text(tail)
            continue

        if line.upper().startswith("SKILLS:"):
            current_section = "skills"
            tail = line.split(":", 1)[1].strip()
            if tail:
                output.skills_section = tail
            continue

        if line.upper().startswith("PROJECT:"):
            current_section = "project"
            current_project = line.split(":", 1)[1].strip()
            project_lines[current_project] = {
                "description": [],
                "bullets": [],
                "narrative": [],
            }
            continue

        # Parse project sub-sections (check for markers in any project_* state)
        if current_project and (
            current_section == "project"
            or (current_section and current_section.startswith("project_"))
        ):
            marker = _SECTION_HEADER_LINE_RE.match(line)
            if marker:
                key = marker.group(1).lower()
                tail = marker.group(2).strip()
                if tail and key in project_lines[current_project]:
                    project_lines[current_project][key].append(tail)
                current_section = f"project_{key}"
                continue

        if current_section == "project_description" and current_project:
            project_lines[current_project]["description"].append(line)
        elif current_section == "project_bullets" and current_project:
            bullet = _BULLET_LINE_RE.match(line)
            if bullet:
                project_lines[current_project]["bullets"].append(
                    _clean_inline_text(bullet.group(1))
                )
        elif current_section == "project_narrative" and current_project:
            project_lines[current_project]["narrative"].append(line)
        elif current_section == "summary" and not output.professional_summary:
            output.professional_summary = _clean_inline_text(line)
        elif current_section == "profile" and not output.developer_profile:
            output.developer_profile = _clean_inline_text(line)
        elif current_section == "skills":
            output.skills_section += "\n" + line

    # Build project sections
    for name, parts in project_lines.items():
        section = ProjectSection(
            description=_clean_inline_text(" ".join(parts["description"])),
            bullets=[b for b in parts["bullets"] if b],
            narrative=_clean_inline_text(" ".join(parts["narrative"])),
        )
        output.project_sections[name] = section

    if output.skills_section:
        output.skills_section = output.skills_section.strip()

    return output


def run_extraction_query(
    bundle: ProjectDataBundle,
    model: str,
    *,
    progress: Optional[Callable[[str], None]] = None,
) -> RawProjectFacts:
    """
    Stage 1: Extract structured facts from a project using LFM2.5-1.2B.

    Returns RawProjectFacts with summary, facts list, and role.
    """
    if progress:
        progress(f"  [Stage 1] Extracting facts for {bundle.project_name}...")

    prompt = build_extraction_prompt(bundle)
    evidence_catalog = build_extraction_evidence_catalog(bundle)

    # Preferred path: strict JSON schema.
    if _should_use_structured_json(model):
        try:
            parsed = _query_structured(
                prompt,
                model,
                EXTRACTION_SYSTEM,
                Stage1ExtractionResponse,
                temperature=0.1,
            )
            if not isinstance(parsed, Stage1ExtractionResponse):
                raise RuntimeError("Structured extraction returned invalid type")

            fact_items: list[EvidenceLinkedFact] = []
            fallback_evidence = (
                [next(iter(evidence_catalog))] if evidence_catalog else []
            )

            for idx, item in enumerate(parsed.facts, start=1):
                fact_text = _clean_inline_text(item.fact)
                if not fact_text:
                    continue
                fact_id = _normalize_fact_id(item.fact_id, idx)
                evidence_keys = [
                    str(key).strip()
                    for key in item.evidence_keys
                    if str(key).strip() in evidence_catalog
                ]
                if not evidence_keys:
                    evidence_keys = fallback_evidence

                fact_items.append(
                    EvidenceLinkedFact(
                        fact_id=fact_id,
                        text=fact_text,
                        evidence_keys=evidence_keys,
                    )
                )

            if not fact_items:
                raise RuntimeError("Structured extraction produced no usable facts")

            output = RawProjectFacts(
                project_name=bundle.project_name,
                summary=_clean_inline_text(parsed.project_summary),
                facts=[item.text for item in fact_items],
                fact_items=fact_items,
                evidence_catalog=evidence_catalog,
                role=_clean_inline_text(parsed.role),
                source_format="json",
            )
            return output
        except Exception as exc:
            log.warning(
                "Structured stage-1 extraction failed for %s (%s). Falling back to text parser.",
                bundle.project_name,
                exc,
            )

    # Fallback path: legacy text parser.
    response = _query(
        prompt,
        model,
        EXTRACTION_SYSTEM,
        max_tokens=512,
    )

    if not response.strip():
        raise RuntimeError(
            f"LLM returned empty response for extraction of {bundle.project_name}"
        )

    parsed_text = _parse_extraction_response(response, bundle.project_name)
    parsed_text.evidence_catalog = evidence_catalog
    parsed_text.source_format = "text"

    fallback_evidence = [next(iter(evidence_catalog))] if evidence_catalog else []
    parsed_text.fact_items = [
        EvidenceLinkedFact(
            fact_id=f"F{idx}",
            text=_clean_inline_text(text),
            evidence_keys=fallback_evidence,
        )
        for idx, text in enumerate(parsed_text.facts, start=1)
        if _clean_inline_text(text)
    ]

    return parsed_text


def run_draft_queries(
    raw_facts: dict[str, RawProjectFacts],
    portfolio: PortfolioDataBundle,
    model: str,
    *,
    progress: Optional[Callable[[str], None]] = None,
) -> ResumeOutput:
    """
    Stage 2: Generate a first-draft resume from extracted facts using Qwen3-1.7B.

    Returns a complete ResumeOutput with stage="draft".
    """
    if progress:
        progress("[Stage 2] Generating draft resume...")

    prompt = build_draft_prompt(raw_facts, portfolio)

    # Preferred path: strict JSON schema.
    if _should_use_structured_json(model):
        try:
            parsed = _query_structured(
                prompt,
                model,
                DRAFT_SYSTEM,
                StageDraftResponse,
                temperature=0.2,
            )
            if not isinstance(parsed, StageDraftResponse):
                raise RuntimeError("Structured draft returned invalid type")

            output = ResumeOutput(stage="draft")
            output.professional_summary = _clean_summary_or_profile(
                parsed.professional_summary
            )
            output.skills_section = _format_skills_from_structured(parsed.skills)
            output.developer_profile = _clean_summary_or_profile(
                parsed.developer_profile
            )

            # Keep project names aligned with Stage-1 keys when possible.
            canonical_names = {name.casefold(): name for name in raw_facts}
            for project in parsed.projects:
                name = project.project_name.strip()
                canonical = canonical_names.get(name.casefold(), name)
                bullets: list[str] = []
                bullet_fact_ids: list[list[str]] = []
                for bullet in project.bullets:
                    text = _clean_inline_text(bullet.text)
                    if not text:
                        continue
                    bullets.append(text)
                    bullet_fact_ids.append(
                        [
                            _normalize_fact_id(fid, i + 1)
                            for i, fid in enumerate(bullet.fact_ids)
                            if str(fid).strip()
                        ]
                    )

                output.project_sections[canonical] = ProjectSection(
                    description=_clean_inline_text(project.description),
                    bullets=bullets,
                    bullet_fact_ids=bullet_fact_ids,
                    narrative=_clean_inline_text(project.narrative),
                )

            output.portfolio_data = portfolio
            output.raw_project_facts = raw_facts
            output.quality_metrics["schema"] = {
                "draft_json": 1,
                "draft_text_fallback": 0,
            }

            if not output.project_sections:
                output.project_sections = _synthesize_sections_from_raw_facts(raw_facts)
            if not output.professional_summary:
                output.professional_summary = (
                    f"Software developer with experience across {portfolio.total_projects} projects "
                    f"using {', '.join(portfolio.languages_used[:3])}."
                )
            if not output.developer_profile:
                output.developer_profile = (
                    "Builds practical systems with a strong implementation focus "
                    "across backend, tooling, and delivery workflows."
                )
            if not output.skills_section:
                output.skills_section = _normalize_skills_section("", portfolio)

            # Citation gate: validate and auto-repair unsupported bullets.
            citation_metrics = _apply_citation_gate(output, raw_facts)
            output.quality_metrics["citations"] = citation_metrics

            if output.skills_section and portfolio:
                output.skills_section = _normalize_skills_section(
                    output.skills_section,
                    portfolio,
                )

            return output
        except Exception as exc:
            log.warning(
                "Structured stage-2 draft failed (%s). Falling back to text parser.",
                exc,
            )

    # Fallback path: legacy text parser.
    response = _query(
        prompt,
        model,
        DRAFT_SYSTEM,
        max_tokens=2048,
    )

    if not response.strip():
        raise RuntimeError("LLM returned empty response for draft generation")

    output = _parse_draft_response(response)
    output.portfolio_data = portfolio
    output.raw_project_facts = raw_facts
    output.quality_metrics["schema"] = {"draft_json": 0, "draft_text_fallback": 1}

    # Fallback: if parsing didn't find project sections, try single-project parsing
    if not output.project_sections:
        section = _parse_project_response(response)
        if section.description or section.bullets:
            for name in raw_facts:
                output.project_sections[name] = section
                break
    if not output.project_sections:
        output.project_sections = _synthesize_sections_from_raw_facts(raw_facts)
    if not output.professional_summary:
        output.professional_summary = (
            f"Software developer with experience across {portfolio.total_projects} projects "
            f"using {', '.join(portfolio.languages_used[:3])}."
        )
    if not output.developer_profile:
        output.developer_profile = (
            "Builds practical systems with a strong implementation focus "
            "across backend, tooling, and delivery workflows."
        )
    if not output.skills_section:
        output.skills_section = _normalize_skills_section("", portfolio)

    # Normalize skills section
    if output.skills_section and portfolio:
        output.skills_section = _normalize_skills_section(
            output.skills_section, portfolio
        )

    citation_metrics = _apply_citation_gate(output, raw_facts)
    output.quality_metrics["citations"] = citation_metrics

    return output


def run_polish_query(
    draft_output: ResumeOutput,
    feedback: UserFeedback,
    model: str,
    *,
    progress: Optional[Callable[[str], None]] = None,
) -> ResumeOutput:
    """
    Stage 3: Polish the draft resume with user feedback using Qwen3-4B.

    Returns the final polished ResumeOutput with stage="polish".
    """
    if progress:
        progress("[Stage 3] Polishing resume with feedback...")

    prompt = build_polish_prompt(draft_output, feedback)
    raw_facts = draft_output.raw_project_facts or {}

    # Preferred path: strict JSON schema.
    if _should_use_structured_json(model):
        try:
            parsed = _query_structured(
                prompt,
                model,
                POLISH_SYSTEM,
                StageDraftResponse,
                temperature=0.2,
            )
            if not isinstance(parsed, StageDraftResponse):
                raise RuntimeError("Structured polish returned invalid type")

            output = ResumeOutput(stage="polish")
            output.professional_summary = _clean_summary_or_profile(
                parsed.professional_summary
            )
            output.skills_section = _format_skills_from_structured(parsed.skills)
            output.developer_profile = _clean_summary_or_profile(
                parsed.developer_profile
            )

            canonical_names = {
                name.casefold(): name for name in draft_output.project_sections
            }
            for project in parsed.projects:
                name = project.project_name.strip()
                canonical = canonical_names.get(name.casefold(), name)
                bullets: list[str] = []
                bullet_fact_ids: list[list[str]] = []
                for bullet in project.bullets:
                    text = _clean_inline_text(bullet.text)
                    if not text:
                        continue
                    bullets.append(text)
                    bullet_fact_ids.append(
                        [
                            _normalize_fact_id(fid, i + 1)
                            for i, fid in enumerate(bullet.fact_ids)
                            if str(fid).strip()
                        ]
                    )

                output.project_sections[canonical] = ProjectSection(
                    description=_clean_inline_text(project.description),
                    bullets=bullets,
                    bullet_fact_ids=bullet_fact_ids,
                    narrative=_clean_inline_text(project.narrative),
                )

            output.portfolio_data = draft_output.portfolio_data
            output.raw_project_facts = raw_facts
            output.quality_metrics["schema"] = {
                "polish_json": 1,
                "polish_text_fallback": 0,
            }

            # Preserve draft sections if polish omitted them
            if not output.professional_summary and draft_output.professional_summary:
                output.professional_summary = draft_output.professional_summary
            if not output.skills_section and draft_output.skills_section:
                output.skills_section = draft_output.skills_section
            if not output.developer_profile and draft_output.developer_profile:
                output.developer_profile = draft_output.developer_profile
            if not output.project_sections and draft_output.project_sections:
                output.project_sections = dict(draft_output.project_sections)
            if not output.project_sections:
                output.project_sections = _synthesize_sections_from_raw_facts(raw_facts)
            if not output.professional_summary and output.portfolio_data:
                output.professional_summary = (
                    f"Software developer with experience across {output.portfolio_data.total_projects} projects "
                    f"using {', '.join(output.portfolio_data.languages_used[:3])}."
                )
            if not output.developer_profile:
                output.developer_profile = (
                    "Builds practical systems with a strong implementation focus "
                    "across backend, tooling, and delivery workflows."
                )
            if not output.skills_section and output.portfolio_data:
                output.skills_section = _normalize_skills_section(
                    "",
                    output.portfolio_data,
                )

            if output.skills_section and output.portfolio_data:
                output.skills_section = _normalize_skills_section(
                    output.skills_section,
                    output.portfolio_data,
                )

            citation_metrics = _apply_citation_gate(output, raw_facts)
            output.quality_metrics["citations"] = citation_metrics
            return output
        except Exception as exc:
            log.warning(
                "Structured stage-3 polish failed (%s). Falling back to text parser.",
                exc,
            )

    # Fallback path: legacy text parser.
    response = _query(
        prompt,
        model,
        POLISH_SYSTEM,
        max_tokens=2048,
    )

    if not response.strip():
        # Fall back to the draft if polish fails
        log.warning("Polish stage returned empty response, using draft")
        draft_output.stage = "polish"
        draft_output.quality_metrics.setdefault("schema", {})
        draft_output.quality_metrics["schema"].update(
            {"polish_json": 0, "polish_text_fallback": 1}
        )
        citation_metrics = _apply_citation_gate(draft_output, raw_facts)
        draft_output.quality_metrics["citations"] = citation_metrics
        return draft_output

    output = _parse_draft_response(response)
    output.stage = "polish"
    output.portfolio_data = draft_output.portfolio_data
    output.raw_project_facts = raw_facts
    output.quality_metrics["schema"] = {"polish_json": 0, "polish_text_fallback": 1}

    # Preserve draft sections if polish didn't produce them
    if not output.professional_summary and draft_output.professional_summary:
        output.professional_summary = draft_output.professional_summary
    if not output.skills_section and draft_output.skills_section:
        output.skills_section = draft_output.skills_section
    if not output.developer_profile and draft_output.developer_profile:
        output.developer_profile = draft_output.developer_profile
    if not output.project_sections and draft_output.project_sections:
        output.project_sections = dict(draft_output.project_sections)
    if not output.project_sections:
        output.project_sections = _synthesize_sections_from_raw_facts(raw_facts)
    if not output.professional_summary and output.portfolio_data:
        output.professional_summary = (
            f"Software developer with experience across {output.portfolio_data.total_projects} projects "
            f"using {', '.join(output.portfolio_data.languages_used[:3])}."
        )
    if not output.developer_profile:
        output.developer_profile = (
            "Builds practical systems with a strong implementation focus "
            "across backend, tooling, and delivery workflows."
        )
    if not output.skills_section and output.portfolio_data:
        output.skills_section = _normalize_skills_section(
            "",
            output.portfolio_data,
        )

    # Normalize skills
    if output.skills_section and output.portfolio_data:
        output.skills_section = _normalize_skills_section(
            output.skills_section, output.portfolio_data
        )

    citation_metrics = _apply_citation_gate(output, raw_facts)
    output.quality_metrics["citations"] = citation_metrics

    return output


# ---------------------------------------------------------------------------
# Per-section micro-prompt queries (Step 6)
# ---------------------------------------------------------------------------


def _parse_bullet_response(text: str) -> list[str]:
    """Parse ``- bullet`` lines from a GBNF-constrained response."""
    if not text:
        return []
    # Strip think tags and emoji garbage before line-splitting
    text = _THINK_TAG_RE.sub("", text)
    text = _EMOJI_GARBAGE_RE.sub("", text)
    bullets: list[str] = []
    for line in text.splitlines():
        match = _BULLET_LINE_RE.match(line.strip())
        if match:
            cleaned = _clean_llm_artifacts(match.group(1))
            cleaned = _clean_inline_text(cleaned)
            if cleaned:
                bullets.append(cleaned)
    return bullets


def _run_bullet_query(
    project_name: str,
    facts: list[str],
    model: str,
    *,
    contribution_pct: float | None = None,
    data_card_context: str = "",
    progress: Optional[Callable[[str], None]] = None,
) -> tuple[list[str], list[list[str]]]:
    """Run a single bullet-generation call for one project.

    Returns ``(bullets, bullet_fact_ids)`` — each bullet mapped to fact IDs.
    """
    from .grammars import BULLET_GRAMMAR

    if progress:
        progress(f"  [Stage 2] Generating bullets for {project_name}...")

    if not facts:
        return [], []

    prompt = build_bullets_prompt(
        project_name,
        facts,
        contribution_pct=contribution_pct,
        data_card_context=data_card_context,
    )

    try:
        response = _query(
            prompt,
            model,
            BULLET_SYSTEM,
            max_tokens=300,
            grammar=BULLET_GRAMMAR,
        )
        # Prepend "- " since prompt primes with it and grammar expects it
        if response and not response.startswith("- "):
            response = "- " + response
        bullets = _parse_bullet_response(response)
    except Exception as exc:
        log.warning("Bullet query failed for %s: %s", project_name, exc)
        bullets = []

    if not bullets:
        # Fallback: convert cleaned facts directly
        bullets = [_fact_to_repair_bullet(f) for f in facts[:3] if f]

    # Map bullets to fact IDs (1:1 with input facts order)
    bullet_fact_ids: list[list[str]] = []
    for i, _bullet in enumerate(bullets):
        if i < len(facts):
            bullet_fact_ids.append([f"F{i + 1}"])
        else:
            bullet_fact_ids.append([])

    return bullets[:3], bullet_fact_ids[:3]


def _run_summary_query(
    portfolio: PortfolioDataBundle,
    model: str,
    *,
    progress: Optional[Callable[[str], None]] = None,
) -> str:
    """Run a single summary-generation call."""
    from .grammars import SUMMARY_GRAMMAR

    if progress:
        progress("  [Stage 2] Generating professional summary...")

    prompt = build_micro_summary_prompt(portfolio)
    try:
        response = _query(
            prompt,
            model,
            BULLET_SYSTEM,
            max_tokens=200,
            grammar=SUMMARY_GRAMMAR,
        )
        cleaned = _clean_summary_or_profile(response)
        if cleaned:
            return cleaned
    except Exception as exc:
        log.warning("Summary query failed: %s", exc)

    # Deterministic fallback
    return (
        f"Software developer with experience across "
        f"{portfolio.total_projects} projects "
        f"using {', '.join(portfolio.languages_used[:3])}."
    )


def _run_profile_query(
    portfolio: PortfolioDataBundle,
    model: str,
    *,
    progress: Optional[Callable[[str], None]] = None,
) -> str:
    """Run a single profile-generation call."""
    from .grammars import SUMMARY_GRAMMAR

    if progress:
        progress("  [Stage 2] Generating developer profile...")

    prompt = build_micro_profile_prompt(portfolio)
    try:
        response = _query(
            prompt,
            model,
            BULLET_SYSTEM,
            max_tokens=200,
            grammar=SUMMARY_GRAMMAR,
        )
        cleaned = _clean_summary_or_profile(response)
        if cleaned:
            return cleaned
    except Exception as exc:
        log.warning("Profile query failed: %s", exc)

    # Deterministic fallback
    return (
        "Builds practical systems with a strong implementation focus "
        "across backend, tooling, and delivery workflows."
    )


# ---------------------------------------------------------------------------
# v2 Stage 2 orchestrator: per-section micro-prompts (Step 7)
# ---------------------------------------------------------------------------


def run_draft_queries_v2(
    raw_facts: dict[str, RawProjectFacts],
    portfolio: PortfolioDataBundle,
    model: str,
    *,
    progress: Optional[Callable[[str], None]] = None,
) -> ResumeOutput:
    """Stage 2 v2: Per-section micro-prompt draft with GBNF grammars.

    1. Clean facts (strip evidence artifacts)
    2. Build skills deterministically
    3. Build descriptions + narratives deterministically
    4. Per-project bullet calls with BULLET_GRAMMAR
    5. Summary + profile calls with SUMMARY_GRAMMAR
    6. Citation gate
    """
    if progress:
        progress("[Stage 2 v2] Generating draft resume with micro-prompts...")

    # 1. Clean facts
    _clean_all_facts(raw_facts)

    # 2. Deterministic skills
    skills_section = _build_skills_deterministic(portfolio)

    # 3. Deterministic descriptions + narratives
    desc_narr = _build_descriptions_deterministic(raw_facts, portfolio)

    # 4. Per-project bullet generation
    output = ResumeOutput(stage="draft")
    bundle_map: dict[str, ProjectDataBundle] = {
        b.project_name: b for b in portfolio.projects
    }

    for project_name, facts in raw_facts.items():
        cleaned_facts = [
            item.text for item in facts.fact_items if item.text
        ] or facts.facts

        bundle = bundle_map.get(project_name)
        pct = bundle.user_contribution_pct if bundle else None

        # Build data card context for richer Stage 2 prompts
        card_context = _build_data_card_context(bundle) if bundle else ""

        bullets, bullet_fact_ids = _run_bullet_query(
            project_name,
            cleaned_facts,
            model,
            contribution_pct=pct,
            data_card_context=card_context,
            progress=progress,
        )

        description, narrative = desc_narr.get(project_name, ("", ""))
        output.project_sections[project_name] = ProjectSection(
            description=description,
            bullets=bullets,
            bullet_fact_ids=bullet_fact_ids,
            narrative=narrative,
        )

    # 5. Summary + profile
    output.professional_summary = _run_summary_query(
        portfolio, model, progress=progress
    )
    output.developer_profile = _run_profile_query(
        portfolio, model, progress=progress
    )
    output.skills_section = skills_section

    # Fallbacks
    if not output.project_sections:
        output.project_sections = _synthesize_sections_from_raw_facts(raw_facts)
    if not output.professional_summary:
        output.professional_summary = (
            f"Software developer with experience across "
            f"{portfolio.total_projects} projects "
            f"using {', '.join(portfolio.languages_used[:3])}."
        )
    if not output.developer_profile:
        output.developer_profile = (
            "Builds practical systems with a strong implementation focus "
            "across backend, tooling, and delivery workflows."
        )
    if not output.skills_section:
        output.skills_section = _build_skills_deterministic(portfolio)

    # 6. Citation gate
    output.portfolio_data = portfolio
    output.raw_project_facts = raw_facts
    citation_metrics = _apply_citation_gate(output, raw_facts)
    output.quality_metrics["citations"] = citation_metrics
    output.quality_metrics["schema"] = {
        "draft_v2_micro": 1,
    }

    return output


# ---------------------------------------------------------------------------
# v2 Stage 3 orchestrator: per-section polish (Step 8)
# ---------------------------------------------------------------------------


def run_polish_query_v2(
    draft_output: ResumeOutput,
    feedback: UserFeedback,
    model: str,
    *,
    progress: Optional[Callable[[str], None]] = None,
) -> ResumeOutput:
    """Stage 3 v2: Per-section polish with GBNF grammars.

    - Per-project bullet polish with BULLET_GRAMMAR
    - Summary + profile polish with SUMMARY_GRAMMAR
    - Direct section edits applied without LLM
    - Skills section never polished (deterministic)
    """
    from .grammars import BULLET_GRAMMAR, SUMMARY_GRAMMAR

    if progress:
        progress("[Stage 3 v2] Polishing resume with micro-prompts...")

    raw_facts = draft_output.raw_project_facts or {}
    has_content_feedback = bool(feedback.general_notes or feedback.tone)

    output = ResumeOutput(stage="polish")
    output.portfolio_data = draft_output.portfolio_data
    output.raw_project_facts = raw_facts

    # --- Apply direct section edits first ---
    if feedback.section_edits:
        for section_name, corrected in feedback.section_edits.items():
            key = section_name.casefold()
            if key in ("summary", "professional_summary"):
                output.professional_summary = corrected
            elif key in ("profile", "developer_profile"):
                output.developer_profile = corrected
            elif key in ("skills", "skills_section"):
                output.skills_section = corrected

    # --- Per-project bullet polish ---
    feedback_text = ""
    if feedback.general_notes:
        feedback_text += feedback.general_notes
    if feedback.tone:
        if feedback_text:
            feedback_text += f" Tone: {feedback.tone}."
        else:
            feedback_text = f"Tone: {feedback.tone}."

    for project_name, section in draft_output.project_sections.items():
        if has_content_feedback and section.bullets:
            if progress:
                progress(
                    f"  [Stage 3 v2] Polishing bullets for {project_name}..."
                )
            prompt = build_bullet_polish_prompt(section.bullets[:3], feedback_text)
            try:
                response = _query(
                    prompt,
                    model,
                    MICRO_POLISH_SYSTEM,
                    max_tokens=300,
                    grammar=BULLET_GRAMMAR,
                )
                if response and not response.startswith("- "):
                    response = "- " + response
                polished_bullets = _parse_bullet_response(response)
                if polished_bullets:
                    output.project_sections[project_name] = ProjectSection(
                        description=section.description,
                        bullets=polished_bullets[:3],
                        bullet_fact_ids=section.bullet_fact_ids,
                        narrative=section.narrative,
                    )
                    continue
            except Exception as exc:
                log.warning(
                    "Bullet polish failed for %s: %s", project_name, exc
                )

        # No polish needed or polish failed — keep draft
        output.project_sections[project_name] = ProjectSection(
            description=section.description,
            bullets=list(section.bullets),
            bullet_fact_ids=list(section.bullet_fact_ids or []),
            narrative=section.narrative,
        )

    # --- Summary polish ---
    if (
        has_content_feedback
        and draft_output.professional_summary
        and not output.professional_summary
    ):
        if progress:
            progress("  [Stage 3 v2] Polishing summary...")
        prompt = build_text_polish_prompt(
            draft_output.professional_summary, feedback_text
        )
        try:
            response = _query(
                prompt,
                model,
                MICRO_POLISH_SYSTEM,
                max_tokens=200,
                grammar=SUMMARY_GRAMMAR,
            )
            cleaned = _clean_summary_or_profile(response)
            if cleaned:
                output.professional_summary = cleaned
        except Exception as exc:
            log.warning("Summary polish failed: %s", exc)

    # --- Profile polish ---
    if (
        has_content_feedback
        and draft_output.developer_profile
        and not output.developer_profile
    ):
        if progress:
            progress("  [Stage 3 v2] Polishing profile...")
        prompt = build_text_polish_prompt(
            draft_output.developer_profile, feedback_text
        )
        try:
            response = _query(
                prompt,
                model,
                MICRO_POLISH_SYSTEM,
                max_tokens=200,
                grammar=SUMMARY_GRAMMAR,
            )
            cleaned = _clean_summary_or_profile(response)
            if cleaned:
                output.developer_profile = cleaned
        except Exception as exc:
            log.warning("Profile polish failed: %s", exc)

    # --- Preserve unmodified sections from draft ---
    if not output.professional_summary:
        output.professional_summary = draft_output.professional_summary
    if not output.skills_section:
        output.skills_section = draft_output.skills_section
    if not output.developer_profile:
        output.developer_profile = draft_output.developer_profile
    if not output.project_sections:
        output.project_sections = dict(draft_output.project_sections)

    # --- Citation gate ---
    citation_metrics = _apply_citation_gate(output, raw_facts)
    output.quality_metrics["citations"] = citation_metrics
    output.quality_metrics["schema"] = {
        "polish_v2_micro": 1,
    }

    return output

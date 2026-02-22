"""
Prompt templates for the v3 resume pipeline.

Each function builds a complete prompt string from data bundles.
Prompts are designed for small models (<=4B params):
  - Positive-only instructions (no negatives)
  - Few-shot example for project prompts
  - Output format front-loaded before data
  - One focused task per prompt
  - Structured output markers (DESCRIPTION: / BULLETS: / NARRATIVE:)
"""

from __future__ import annotations

import json

from ..models import (
    EvidenceLinkedFact,
    ProjectDataBundle,
    PortfolioDataBundle,
    RawProjectFacts,
    ResumeOutput,
    UserFeedback,
)


# ---------------------------------------------------------------------------
# System prompts — all positive instructions, no negatives
# ---------------------------------------------------------------------------

PROJECT_SYSTEM = (
    "You are a resume editor for software engineers. "
    "Write concise, achievement-focused content in a natural professional tone.\n"
    "Rules:\n"
    "- Reference ONLY features, endpoints, classes, and tools that appear in the project data below.\n"
    "- Use numbers ONLY when they are explicitly present in the data.\n"
    "- Do NOT invent features, metrics, or technologies not in the data.\n"
    "- Do NOT copy raw data lines into the output — rephrase as professional achievements.\n"
    "- Match the developer's role to their contribution percentage (see Role line in data).\n"
    "- Prefer concrete technical work from commits and code constructs.\n"
    "- Keep each section's claims distinct from the others.\n"
    "- Output plain text only: use section markers exactly as written."
)

SUMMARY_SYSTEM = (
    "You are a resume editor. Write concise, factual content in a natural professional tone. "
    "Reference ONLY technologies and projects that appear in the data provided. "
    "Do NOT invent skills, technologies, or achievements not in the data. "
    "Name the exact technologies used. "
    "Output plain text only (use section markers as written, no markdown decoration)."
)


# ---------------------------------------------------------------------------
# Per-project prompt
# ---------------------------------------------------------------------------


def build_project_prompt(bundle: ProjectDataBundle) -> str:
    """
    Build a prompt for generating one project's resume section.

    Uses 0-shot with structural template (no few-shot example to prevent copying).
    """
    context = bundle.to_prompt_context()

    ownership_hint = ""
    if bundle.user_contribution_pct is not None:
        pct = bundle.user_contribution_pct
        if pct >= 95:
            ownership_hint = (
                "\nThis is a SOLO project (the developer wrote nearly all the code). "
                'You may say "Built" or "Designed". Keep claims factual.\n'
            )
        elif pct >= 50:
            ownership_hint = (
                f"\nThis is a TEAM project where the developer contributed {pct:.0f}%. "
                'Use phrases like "Led development of" or "Architected". '
                'Do NOT say "Independently built".\n'
            )
        else:
            ownership_hint = (
                f"\nThis is a TEAM project where the developer contributed {pct:.0f}%. "
                'Use phrases like "Contributed to" or "Implemented". '
                'Do NOT say "Independently built" or "Led".\n'
            )

    return f"""{ownership_hint}
Your task: write a resume section using ONLY information from the project data below.

Output format (use these exact markers):
DESCRIPTION: <1 sentence: what the project does, using the README and project type>
BULLETS:
- <achievement: [action verb] [specific feature/component from commits or constructs] [using technology from stack]>
- <achievement: same pattern, different feature>
- <achievement: same pattern, different feature>
NARRATIVE: <1 sentence: developer's specific role and measurable contribution>

Rules:
- Each bullet MUST reference a specific commit message, route, class, or function from the data.
- Do NOT invent features, numbers, or technologies not present in the data.
- Do NOT copy raw data lines — rephrase as professional achievements.
- Write 2-4 bullets depending on available data. If data is sparse, write fewer bullets.
- The NARRATIVE must use the actual contribution percentage from the data.

Project data:

{context}"""


# ---------------------------------------------------------------------------
# Portfolio prompts (3 separate calls) — format front-loaded before data
# ---------------------------------------------------------------------------


def build_summary_prompt(portfolio: PortfolioDataBundle) -> str:
    """Build prompt for the professional summary (2-3 sentences)."""
    lines = [
        f"Projects: {portfolio.total_projects}",
        f"Total commits: {portfolio.total_commits}",
    ]
    if portfolio.languages_used:
        lines.append(f"Languages: {', '.join(portfolio.languages_used[:6])}")
    if portfolio.frameworks_used:
        lines.append(f"Frameworks: {', '.join(portfolio.frameworks_used[:8])}")
    if portfolio.earliest_commit and portfolio.latest_commit:
        lines.append(
            f"Active period: {portfolio.earliest_commit[:10]} to {portfolio.latest_commit[:10]}"
        )

    # Project summaries
    for p in portfolio.projects:
        lines.append(
            f"\n- {p.project_name}: {p.project_type}, {p.primary_language or 'multi-language'}"
        )

    context = "\n".join(lines)

    return f"""Your task: write a 2-3 sentence professional summary for the top of a software engineer's resume.

Rules:
- Mention the number of projects and name the primary technologies.
- Reference specific types of systems built (from the project types below).
- Write in third person implied (no "I" or "they").

Portfolio data:
{context}

Write the summary now (plain text, no preamble):"""


def build_skills_prompt(portfolio: PortfolioDataBundle) -> str:
    """Build prompt for the technical skills section."""
    # Collect all languages and frameworks
    all_langs = portfolio.languages_used[:8]
    all_frameworks = portfolio.frameworks_used[:10]
    all_skills = portfolio.top_skills[:15]

    return f"""Your task: organize the following technologies into a clean skills section for a resume.

Format:
Languages: ...
Frameworks & Libraries: ...
Tools & Infrastructure: ...
Practices: ...

Rules:
- Group into: Languages, Frameworks & Libraries, Tools & Infrastructure, Practices.
- Include only items from the lists below.
- Each item appears in exactly one category.
- List skill names only, separated by commas.
- If a category would be empty, omit it.

Languages: {", ".join(all_langs)}
Frameworks/Libraries: {", ".join(all_frameworks)}
Skills/Practices: {", ".join(all_skills)}"""


def build_profile_prompt(portfolio: PortfolioDataBundle) -> str:
    """Build prompt for the developer profile narrative (2-3 sentences)."""
    lines = []
    for p in portfolio.projects:
        contrib = (
            f"{p.user_contribution_pct:.0f}%" if p.user_contribution_pct else "N/A"
        )
        commit_types = p.commit_count_by_type()
        type_str = (
            ", ".join(f"{k}: {v}" for k, v in commit_types.items())
            if commit_types
            else "N/A"
        )
        lines.append(
            f"- {p.project_name} ({p.project_type}): "
            f"{p.primary_language or '?'}, {contrib} contribution, "
            f"commits: {type_str}"
        )

    context = "\n".join(lines)

    return f"""Your task: write a 2-3 sentence developer profile paragraph based on these projects.

Rules:
- Describe the developer's strengths and technical range.
- Reference specific project types and technologies from the data.
- Focus on patterns across projects (e.g., "consistently writes tests", "full-stack range").
- Every claim must connect to the data below.

Project data:
{context}

Write the profile now (plain text, no preamble):"""


# ---------------------------------------------------------------------------
# Multi-stage pipeline prompts (Strategy B)
# ---------------------------------------------------------------------------


def build_extraction_evidence_catalog(
    bundle: ProjectDataBundle,
    *,
    max_items: int = 36,
) -> dict[str, str]:
    """Build a compact evidence catalog keyed by deterministic IDs (E1, E2...)."""
    raw_items: list[str] = []

    # Commit evidence (highest-signal first)
    ordered_categories = ["feature", "bugfix", "refactor", "test", "docs", "chore"]
    by_category = {g.category: g.messages for g in bundle.commit_groups}
    for category in ordered_categories:
        for msg in by_category.get(category, [])[:6]:
            raw_items.append(f"commit:{category}:{msg}")

    # Structural constructs
    for route in bundle.constructs.routes[:10]:
        raw_items.append(f"route:{route}")
    for cls in bundle.constructs.classes[:10]:
        raw_items.append(f"class:{cls}")
    for fn in bundle.constructs.key_functions[:10]:
        raw_items.append(f"function:{fn}")

    # Stack and module scope
    for framework in bundle.frameworks[:8]:
        raw_items.append(f"framework:{framework}")
    for module, files in sorted(bundle.module_groups.items())[:8]:
        raw_items.append(f"module:{module} ({len(files)} files)")

    # Architecture layers from import_graph
    ig = bundle.import_graph
    if ig is not None:
        for layer in ig.layer_detection:
            raw_items.append(f"arch_layer:{layer}")
        for dep in ig.external_deps[:8]:
            raw_items.append(f"external_dep:{dep}")

    # Toolchain items from config_fingerprint
    cfp = bundle.config_fingerprint
    if cfp is not None:
        for tool in cfp.linters[:4]:
            raw_items.append(f"linter:{tool}")
        for tool in cfp.test_frameworks[:4]:
            raw_items.append(f"test_framework:{tool}")
        for tool in cfp.deployment_tools[:4]:
            raw_items.append(f"deployment:{tool}")
        for mgr in cfp.package_managers[:2]:
            raw_items.append(f"package_manager:{mgr}")

    # Churn-complexity hotspots
    for hs in bundle.churn_complexity_hotspots[:3]:
        raw_items.append(
            f"hotspot:{hs.filepath} (edits={hs.edit_count}, risk={hs.risk_score:.2f})"
        )

    seen: set[str] = set()
    deduped: list[str] = []
    for item in raw_items:
        key = item.casefold()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
        if len(deduped) >= max_items:
            break

    return {f"E{i}": item for i, item in enumerate(deduped, start=1)}


def _iter_fact_items(facts: RawProjectFacts) -> list[EvidenceLinkedFact]:
    """Return evidence-linked facts with backward-compatible fallback synthesis."""
    if facts.fact_items:
        return facts.fact_items

    synthesized: list[EvidenceLinkedFact] = []
    for idx, text in enumerate(facts.facts, start=1):
        synthesized.append(
            EvidenceLinkedFact(
                fact_id=f"F{idx}",
                text=text,
                evidence_keys=[],
            )
        )
    return synthesized


def _resume_output_to_json_payload(output: ResumeOutput) -> dict:
    """Serialize resume output into the structured schema payload shape."""
    projects_payload: list[dict] = []
    for name, section in output.project_sections.items():
        bullet_ids = section.bullet_fact_ids or []
        bullets: list[dict] = []
        for i, bullet_text in enumerate(section.bullets):
            fact_ids = bullet_ids[i] if i < len(bullet_ids) else []
            bullets.append(
                {
                    "text": bullet_text,
                    "fact_ids": fact_ids,
                }
            )
        projects_payload.append(
            {
                "project_name": name,
                "description": section.description,
                "bullets": bullets,
                "narrative": section.narrative,
            }
        )

    skills_payload = {
        "languages": [],
        "frameworks_libraries": [],
        "tools_infrastructure": [],
        "practices": [],
    }

    if output.skills_section:
        for raw_line in output.skills_section.splitlines():
            line = raw_line.strip()
            if not line or ":" not in line:
                continue
            key, value = line.split(":", 1)
            entries = [item.strip() for item in value.split(",") if item.strip()]
            k = key.strip().casefold()
            if "language" in k:
                skills_payload["languages"].extend(entries)
            elif "framework" in k or "librar" in k:
                skills_payload["frameworks_libraries"].extend(entries)
            elif "tool" in k or "infrastructure" in k:
                skills_payload["tools_infrastructure"].extend(entries)
            else:
                skills_payload["practices"].extend(entries)

    return {
        "professional_summary": output.professional_summary,
        "skills": skills_payload,
        "projects": projects_payload,
        "developer_profile": output.developer_profile,
    }


# ---------------------------------------------------------------------------
# Per-section micro-prompt system prompts
# ---------------------------------------------------------------------------

BULLET_SYSTEM = (
    "You are a resume editor for software engineers. "
    "Write concise, achievement-focused resume bullets as plain bullet lines only. "
    "Each bullet starts with a strong action verb. "
    "Reference ONLY features, technologies, and specifics from the provided facts. "
    "Prioritize shipped features and concrete implementation details over process metadata. "
    "Do NOT invent features, metrics, or technologies not present in the facts."
)

SUMMARY_MICRO_SYSTEM = (
    "You are a resume editor for software engineers. "
    "Write concise, factual resume prose in third-person implied voice. "
    "Output only the requested sentences, with no preface or commentary. "
    "Reference only projects, technologies, and scope present in the provided data."
)

MICRO_POLISH_SYSTEM = (
    "You are a senior resume editor. "
    "Improve clarity, tone, and impact of resume content. "
    "Preserve all factual claims — only improve phrasing. "
    "Return only polished resume text with no preface or notes. "
    "Do NOT add new features, technologies, or metrics not in the original."
)


# ---------------------------------------------------------------------------
# Per-section micro-prompt builders
# ---------------------------------------------------------------------------


def build_bullets_prompt(
    project_name: str,
    facts: list[str],
    *,
    contribution_pct: float | None = None,
    data_card_context: str = "",
    target_bullets: int = 3,
) -> str:
    """Build a per-project bullet generation prompt (uses BULLET_GRAMMAR)."""
    target = max(2, min(4, target_bullets))

    ownership_hint = ""
    if contribution_pct is not None:
        if contribution_pct >= 95:
            ownership_hint = (
                'Use "Built", "Designed", or "Developed" as action verbs.\n'
            )
        elif contribution_pct >= 50:
            ownership_hint = (
                'Use "Implemented", "Led development of", '
                'or "Architected" as action verbs.\n'
            )
        else:
            ownership_hint = (
                'Use "Implemented", "Built", or "Contributed to" as action verbs.\n'
            )

    facts_block = "\n".join(f"- {f}" for f in facts[:15])

    if data_card_context:
        return (
            f"Project: {project_name}\n"
            f"{ownership_hint}\n"
            f"Data card:\n{data_card_context}\n\n"
            f"Facts:\n{facts_block}\n\n"
            f"Using the data card and facts above, write exactly {target} "
            "professional resume bullets that show:\n"
            "- WHAT the developer built (specific features, endpoints, components)\n"
            "- WHY it matters (what problem it solves, who benefits, the impact)\n"
            "- HOW they did it (technologies, approaches, technical decisions)\n"
            "Each bullet should tell a complete story: action + specific technical work + outcome/impact.\n"
            "Prioritize shipped functionality and concrete achievements over process metadata.\n"
            "Return bullet lines only (no headings, notes, or commentary).\n"
            f"Write {target} bullets now:\n- "
        )

    return (
        f"Project: {project_name}\n"
        f"{ownership_hint}\n"
        f"Facts:\n{facts_block}\n\n"
        f"Write exactly {target} professional resume bullets that show:\n"
        "- WHAT the developer built (specific features, components, endpoints)\n"
        "- WHY it matters (what problem it solves, who benefits)\n"
        "- HOW they did it (technologies, approaches)\n"
        "Each bullet should tell a story: action verb + specific technical work + outcome/impact.\n"
        "Prioritize shipped functionality and concrete achievements over process metadata.\n"
        "Return bullet lines only (no headings, notes, or commentary).\n"
        f"Write {target} bullets now:\n- "
    )


def build_micro_summary_prompt(portfolio: "PortfolioDataBundle") -> str:
    """Build a professional summary prompt (uses SUMMARY_GRAMMAR)."""
    project_types = ", ".join(
        f"{count} {ptype}" for ptype, count in portfolio.project_types.items()
    )
    langs = ", ".join(portfolio.languages_used[:4])

    return (
        f"Portfolio: {portfolio.total_projects} projects ({project_types}).\n"
        f"Technologies: {langs}.\n"
        f"Total commits: {portfolio.total_commits}.\n\n"
        "Write exactly 2 sentences for a professional resume summary.\n"
        "Mention project count, key technologies, and system types built.\n"
        "Use third-person implied voice and start directly with the summary text.\n"
        "Return summary text only (no lead-in phrase or labels).\n"
        "Write the summary now:\n"
    )


def build_micro_profile_prompt(portfolio: "PortfolioDataBundle") -> str:
    """Build a developer profile prompt (uses SUMMARY_GRAMMAR)."""
    project_lines = []
    for p in portfolio.projects:
        project_lines.append(
            f"- {p.project_name}: {p.project_type}, "
            f"{p.primary_language or 'multi-language'}"
        )
    projects_block = "\n".join(project_lines)

    return (
        f"Projects:\n{projects_block}\n\n"
        "Write exactly 2 sentences for a developer profile describing "
        "technical strengths and range.\n"
        "Reference specific project types and technologies from the data.\n"
        "Use third-person implied voice and return profile text only.\n"
        "Do not include lead-in phrases or labels.\n"
        "Write the profile now:\n"
    )


def build_bullet_polish_prompt(
    bullets: list[str],
    feedback: str,
    *,
    target_bullets: int | None = None,
) -> str:
    """Build a bullet polish prompt (uses BULLET_GRAMMAR)."""
    target = target_bullets if target_bullets is not None else len(bullets)
    target = max(2, min(4, target))
    bullets_block = "\n".join(f"- {b}" for b in bullets[:4])

    return (
        f"Current bullets:\n{bullets_block}\n\n"
        f"Feedback: {feedback}\n\n"
        f"Improve these {target} bullets based on the feedback. "
        "Keep all factual claims and concrete technologies.\n"
        "Return bullet lines only (no headings, notes, or commentary).\n"
        f"Write {target} improved bullets now:\n- "
    )


def build_text_polish_prompt(text: str, feedback: str) -> str:
    """Build a text polish prompt for summary/profile (uses SUMMARY_GRAMMAR)."""
    return (
        f"Current text:\n{text}\n\n"
        f"Feedback: {feedback}\n\n"
        "Improve this text based on the feedback. "
        "Keep all factual claims. Write exactly 2 sentences.\n"
        "Use third-person implied voice and return text only.\n"
        "Write the improved text now:\n"
    )


EXTRACTION_SYSTEM = (
    "You are a data extraction assistant. "
    "Extract structured facts from project data. "
    "Output only valid JSON for the requested schema. "
    "Reference ONLY information explicitly present in the data. "
    "Do NOT invent features, numbers, or technologies. "
    "Each fact must be traceable to a specific evidence key."
)

DRAFT_SYSTEM = (
    "You are a resume writer for software engineers. "
    "Write professional, achievement-focused resume content. "
    "Reference ONLY technologies and facts provided in the input. "
    "Do NOT invent features, metrics, or technologies not in the facts. "
    "Do NOT copy raw fact text verbatim — rephrase as professional achievements. "
    "Output only valid JSON for the requested schema."
)

POLISH_SYSTEM = (
    "You are a senior resume editor. "
    "Refine and polish resume content while preserving factual accuracy. "
    "Apply the user's feedback precisely. "
    "Maintain a consistent, professional tone throughout. "
    "Output only valid JSON for the requested schema."
)


def build_extraction_prompt(bundle: ProjectDataBundle) -> str:
    """
    Build a Stage 1 extraction prompt for LFM2.5-1.2B.

    Extracts top 5 resume-worthy facts per project. Simple, single-task prompt.
    """
    context = bundle.to_prompt_context()
    evidence_catalog = build_extraction_evidence_catalog(bundle)
    evidence_lines = [f"- {k}: {v}" for k, v in evidence_catalog.items()]
    evidence_block = (
        "\n".join(evidence_lines) if evidence_lines else "- E1: no evidence entries"
    )

    return f"""Your task: extract the top resume-worthy facts from this project as strict JSON.

Return exactly one JSON object with this shape:
{{
  "project_summary": "1 sentence describing what the project does",
  "facts": [
    {{"fact_id": "F1", "fact": "specific technical achievement", "evidence_keys": ["E1", "E4"]}},
    {{"fact_id": "F2", "fact": "specific technical achievement", "evidence_keys": ["E2"]}}
  ],
  "role": "1 sentence about the developer contribution"
}}

Rules:
- Return 3-5 facts.
- Use fact IDs F1, F2, F3, ... in order.
- Each fact must reference concrete work from the evidence catalog.
- Each fact must cite 1-3 evidence keys from the catalog.
- Keep facts concise and factual.

Evidence catalog:
{evidence_block}

Project data:
{context}"""


def build_draft_prompt(
    raw_facts: dict[str, RawProjectFacts],
    portfolio: PortfolioDataBundle,
) -> str:
    """
    Build a Stage 2 draft prompt for Qwen3-1.7B.

    Takes extracted facts from Stage 1 and produces a first-draft resume.
    """
    # Format the extracted facts
    facts_lines: list[str] = []
    for name, facts in raw_facts.items():
        facts_lines.append(f"PROJECT: {name}")
        if facts.summary:
            facts_lines.append(f"PROJECT_SUMMARY: {facts.summary}")
        fact_items = _iter_fact_items(facts)
        if fact_items:
            facts_lines.append("FACTS:")
            for item in fact_items:
                ev = ", ".join(item.evidence_keys[:3]) if item.evidence_keys else ""
                ev_suffix = f" | evidence: {ev}" if ev else ""
                facts_lines.append(f"- {item.fact_id}: {item.text}{ev_suffix}")
        if facts.role:
            facts_lines.append(f"ROLE: {facts.role}")
        facts_lines.append("")

    facts_text = "\n".join(facts_lines)

    # Portfolio context
    portfolio_lines = [
        f"Total projects: {portfolio.total_projects}",
        f"Languages: {', '.join(portfolio.languages_used[:6])}",
    ]
    if portfolio.frameworks_used:
        portfolio_lines.append(
            f"Frameworks: {', '.join(portfolio.frameworks_used[:8])}"
        )
    if portfolio.top_skills:
        portfolio_lines.append(f"Skills: {', '.join(portfolio.top_skills[:10])}")
    portfolio_text = "\n".join(portfolio_lines)

    return f"""Your task: write a complete first-draft resume as strict JSON.

Return exactly one JSON object with this shape:
{{
  "professional_summary": "2-3 sentences",
  "skills": {{
    "languages": ["Python"],
    "frameworks_libraries": ["FastAPI"],
    "tools_infrastructure": ["Docker"],
    "practices": ["Testing"]
  }},
  "projects": [
    {{
      "project_name": "project name",
      "description": "1 sentence",
      "bullets": [
        {{"text": "achievement bullet", "fact_ids": ["F1", "F2"]}}
      ],
      "narrative": "1 sentence about contribution"
    }}
  ],
  "developer_profile": "2-3 sentences"
}}

Rules:
- Use ONLY provided project facts. Do NOT invent features or numbers.
- Each project bullet must cite at least one fact_id from that project.
- Use exact project names from the input.
- Rephrase facts as professional achievements (do NOT copy fact text verbatim).
- For the narrative, use the ROLE line from each project's facts.
- Contribution phrasing: >=95% = "Built", 50-94% = "Led development of", <50% = "Contributed to".
- Keep tone professional and specific.

Portfolio context:
{portfolio_text}

Extracted project facts:
{facts_text}

Return JSON now:"""


def build_polish_prompt(
    draft_output: ResumeOutput,
    feedback: UserFeedback,
) -> str:
    """
    Build a Stage 3 polish prompt for Qwen3-4B.

    Takes the draft resume and user feedback to produce the final version.
    """
    draft_text = json.dumps(
        _resume_output_to_json_payload(draft_output),
        indent=2,
    )

    # Format user feedback
    feedback_lines: list[str] = []
    if feedback.tone:
        feedback_lines.append(f"Tone preference: {feedback.tone}")
    if feedback.general_notes:
        feedback_lines.append(f"General notes: {feedback.general_notes}")
    if feedback.section_edits:
        feedback_lines.append("Section corrections:")
        for section_name, corrected in feedback.section_edits.items():
            feedback_lines.append(f"  {section_name}: {corrected}")
    if feedback.additions:
        feedback_lines.append("Additional information to include:")
        for addition in feedback.additions:
            feedback_lines.append(f"  - {addition}")
    if feedback.removals:
        feedback_lines.append("Claims to remove:")
        for removal in feedback.removals:
            feedback_lines.append(f"  - {removal}")

    feedback_text = (
        "\n".join(feedback_lines)
        if feedback_lines
        else "No specific feedback provided. Polish for clarity and consistency."
    )

    return f"""Your task: polish this structured resume draft while preserving factual grounding.

Return exactly one JSON object with the same schema as the draft:
{{
  "professional_summary": "...",
  "skills": {{"languages": [], "frameworks_libraries": [], "tools_infrastructure": [], "practices": []}},
  "projects": [
    {{"project_name": "...", "description": "...", "bullets": [{{"text": "...", "fact_ids": ["F1"]}}], "narrative": "..."}}
  ],
  "developer_profile": "..."
}}

Rules:
- Preserve factual claims unless user feedback requests removal.
- Keep every bullet tied to at least one valid fact_id.
- Apply user tone and correction requests.
- Improve clarity and flow while keeping structure stable.

User feedback:
{feedback_text}

Draft resume JSON:
{draft_text}

Return polished JSON now:"""

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
    "- Reference only features, endpoints, classes, and tools that appear in the project data.\n"
    "- Use numbers only when they are explicitly present in the data.\n"
    "- Describe the developer's specific role within the team.\n"
    "- If contribution is >=95%, you may use 'Independently built' once.\n"
    "- Prefer concrete technical work from commits and code constructs.\n"
    "- Keep each section's claims distinct from the others.\n"
    "- Output plain text only: use section markers exactly as written."
)

SUMMARY_SYSTEM = (
    "You are a resume editor. Write concise, factual content in a natural professional tone. "
    "Reference only technologies and projects that appear in the data provided. "
    "Name the exact technologies used. "
    "Output plain text only (use section markers as written, no markdown decoration)."
)


# ---------------------------------------------------------------------------
# Few-shot example for project prompts (~250 tokens)
# ---------------------------------------------------------------------------

_PROJECT_FEW_SHOT = """EXAMPLE INPUT:
PROJECT: TaskTracker
Type: Web Application | Stack: Python (72%), JavaScript (28%) | Contribution: 85%
FEATURE commits (6):
  - feat: add real-time WebSocket notifications
  - feat: implement role-based access control with JWT
  - feat: build REST API with 12 CRUD endpoints
BUGFIX commits (2):
  - fix: resolve race condition in notification dispatch
Routes: GET /api/tasks, POST /api/tasks, PUT /api/tasks/:id, DELETE /api/tasks/:id
Classes: TaskService, NotificationManager, AuthMiddleware

EXAMPLE OUTPUT:
DESCRIPTION: A full-stack task management application with real-time notifications and role-based access control, built with Python and JavaScript.
BULLETS:
- Built REST API with 12 CRUD endpoints for task lifecycle management using FastAPI
- Implemented WebSocket-based real-time notifications reducing polling overhead
- Added role-based access control with JWT authentication and AuthMiddleware
NARRATIVE: Contributed 85% of the codebase over the project's development period, focusing on backend API architecture and the real-time notification system.

"""


# ---------------------------------------------------------------------------
# Per-project prompt
# ---------------------------------------------------------------------------


def build_project_prompt(bundle: ProjectDataBundle) -> str:
    """
    Build a prompt for generating one project's resume section.

    Format is front-loaded before data. Includes one few-shot example.
    """
    context = bundle.to_prompt_context()

    ownership_hint = ""
    if bundle.user_contribution_pct is not None and bundle.user_contribution_pct >= 95:
        ownership_hint = (
            "\nThis is a SOLO project (the developer wrote nearly all the code). "
            "Ownership language is allowed, but keep claims factual and brief.\n"
        )
    elif bundle.user_contribution_pct is not None and bundle.user_contribution_pct < 95:
        ownership_hint = (
            "\nThis is a TEAM project (partial contribution). "
            "Describe the developer's specific role within the team.\n"
        )

    return f"""{ownership_hint}
Your task: write a resume section in EXACTLY this format:

DESCRIPTION: [1 sentence describing what this project is and does]
BULLETS:
- [achievement bullet 1]
- [achievement bullet 2]
- [achievement bullet 3]
NARRATIVE: [1 sentence about the developer's specific contribution and impact]

Rules:
- The DESCRIPTION should explain what the project does in 1 sentence.
- Each BULLET must reference a concrete feature, endpoint, class, or fix from the data.
- The NARRATIVE should be 1 sentence about the developer's role and impact.
- Write 2-4 bullets depending on how much data is available.
- Keep each bullet to one sentence and keep tone natural.
- Keep each section's claims distinct from the others.
- Use plain text section markers exactly as written: DESCRIPTION:, BULLETS:, NARRATIVE:.

{_PROJECT_FEW_SHOT}
Now write the resume section for this project:

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
    max_items: int = 28,
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


EXTRACTION_SYSTEM = (
    "You are a data extraction assistant. "
    "Extract structured facts from project data. "
    "Output only valid JSON for the requested schema. "
    "Reference only information present in the data."
)

DRAFT_SYSTEM = (
    "You are a resume writer for software engineers. "
    "Write professional, achievement-focused resume content. "
    "Reference only technologies and facts provided. "
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
- Use only provided project facts.
- Each project bullet must cite at least one fact_id from that project.
- Use exact project names from the input.
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

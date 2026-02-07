"""
Prompt templates for the v3 resume pipeline.

Each function builds a complete prompt string from data bundles.
Prompts are designed for small models (3B, 16K context):
  - One focused task per prompt
  - Structured output markers (DESCRIPTION: / BULLETS: / NARRATIVE:)
  - Concrete data inlined (commit messages, routes, classes)
"""

from __future__ import annotations

from ..models import ProjectDataBundle, PortfolioDataBundle


# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

PROJECT_SYSTEM = (
    "You are a resume editor for software engineers. "
    "Write concise, natural, achievement-focused content. "
    "Rules:\n"
    "- Use ONLY facts present in the project data below.\n"
    "- Never invent features, endpoints, classes, tools, or outcomes.\n"
    "- Use numbers only when they are explicitly present in the data.\n"
    "- If contribution is >=95%, you may use 'Independently built' once.\n"
    "- If contribution is <95%, do not imply sole ownership.\n"
    "- Prefer concrete technical work from commits and code constructs over generic claims.\n"
    "- Avoid repeating the same claim across sections.\n"
    "- Output plain text only: no markdown headings, no bold markers, no code fences."
)

SUMMARY_SYSTEM = (
    "You are a resume editor. Write concise, natural, factual content. "
    "Only reference technologies and projects that appear in the data provided. "
    "Do not invent metrics, ownership claims, or tools not present in the data. "
    "Output plain text only (no markdown decoration)."
)


# ---------------------------------------------------------------------------
# Per-project prompt
# ---------------------------------------------------------------------------


def build_project_prompt(bundle: ProjectDataBundle) -> str:
    """
    Build a prompt for generating one project's resume section.

    The LLM receives the full project context and must output three
    clearly-marked sections: DESCRIPTION, BULLETS, NARRATIVE.
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
            "Do not claim full ownership or use words like 'independently', "
            "'solely', 'from scratch', or 'entire system'.\n"
        )

    return f"""{ownership_hint}
Using the project data below, write a resume section with EXACTLY this format:

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
- If fewer than 2 commit messages exist, write fewer bullets — never fabricate.
- Keep each bullet to one sentence and keep tone natural.
- Do not repeat the same claim across DESCRIPTION, BULLETS, and NARRATIVE.
- Use plain text section markers exactly as written: DESCRIPTION:, BULLETS:, NARRATIVE:.
- Do not wrap section labels or bullets in markdown formatting (no **, no headers).

{context}"""


# ---------------------------------------------------------------------------
# Portfolio prompts (3 separate calls)
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

    return f"""Write a 2-3 sentence professional summary for the top of a software engineer's resume.

Portfolio data:
{context}

Rules:
- Mention the number of projects and primary technologies.
- Reference specific types of systems built (from project types above).
- Do NOT use placeholder phrases like "various technologies".
- Write in third person implied (no "I" or "they").

Write the summary now (no preamble, just the summary text):"""


def build_skills_prompt(portfolio: PortfolioDataBundle) -> str:
    """Build prompt for the technical skills section."""
    # Collect all languages and frameworks
    all_langs = portfolio.languages_used[:8]
    all_frameworks = portfolio.frameworks_used[:10]
    all_skills = portfolio.top_skills[:15]

    return f"""Organize the following technologies into a clean skills section for a resume.

Languages: {", ".join(all_langs)}
Frameworks/Libraries: {", ".join(all_frameworks)}
Skills/Practices: {", ".join(all_skills)}

Rules:
- Group into: Languages, Frameworks & Libraries, Tools & Infrastructure, Practices
- ONLY include items from the lists above — do NOT add technologies not listed.
- Each item appears in EXACTLY ONE category.
- List skill names only, separated by commas. No descriptions or percentages.
- If a category would be empty, omit it.

Format:
Languages: ...
Frameworks & Libraries: ...
Tools & Infrastructure: ...
Practices: ..."""


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

    return f"""Write a 2-3 sentence developer profile paragraph based on these projects.

{context}

Rules:
- Describe the developer's strengths and technical range.
- Reference specific project types and technologies from the data.
- Focus on patterns across projects (e.g., "consistently writes tests", "full-stack range").
- Do NOT include weaknesses, growth areas, or limiting language.
- Do NOT use generic filler. Every claim must connect to the data above.

Write the profile now (no preamble, just the paragraph):"""

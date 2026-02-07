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
    "You are a professional resume writer for software engineers. "
    "You write concise, achievement-oriented content. "
    "Rules:\n"
    "- Be SPECIFIC: name actual features, endpoints, classes from the data below.\n"
    "- Use STRONG action verbs: Architected, Implemented, Designed, Engineered.\n"
    "- EVERY bullet must trace to a commit message or code construct listed below.\n"
    "- NEVER invent features not present in the data.\n"
    "- QUANTIFY when possible: contribution %, commit counts, number of endpoints.\n"
    "- If the developer contributed >95%, use 'Independently built' or 'Architected'.\n"
    "- Output plain text only: no markdown headings, no bold markers, no code fences."
)

SUMMARY_SYSTEM = (
    "You are a professional resume writer. Write concise, factual content. "
    "Only reference technologies and projects that appear in the data provided. "
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

    solo_hint = ""
    if bundle.user_contribution_pct is not None and bundle.user_contribution_pct >= 95:
        solo_hint = (
            "\nThis is a SOLO project (the developer wrote nearly all the code). "
            "Use phrases like 'Independently built', 'Architected and implemented', "
            "or 'Designed from scratch'.\n"
        )

    return f"""{solo_hint}
Using the project data below, write a resume section with EXACTLY this format:

DESCRIPTION: [1-2 sentences describing what this project is and does]
BULLETS:
- [achievement bullet 1]
- [achievement bullet 2]
- [achievement bullet 3]
NARRATIVE: [2-3 sentences about the developer's specific contribution and impact]

Rules:
- The DESCRIPTION should explain what the project does (use the README and project type).
- Each BULLET must reference a concrete feature, endpoint, class, or fix from the data.
- The NARRATIVE should highlight the developer's role and key technical decisions.
- Write 3-5 bullets depending on how much data is available.
- If fewer than 3 commit messages exist, write fewer bullets — never fabricate.
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
    """Build prompt for the developer profile narrative (3-4 sentences)."""
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

    return f"""Write a 3-4 sentence developer profile paragraph based on these projects.

{context}

Rules:
- Describe the developer's strengths, growth areas, and technical range.
- Reference specific project types and technologies from the data.
- Focus on patterns across projects (e.g., "consistently writes tests", "full-stack range").
- Do NOT use generic filler. Every claim must connect to the data above.

Write the profile now (no preamble, just the paragraph):"""

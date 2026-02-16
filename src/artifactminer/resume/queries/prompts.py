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

from ..models import (
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

EXTRACTION_SYSTEM = (
    "You are a data extraction assistant. "
    "Extract structured facts from project data. "
    "Output only the requested format with section markers. "
    "Reference only information present in the data."
)

DRAFT_SYSTEM = (
    "You are a resume writer for software engineers. "
    "Write professional, achievement-focused resume content. "
    "Reference only technologies and facts provided. "
    "Output clean plain text with section markers as written."
)

POLISH_SYSTEM = (
    "You are a senior resume editor. "
    "Refine and polish resume content while preserving factual accuracy. "
    "Apply the user's feedback precisely. "
    "Maintain a consistent, professional tone throughout."
)


def build_extraction_prompt(bundle: ProjectDataBundle) -> str:
    """
    Build a Stage 1 extraction prompt for LFM2.5-1.2B.

    Extracts top 5 resume-worthy facts per project. Simple, single-task prompt.
    """
    context = bundle.to_prompt_context()

    return f"""Your task: extract the top resume-worthy facts from this project.

Output format:
PROJECT_SUMMARY: [1 sentence describing what the project does]
FACTS:
- [fact 1: a specific technical achievement]
- [fact 2: a specific technical achievement]
- [fact 3: a specific technical achievement]
- [fact 4: a specific technical achievement (if available)]
- [fact 5: a specific technical achievement (if available)]
ROLE: [1 sentence about the developer's specific contribution]

Rules:
- Each fact must reference a concrete feature, endpoint, class, or fix from the data.
- Write 3-5 facts depending on how much data is available.
- Facts should be short phrases, not full sentences.
- The ROLE should mention contribution percentage if available.

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
        facts_lines.append(f"SUMMARY: {facts.summary}")
        if facts.facts:
            facts_lines.append("FACTS:")
            for f in facts.facts:
                facts_lines.append(f"- {f}")
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
        portfolio_lines.append(f"Frameworks: {', '.join(portfolio.frameworks_used[:8])}")
    if portfolio.top_skills:
        portfolio_lines.append(f"Skills: {', '.join(portfolio.top_skills[:10])}")
    portfolio_text = "\n".join(portfolio_lines)

    return f"""Your task: write a complete first-draft resume using the extracted project facts below.

Output format:
PROFESSIONAL_SUMMARY: [2-3 sentences summarizing the developer's experience]

SKILLS:
Languages: [comma-separated list]
Frameworks & Libraries: [comma-separated list]
Tools & Infrastructure: [comma-separated list if applicable]
Practices: [comma-separated list if applicable]

For each project, write:
PROJECT: [name]
DESCRIPTION: [1 sentence]
BULLETS:
- [bullet 1]
- [bullet 2]
- [bullet 3]
NARRATIVE: [1 sentence about contribution]

DEVELOPER_PROFILE: [2-3 sentences about the developer's strengths]

Rules:
- Use the extracted facts as the basis for each project section.
- Write in third person implied (no "I" or "they").
- Each bullet should reference a specific technical achievement.
- Name the exact technologies used.

Portfolio context:
{portfolio_text}

Extracted project facts:
{facts_text}

Write the complete resume draft now:"""


def build_polish_prompt(
    draft_output: ResumeOutput,
    feedback: UserFeedback,
) -> str:
    """
    Build a Stage 3 polish prompt for Qwen3-4B.

    Takes the draft resume and user feedback to produce the final version.
    """
    # Format the draft sections
    draft_lines: list[str] = []

    if draft_output.professional_summary:
        draft_lines.append(f"PROFESSIONAL_SUMMARY: {draft_output.professional_summary}")
        draft_lines.append("")

    if draft_output.skills_section:
        draft_lines.append(f"SKILLS:\n{draft_output.skills_section}")
        draft_lines.append("")

    for name, section in draft_output.project_sections.items():
        draft_lines.append(f"PROJECT: {name}")
        if section.description:
            draft_lines.append(f"DESCRIPTION: {section.description}")
        if section.bullets:
            draft_lines.append("BULLETS:")
            for b in section.bullets:
                draft_lines.append(f"- {b}")
        if section.narrative:
            draft_lines.append(f"NARRATIVE: {section.narrative}")
        draft_lines.append("")

    if draft_output.developer_profile:
        draft_lines.append(f"DEVELOPER_PROFILE: {draft_output.developer_profile}")

    draft_text = "\n".join(draft_lines)

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

    feedback_text = "\n".join(feedback_lines) if feedback_lines else "No specific feedback provided. Polish for clarity and consistency."

    return f"""Your task: polish this resume draft, applying the user's feedback.

Output the polished resume in the same format as the draft:
PROFESSIONAL_SUMMARY: [polished text]
SKILLS: [organized skills]
PROJECT: [name]
DESCRIPTION: [polished text]
BULLETS: [polished bullets]
NARRATIVE: [polished text]
DEVELOPER_PROFILE: [polished text]

Rules:
- Preserve all factual claims from the draft unless the user asked to remove them.
- Apply the user's corrections and tone preferences.
- Improve prose quality, flow, and consistency.
- Keep the same section structure.

User feedback:
{feedback_text}

Draft resume:
{draft_text}

Write the polished resume now:"""

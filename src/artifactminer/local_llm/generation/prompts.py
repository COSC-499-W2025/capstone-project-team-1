"""Prompt helpers for the minimal local-generation pipeline."""

from __future__ import annotations

import json


# ── Stage 1: Facts (JSON output, unchanged) ──────────────────────────────────

FACTS_SYSTEM = """You analyze software repositories and produce grounded project facts as JSON.
Only use the provided repository snapshot. Do not invent technologies, impact, or scale.
Keep the output concise, specific, and resume-friendly.
Respond with a single JSON object. Do not include any text outside the JSON."""


def build_project_facts_prompt(snapshot: dict[str, object]) -> str:
    pretty_snapshot = json.dumps(snapshot, indent=2, ensure_ascii=True)
    return (
        "Turn this repository snapshot into grounded project facts.\n"
        "Requirements:\n"
        "- project_name: use the repository's real name.\n"
        "- project_type: choose a short type like web app, cli tool, library, api service, mobile app, data project, or platform tool.\n"
        "- Summary: 1-2 sentences.\n"
        "- technologies: list the main languages, frameworks, and tools clearly supported by the snapshot.\n"
        "- Highlights: 2-4 specific, resume-ready statements.\n"
        "- Evidence: short concrete proofs from commits/files/frameworks/readme.\n"
        "- Contribution focus: describe what the user appears to have owned.\n"
        "- Keep technologies/frameworks aligned with the snapshot.\n\n"
        f"Repository snapshot:\n{pretty_snapshot}"
    )


# ── Stage 2: Focused calls (plain-text markdown output) ─────────────────────

PROJECT_CONTENT_SYSTEM = """You write resume project descriptions from repository evidence.
Stay factual and specific. Every claim must be supported by the data provided.
Output plain markdown. Do not wrap in code fences."""

SUMMARY_SYSTEM = """You write professional resume summaries for software developers.
Stay factual, concise, and specific. Do not invent skills or experience.
Output plain text. Do not wrap in code fences."""

PROFILE_SYSTEM = """You write developer profile paragraphs for software resumes.
Focus on development style, strengths, and work patterns visible in the data.
Output plain text. Do not wrap in code fences."""

POLISH_SYSTEM = """You refine an existing grounded resume draft using explicit user feedback.
Preserve the technical truth of the draft. Do not add claims unsupported by the provided draft and facts.
Output plain markdown with the exact section headers requested. Do not wrap output in code fences."""


def _format_activity(snapshot: dict[str, object]) -> str:
    """Format activity breakdown for prompt context."""
    breakdown = snapshot.get("activity_breakdown", {})
    if not breakdown or not isinstance(breakdown, dict):
        return ""
    parts = []
    for activity, data in breakdown.items():
        if isinstance(data, dict):
            pct = data.get("percentage", 0)
            commits = data.get("commits", 0)
            if pct > 0:
                parts.append(f"  {activity}: {pct}% of work ({commits} commits)")
    if not parts:
        return ""
    return "Activity breakdown:\n" + "\n".join(parts)


def _format_commit_messages(snapshot: dict[str, object]) -> str:
    """Format recent commit messages for prompt context."""
    messages = snapshot.get("recent_commit_messages", [])
    if not messages:
        return ""
    return "Recent commit messages:\n" + "\n".join(f"  - {m}" for m in messages[:10])


def _format_code_samples(snapshot: dict[str, object]) -> str:
    """Format recent code additions for prompt context."""
    additions = snapshot.get("recent_added_lines", [])
    if not additions:
        return ""
    combined = "\n".join(str(a)[:500] for a in additions[:5])
    if not combined.strip():
        return ""
    return f"Recent code written by this developer:\n{combined[:2000]}"


def build_project_content_prompt(
    facts: dict[str, object],
    snapshot: dict[str, object],
) -> str:
    """Build a focused prompt for a single project's description + bullets."""
    facts_json = json.dumps(facts, indent=2, ensure_ascii=True)
    readme = snapshot.get("readme_excerpt", "")
    commit_msgs = _format_commit_messages(snapshot)
    activity = _format_activity(snapshot)
    code_samples = _format_code_samples(snapshot)
    file_tree = snapshot.get("sample_files", [])

    context_parts = [f"Project facts:\n{facts_json}"]
    if readme:
        context_parts.append(f"README excerpt:\n{readme[:2000]}")
    if commit_msgs:
        context_parts.append(commit_msgs)
    if activity:
        context_parts.append(activity)
    if code_samples:
        context_parts.append(code_samples)
    if file_tree:
        context_parts.append("File structure:\n" + "\n".join(f"  {f}" for f in file_tree[:15]))

    context = "\n\n".join(context_parts)

    return (
        f"Write a resume entry for the project \"{snapshot.get('project_name', 'project')}\".\n\n"
        "Output format (plain markdown, no code fences):\n"
        "A 1-2 sentence description of what this project is and what the developer built.\n"
        "Then 3-4 bullet points, each following this pattern:\n"
        "- [Action verb] [what was built/done] [using what technology] [with what result/impact]\n\n"
        "Example of good bullets:\n"
        "- Designed and built a REST API using FastAPI with SQLAlchemy ORM, serving 15+ endpoints\n"
        "- Implemented JWT-based authentication flow with role-based access control\n"
        "- Created automated test suite with pytest achieving 85% code coverage\n"
        "- Developed CLI interface with argument parsing, validation, and colored output\n\n"
        "Requirements:\n"
        "- Every bullet must be grounded in the evidence below.\n"
        "- Mention specific technologies, frameworks, and tools from the project.\n"
        "- Be specific about what was built, not vague.\n"
        "- Do not invent features or metrics not supported by the evidence.\n\n"
        f"{context}"
    )


def build_summary_prompt(
    all_facts: list[dict[str, object]],
    all_snapshots: list[dict[str, object]],
) -> str:
    """Build a prompt for the professional summary (all projects)."""
    facts_json = json.dumps(all_facts, indent=2, ensure_ascii=True)

    # Aggregate key stats
    total_commits = sum(s.get("user_total_commits", 0) or 0 for s in all_snapshots)
    languages = []
    frameworks = []
    for s in all_snapshots:
        for lang in (s.get("languages") or []):
            if lang not in languages:
                languages.append(lang)
        for fw in (s.get("frameworks") or []):
            if fw not in frameworks:
                frameworks.append(fw)

    stats_context = (
        f"Total projects: {len(all_facts)}\n"
        f"Total commits across all projects: {total_commits}\n"
        f"Languages used: {', '.join(languages[:8]) if languages else 'N/A'}\n"
        f"Frameworks used: {', '.join(frameworks[:8]) if frameworks else 'N/A'}"
    )

    return (
        "Write a professional summary for a software developer's resume.\n\n"
        "Requirements:\n"
        "- Write 3-5 sentences.\n"
        "- Mention the developer's primary languages and areas of strength.\n"
        "- Reference specific project types they've worked on.\n"
        "- Mention any notable patterns (full-stack, backend-focused, testing discipline, etc.).\n"
        "- Keep it factual — only reference what's in the data.\n\n"
        "Example of a good summary:\n"
        "Full-stack developer with hands-on experience building web applications and CLI tools "
        "using Python, TypeScript, and Go. Contributed to 4 projects spanning REST APIs, "
        "data pipelines, and developer tooling. Demonstrates strong testing discipline with "
        "automated test suites across multiple projects. Comfortable working across frontend "
        "and backend, with a focus on clean API design and reliable deployments.\n\n"
        f"Developer statistics:\n{stats_context}\n\n"
        f"Project facts:\n{facts_json}"
    )


def build_profile_prompt(
    all_facts: list[dict[str, object]],
    all_snapshots: list[dict[str, object]],
) -> str:
    """Build a prompt for the developer profile section."""
    facts_json = json.dumps(all_facts, indent=2, ensure_ascii=True)

    # Aggregate activity patterns
    activity_lines = []
    for snapshot in all_snapshots:
        name = snapshot.get("project_name", "")
        breakdown = snapshot.get("activity_breakdown", {})
        if isinstance(breakdown, dict) and breakdown:
            parts = []
            for activity, data in breakdown.items():
                if isinstance(data, dict) and data.get("percentage", 0) > 10:
                    parts.append(f"{activity} {data['percentage']}%")
            if parts:
                activity_lines.append(f"  {name}: {', '.join(parts)}")

    # Contribution patterns
    contrib_lines = []
    for snapshot in all_snapshots:
        name = snapshot.get("project_name", "")
        pct = snapshot.get("user_contribution_pct")
        freq = snapshot.get("commit_frequency")
        collab = snapshot.get("is_collaborative", False)
        parts = []
        if pct is not None:
            parts.append(f"{pct}% of commits")
        if freq is not None:
            parts.append(f"{freq} commits/week")
        if collab:
            parts.append("collaborative project")
        if parts:
            contrib_lines.append(f"  {name}: {', '.join(parts)}")

    context_parts = [f"Project facts:\n{facts_json}"]
    if activity_lines:
        context_parts.append("Work patterns by project:\n" + "\n".join(activity_lines))
    if contrib_lines:
        context_parts.append("Contribution patterns:\n" + "\n".join(contrib_lines))

    context = "\n\n".join(context_parts)

    return (
        "Write a developer profile for a software developer's resume.\n\n"
        "Requirements:\n"
        "- Write 3-5 sentences.\n"
        "- Describe the developer's working style based on the evidence.\n"
        "- Mention coding patterns: do they write tests? documentation? focus on features?\n"
        "- Comment on collaboration style if evidence supports it.\n"
        "- Reference specific technologies and project types.\n"
        "- Be specific and grounded, not generic.\n\n"
        "Example of a good profile:\n"
        "Methodical backend developer who pairs every feature with tests — test code accounts "
        "for 30% of contributions across projects. Consistently writes documentation alongside "
        "code changes. Gravitates toward API design and data modeling, with most commits "
        "focused on core business logic rather than configuration. Active contributor averaging "
        "4 commits per week, with ownership of critical paths in collaborative projects.\n\n"
        f"{context}"
    )


def build_polish_prompt(
    *,
    draft_markdown: str,
    feedback: dict[str, object],
) -> str:
    feedback_json = json.dumps(feedback, indent=2, ensure_ascii=True)
    return (
        "Polish this grounded resume draft using the user feedback.\n"
        "Output the full resume again in the same markdown format with the same section headers.\n"
        "Requirements:\n"
        "- Keep the draft truthful and grounded.\n"
        "- Apply feedback to tone/emphasis where possible.\n"
        "- Keep every project present in the output.\n"
        "- Remove claims only if the feedback explicitly asks for it.\n"
        "- Do not wrap output in code fences.\n\n"
        f"Current draft:\n{draft_markdown}\n\n"
        f"Feedback:\n{feedback_json}"
    )

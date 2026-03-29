"""Prompt helpers for the minimal local-generation pipeline."""

from __future__ import annotations

import json


FACTS_SYSTEM = """You analyze software repositories and produce grounded project facts.
Only use the provided repository snapshot. Do not invent technologies, impact, or scale.
Keep the output concise, specific, and resume-friendly."""


DRAFT_SYSTEM = """You write compact, grounded resume drafts from structured project facts.
Stay factual, technical, and concise. Do not invent tools or achievements."""


POLISH_SYSTEM = """You refine an existing grounded resume draft using explicit user feedback.
Preserve the technical truth of the draft. Do not add claims unsupported by the provided draft and facts."""


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


def build_draft_prompt(
    *,
    user_email: str,
    project_facts: list[dict[str, object]],
    portfolio_summary: dict[str, object],
) -> str:
    facts_json = json.dumps(project_facts, indent=2, ensure_ascii=True)
    portfolio_json = json.dumps(portfolio_summary, indent=2, ensure_ascii=True)
    return (
        "Generate a grounded draft resume JSON.\n"
        "Requirements:\n"
        "- Professional summary: 2-4 lines.\n"
        "- Skills section: newline-separated skills/themes.\n"
        "- Developer profile: 2-4 lines.\n"
        "- Each project should include: name, type, primary_language, frameworks, contribution_pct, commit_breakdown, period, description, bullets, bullet_fact_ids, and narrative.\n"
        "- Each project should have 2-4 bullets.\n"
        "- bullet_fact_ids may be empty lists if exact fact-to-bullet mapping is unclear.\n"
        "- Keep tone strong but believable.\n\n"
        f"User email: {user_email}\n"
        f"Portfolio summary:\n{portfolio_json}\n\n"
        f"Project facts:\n{facts_json}"
    )


def build_polish_prompt(
    *,
    draft_output: dict[str, object],
    feedback: dict[str, object],
) -> str:
    draft_json = json.dumps(draft_output, indent=2, ensure_ascii=True)
    feedback_json = json.dumps(feedback, indent=2, ensure_ascii=True)
    return (
        "Polish this grounded resume draft using the user feedback.\n"
        "Requirements:\n"
        "- Preserve the same JSON schema.\n"
        "- Keep the draft truthful and grounded.\n"
        "- Apply feedback to tone/emphasis where possible.\n"
        "- Keep every required project field present in the final JSON.\n"
        "- Remove claims only if the feedback explicitly asks for it.\n\n"
        f"Current draft:\n{draft_json}\n\n"
        f"Feedback:\n{feedback_json}"
    )

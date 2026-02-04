from __future__ import annotations

from artifactminer.resume.ollama_client import DEFAULT_MODEL, query_ollama_text
from artifactminer.resume.prompts import SYSTEM_PROMPT, build_portfolio_prompt
from artifactminer.resume.schemas import ProjectSummary


def synthesize_portfolio(
    project_summaries: list[ProjectSummary],
    top_skills: list[str],
    model: str = DEFAULT_MODEL,
) -> str:
    summaries_text = "\n".join(summary.model_dump_json() for summary in project_summaries)
    prompt = build_portfolio_prompt(summaries_text, ", ".join(top_skills) or "N/A")
    return query_ollama_text(prompt, model=model, system=SYSTEM_PROMPT)

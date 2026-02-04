from __future__ import annotations

from artifactminer.resume.ollama_client import DEFAULT_MODEL, query_ollama
from artifactminer.resume.prompts import SYSTEM_PROMPT, build_project_synthesis_prompt
from artifactminer.resume.schemas import FileAnalysis, ProjectSummary


def synthesize_project(
    *,
    project_name: str,
    languages: str,
    frameworks: str,
    contribution_pct: float,
    total_user_commits: int,
    first_commit: str,
    last_commit: str,
    skills_list: str,
    file_analyses: list[FileAnalysis],
    model: str = DEFAULT_MODEL,
) -> ProjectSummary:
    analyses_json = "[\n" + ",\n".join(a.model_dump_json() for a in file_analyses) + "\n]"

    prompt = build_project_synthesis_prompt(
        project_name=project_name,
        languages=languages,
        frameworks=frameworks,
        contribution_pct=contribution_pct,
        total_user_commits=total_user_commits,
        first_commit=first_commit,
        last_commit=last_commit,
        skills_list=skills_list,
        file_analyses_json=analyses_json,
    )

    return query_ollama(prompt, ProjectSummary, model=model, system=SYSTEM_PROMPT)

from __future__ import annotations

from artifactminer.resume.ollama_client import (
    DEFAULT_MODEL,
    query_ollama,
    query_ollama_async,
)
from artifactminer.resume.prompts import SYSTEM_PROMPT, build_file_analysis_prompt
from artifactminer.resume.schemas import FileAnalysis


def analyze_file(
    *,
    file_path: str,
    project_name: str,
    languages: str,
    frameworks: str,
    tree_sitter_summary: str | None,
    user_code: str,
    model: str = DEFAULT_MODEL,
    max_raw_lines: int = 150,
) -> FileAnalysis:
    code_lines = user_code.splitlines()
    code_omitted = len(code_lines) > max_raw_lines
    raw_code = "\n".join(code_lines[:max_raw_lines]) if not code_omitted else ""
    safe_code = raw_code.replace("```", "`\\`\\`\\`")

    summary = tree_sitter_summary or "Tree-sitter summary unavailable."

    prompt = build_file_analysis_prompt(
        file_path=file_path,
        project_name=project_name,
        languages=languages,
        frameworks=frameworks,
        tree_sitter_header=summary,
        user_code=safe_code,
        code_omitted=code_omitted,
    )

    return query_ollama(prompt, FileAnalysis, model=model, system=SYSTEM_PROMPT)


async def analyze_file_async(
    *,
    file_path: str,
    project_name: str,
    languages: str,
    frameworks: str,
    tree_sitter_summary: str | None,
    user_code: str,
    model: str = DEFAULT_MODEL,
    max_raw_lines: int = 150,
) -> FileAnalysis:
    """Async version of analyze_file for concurrent execution."""
    code_lines = user_code.splitlines()
    code_omitted = len(code_lines) > max_raw_lines
    raw_code = "\n".join(code_lines[:max_raw_lines]) if not code_omitted else ""
    safe_code = raw_code.replace("```", "`\\`\\`\\`")

    summary = tree_sitter_summary or "Tree-sitter summary unavailable."

    prompt = build_file_analysis_prompt(
        file_path=file_path,
        project_name=project_name,
        languages=languages,
        frameworks=frameworks,
        tree_sitter_header=summary,
        user_code=safe_code,
        code_omitted=code_omitted,
    )

    return await query_ollama_async(
        prompt, FileAnalysis, model=model, system=SYSTEM_PROMPT
    )

from __future__ import annotations

from typing import Iterable, List, Tuple

from artifactminer.resume.ollama_client import DEFAULT_MODEL, query_ollama
from artifactminer.resume.prompts import SYSTEM_PROMPT, build_file_discovery_prompt
from artifactminer.resume.schemas import FileRanking


def rank_files(
    project_name: str,
    file_line_counts: Iterable[Tuple[str, int]],
    top_n: int,
    model: str = DEFAULT_MODEL,
) -> List[str]:
    file_line_counts = list(file_line_counts)
    file_list = "\n".join(
        f"- {path} ({lines} lines)" for path, lines in file_line_counts
    )
    prompt = build_file_discovery_prompt(project_name, file_list, top_n)
    ranking = query_ollama(prompt, FileRanking, model=model, system=SYSTEM_PROMPT)

    ordered = sorted(ranking.ranked_files, key=lambda rf: rf.importance)
    ranked_paths = [rf.file_path for rf in ordered]

    # Keep only files we actually provided.
    provided_paths = {path for path, _ in file_line_counts}
    filtered = [path for path in ranked_paths if path in provided_paths]

    if not filtered:
        return [path for path, _ in file_line_counts[:top_n]]

    # Preserve order and trim to top_n.
    deduped: List[str] = []
    for path in filtered:
        if path not in deduped:
            deduped.append(path)
        if len(deduped) >= top_n:
            break
    return deduped

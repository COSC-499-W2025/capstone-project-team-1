"""Thin wrapper around the kit CLI to fetch semantic evidence for skills."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set


class KitCliError(RuntimeError):
    """Raised when the kit CLI fails or returns unparsable output."""


def _norm_path(value: str | None) -> str:
    """Normalize paths to posix with no leading ./ for set lookups."""
    if not value:
        return ""
    return Path(value).as_posix().lstrip("./")


def _run_kit_search_semantic(
    repo_path: str,
    query: str,
    *,
    top_k: int = 3,
    chunk_by: str = "symbols",
    persist_dir: Optional[str] = None,
    build_index: bool = False,
) -> List[Dict]:
    """Invoke kit search-semantic and return parsed JSON results."""
    cmd: List[str] = [
        "kit",
        "search-semantic",
        repo_path,
        query,
        "--top-k",
        str(top_k),
        "--format",
        "json",
        "--chunk-by",
        chunk_by,
    ]
    cmd.append("--build-index" if build_index else "--no-build-index")
    if persist_dir:
        cmd += ["--persist-dir", persist_dir]

    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise KitCliError(proc.stderr.strip() or proc.stdout.strip() or "kit search-semantic failed")

    try:
        return json.loads(proc.stdout)
    except Exception as exc:  # pragma: no cover - defensive
        raise KitCliError(f"Unable to parse kit output for query '{query}'") from exc


def _hits_to_evidence(hits: Iterable[Dict], touched_paths: Optional[Set[str]]) -> List[str]:
    """Convert kit hits to concise evidence strings, filtered by touched paths when provided."""
    evidence: List[str] = []
    for hit in hits:
        path = _norm_path(hit.get("file") or hit.get("path"))
        if touched_paths and path and path not in touched_paths:
            continue

        symbol = hit.get("symbol") or hit.get("name") or ""
        score = hit.get("score")
        snippet = (
            hit.get("snippet")
            or hit.get("context")
            or hit.get("preview")
            or hit.get("text")
            or hit.get("content")
            or ""
        )
        snippet = " ".join(str(snippet).split())
        if len(snippet) > 200:
            snippet = snippet[:197] + "..."

        parts = [p for p in [path, symbol] if p]
        if score is not None:
            try:
                parts.append(f"score={float(score):.3f}")
            except Exception:
                parts.append(f"score={score}")
        if snippet:
            parts.append(snippet)
        if parts:
            evidence.append(" | ".join(parts))
    return evidence


def semantic_skill_evidence(
    repo_path: str,
    skill_queries: Sequence[str],
    *,
    top_k: int = 3,
    chunk_by: str = "symbols",
    persist_dir: Optional[str] = None,
    touched_paths: Optional[Iterable[str]] = None,
    build_index: bool = False,
) -> Dict[str, List[str]]:
    """Run kit semantic search for each skill query and return evidence per skill name."""
    touched_norm = {_norm_path(p) for p in touched_paths} if touched_paths else None
    results: Dict[str, List[str]] = {}
    for query in skill_queries:
        try:
            hits = _run_kit_search_semantic(
                repo_path,
                query,
                top_k=top_k,
                chunk_by=chunk_by,
                persist_dir=persist_dir,
                build_index=build_index,
            )
            results[query] = _hits_to_evidence(hits, touched_norm)
        except Exception:
            # Keep failures isolated to the offending query.
            results[query] = []
    return results

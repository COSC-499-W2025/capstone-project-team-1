"""
LLM semantic extractor — infer project purpose and capabilities from raw code.

This extractor complements static regex signals by asking a local LLM to reason
over small, targeted snippets from real source files.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from ..llm_client import query_llm
from ..models import CommitGroup, LLMProjectUnderstanding

log = logging.getLogger(__name__)


_CODE_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".go",
    ".java",
    ".kt",
    ".rs",
    ".rb",
    ".php",
    ".cs",
}

_ENTRYPOINT_CANDIDATES = [
    "main.py",
    "app.py",
    "server.py",
    "index.js",
    "index.ts",
    "src/main.py",
    "src/app.py",
    "src/server.py",
    "src/index.ts",
    "src/index.js",
    "cmd/main.go",
]

_SKIP_DIR_PARTS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "target",
    "__pycache__",
    ".next",
    ".nuxt",
}


class _UnderstandingPayload(BaseModel):
    """Structured schema for semantic project understanding."""

    project_purpose: str = Field(default="")
    user_value: str = Field(default="")
    architecture_summary: str = Field(default="")
    key_capabilities: list[str] = Field(default_factory=list)
    implementation_highlights: list[str] = Field(default_factory=list)


_UNDERSTANDING_SYSTEM = (
    "You are a software project analyst. "
    "Infer what the project does, who benefits, and what capabilities were implemented. "
    "Use only the provided README, commits, routes, and code snippets. "
    "Keep claims concrete and factual."
)


def _clean_text(value: str, *, max_chars: int = 260) -> str:
    """Normalize whitespace and clip to a safe length."""
    text = " ".join(value.split())
    if len(text) > max_chars:
        text = text[:max_chars].rsplit(" ", 1)[0].strip()
    return text


def _clean_list(
    values: list[str], *, max_items: int, max_chars: int = 170
) -> list[str]:
    """Normalize and dedupe a list of short strings."""
    out: list[str] = []
    seen: set[str] = set()
    for raw in values:
        cleaned = _clean_text(raw, max_chars=max_chars)
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(cleaned)
        if len(out) >= max_items:
            break
    return out


def _flatten_commit_lines(
    commit_groups: list[CommitGroup], *, max_messages: int = 14
) -> str:
    """Render a concise commit summary block for prompt context."""
    lines: list[str] = []
    ordered = ["feature", "bugfix", "refactor", "test", "docs", "chore"]
    by_cat = {g.category: g.messages for g in commit_groups}

    for cat in ordered:
        for msg in by_cat.get(cat, [])[:4]:
            lines.append(f"- [{cat}] {msg}")
            if len(lines) >= max_messages:
                return "\n".join(lines)
    return "\n".join(lines)


def _is_candidate_file(path: Path) -> bool:
    """Return True when a file is a likely useful source snippet."""
    if path.suffix.lower() not in _CODE_EXTENSIONS:
        return False
    for part in path.parts:
        if part in _SKIP_DIR_PARTS:
            return False
    return True


def _collect_candidate_files(
    root: Path,
    module_groups: Dict[str, List[str]],
    *,
    max_files: int,
) -> list[Path]:
    """Select a small, high-signal set of source files for semantic reasoning."""
    selected: list[Path] = []
    seen: set[Path] = set()

    def add(path: Path) -> None:
        if len(selected) >= max_files:
            return
        if path in seen or not path.is_file() or not _is_candidate_file(path):
            return
        seen.add(path)
        selected.append(path)

    # 1) Common entrypoints
    for rel in _ENTRYPOINT_CANDIDATES:
        add(root / rel)

    # 2) User-touched files from git history
    if len(selected) < max_files:
        for files in module_groups.values():
            for rel in files:
                if len(selected) >= max_files:
                    break
                add(root / rel)
            if len(selected) >= max_files:
                break

    # 3) Fallback scan for common app files
    if len(selected) < max_files:
        for pattern in (
            "**/main.*",
            "**/app.*",
            "**/server.*",
            "**/routes.*",
            "**/api.*",
        ):
            for path in root.glob(pattern):
                if len(selected) >= max_files:
                    break
                add(path)
            if len(selected) >= max_files:
                break

    return selected


def _read_snippet(path: Path, *, max_chars: int = 1400) -> str:
    """Read and trim a source snippet from disk."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""
    if not text:
        return ""
    return text[:max_chars]


def extract_llm_project_understanding(
    repo_path: str,
    *,
    model: str,
    project_name: str,
    project_type: str,
    primary_language: Optional[str] = None,
    frameworks: Optional[list[str]] = None,
    readme_text: str = "",
    commit_groups: Optional[list[CommitGroup]] = None,
    module_groups: Optional[Dict[str, List[str]]] = None,
    routes: Optional[list[str]] = None,
    max_files: int = 6,
) -> Optional[LLMProjectUnderstanding]:
    """
    Infer semantic project understanding from raw code snippets + static signals.

    Returns None when there is not enough evidence or inference fails.
    """
    if not model:
        return None

    root = Path(repo_path)
    if not root.exists():
        return None

    groups = commit_groups or []
    modules = module_groups or {}
    route_lines = routes or []

    files = _collect_candidate_files(root, modules, max_files=max_files)
    snippets: list[str] = []
    for path in files:
        snippet = _read_snippet(path)
        if not snippet:
            continue
        rel = str(path.relative_to(root))
        snippets.append(f"FILE: {rel}\n{snippet}")

    commit_block = _flatten_commit_lines(groups)
    readme_excerpt = (readme_text or "").strip()[:2600]

    if not snippets and not readme_excerpt and not commit_block and not route_lines:
        return None

    frameworks_str = ", ".join((frameworks or [])[:8])
    routes_str = "\n".join(f"- {route}" for route in route_lines[:10])
    snippet_block = "\n\n".join(snippets)

    prompt = (
        f"Project name: {project_name}\n"
        f"Project type: {project_type}\n"
        f"Primary language: {primary_language or 'unknown'}\n"
        f"Frameworks: {frameworks_str or 'none listed'}\n\n"
        "README excerpt:\n"
        f"{readme_excerpt or 'N/A'}\n\n"
        "Key commits:\n"
        f"{commit_block or 'N/A'}\n\n"
        "Detected routes/endpoints:\n"
        f"{routes_str or 'N/A'}\n\n"
        "Code snippets:\n"
        f"{snippet_block or 'N/A'}\n\n"
        "Return JSON with:\n"
        "- project_purpose: one factual sentence describing what this project is\n"
        "- user_value: one sentence explaining why it matters to users\n"
        "- architecture_summary: one sentence about implementation approach\n"
        "- key_capabilities: 2-5 concrete capabilities implemented in this project\n"
        "- implementation_highlights: 1-4 specific technical implementation points"
    )

    try:
        payload = query_llm(
            prompt,
            _UnderstandingPayload,
            model=model,
            system=_UNDERSTANDING_SYSTEM,
            temperature=0.1,
        )
    except Exception as exc:
        log.warning("LLM project understanding failed for %s: %s", project_name, exc)
        return None

    understanding = LLMProjectUnderstanding(
        project_purpose=_clean_text(payload.project_purpose, max_chars=260),
        user_value=_clean_text(payload.user_value, max_chars=260),
        architecture_summary=_clean_text(payload.architecture_summary, max_chars=260),
        key_capabilities=_clean_list(
            payload.key_capabilities, max_items=5, max_chars=170
        ),
        implementation_highlights=_clean_list(
            payload.implementation_highlights,
            max_items=4,
            max_chars=170,
        ),
    )

    if not any(
        [
            understanding.project_purpose,
            understanding.user_value,
            understanding.architecture_summary,
            understanding.key_capabilities,
            understanding.implementation_highlights,
        ]
    ):
        return None

    return understanding

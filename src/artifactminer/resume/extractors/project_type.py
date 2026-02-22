"""
Project type inference — classifies repos as Web API, CLI Tool, Library, etc.

Uses a heuristic scoring system based on:
  - Framework presence (FastAPI/Flask/Express → Web API)
  - File patterns (setup.py without app code → Library)
  - Directory names (src/cli, bin/ → CLI Tool)
  - README keywords

When the heuristic confidence is low (score < 6), falls back to a local LLM
call via ``query_llm`` for more nuanced classification.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

log = logging.getLogger(__name__)

# Minimum heuristic score to trust without LLM fallback.
_CONFIDENCE_THRESHOLD = 6


class _ProjectTypePayload(BaseModel):
    """Structured schema for LLM project-type inference."""

    project_type: str = Field(
        default="Software Project",
        description=(
            "One of: Web API, Web App, CLI Tool, Library, "
            "ML/Data Pipeline, Mobile App, Desktop App, "
            "Containerized Service, or Software Project"
        ),
    )
    reasoning: str = Field(
        default="",
        description="One sentence explaining why this type was chosen",
    )


_PROJECT_TYPE_SYSTEM = (
    "You are a software project classifier. "
    "Given a project's directory listing, README excerpt, and detected frameworks, "
    "determine the most accurate project type. "
    "Choose exactly one of: Web API, Web App, CLI Tool, Library, "
    "ML/Data Pipeline, Mobile App, Desktop App, Containerized Service, "
    "or Software Project (if none of the others fit). "
    "Be concise and factual."
)


# Score-based type mapping: (indicator, type, score)
_INDICATORS: List[tuple[str, str, int]] = [
    # Frameworks → Web API / Web App
    ("fastapi", "Web API", 10),
    ("flask", "Web API", 10),
    ("django", "Web App", 10),
    ("express", "Web API", 10),
    ("spring", "Web API", 10),
    ("rails", "Web App", 10),
    ("nextjs", "Web App", 10),
    ("next", "Web App", 8),
    ("react", "Web App", 6),
    ("vue", "Web App", 6),
    ("angular", "Web App", 6),
    ("svelte", "Web App", 6),
    # CLI indicators
    ("typer", "CLI Tool", 8),
    ("click", "CLI Tool", 8),
    ("argparse", "CLI Tool", 6),
    ("commander", "CLI Tool", 6),
    ("yargs", "CLI Tool", 6),
    # Library indicators
    ("setuptools", "Library", 4),
    ("pyproject.toml", "Library", 3),
    # Data / ML
    ("tensorflow", "ML/Data Pipeline", 8),
    ("pytorch", "ML/Data Pipeline", 8),
    ("torch", "ML/Data Pipeline", 8),
    ("scikit-learn", "ML/Data Pipeline", 6),
    ("pandas", "Data Pipeline", 5),
    # Mobile
    ("react-native", "Mobile App", 10),
    ("flutter", "Mobile App", 10),
    ("swiftui", "Mobile App", 8),
]


def _score_heuristics(
    repo_path: str,
    frameworks: List[str] | None = None,
    readme_text: str = "",
) -> Dict[str, int]:
    """Run all heuristic checks, returning a {project_type: score} dict."""
    root = Path(repo_path)
    scores: Dict[str, int] = {}

    # Score from known frameworks
    if frameworks:
        fw_lower = [f.lower() for f in frameworks]
        for indicator, proj_type, score in _INDICATORS:
            if any(indicator in fw for fw in fw_lower):
                scores[proj_type] = scores.get(proj_type, 0) + score

    # Score from README keywords
    if readme_text:
        readme_lower = readme_text.lower()
        for indicator, proj_type, score in _INDICATORS:
            if indicator in readme_lower:
                scores[proj_type] = scores.get(proj_type, 0) + score // 2

        # Extra README heuristics
        if re.search(r"\bapi\b", readme_lower):
            scores["Web API"] = scores.get("Web API", 0) + 3
        if re.search(r"\bcli\b|\bcommand.line\b", readme_lower):
            scores["CLI Tool"] = scores.get("CLI Tool", 0) + 3
        if re.search(r"\blibrary\b|\bpackage\b|\bmodule\b", readme_lower):
            scores["Library"] = scores.get("Library", 0) + 3

    # Score from directory structure
    dirs = {d.name.lower() for d in root.iterdir() if d.is_dir()}
    files = {f.name.lower() for f in root.iterdir() if f.is_file()}

    if "bin" in dirs or "cli" in dirs:
        scores["CLI Tool"] = scores.get("CLI Tool", 0) + 4
    if "api" in dirs or "routes" in dirs or "endpoints" in dirs:
        scores["Web API"] = scores.get("Web API", 0) + 5
    if "templates" in dirs or "views" in dirs or "pages" in dirs:
        scores["Web App"] = scores.get("Web App", 0) + 4
    if "components" in dirs:
        scores["Web App"] = scores.get("Web App", 0) + 3
    if "models" in dirs and "migrations" in dirs:
        scores["Web App"] = scores.get("Web App", 0) + 4
    if "tests" in dirs or "test" in dirs:
        scores["Library"] = scores.get("Library", 0) + 1  # minor signal
    if "dockerfile" in files or "docker-compose.yml" in files:
        scores["Containerized Service"] = scores.get("Containerized Service", 0) + 2

    return scores


def _llm_infer_project_type(
    repo_path: str,
    *,
    model: str,
    frameworks: List[str] | None = None,
    readme_text: str = "",
) -> str:
    """Ask the local LLM to classify the project type."""
    from ..llm_client import query_llm

    root = Path(repo_path)

    # Build a compact directory listing (top-level only, keep it small)
    try:
        entries = sorted(p.name + ("/" if p.is_dir() else "") for p in root.iterdir())
        dir_listing = "\n".join(entries[:40])
    except OSError:
        dir_listing = "N/A"

    frameworks_str = ", ".join((frameworks or [])[:10]) or "none detected"
    readme_excerpt = (readme_text or "").strip()[:1200] or "N/A"

    prompt = (
        f"Project directory listing:\n{dir_listing}\n\n"
        f"Detected frameworks: {frameworks_str}\n\n"
        f"README excerpt:\n{readme_excerpt}\n\n"
        "Based on the above, classify this project."
    )

    try:
        payload = query_llm(
            prompt,
            _ProjectTypePayload,
            model=model,
            system=_PROJECT_TYPE_SYSTEM,
            temperature=0.1,
        )
        result = payload.project_type.strip()
        log.info(
            "LLM classified %s as %r (reason: %s)",
            root.name,
            result,
            payload.reasoning,
        )
        return result if result else "Software Project"
    except Exception as exc:
        log.warning("LLM project-type inference failed for %s: %s", root.name, exc)
        return "Software Project"


def infer_project_type(
    repo_path: str,
    frameworks: List[str] | None = None,
    readme_text: str = "",
    *,
    llm_model: Optional[str] = None,
) -> str:
    """
    Infer project type from frameworks, file patterns, and README content.

    Uses a fast heuristic scorer first. When the best heuristic score is below
    ``_CONFIDENCE_THRESHOLD`` (currently 6) **and** an ``llm_model`` is
    provided, falls back to a local LLM call for more nuanced classification.

    Returns a human-readable type string like "Web API", "CLI Tool", "Library".
    """
    scores = _score_heuristics(repo_path, frameworks, readme_text)

    if not scores:
        best_score = 0
    else:
        best_score = max(scores.values())

    # High confidence — trust the heuristic
    if best_score >= _CONFIDENCE_THRESHOLD:
        result = max(scores, key=lambda t: scores[t])
        log.debug(
            "Heuristic confident for %s: %r (score=%d)",
            repo_path,
            result,
            best_score,
        )
        return result

    # Low confidence — ask the LLM if available
    if llm_model:
        log.info(
            "Heuristic score %d < %d for %s, falling back to LLM",
            best_score,
            _CONFIDENCE_THRESHOLD,
            repo_path,
        )
        return _llm_infer_project_type(
            repo_path,
            model=llm_model,
            frameworks=frameworks,
            readme_text=readme_text,
        )

    # No LLM available — return best heuristic guess or fallback
    if scores:
        return max(scores, key=lambda t: scores[t])
    return "Software Project"

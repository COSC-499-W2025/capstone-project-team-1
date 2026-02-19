"""
Project type inference — classifies repos as Web API, CLI Tool, Library, etc.

Uses a heuristic scoring system based on:
  - Framework presence (FastAPI/Flask/Express → Web API)
  - File patterns (setup.py without app code → Library)
  - Directory names (src/cli, bin/ → CLI Tool)
  - README keywords
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List


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


def infer_project_type(
    repo_path: str,
    frameworks: List[str] | None = None,
    readme_text: str = "",
) -> str:
    """
    Infer project type from frameworks, file patterns, and README content.

    Returns a human-readable type string like "Web API", "CLI Tool", "Library".
    """
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

    if not scores:
        return "Software Project"

    # Return highest-scoring type
    return max(scores, key=lambda t: scores[t])

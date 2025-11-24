"""Language detection heuristics."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Dict, List, Set, Tuple

from artifactminer.mappings import CATEGORIES
from artifactminer.skills.signals.file_signals import path_in_touched


def count_files_by_ext(repo_path: str) -> Counter:
    """Count files by extension for a repository."""
    counts: Counter = Counter()
    for path in Path(repo_path).rglob("*"):
        if path.is_file():
            counts[path.suffix.lower()] += 1
    return counts


def language_signals(
    repo_path: str, *, touched_paths: Set[str] | None = None
) -> List[Tuple[Tuple[str, str], str]]:
    """Infer languages from manifests and shebangs to avoid a giant hard-coded list."""
    signals: List[Tuple[Tuple[str, str], str]] = []
    root = Path(repo_path)

    key_files: Dict[str, Tuple[str, str]] = {
        "package.json": ("JavaScript", CATEGORIES["languages"]),
        "tsconfig.json": ("TypeScript", CATEGORIES["languages"]),
        "requirements.txt": ("Python", CATEGORIES["languages"]),
        "pyproject.toml": ("Python", CATEGORIES["languages"]),
        "Pipfile": ("Python", CATEGORIES["languages"]),
        "pom.xml": ("Java", CATEGORIES["languages"]),
        "build.gradle": ("Java", CATEGORIES["languages"]),
        "build.gradle.kts": ("Kotlin", CATEGORIES["languages"]),
        "go.mod": ("Go", CATEGORIES["languages"]),
        "Cargo.toml": ("Rust", CATEGORIES["languages"]),
        ".csproj": ("C#", CATEGORIES["languages"]),
        "Gemfile": ("Ruby", CATEGORIES["languages"]),
        "composer.json": ("PHP", CATEGORIES["languages"]),
        "mix.exs": ("Elixir", CATEGORIES["languages"]),
        "Makefile": ("Shell Scripting", CATEGORIES["languages"]),
    }

    for rel, mapping in key_files.items():
        if touched_paths is not None and not path_in_touched(rel, touched_paths):
            continue
        if rel.startswith("."):
            matches = list(root.glob(f"**/*{rel}"))
        else:
            matches = list(root.glob(rel))
        if matches:
            signals.append((mapping, f"Detected {rel}"))

    shebang_map = {
        "python": ("Python", CATEGORIES["languages"]),
        "node": ("JavaScript", CATEGORIES["languages"]),
        "bash": ("Shell Scripting", CATEGORIES["languages"]),
        "sh": ("Shell Scripting", CATEGORIES["languages"]),
        "perl": ("Perl", CATEGORIES["languages"]),
        "ruby": ("Ruby", CATEGORIES["languages"]),
        "php": ("PHP", CATEGORIES["languages"]),
    }
    sample_limit = 50
    sampled = 0
    if touched_paths is not None:
        candidate_paths = [root / p for p in touched_paths if (root / p).is_file()]
    else:
        candidate_paths = root.rglob("*")

    for path in candidate_paths:
        if sampled >= sample_limit:
            break
        if not path.is_file():
            continue
        try:
            first_line = path.open("r", encoding="utf-8", errors="ignore").readline()
        except Exception:
            continue
        if first_line.startswith("#!"):
            sampled += 1
            for key, mapping in shebang_map.items():
                if key in first_line.lower():
                    signals.append((mapping, f"Shebang indicates {mapping[0]} in {path.name}"))
                    break

    return signals

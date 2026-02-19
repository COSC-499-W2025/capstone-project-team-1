"""
Code Complexity Narratives.

Computes per-file complexity metrics (decision points, nesting depth, LOC)
and uses a single LLM call to generate resume-ready phrases.

Output example:
"Managed complex authentication logic across 12 high-decision-density functions"
"""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class FileComplexity:
    """Complexity metrics for a single file."""
    filepath: str
    cyclomatic_complexity: int  # number of decision points + 1
    max_nesting_depth: int
    loc: int
    function_count: int


class ComplexityNarrative(BaseModel):
    narrative: str
    highlight_files: list[str]


# ---------------------------------------------------------------------------
# Static analysis: compute complexity
# ---------------------------------------------------------------------------

# Patterns that increase cyclomatic complexity
_DECISION_PATTERNS_PY = re.compile(
    r"^\s*(if |elif |else:|for |while |except |except\s*\(|"
    r"case |match |and |or |assert )", re.MULTILINE
)
_DECISION_PATTERNS_JS = re.compile(
    r"^\s*(if\s*\(|else\s*(if\s*\(|\{)|for\s*\(|while\s*\(|"
    r"switch\s*\(|case |catch\s*\(|\?\?|&&|\|\|)", re.MULTILINE
)


def _compute_nesting_depth(lines: List[str], language: str) -> int:
    """Estimate maximum nesting depth from indentation."""
    max_depth = 0

    if language == "python":
        for line in lines:
            stripped = line.rstrip()
            if not stripped or stripped.startswith("#"):
                continue
            indent = len(line) - len(line.lstrip())
            # Python uses 4 spaces typically
            depth = indent // 4
            max_depth = max(max_depth, depth)
    else:
        # JS/TS: count braces
        depth = 0
        for line in lines:
            depth += line.count("{") - line.count("}")
            max_depth = max(max_depth, depth)

    return max_depth


def _count_functions(content: str, language: str) -> int:
    """Count functions in source code."""
    if language == "python":
        return len(re.findall(r"^\s*(async\s+)?def\s+\w+", content, re.MULTILINE))
    else:
        # JS/TS: function declarations + arrow functions
        decl = len(re.findall(r"^\s*(export\s+)?(async\s+)?function\s+\w+", content, re.MULTILINE))
        arrow = len(re.findall(r"^\s*(export\s+)?(const|let|var)\s+\w+\s*=\s*(async\s+)?\(", content, re.MULTILINE))
        return decl + arrow


def compute_complexity_metrics(
    repo_path: str,
    user_email: str,
    max_files: int = 80,
) -> List[FileComplexity]:
    """
    Compute per-file complexity metrics for user-attributed files.

    Args:
        repo_path: Path to the git repository
        user_email: Author email for file attribution
        max_files: Maximum files to analyze

    Returns:
        List of FileComplexity objects, sorted by complexity (highest first)
    """
    from git import Repo

    repo = Repo(repo_path)

    supported_exts = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
    }

    # Collect user-touched files
    user_files: set[str] = set()
    for commit in repo.iter_commits():
        if len(user_files) >= max_files:
            break
        if commit.author.email and commit.author.email.lower() == user_email.lower():
            for filepath in commit.stats.files:
                ext = Path(filepath).suffix.lower()
                if ext in supported_exts:
                    user_files.add(filepath)

    results = []
    for filepath in list(user_files)[:max_files]:
        full_path = Path(repo_path) / filepath
        if not full_path.exists():
            continue

        try:
            content = full_path.read_text(errors="ignore")
        except (OSError, UnicodeDecodeError):
            continue

        ext = Path(filepath).suffix.lower()
        language = supported_exts.get(ext, "python")
        lines = content.split("\n")

        # Cyclomatic complexity: count decision points
        if language == "python":
            decisions = len(_DECISION_PATTERNS_PY.findall(content))
        else:
            decisions = len(_DECISION_PATTERNS_JS.findall(content))

        results.append(FileComplexity(
            filepath=filepath,
            cyclomatic_complexity=decisions + 1,
            max_nesting_depth=_compute_nesting_depth(lines, language),
            loc=len([l for l in lines if l.strip()]),  # non-empty lines
            function_count=_count_functions(content, language),
        ))

    # Sort by complexity (highest first)
    results.sort(key=lambda f: f.cyclomatic_complexity, reverse=True)
    return results


# ---------------------------------------------------------------------------
# LLM narrative generation
# ---------------------------------------------------------------------------

COMPLEXITY_SYSTEM = (
    "You are a professional resume writer. Generate a concise 1-2 sentence "
    "narrative about a developer's ability to handle complex code. "
    "Focus on competence and capability, not difficulty. "
    "Also list the top 3 most complex files by name."
)


def generate_complexity_narrative(
    metrics: List[FileComplexity],
    model: str,
) -> Optional[ComplexityNarrative]:
    """
    Generate a complexity narrative from pre-computed metrics.

    Args:
        metrics: Per-file complexity metrics (sorted by complexity)
        model: LLM model name

    Returns:
        ComplexityNarrative with narrative and highlight files,
        or None if insufficient data
    """
    from ..llm_client import query_llm

    if len(metrics) < 2:
        return None

    # Aggregate stats
    total_functions = sum(f.function_count for f in metrics)
    total_loc = sum(f.loc for f in metrics)
    avg_complexity = sum(f.cyclomatic_complexity for f in metrics) / len(metrics)
    max_depth = max(f.max_nesting_depth for f in metrics)
    top_complex = metrics[:5]  # Top 5 most complex files

    prompt = (
        "Generate a resume-ready narrative about this developer's complexity handling:\n\n"
        f"- Total files with complex logic: {len(metrics)}\n"
        f"- Total functions: {total_functions}\n"
        f"- Total lines of code: {total_loc}\n"
        f"- Average cyclomatic complexity: {avg_complexity:.1f}\n"
        f"- Maximum nesting depth: {max_depth}\n"
        f"\nMost complex files:\n"
    )
    for f in top_complex:
        prompt += (
            f"  - {f.filepath}: complexity={f.cyclomatic_complexity}, "
            f"depth={f.max_nesting_depth}, {f.function_count} functions, "
            f"{f.loc} LOC\n"
        )

    prompt += "\nWrite a 1-2 sentence narrative and list the top 3 files."

    return query_llm(
        prompt,
        ComplexityNarrative,
        model=model,
        system=COMPLEXITY_SYSTEM,
        temperature=0.3,
    )

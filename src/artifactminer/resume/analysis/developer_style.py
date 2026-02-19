"""
Developer Style Fingerprint.

Computes code style metrics from user-attributed files using tree-sitter,
then uses a single LLM call to generate a brief developer profile narrative.

Output example:
"Writes concise functions (avg 12 lines), consistent type annotations,
favors composition over inheritance"
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
class StyleMetrics:
    """Aggregated code style metrics for a developer."""
    avg_function_length: float  # average lines per function
    max_function_length: int
    total_functions: int
    naming_convention: str  # "snake_case" | "camelCase" | "mixed"
    type_annotation_ratio: float  # 0.0-1.0, fraction with type hints
    comment_density: float  # comments per 100 lines of code
    docstring_coverage: float  # fraction of functions with docstrings
    avg_imports_per_file: float
    files_analyzed: int


class DeveloperFingerprint(BaseModel):
    narrative: str
    strengths: list[str]


# ---------------------------------------------------------------------------
# Static analysis: compute style metrics
# ---------------------------------------------------------------------------

def _count_functions_in_python(content: str) -> List[Dict]:
    """Extract function info from Python source using regex (fast fallback)."""
    functions = []
    lines = content.split("\n")
    func_pattern = re.compile(r"^\s*(async\s+)?def\s+(\w+)\s*\(")
    type_hint_pattern = re.compile(r"\)\s*->\s*")
    docstring_pattern = re.compile(r'^\s*("""|\'\'\')')

    i = 0
    while i < len(lines):
        match = func_pattern.match(lines[i])
        if match:
            func_name = match.group(2)
            has_type_hint = bool(type_hint_pattern.search(lines[i]))

            # Count function body lines
            indent = len(lines[i]) - len(lines[i].lstrip())
            body_start = i + 1
            body_end = body_start

            # Check for docstring
            has_docstring = False
            if body_start < len(lines) and docstring_pattern.match(lines[body_start]):
                has_docstring = True

            # Find end of function (next line at same or lower indent, or EOF)
            for j in range(body_start, len(lines)):
                stripped = lines[j].strip()
                if stripped == "":
                    continue
                line_indent = len(lines[j]) - len(lines[j].lstrip())
                if line_indent <= indent and stripped and not stripped.startswith("#"):
                    body_end = j
                    break
            else:
                body_end = len(lines)

            func_length = body_end - i
            functions.append({
                "name": func_name,
                "length": func_length,
                "has_type_hint": has_type_hint,
                "has_docstring": has_docstring,
            })
        i += 1

    return functions


def _count_functions_in_js_ts(content: str) -> List[Dict]:
    """Extract function info from JS/TS source using regex."""
    functions = []
    lines = content.split("\n")

    # Match: function name(...), const name = (...) =>, async function name(...)
    patterns = [
        re.compile(r"^\s*(export\s+)?(async\s+)?function\s+(\w+)"),
        re.compile(r"^\s*(export\s+)?(const|let|var)\s+(\w+)\s*=\s*(async\s+)?\("),
    ]
    ts_type_pattern = re.compile(r"\):\s*\w+")

    for i, line in enumerate(lines):
        for pat in patterns:
            match = pat.match(line)
            if match:
                func_name = match.group(3) if match.lastindex and match.lastindex >= 3 else "anonymous"
                has_type_hint = bool(ts_type_pattern.search(line))

                # Estimate function length (look for closing brace)
                brace_count = line.count("{") - line.count("}")
                end = i + 1
                for j in range(i + 1, min(i + 200, len(lines))):
                    brace_count += lines[j].count("{") - lines[j].count("}")
                    if brace_count <= 0:
                        end = j + 1
                        break

                functions.append({
                    "name": func_name,
                    "length": end - i,
                    "has_type_hint": has_type_hint,
                    "has_docstring": False,  # JS/TS docstrings handled separately
                })
                break

    return functions


def _detect_naming_convention(function_names: List[str]) -> str:
    """Detect the dominant naming convention from function names."""
    snake = 0
    camel = 0

    for name in function_names:
        if name.startswith("_"):
            name = name.lstrip("_")
        if not name:
            continue
        if "_" in name:
            snake += 1
        elif name[0].islower() and any(c.isupper() for c in name[1:]):
            camel += 1

    if snake > camel * 2:
        return "snake_case"
    elif camel > snake * 2:
        return "camelCase"
    return "mixed"


def compute_style_metrics(
    repo_path: str,
    user_email: str,
    primary_language: Optional[str] = None,
    max_files: int = 100,
) -> Optional[StyleMetrics]:
    """
    Compute code style metrics from user-attributed files.

    Uses regex-based parsing (no tree-sitter required) for broad compatibility.

    Args:
        repo_path: Path to the git repository
        user_email: Author email to filter file attribution
        primary_language: Dominant language (for parser selection)
        max_files: Maximum files to analyze

    Returns:
        StyleMetrics or None if insufficient data
    """
    from git import Repo

    repo = Repo(repo_path)

    # Determine which file extensions to analyze
    lang_extensions = {
        "Python": [".py"],
        "JavaScript": [".js", ".jsx"],
        "TypeScript": [".ts", ".tsx"],
    }

    target_exts = set()
    if primary_language and primary_language in lang_extensions:
        target_exts = set(lang_extensions[primary_language])
    else:
        # Analyze all supported languages
        for exts in lang_extensions.values():
            target_exts.update(exts)

    # Collect user-touched files from recent commits
    user_files: set[str] = set()
    for commit in repo.iter_commits():
        if len(user_files) >= max_files:
            break
        if commit.author.email and commit.author.email.lower() == user_email.lower():
            for filepath in commit.stats.files:
                if any(filepath.endswith(ext) for ext in target_exts):
                    user_files.add(filepath)

    if not user_files:
        return None

    # Analyze each file
    all_functions: List[Dict] = []
    total_lines = 0
    total_comments = 0
    total_imports = 0
    files_analyzed = 0

    for filepath in list(user_files)[:max_files]:
        full_path = Path(repo_path) / filepath
        if not full_path.exists():
            continue

        try:
            content = full_path.read_text(errors="ignore")
        except (OSError, UnicodeDecodeError):
            continue

        files_analyzed += 1
        lines = content.split("\n")
        total_lines += len(lines)

        # Count comments
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith("//"):
                total_comments += 1

        # Count imports
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("from "):
                total_imports += 1

        # Extract functions
        if filepath.endswith(".py"):
            all_functions.extend(_count_functions_in_python(content))
        elif filepath.endswith((".js", ".jsx", ".ts", ".tsx")):
            all_functions.extend(_count_functions_in_js_ts(content))

    if not all_functions or files_analyzed == 0:
        return None

    func_lengths = [f["length"] for f in all_functions]
    func_names = [f["name"] for f in all_functions]
    type_hint_count = sum(1 for f in all_functions if f.get("has_type_hint"))
    docstring_count = sum(1 for f in all_functions if f.get("has_docstring"))

    return StyleMetrics(
        avg_function_length=sum(func_lengths) / len(func_lengths),
        max_function_length=max(func_lengths),
        total_functions=len(all_functions),
        naming_convention=_detect_naming_convention(func_names),
        type_annotation_ratio=type_hint_count / len(all_functions),
        comment_density=(total_comments / total_lines * 100) if total_lines > 0 else 0,
        docstring_coverage=docstring_count / len(all_functions),
        avg_imports_per_file=total_imports / files_analyzed,
        files_analyzed=files_analyzed,
    )


# ---------------------------------------------------------------------------
# LLM narrative generation
# ---------------------------------------------------------------------------

STYLE_SYSTEM = (
    "You are a professional resume writer analyzing a developer's coding style. "
    "Generate a brief 2-sentence developer profile based on the metrics provided. "
    "Focus on strengths and professional qualities. Be factual — only mention "
    "what the metrics support. Also list 3-5 specific strengths."
)


def generate_style_fingerprint(
    metrics: StyleMetrics,
    model: str,
) -> Optional[DeveloperFingerprint]:
    """
    Generate a developer style narrative from pre-computed metrics.

    Args:
        metrics: Pre-computed style metrics
        model: LLM model name

    Returns:
        DeveloperFingerprint with narrative and strengths, or None on failure
    """
    from ..llm_client import query_llm

    prompt = (
        "Generate a developer profile from these code style metrics:\n\n"
        f"- Average function length: {metrics.avg_function_length:.1f} lines\n"
        f"- Longest function: {metrics.max_function_length} lines\n"
        f"- Total functions analyzed: {metrics.total_functions}\n"
        f"- Naming convention: {metrics.naming_convention}\n"
        f"- Type annotation coverage: {metrics.type_annotation_ratio:.0%}\n"
        f"- Comment density: {metrics.comment_density:.1f} comments per 100 lines\n"
        f"- Docstring coverage: {metrics.docstring_coverage:.0%}\n"
        f"- Average imports per file: {metrics.avg_imports_per_file:.1f}\n"
        f"- Files analyzed: {metrics.files_analyzed}\n"
        "\nWrite a 2-sentence developer profile and list 3-5 strengths."
    )

    return query_llm(
        prompt,
        DeveloperFingerprint,
        model=model,
        system=STYLE_SYSTEM,
        temperature=0.3,
    )

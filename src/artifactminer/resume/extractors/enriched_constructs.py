"""
Enriched code construct extractor — classes, functions with structural metadata.

Goes beyond ``constructs.py`` (which captures names only) to capture:
- Class: method count, LOC, parent class
- Function: param count, LOC, return type annotation
- Routes and test functions (reused from constructs.py patterns)

Still regex-based (no AST) for broad language compatibility and speed.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional, Set

from ..models import EnrichedClass, EnrichedConstructs, EnrichedFunction

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# Python class: capture name and optional parent
# [^\S\n]* matches horizontal whitespace only (no newlines) for indent detection
_PY_CLASS_RE = re.compile(
    r"^([^\S\n]*)class\s+(\w+)\s*(?:\(([^)]*)\))?\s*:", re.MULTILINE
)

# Python def: capture indent, name, params, optional return type
_PY_FUNC_RE = re.compile(
    r"^([^\S\n]*)(?:async\s+)?def\s+(\w+)\s*\(([^)]*)\)(\s*->\s*\S+)?\s*:", re.MULTILINE
)

# JS/TS class
_JS_CLASS_RE = re.compile(
    r"^\s*(?:export\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?", re.MULTILINE
)

# JS/TS function declarations + arrow functions
_JS_FUNC_PATTERNS = [
    re.compile(
        r"^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)(\s*:\s*\S+)?",
        re.MULTILINE,
    ),
    re.compile(
        r"^\s*(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\(([^)]*)\)(\s*:\s*\S+)?",
        re.MULTILINE,
    ),
]

# Route patterns (reused from constructs.py)
_ROUTE_PATTERNS = [
    re.compile(
        r'@(?:app|router|api)\.\s*(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)',
        re.I,
    ),
    re.compile(
        r'(?:app|router)\.\s*(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)',
        re.I,
    ),
    re.compile(
        r'@(?:Get|Post|Put|Delete|Patch|Request)Mapping\s*\(\s*(?:value\s*=\s*)?["\']([^"\']+)',
        re.I,
    ),
]

# Test function patterns (reused from constructs.py)
_TEST_PATTERNS = [
    re.compile(r"^\s*(?:async\s+)?def\s+(test_\w+)", re.M),
    re.compile(r'^\s*(?:it|test|describe)\s*\(\s*["\']([^"\']+)', re.M),
]

# File extensions to scan
_CODE_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".java",
    ".kt",
    ".go",
    ".rs",
    ".rb",
    ".cs",
    ".cpp",
    ".c",
    ".php",
}

_SKIP_FUNCTIONS = {
    "__init__",
    "__str__",
    "__repr__",
    "__eq__",
    "__hash__",
    "__len__",
    "__getitem__",
    "__setitem__",
    "__delitem__",
    "__enter__",
    "__exit__",
    "__iter__",
    "__next__",
    "setup",
    "teardown",
    "setUp",
    "tearDown",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _count_params(params_str: str) -> int:
    """Count function parameters, excluding self/cls."""
    if not params_str.strip():
        return 0
    parts = [p.strip() for p in params_str.split(",") if p.strip()]
    return len([p for p in parts if p.split(":")[0].split("=")[0].strip() not in ("self", "cls")])


def _estimate_body_loc_python(lines: List[str], start_line: int, indent: int) -> int:
    """Estimate LOC of a Python block starting at start_line with given indent."""
    count = 0
    for i in range(start_line, len(lines)):
        stripped = lines[i].strip()
        if not stripped:
            continue
        line_indent = len(lines[i]) - len(lines[i].lstrip())
        if line_indent <= indent and stripped and i > start_line:
            break
        count += 1
    return max(count, 1)


def _estimate_body_loc_braces(lines: List[str], start_line: int) -> int:
    """Estimate LOC of a brace-delimited block."""
    depth = 0
    count = 0
    for i in range(start_line, min(start_line + 500, len(lines))):
        line = lines[i]
        depth += line.count("{") - line.count("}")
        count += 1
        if depth <= 0 and i > start_line:
            break
    return max(count, 1)


# ---------------------------------------------------------------------------
# Python extraction
# ---------------------------------------------------------------------------


def _extract_python(content: str, lines: List[str]) -> tuple[List[EnrichedClass], List[EnrichedFunction]]:
    """Extract enriched classes and functions from Python source."""
    classes: List[EnrichedClass] = []
    functions: List[EnrichedFunction] = []

    # Classes
    for m in _PY_CLASS_RE.finditer(content):
        indent = len(m.group(1))
        name = m.group(2)
        parent = (m.group(3) or "").strip()
        # Simplify parent: take first base class
        if "," in parent:
            parent = parent.split(",")[0].strip()

        start = content[:m.start()].count("\n") + 1
        body_loc = _estimate_body_loc_python(lines, start, indent)

        # Count methods inside this class
        method_count = 0
        for i in range(start, min(start + body_loc, len(lines))):
            if re.match(r"^\s+(?:async\s+)?def\s+\w+", lines[i]):
                method_count += 1

        classes.append(
            EnrichedClass(
                name=name,
                method_count=method_count,
                total_loc=body_loc,
                parent_class=parent,
            )
        )

    # Functions (top-level only — skip methods already counted above)
    for m in _PY_FUNC_RE.finditer(content):
        indent = len(m.group(1))
        name = m.group(2)
        params_str = m.group(3) or ""
        has_return = m.group(4) is not None

        if name in _SKIP_FUNCTIONS:
            continue
        if name.startswith("test_"):
            continue
        # Skip indented functions (methods) — only capture top-level
        if indent > 0:
            continue

        start = content[:m.start()].count("\n") + 1
        loc = _estimate_body_loc_python(lines, start, indent)

        functions.append(
            EnrichedFunction(
                name=name,
                param_count=_count_params(params_str),
                loc=loc,
                has_return_type=has_return,
            )
        )

    return classes, functions


# ---------------------------------------------------------------------------
# JS/TS extraction
# ---------------------------------------------------------------------------


def _extract_js_ts(content: str, lines: List[str]) -> tuple[List[EnrichedClass], List[EnrichedFunction]]:
    """Extract enriched classes and functions from JS/TS source."""
    classes: List[EnrichedClass] = []
    functions: List[EnrichedFunction] = []

    # Classes
    for m in _JS_CLASS_RE.finditer(content):
        name = m.group(1)
        parent = m.group(2) or ""

        start = content[:m.start()].count("\n")
        body_loc = _estimate_body_loc_braces(lines, start)

        # Count methods
        method_count = 0
        for i in range(start + 1, min(start + body_loc, len(lines))):
            stripped = lines[i].strip()
            if re.match(r"(?:async\s+)?\w+\s*\(", stripped) and not stripped.startswith(("if", "for", "while", "switch")):
                method_count += 1

        classes.append(
            EnrichedClass(
                name=name,
                method_count=method_count,
                total_loc=body_loc,
                parent_class=parent,
            )
        )

    # Functions
    for pat in _JS_FUNC_PATTERNS:
        for m in pat.finditer(content):
            name = m.group(1)
            params_str = m.group(2) or ""
            has_return = m.group(3) is not None

            if name in _SKIP_FUNCTIONS or name.startswith("test"):
                continue

            start = content[:m.start()].count("\n")
            loc = _estimate_body_loc_braces(lines, start)

            functions.append(
                EnrichedFunction(
                    name=name,
                    param_count=_count_params(params_str),
                    loc=loc,
                    has_return_type=has_return,
                )
            )

    return classes, functions


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_enriched_constructs(
    repo_path: str,
    touched_files: Optional[Set[str]] = None,
    *,
    max_files: int = 100,
) -> EnrichedConstructs:
    """
    Extract enriched code constructs (classes, functions, routes, tests).

    If ``touched_files`` is provided, only scan those files (relative paths).
    Otherwise scan all source files under the repo root.
    """
    root = Path(repo_path)
    result = EnrichedConstructs()

    files_to_scan: List[Path] = []
    if touched_files:
        for rel in touched_files:
            p = root / rel
            if p.is_file() and p.suffix.lower() in _CODE_EXTENSIONS:
                files_to_scan.append(p)
    else:
        for ext in _CODE_EXTENSIONS:
            files_to_scan.extend(root.rglob(f"*{ext}"))

    files_to_scan = files_to_scan[:max_files]
    seen_classes: set[str] = set()
    seen_functions: set[str] = set()

    for filepath in files_to_scan:
        try:
            content = filepath.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        lines = content.split("\n")
        suffix = filepath.suffix.lower()

        # Extract classes and functions
        if suffix == ".py":
            classes, functions = _extract_python(content, lines)
        elif suffix in (".js", ".jsx", ".ts", ".tsx"):
            classes, functions = _extract_js_ts(content, lines)
        else:
            classes, functions = [], []

        for cls in classes:
            if cls.name not in seen_classes:
                seen_classes.add(cls.name)
                result.classes.append(cls)

        for fn in functions:
            if fn.name not in seen_functions:
                seen_functions.add(fn.name)
                result.functions.append(fn)

        # Routes
        for pattern in _ROUTE_PATTERNS:
            for m in pattern.finditer(content):
                groups = m.groups()
                if len(groups) == 2:
                    method, path = groups
                    route_str = f"{method.upper()} {path}"
                elif len(groups) == 1:
                    route_str = groups[0]
                else:
                    continue
                if route_str not in result.routes:
                    result.routes.append(route_str)

        # Tests
        for pattern in _TEST_PATTERNS:
            for m in pattern.finditer(content):
                name = m.group(1)
                if name not in result.test_functions:
                    result.test_functions.append(name)

    # Limit sizes
    result.classes = result.classes[:20]
    result.functions = result.functions[:20]
    result.routes = result.routes[:20]
    result.test_functions = result.test_functions[:30]

    return result

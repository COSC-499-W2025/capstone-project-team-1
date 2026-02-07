"""
Code construct extractor — routes, classes, tests, key functions via regex.

Scans user-touched files for concrete code constructs that can be
referenced in resume bullets. We intentionally keep this lightweight —
regex over file contents, no AST parsing.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Set

from ..models import CodeConstructs

# ---------------------------------------------------------------------------
# Regex patterns by language family
# ---------------------------------------------------------------------------

# Route patterns (framework-specific)
_ROUTE_PATTERNS = [
    # FastAPI / Flask decorators
    re.compile(r'@(?:app|router|api)\.\s*(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)', re.I),
    # Express.js
    re.compile(r'(?:app|router)\.\s*(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)', re.I),
    # Spring @RequestMapping / @GetMapping etc.
    re.compile(r'@(?:Get|Post|Put|Delete|Patch|Request)Mapping\s*\(\s*(?:value\s*=\s*)?["\']([^"\']+)', re.I),
]

# Class definitions
_CLASS_PATTERNS = [
    re.compile(r'^\s*class\s+(\w+)', re.M),                          # Python
    re.compile(r'^\s*(?:export\s+)?class\s+(\w+)', re.M),            # JS/TS
    re.compile(r'^\s*(?:public\s+)?class\s+(\w+)', re.M),            # Java/C#
    re.compile(r'^\s*(?:pub\s+)?struct\s+(\w+)', re.M),              # Rust/Go
]

# Test function definitions
_TEST_PATTERNS = [
    re.compile(r'^\s*(?:async\s+)?def\s+(test_\w+)', re.M),          # Python pytest
    re.compile(r'^\s*(?:it|test|describe)\s*\(\s*["\']([^"\']+)', re.M),  # JS/TS
    re.compile(r'@Test\s+.*?(?:public\s+)?void\s+(\w+)', re.M | re.S),    # Java JUnit
]

# Key function definitions (non-test, non-dunder)
_FUNCTION_PATTERNS = [
    re.compile(r'^\s*(?:async\s+)?def\s+(\w+)\s*\(', re.M),         # Python
    re.compile(r'^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)', re.M),  # JS
    re.compile(r'^\s*(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\(', re.M),  # JS arrow
    re.compile(r'^\s*(?:pub\s+)?fn\s+(\w+)', re.M),                  # Rust
    re.compile(r'^\s*func\s+(\w+)', re.M),                           # Go
]

# Boring function names to skip
_SKIP_FUNCTIONS = {
    "__init__", "__str__", "__repr__", "__eq__", "__hash__",
    "__len__", "__getitem__", "__setitem__", "__delitem__",
    "__enter__", "__exit__", "__iter__", "__next__",
    "setup", "teardown", "setUp", "tearDown",
    "main", "run", "start", "stop",
    "toString", "equals", "hashCode",
}


def _is_interesting_function(name: str) -> bool:
    """Filter out dunder methods and trivial names."""
    if name.startswith("_") and not name.startswith("__"):
        return False  # private helpers — skip
    if name in _SKIP_FUNCTIONS:
        return False
    if name.startswith("test_") or name.startswith("test"):
        return False  # tests are tracked separately
    return True


def extract_constructs(
    repo_path: str,
    touched_files: Set[str] | None = None,
    *,
    max_files: int = 100,
) -> CodeConstructs:
    """
    Extract code constructs from repo files.

    If ``touched_files`` is provided, only scan those files (relative paths).
    Otherwise scan all source files under the repo root.
    """
    root = Path(repo_path)
    constructs = CodeConstructs()

    # Determine which files to scan
    code_extensions = {
        ".py", ".js", ".ts", ".tsx", ".jsx",
        ".java", ".kt", ".go", ".rs", ".rb",
        ".cs", ".cpp", ".c", ".php",
    }

    files_to_scan: List[Path] = []
    if touched_files:
        for rel in touched_files:
            p = root / rel
            if p.is_file() and p.suffix.lower() in code_extensions:
                files_to_scan.append(p)
    else:
        for ext in code_extensions:
            files_to_scan.extend(root.rglob(f"*{ext}"))

    files_to_scan = files_to_scan[:max_files]

    for filepath in files_to_scan:
        try:
            content = filepath.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        # Routes
        for pattern in _ROUTE_PATTERNS:
            for m in pattern.finditer(content):
                groups = m.groups()
                if len(groups) == 2:
                    method, path = groups
                    constructs.routes.append(f"{method.upper()} {path}")
                elif len(groups) == 1:
                    constructs.routes.append(groups[0])

        # Classes
        for pattern in _CLASS_PATTERNS:
            for m in pattern.finditer(content):
                name = m.group(1)
                if name not in constructs.classes:
                    constructs.classes.append(name)

        # Tests
        for pattern in _TEST_PATTERNS:
            for m in pattern.finditer(content):
                name = m.group(1)
                if name not in constructs.test_functions:
                    constructs.test_functions.append(name)

        # Key functions
        for pattern in _FUNCTION_PATTERNS:
            for m in pattern.finditer(content):
                name = m.group(1)
                if _is_interesting_function(name) and name not in constructs.key_functions:
                    constructs.key_functions.append(name)

    # Deduplicate and limit
    constructs.routes = constructs.routes[:20]
    constructs.classes = constructs.classes[:20]
    constructs.test_functions = constructs.test_functions[:30]
    constructs.key_functions = constructs.key_functions[:20]

    return constructs

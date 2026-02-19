"""
Import graph analyzer — maps internal/external dependencies and detects layers.

Parses Python ``import`` / ``from ... import`` and JS/TS ``import ... from``
/ ``require()`` statements via regex. Classifies imports as internal vs
external, detects architectural layers, and finds circular dependencies.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Set

from ..models import ImportGraph

# ---------------------------------------------------------------------------
# Import regex patterns
# ---------------------------------------------------------------------------

# Python: import X / from X import Y
_PY_IMPORT_RE = re.compile(
    r"^\s*(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))", re.MULTILINE
)

# JS/TS: import ... from "X" / require("X")
_JS_IMPORT_RE = re.compile(
    r"""^\s*(?:import\s+.*?\s+from\s+['"]([^'"]+)['"]|"""
    r"""(?:const|let|var)\s+.*?=\s*require\s*\(\s*['"]([^'"]+)['"]\s*\))""",
    re.MULTILINE,
)

# ---------------------------------------------------------------------------
# Layer detection heuristics
# ---------------------------------------------------------------------------

_LAYER_PATTERNS: Dict[str, List[str]] = {
    "presentation": ["routes", "api", "endpoints", "views", "controllers", "handlers", "pages"],
    "business": ["services", "use_cases", "usecases", "logic", "core", "domain"],
    "data": ["models", "schemas", "entities", "repositories", "db", "database", "orm"],
}


def _detect_layers(imports_map: Dict[str, List[str]], repo_root: Path) -> List[str]:
    """Detect architectural layers from directory names in imports map."""
    found_layers: Dict[str, bool] = {}

    all_modules = set(imports_map.keys())
    for module in all_modules:
        # Module keys may use dots or slashes — normalize both
        parts = module.lower().replace("\\", "/").replace(".", "/").split("/")
        for layer_name, patterns in _LAYER_PATTERNS.items():
            for part in parts:
                if part in patterns:
                    found_layers[layer_name] = True
                    break

    # Return in standard order: presentation → business → data
    ordered = ["presentation", "business", "data"]
    return [layer for layer in ordered if layer in found_layers]


# ---------------------------------------------------------------------------
# Circular dependency detection (simple DFS)
# ---------------------------------------------------------------------------


def _find_circular_deps(imports_map: Dict[str, List[str]]) -> List[tuple]:
    """Find circular dependencies using DFS."""
    cycles: List[tuple] = []
    visited: Set[str] = set()

    def _dfs(node: str, path: List[str], path_set: Set[str]) -> None:
        if node in path_set:
            # Found a cycle
            cycle_start = path.index(node)
            cycle = tuple(path[cycle_start:] + [node])
            if cycle not in cycles:
                cycles.append(cycle)
            return
        if node in visited:
            return

        path.append(node)
        path_set.add(node)

        for dep in imports_map.get(node, []):
            if dep in imports_map:  # Only follow internal deps
                _dfs(dep, path, path_set)

        path.pop()
        path_set.discard(node)
        visited.add(node)

    for module in imports_map:
        visited.clear()
        _dfs(module, [], set())

    return cycles[:10]  # Limit to 10


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


_CODE_EXTENSIONS = {".py", ".js", ".ts", ".tsx", ".jsx"}


def extract_import_graph(
    repo_path: str,
    touched_files: Optional[Set[str]] = None,
    *,
    max_files: int = 100,
) -> ImportGraph:
    """
    Extract import graph from repository source files.

    Parses Python and JS/TS import statements, classifies internal vs
    external, detects architectural layers, and finds circular deps.
    """
    root = Path(repo_path)
    result = ImportGraph()

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

    # Collect all internal module paths (relative to root) for classification
    internal_modules: Set[str] = set()
    for f in files_to_scan:
        rel = str(f.relative_to(root))
        # Convert path to module-like name
        module = rel.rsplit(".", 1)[0].replace("/", ".").replace("\\", ".")
        internal_modules.add(module)
        # Also add parent packages
        parts = module.split(".")
        for i in range(1, len(parts)):
            internal_modules.add(".".join(parts[:i]))

    # Also index directory names for local import resolution
    internal_dirs: Set[str] = set()
    for f in files_to_scan:
        rel = f.relative_to(root)
        for parent in rel.parents:
            if str(parent) != ".":
                internal_dirs.add(str(parent).replace("/", ".").replace("\\", "."))

    external_deps_set: Set[str] = set()

    for filepath in files_to_scan:
        try:
            content = filepath.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        rel_path = str(filepath.relative_to(root))
        file_key = rel_path.rsplit(".", 1)[0].replace("/", ".").replace("\\", ".")
        imports: List[str] = []

        suffix = filepath.suffix.lower()

        if suffix == ".py":
            for m in _PY_IMPORT_RE.finditer(content):
                module = m.group(1) or m.group(2)
                if module:
                    imports.append(module)
        elif suffix in (".js", ".jsx", ".ts", ".tsx"):
            for m in _JS_IMPORT_RE.finditer(content):
                module = m.group(1) or m.group(2)
                if module:
                    # Normalize relative imports
                    if module.startswith("."):
                        # Resolve relative to file's directory
                        file_dir = str(filepath.parent.relative_to(root))
                        module = f"{file_dir.replace('/', '.')}.{module.lstrip('./')}"
                    imports.append(module)

        if imports:
            result.imports_map[file_key] = imports

        # Classify internal vs external
        for imp in imports:
            top_level = imp.split(".")[0]
            is_internal = (
                imp in internal_modules
                or top_level in internal_dirs
                or imp.startswith(".")
            )
            if not is_internal:
                external_deps_set.add(top_level)

    result.external_deps = sorted(external_deps_set)
    result.layer_detection = _detect_layers(result.imports_map, root)
    result.circular_deps = _find_circular_deps(result.imports_map)

    return result

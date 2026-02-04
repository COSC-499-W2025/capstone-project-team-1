from __future__ import annotations

from typing import Iterable

try:  # Tree-sitter is optional but recommended.
    from tree_sitter import Language, Parser
    import tree_sitter_python as tspython
    import tree_sitter_javascript as tsjavascript
    import tree_sitter_typescript as tstypescript

    _TS_AVAILABLE = True
except Exception:  # pragma: no cover - depends on local installation
    _TS_AVAILABLE = False


def _language_map() -> dict[str, Language]:
    if not _TS_AVAILABLE:
        return {}
    return {
        ".py": Language(tspython.language()),
        ".js": Language(tsjavascript.language()),
        ".ts": Language(tstypescript.language_typescript()),
        ".tsx": Language(tstypescript.language_tsx()),
    }


def _iter_nodes(root) -> Iterable:
    stack = [root]
    while stack:
        node = stack.pop()
        yield node
        if getattr(node, "children", None):
            stack.extend(reversed(node.children))


def _node_text(code_bytes: bytes, node) -> str:
    return code_bytes[node.start_byte : node.end_byte].decode("utf-8", errors="ignore")


def _clean(text: str, limit: int = 120) -> str:
    compact = " ".join(text.split())
    return compact[:limit] if len(compact) > limit else compact


def _get_name(code_bytes: bytes, node) -> str | None:
    name_node = (
        node.child_by_field_name("name")
        if hasattr(node, "child_by_field_name")
        else None
    )
    if name_node is not None:
        return _clean(_node_text(code_bytes, name_node), limit=80)
    return None


def _get_params(code_bytes: bytes, node) -> str | None:
    params_node = (
        node.child_by_field_name("parameters")
        if hasattr(node, "child_by_field_name")
        else None
    )
    if params_node is not None:
        return _clean(_node_text(code_bytes, params_node), limit=80)
    return None


def get_structural_summary(code: str, file_ext: str) -> str | None:
    if not _TS_AVAILABLE:
        return None

    lang = _language_map().get(file_ext)
    if not lang:
        return None

    parser = Parser(lang)

    code_bytes = code.encode("utf-8", errors="ignore")
    tree = parser.parse(code_bytes)
    root = tree.root_node

    classes: list[str] = []
    functions: list[str] = []
    imports: list[str] = []

    for node in _iter_nodes(root):
        if node.type in ("class_definition", "class_declaration"):
            name = _get_name(code_bytes, node)
            if name:
                classes.append(name)
        elif node.type in (
            "function_definition",
            "function_declaration",
            "method_definition",
            "arrow_function",
        ):
            name = _get_name(code_bytes, node)
            params = _get_params(code_bytes, node)
            if name:
                functions.append(f"{name}({params})" if params else name)
        elif node.type in (
            "import_statement",
            "import_from_statement",
            "import_declaration",
        ):
            imports.append(_clean(_node_text(code_bytes, node), limit=120))

    lines: list[str] = []
    if classes:
        lines.append(f"Classes: {', '.join(classes[:10])}")
    if functions:
        lines.append(f"Functions: {', '.join(functions[:12])}")
    if imports:
        unique_imports = list(dict.fromkeys(imports))[:10]
        lines.append(f"Imports: {'; '.join(unique_imports)}")

    return "\n".join(lines) if lines else None

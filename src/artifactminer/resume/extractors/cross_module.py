"""
Cross-module breadth extractor — measure contribution breadth.

Computes how many top-level modules a user touched relative to
the total, plus the deepest nested file path.
"""

from __future__ import annotations

from typing import Dict, List

from ..models import ModuleBreadth


def extract_cross_module_breadth(
    module_groups: Dict[str, List[str]],
    directory_overview: List[str],
) -> ModuleBreadth:
    """
    Measure breadth of contribution across the codebase.

    Args:
        module_groups: Dict mapping top-level dir to user-touched files
                       (from extract_structure).
        directory_overview: List of all top-level directory names
                           (from extract_structure).

    Returns:
        ModuleBreadth with touch counts, percentage, and deepest path.
    """
    # Modules with user changes (exclude root-level files)
    touched = {m for m in module_groups if m != "(root)"}
    modules_touched = len(touched)

    # Total modules = all top-level dirs
    total_modules = len(directory_overview) if directory_overview else 0

    breadth_pct = round(
        modules_touched / total_modules * 100, 1
    ) if total_modules > 0 else 0.0

    # Find deepest nested file path
    deepest_path = ""
    max_depth = 0
    for files in module_groups.values():
        for f in files:
            depth = f.count("/") + f.count("\\")
            if depth > max_depth:
                max_depth = depth
                deepest_path = f

    return ModuleBreadth(
        modules_touched=modules_touched,
        total_modules=total_modules,
        breadth_pct=breadth_pct,
        deepest_path=deepest_path,
    )

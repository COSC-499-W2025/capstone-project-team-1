"""Regex-based code signals from user additions/changes."""

from __future__ import annotations

import re
from typing import Dict, Iterable, Iterator, Set, Tuple

from artifactminer.skills.skill_patterns import CODE_REGEX_PATTERNS, CodePattern


def collect_additions_text(user_contributions: Dict) -> str:
    """Normalize additions into a single string."""
    additions = user_contributions.get("additions") or user_contributions.get("user_additions")
    if not additions:
        return ""
    if isinstance(additions, str):
        return additions
    if isinstance(additions, Iterable):
        return "\n".join([str(a) for a in additions])
    return str(additions)


def iter_code_pattern_hits(additions_text: str, ecosystems: Set[str]) -> Iterator[Tuple[CodePattern, int]]:
    """Yield patterns and hit counts for additions text, respecting ecosystem gates."""
    for pattern in CODE_REGEX_PATTERNS:
        if pattern.ecosystems:
            if not ecosystems.intersection(set(pattern.ecosystems)):
                continue
        hits = len(re.findall(pattern.regex, additions_text, flags=re.MULTILINE))
        if hits:
            yield pattern, hits

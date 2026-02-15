"""Shared helpers for structured output benchmarks."""

from __future__ import annotations

import json
import re
from typing import List, Tuple

from pydantic import BaseModel, Field

OLLAMA_MODELS: List[str] = [
    "llama3.2:1b",
    "llama3.2:3b",
    "gemma3:1b",
    "gemma3:4b",
    "qwen2.5:0.5b",
    "qwen2.5:1.5b",
    "qwen2:0.5b",
    "qwen2:1.5b",
    "phi3:mini",
    "phi3:small",
    "tinyllama:1.1b",
    "stablelm2:1.6b",
    "dolphin-phi:2.7b",
]

PROMPT_VARIANTS: List[Tuple[str, str]] = [
    ("baseline", ""),
    (
        "impact",
        "Emphasize outcomes and reliability. Avoid numbers or tools not present. ",
    ),
    (
        "skills",
        "Emphasize tools, architecture, and test coverage from the snapshot. ",
    ),
    (
        "changes",
        "Focus highlights on the notable changes and related tests only. ",
    ),
]

_TOKEN_PATTERN = re.compile(r"[a-z0-9+.#/-]+")
_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "built",
    "by",
    "for",
    "from",
    "in",
    "into",
    "is",
    "it",
    "its",
    "of",
    "on",
    "or",
    "the",
    "to",
    "using",
    "with",
    "student",
    "project",
    "resume",
    "summary",
    "highlights",
    "skills",
    "app",
    "web",
    "api",
    "apis",
    "service",
    "services",
    "tests",
    "testing",
}

PROJECT_SNAPSHOT = """
Project: Campus Resource Tracker

Files:
- README.md: Web app to help students log study spaces, equipment loans, and lab availability.
- src/api/routes.py: FastAPI endpoints for spaces, availability, and reservations.
- src/services/availability.py: Caches live availability with TTL and retries.
- src/db/models.py: SQLAlchemy models for spaces, reservations, and users.
- src/ui/Dashboard.tsx: React dashboard with filters, calendar view, and alerts.
- src/ui/components/UsageChart.tsx: D3-based chart for weekly utilization.
- tests/api/test_availability.py: Validates API responses and error handling.
- tests/ui/test_dashboard.py: Covers filtering behavior and empty states.

Notable changes:
- Added caching to reduce API latency and rate limits.
- Added audit logging for reservation updates.
- Improved error messages and validation for booking conflicts.
"""


class ResumeProjectSummary(BaseModel):
    project_name: str = Field(..., description="Project name.")
    one_liner: str = Field(..., description="Resume-ready single sentence.")
    highlights: List[str] = Field(..., description="3-5 resume-worthy bullet points.")
    skills: List[str] = Field(..., description="Technical skills demonstrated.")


def build_prompt(variant_instructions: str) -> str:
    schema = json.dumps(
        ResumeProjectSummary.model_json_schema(), indent=2, sort_keys=True
    )
    return (
        "You are summarizing a student project for a resume. "
        "Return only JSON that matches the provided schema. "
        "Keep it concise, factual, and positive. "
        f"{variant_instructions}"
        "Schema:\n"
        f"{schema}\n\n"
        "Use the project snapshot below.\n\n"
        f"{PROJECT_SNAPSHOT}"
    )


def prompt_variants() -> List[Tuple[str, str]]:
    return [(name, build_prompt(instructions)) for name, instructions in PROMPT_VARIANTS]


def tokenize(text: str) -> List[str]:
    return [t for t in _TOKEN_PATTERN.findall(text.lower()) if len(t) > 1]


def token_set(text: str) -> set[str]:
    return set(tokenize(text))


def _content_from_parsed(parsed: ResumeProjectSummary) -> str:
    return " ".join(
        [
            parsed.project_name,
            parsed.one_liner,
            " ".join(parsed.highlights),
            " ".join(parsed.skills),
        ]
    )


def mirage_metric(
    parsed: ResumeProjectSummary, snapshot: str
) -> Tuple[float, int, int]:
    # Heuristic: tokens not present in the snapshot or in a stopword list are treated as hallucinated.
    snapshot_tokens = token_set(snapshot)
    tokens = tokenize(_content_from_parsed(parsed))
    if not tokens:
        return 0.0, 0, 0
    hallucinated_tokens = [
        t for t in tokens if t not in snapshot_tokens and t not in _STOPWORDS
    ]
    rate = len(hallucinated_tokens) / len(tokens)
    return rate, len(hallucinated_tokens), len(tokens)


def entity_grounding_metric(
    parsed: ResumeProjectSummary, snapshot: str
) -> Tuple[float, int, int]:
    snapshot_tokens = token_set(snapshot)
    tokens = tokenize(_content_from_parsed(parsed))
    entity_candidates = [
        t for t in tokens if t not in _STOPWORDS and not t.isdigit() and len(t) > 2
    ]
    if not entity_candidates:
        return 0.0, 0, 0
    grounded = [t for t in entity_candidates if t in snapshot_tokens]
    rate = len(grounded) / len(entity_candidates)
    return rate, len(grounded), len(entity_candidates)


def redundancy_metric(parsed: ResumeProjectSummary) -> Tuple[float, int, int]:
    def normalize_item(item: str) -> str:
        return " ".join(_TOKEN_PATTERN.findall(item.lower())).strip()

    def count_duplicates(items: List[str]) -> Tuple[int, int]:
        normalized = [normalize_item(item) for item in items if item.strip()]
        counts: dict[str, int] = {}
        for item in normalized:
            counts[item] = counts.get(item, 0) + 1
        duplicates = sum(count - 1 for count in counts.values() if count > 1)
        return duplicates, len(normalized)

    highlight_dupes, highlight_total = count_duplicates(parsed.highlights)
    skill_dupes, skill_total = count_duplicates(parsed.skills)
    duplicate_count = highlight_dupes + skill_dupes
    total_items = highlight_total + skill_total
    if total_items == 0:
        return 0.0, 0, 0
    rate = duplicate_count / total_items
    return rate, duplicate_count, total_items

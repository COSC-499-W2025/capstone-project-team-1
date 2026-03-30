"""Shared generator models and proficiency helpers."""

from __future__ import annotations

from enum import Enum
from typing import Iterable


class ExpertiseLevel(str, Enum):
    BEGINNER = "Beginner"
    INTERMEDIATE = "Intermediate"
    ADVANCED = "Advanced"
    EXPERT = "Expert"


def proficiency_to_level(proficiency: float | None) -> ExpertiseLevel:
    """Map a raw 0.0-1.0 proficiency to a human-readable expertise level."""
    if proficiency is None or proficiency < 0.25:
        return ExpertiseLevel.BEGINNER
    if proficiency >= 0.75:
        return ExpertiseLevel.EXPERT
    if proficiency >= 0.50:
        return ExpertiseLevel.ADVANCED
    return ExpertiseLevel.INTERMEDIATE


def aggregate_skill_proficiency(
    proficiencies: Iterable[float | None],
) -> float | None:
    """Return the max non-null proficiency from an iterable of values."""
    maximum: float | None = None
    for proficiency in proficiencies:
        if proficiency is None:
            continue
        if maximum is None or proficiency > maximum:
            maximum = float(proficiency)
    return maximum

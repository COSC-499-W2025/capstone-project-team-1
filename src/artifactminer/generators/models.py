from enum import Enum
from typing import Optional


class ExpertiseLevel(str, Enum):
    Expert = "Expert"
    Advanced = "Advanced"
    Intermediate = "Intermediate"
    Beginner = "Beginner"


def proficiency_to_level(proficiency: Optional[float]) -> ExpertiseLevel:
    """Map a 0.0–1.0 proficiency (or None) to an expertise level.

    Thresholds (inclusive lower bounds):
    - >= 0.75 -> Expert
    - >= 0.50 -> Advanced
    - >= 0.25 -> Intermediate
    - else -> Beginner (also for None)
    """
    if proficiency is None:
        return ExpertiseLevel.Beginner

    # Guard against minor float noise by using >= comparisons in descending order
    if proficiency >= 0.75:
        return ExpertiseLevel.Expert
    if proficiency >= 0.50:
        return ExpertiseLevel.Advanced
    if proficiency >= 0.25:
        return ExpertiseLevel.Intermediate
    return ExpertiseLevel.Beginner


def aggregate_skill_proficiency(proficiencies: list[Optional[float]]) -> float:
    """Aggregate a list of proficiencies by taking the max of non-None values.

    Returns 0.0 when the input is empty or all values are None.
    """
    non_none = [p for p in proficiencies if p is not None]
    return float(max(non_none)) if non_none else 0.0

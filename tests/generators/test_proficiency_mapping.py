from artifactminer.generators.models import (
    ExpertiseLevel,
    aggregate_skill_proficiency,
    proficiency_to_level,
)


def test_proficiency_to_level_thresholds():
    assert proficiency_to_level(None) == ExpertiseLevel.BEGINNER
    assert proficiency_to_level(0.0) == ExpertiseLevel.BEGINNER
    assert proficiency_to_level(0.2499) == ExpertiseLevel.BEGINNER
    assert proficiency_to_level(0.25) == ExpertiseLevel.INTERMEDIATE
    assert proficiency_to_level(0.5) == ExpertiseLevel.ADVANCED
    assert proficiency_to_level(0.75) == ExpertiseLevel.EXPERT
    assert proficiency_to_level(1.0) == ExpertiseLevel.EXPERT


def test_aggregate_skill_proficiency_uses_max_non_null_value():
    assert aggregate_skill_proficiency([]) is None
    assert aggregate_skill_proficiency([None, None]) is None
    assert aggregate_skill_proficiency([None, 0.2, 0.8, 0.5]) == 0.8
    assert aggregate_skill_proficiency([0.3, 0.3]) == 0.3

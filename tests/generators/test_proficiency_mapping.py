from artifactminer.generators.models import ExpertiseLevel, proficiency_to_level


def test_proficiency_to_level_none_and_low():
    assert proficiency_to_level(None) == ExpertiseLevel.Beginner
    assert proficiency_to_level(0.0) == ExpertiseLevel.Beginner
    assert proficiency_to_level(0.249999) == ExpertiseLevel.Beginner


def test_proficiency_to_level_boundaries():
    assert proficiency_to_level(0.25) == ExpertiseLevel.Intermediate
    assert proficiency_to_level(0.50) == ExpertiseLevel.Advanced
    assert proficiency_to_level(0.75) == ExpertiseLevel.Expert


def test_proficiency_to_level_upper():
    assert proficiency_to_level(0.74) == ExpertiseLevel.Advanced
    assert proficiency_to_level(0.51) == ExpertiseLevel.Advanced
    assert proficiency_to_level(0.99) == ExpertiseLevel.Expert
    assert proficiency_to_level(1.0) == ExpertiseLevel.Expert

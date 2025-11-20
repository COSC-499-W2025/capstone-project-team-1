from pathlib import Path

from artifactminer.skills.skill_extractor import SkillExtractor


def test_extract_skills_offline_with_no_llm_consent():
    repo_root = Path(__file__).resolve().parents[1]
    extractor = SkillExtractor(enable_llm=False)

    # Simulate user additions to trigger code-pattern based skills
    additions = [
        "async def run_job():\n    return True",
        "class CustomException(Exception):\n    pass",
        "SELECT * FROM artifacts",
        "import unittest\n",
    ]
    user_contributions = {
        "additions": additions,
        "merge_commits": 2,
        "branches": ["main", "feature/skills"],
    }

    skills = extractor.extract_skills(
        repo_path=repo_root,
        user_contributions=user_contributions,
        consent_level="no_llm",
    )

    assert skills, "Expected at least one skill to be extracted"
    names = {s.skill for s in skills}

    # Repository-level signals
    assert "Python" in names
    assert "FastAPI" in names or "REST API Design" in names
    assert "SQLAlchemy" in names
    assert "Dependency Management" in names
    assert "Automated Testing" in names

    # Contribution-driven signals
    assert "Unit Testing" in names
    assert "Asynchronous Programming" in names
    assert "Error Handling" in names
    assert "SQL" in names
    assert "Version Control" in names
    assert "Branching Strategies" in names

    for skill in skills:
        assert 0.0 <= skill.proficiency <= 1.0
        assert skill.evidence

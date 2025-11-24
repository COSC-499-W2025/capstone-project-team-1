from pathlib import Path

import git
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from artifactminer.db import Base
from artifactminer.db.models import RepoStat
from artifactminer.skills import SkillExtractor
from artifactminer.RepositoryIntelligence.framework_detector import detect_frameworks


class DummyRepoStat:
    def __init__(self, is_collaborative: bool = False, languages=None, frameworks=None):
        self.is_collaborative = is_collaborative
        self.Languages = languages or []
        self.languages = self.Languages
        self.frameworks = frameworks or []


def test_extract_skills_offline_with_no_llm_consent():
    repo_root = Path(__file__).resolve().parents[1]
    extractor = SkillExtractor(enable_llm=False)
    repo_stat = DummyRepoStat(is_collaborative=False, languages=["Python"], frameworks=["FastAPI"])

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
        repo_stat=repo_stat,
        user_email="user@example.com",
        user_contributions=user_contributions,
        consent_level="none",  # disable kit/LLM for deterministic testing
    )

    assert skills, "Expected at least one skill to be extracted"
    names = {s.skill for s in skills}

    # Repository-level signals
    assert "Python" in names
    assert "FastAPI" in names or "REST API Design" in names
    assert "SQLAlchemy" in names

    # Contribution-driven signals
    assert "Unit Testing" in names
    assert "Asynchronous Programming" in names
    assert "Error Handling" in names
    assert "SQL" in names

    for skill in skills:
        assert 0.0 <= skill.proficiency <= 1.0
        assert skill.evidence





def test_ecosystem_filtering_skips_python_patterns_for_java_context(tmp_path):
    # Create a minimal Java-ish repo to avoid Python language signals from this repo
    java_repo = tmp_path / "java_repo"
    java_repo.mkdir()
    (java_repo / "Main.java").write_text("public class Main {}")
    (java_repo / "pom.xml").write_text("<project></project>")

    extractor = SkillExtractor(enable_llm=False)
    repo_stat = DummyRepoStat(is_collaborative=False, languages=["Java"], frameworks=["Spring Boot"])
    skills = extractor.extract_skills(
        repo_path=java_repo,
        repo_stat=repo_stat,
        user_email="user@example.com",
        user_contributions={"additions": ["async def foo():\n    return True"]},
        consent_level="none",  # disable kit/LLM for deterministic testing
        languages=["Java"],
        frameworks=["Spring Boot"],
    )
    names = {s.skill for s in skills}
    assert "Asynchronous Programming" not in names  # python-only pattern should be gated out


def test_user_scoped_skills_ignore_other_authors(tmp_path):
    repo_root = tmp_path / "collab_repo"
    repo_root.mkdir()
    repo = git.Repo.init(repo_root)
    repo_stat = DummyRepoStat(is_collaborative=True)

    target_actor = git.Actor("Target User", "target@example.com")
    other_actor = git.Actor("Other User", "other@example.com")

    # Other contributor adds Java content
    java_file = repo_root / "Main.java"
    java_file.write_text("public class Main {}")
    repo.index.add([str(java_file.relative_to(repo_root))])
    repo.index.commit("java commit", author=other_actor, committer=other_actor)

    # Target user adds Python content plus dependency manifest
    py_file = repo_root / "app.py"
    py_file.write_text("import flask\n\nasync def handler():\n    return True\n")
    requirements = repo_root / "requirements.txt"
    requirements.write_text("flask\n")
    repo.index.add([str(py_file.relative_to(repo_root)), str(requirements.relative_to(repo_root))])
    repo.index.commit("python commit", author=target_actor, committer=target_actor)

    extractor = SkillExtractor(enable_llm=False)
    skills = extractor.extract_skills(
        repo_path=repo_root,
        repo_stat=repo_stat,
        user_email="target@example.com",
        consent_level="none",  # disable kit/LLM for deterministic testing
    )

    names = {s.skill for s in skills}
    assert "Python" in names
    assert "Flask" in names  # from requirements touched by the user
    assert "Java" not in names
    assert "Asynchronous Programming" in names  # regex pulled from user additions


def test_shared_dependency_mapping_drives_detector_and_extractor(tmp_path):
    repo_root = tmp_path / "shared_mapping_repo"
    repo_root.mkdir()
    (repo_root / "requirements.txt").write_text("flask\n")

    extractor = SkillExtractor(enable_llm=False)
    repo_stat = DummyRepoStat(is_collaborative=False, languages=["Python"])
    skills = extractor.extract_skills(
        repo_path=repo_root,
        repo_stat=repo_stat,
        user_email="user@example.com",
        user_contributions={},
        consent_level="none",  # disable kit/LLM for deterministic testing
    )
    names = {s.skill for s in skills}
    assert "Flask" in names

    frameworks = detect_frameworks(repo_root)
    assert "Flask" in frameworks

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from artifactminer.db import Base
from artifactminer.db.models import RepoStat
from artifactminer.skills.skill_extractor import SkillExtractor, persist_extracted_skills


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


def test_persist_skills_to_db():
    repo_root = Path(__file__).resolve().parents[1]
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    # Seed a RepoStat row
    repo_stat = RepoStat(project_name=repo_root.name, primary_language="Python")
    db.add(repo_stat)
    db.commit()
    db.refresh(repo_stat)

    extractor = SkillExtractor(enable_llm=False)
    skills = extractor.extract_skills(
        repo_path=repo_root,
        user_contributions={"additions": ["async def foo():\n    return True"]},
        consent_level="no_llm",
        languages=["Python"],
    )

    saved = persist_extracted_skills(db, repo_stat.id, skills)
    assert saved, "Project skills should be persisted"
    assert db.query(RepoStat).filter(RepoStat.id == repo_stat.id).first()

    for ps in saved:
        assert ps.proficiency is not None
        assert ps.evidence


def test_ecosystem_filtering_skips_python_patterns_for_java_context(tmp_path):
    # Create a minimal Java-ish repo to avoid Python language signals from this repo
    java_repo = tmp_path / "java_repo"
    java_repo.mkdir()
    (java_repo / "Main.java").write_text("public class Main {}")
    (java_repo / "pom.xml").write_text("<project></project>")

    extractor = SkillExtractor(enable_llm=False)
    skills = extractor.extract_skills(
        repo_path=java_repo,
        user_contributions={"additions": ["async def foo():\n    return True"]},
        consent_level="no_llm",
        languages=["Java"],
        frameworks=["Spring Boot"],
    )
    names = {s.skill for s in skills}
    assert "Asynchronous Programming" not in names  # python-only pattern should be gated out

from pathlib import Path

import git
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from artifactminer.RepositoryIntelligence.framework_detector import detect_frameworks
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


def test_git_signals_count_user_merge_commits(tmp_path):
    repo_root = tmp_path / "git_signals_repo"
    repo_root.mkdir()
    repo = git.Repo.init(repo_root)

    main_file = repo_root / "file.txt"
    main_file.write_text("init")
    repo.index.add(["file.txt"])

    target_actor = git.Actor("Target User", "target@example.com")
    other_actor = git.Actor("Other User", "other@example.com")

    # Seed main with an initial commit by someone else
    repo.index.commit("initial", author=other_actor, committer=other_actor)

    # Feature branch merged by target author (should count)
    repo.git.checkout("-b", "feature1")
    main_file.write_text("user change 1")
    repo.index.add(["file.txt"])
    repo.index.commit("user change 1", author=target_actor, committer=target_actor)
    repo.git.checkout("main")
    main_file.write_text("user change 1 merged")
    repo.index.add(["file.txt"])
    repo.index.commit(
        "Merge branch 'feature1'",
        parent_commits=(repo.head.commit, repo.refs["feature1"].commit),
        author=target_actor,
        committer=target_actor,
    )

    # Feature branch merged by someone else but referencing target's PR number (should count)
    repo.git.checkout("-b", "feature2")
    main_file.write_text("other change 2")
    repo.index.add(["file.txt"])
    repo.index.commit("other change 2", author=other_actor, committer=other_actor)
    repo.git.checkout("main")
    main_file.write_text("other change 2 merged")
    repo.index.add(["file.txt"])
    repo.index.commit(
        "Merge pull request #99 from someone/feature2",
        parent_commits=(repo.head.commit, repo.refs["feature2"].commit),
        author=other_actor,
        committer=other_actor,
    )

    # Feature branch merged by someone else with no relation to user (should NOT count)
    repo.git.checkout("-b", "feature3")
    main_file.write_text("other change 3")
    repo.index.add(["file.txt"])
    repo.index.commit("other change 3", author=other_actor, committer=other_actor)
    repo.git.checkout("main")
    main_file.write_text("other change 3 merged")
    repo.index.add(["file.txt"])
    repo.index.commit(
        "Merge branch 'feature3'",
        parent_commits=(repo.head.commit, repo.refs["feature3"].commit),
        author=other_actor,
        committer=other_actor,
    )

    extractor = SkillExtractor(enable_llm=False)
    signals = extractor._git_signals(
        repo_root,
        {"user_email": "target@example.com", "pr_numbers": [99]},
    )

    assert signals["merge_commits"] == 2  # target-authored merge + PR #99 merge
    assert signals["branches"] >= 3  # main + feature branches


def test_shared_dependency_mapping_drives_detector_and_extractor(tmp_path):
    repo_root = tmp_path / "shared_mapping_repo"
    repo_root.mkdir()
    (repo_root / "requirements.txt").write_text("flask\n")

    extractor = SkillExtractor(enable_llm=False)
    skills = extractor.extract_skills(
        repo_path=repo_root,
        user_contributions={},
        consent_level="no_llm",
    )
    names = {s.skill for s in skills}
    assert "Flask" in names

    frameworks = detect_frameworks(repo_root)
    assert "Flask" in frameworks

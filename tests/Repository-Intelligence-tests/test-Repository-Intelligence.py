import sys
import os
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.artifactminer.RepositoryIntelligence.repo_intelligence_main import RepoStats, isGitRepo, getRepoStats, save_repo_stats

def test_create_RepoStats():
    mytestproject = RepoStats(project_name="test-project", primary_language="Python", is_collaborative=True)
    
    assert mytestproject.project_name == "test-project" #test to see if the name is correct
    assert mytestproject.primary_language == "Python" #test to see if the language is correct
    assert mytestproject.is_collaborative is True #test to see if the project is collaborative or not

def test_create_RepoStats_false():
    mytestproject_wrong = RepoStats(project_name="test-project-wrong", primary_language="Java", is_collaborative=False)
    
    assert mytestproject_wrong.project_name != "test-project" #test to see if the name does not match the last test, and that the variable is being set correctly
    assert mytestproject_wrong.primary_language != "Python" #test to see if the language does not match the last test, and that the variable is being set correctly
    assert mytestproject_wrong.is_collaborative is not True #test to see if the project is being set correctly to show if it is collaborative or not.

def test_isGitRepo(tmp_path):
    repo = tmp_path/"projA"
    (repo / ".git").mkdir(parents=True)
    assert isGitRepo(repo) is True #checks that the git directory exists inside of the given path

def test_isGitRepoFalse(tmp_path):
    not_repo = tmp_path/"projB"
    not_repo.mkdir()
    assert isGitRepo(not_repo) is False #checks that the git directory does not exists inside of the given path


def test_isGitRepo2(): #checks that our current repo is a git repo
    root = Path(__file__).resolve().parents[2]
    assert isGitRepo(root) is True #checks that the git directory exists inside of the given path

def test_getRepoStats():#checks that we can get the repo stats for our current repo
    root = Path(__file__).resolve().parents[2]
    stats = getRepoStats(root)
    assert isinstance(stats, RepoStats)
    assert isinstance(stats.project_name, str)
    assert isinstance(stats.primary_language, str)
    assert isinstance(stats.is_collaborative, bool)

def test_save_repo_stats(): #checks that we can save the repo stats to the database
    root = Path(__file__).resolve().parents[2]
    stats = getRepoStats(root)
    try:
        save_repo_stats(stats)
    except Exception as e:
        assert False, f"save_repo_stats raised an exception: {e}"

def test_select_repo_stats_from_db(): #checks that we can select the saved repo stats from the database
    from src.artifactminer.db.database import SessionLocal
    from src.artifactminer.db.models import RepoStat

    root = Path(__file__).resolve().parents[2]
    stats = getRepoStats(root)
    save_repo_stats(stats)#save the stats first

    db = SessionLocal()#create a new session
    repo_stat = db.query(RepoStat).filter(RepoStat.project_name == stats.project_name).first()#select the saved stats
    assert repo_stat is not None
    assert repo_stat.project_name == stats.project_name
    assert repo_stat.primary_language == stats.primary_language
    assert repo_stat.is_collaborative == stats.is_collaborative
    db.close()#close the session


import sys
import os


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.artifactminer.RepositoryIntelligence.repo_intelligence_main import RepoStats

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
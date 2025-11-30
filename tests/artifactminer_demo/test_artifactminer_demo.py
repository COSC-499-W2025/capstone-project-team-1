from sqlalchemy import text
from artifactminer.artifactminer_demo.artifactminer_demo import run_demo
import artifactminer.artifactminer_demo.artifactminer_demo as demo
from artifactminer.db.database import SessionLocal
def test_artifact_demo():
    demo.ZIPPATH = "/Users/nathanhelm/Code/Projects/capstone/capstone-project-team-1/tests/directorycrawler/mocks/mockdirectory-git.zip"
    demo.EMAIL = "ecrowl01@student.ubc.ca"
    demo.run_demo()
    db = SessionLocal()#create a new session (copied from test_repo_intelligence)
    sql ="SELECT * FROM repo_stats;"
    res = db.execute(text(sql)).all()
    objects = [dict(row._mapping) for row in res]
    assert objects[0]["project_name"] == "mockdirectory-git" 
    assert objects[1]["project_name"] == "mock-git_2"
    

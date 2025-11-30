from artifactminer.artifactminer_demo.artifactminer_demo import run_demo
import artifactminer.artifactminer_demo.artifactminer_demo as demo
def test_artifact_demo():
    demo.ZIPPATH = "/Users/nathanhelm/Code/Projects/capstone/capstone-project-team-1/tests/directorycrawler/mocks/mockdirectory-git.zip"
    demo.EMAIL = "ecrowl01@student.ubc.ca"
    demo.run_demo()
    

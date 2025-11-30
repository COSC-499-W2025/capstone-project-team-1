
import httpx
from sqlalchemy import text
from artifactminer.RepositoryIntelligence.repo_intelligence_user import getUserRepoStats, saveUserRepoStats
from artifactminer.db.database import SessionLocal
from artifactminer.helpers.project_ranker import rank_projects
from src.artifactminer.directorycrawler.directory_walk import crawl_directory
from src.artifactminer.directorycrawler.zip_file_handler import process_zip
import src.artifactminer.directorycrawler.directory_walk as d_walk
import httpx
import asyncio

#data needed for demonstration
EMAIL = "" 
USERCONFIG_EXCLUDEFILE = ""
USERCONFIG_INCLUDEFILE = ""
ZIPPATH = ""


async def analyze_repo(git_repos):

    for repo_path in git_repos:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/repos/analyze",
                params={
                    "repo_path": repo_path,
                    "user_email": EMAIL
                }  
            )


def run_demo(): 
    '''Here is the orchistration:'''   
    extracted_path = process_zip(ZIPPATH)[0] #extract zip file via process zip function

    #set path to crawler
    d_walk.CURRENTPATH = str(extracted_path)

    crawl_directory() #will return the stored git repo's

    git_repos = d_walk.STORE_GIT_REPO #returns list of repos that in the extracted zip file. 

    '''
    for repo in git_repos:
        repo_stats = getRepoStats(str(repo))
        saveRepoStats(repo_stats)
        user_stats = getUserRepoStats(str(repo), EMAIL)
        saveUserRepoStats(user_stats)
    '''

    #call analyze via post request
    for repo_path in git_repos:
        url = "http://localhost:8000/repos/analyze"
        params = {
        "repo_path": repo_path,
        "user_email": EMAIL
        }

    asyncio.run(analyze_repo(git_repos))

    ranking_results = rank_projects(str(extracted_path), EMAIL) 

    print(ranking_results)
    



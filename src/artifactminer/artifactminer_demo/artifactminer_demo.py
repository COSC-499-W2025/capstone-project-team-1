
import httpx
from sqlalchemy import text
from artifactminer.RepositoryIntelligence.repo_intelligence_user import generate_summaries_for_ranked, getUserRepoStats, saveUserRepoStats
from artifactminer.db.database import SessionLocal
from artifactminer.directorycrawler.store_file_dict import store_file_dict
from artifactminer.helpers.project_ranker import rank_projects
from src.artifactminer.directorycrawler.directory_walk import crawl_directory
from src.artifactminer.directorycrawler.zip_file_handler import process_zip
import src.artifactminer.directorycrawler.directory_walk as d_walk
import httpx
import asyncio

#data needed for demonstration
EMAIL = "" 
USERCONFIG_EXCLUDEFILE = []
USERCONFIG_INCLUDEFILE = []
ZIPPATH = ""

db = SessionLocal()

    

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
    extracted_path = process_zip(ZIPPATH)[0] #extract zip file path via process zip function

    #set path to crawler
    d_walk.CURRENTPATH = str(extracted_path)

    crawl_directory() #will return the stored git repo's

    git_repos = d_walk.STORE_GIT_REPO #returns list of repos that in the extracted zip file. 

    '''
    without a post request, we would use this to gather data
    for repo in git_repos:
        repo_stats = getRepoStats(str(repo))
        saveRepoStats(repo_stats)
        user_stats = getUserRepoStats(str(repo), EMAIL)
        saveUserRepoStats(user_stats)
    '''

    asyncio.run(analyze_repo(git_repos)) #uses post request to save git repos to database

    ranking_results = rank_projects(str(extracted_path), EMAIL) 
    print("Ranking ",ranking_results,"\n\n")
    summaries = generate_summaries_for_ranked(db) #get generated summaries
    print("Summaries ", summaries, "\n\n")
    print(store_file_dict.get_dict_len())
    print("crawler dictionary ", store_file_dict.get_values() , "\n\n") #get valid files from crawler

    


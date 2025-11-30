from artifactminer.RepositoryIntelligence.repo_intelligence_main import getRepoStats, saveRepoStats
from artifactminer.RepositoryIntelligence.repo_intelligence_user import getUserRepoStats, saveUserRepoStats
from src.artifactminer.directorycrawler.directory_walk import crawl_directory
from src.artifactminer.directorycrawler.zip_file_handler import process_zip
import src.artifactminer.directorycrawler.directory_walk as d_walk

#data needed for demonstration
EMAIL = "" 
USERCONFIG_EXCLUDEFILE = ""
USERCONFIG_INCLUDEFILE = ""
ZIPPATH = ""

def run_demo():    
    extracted_path = process_zip(ZIPPATH)[0] #extract zip file via process zip function

    #set path to crawler
    d_walk.CURRENTPATH = str(extracted_path)

    crawl_directory()

    git_repos = d_walk.STORE_GIT_REPO #returns list of repos that in the extracted zip file. 

    for repo in git_repos:
        repo_stats = getRepoStats(str(repo))
        saveRepoStats(repo_stats)
        user_stats = getUserRepoStats(str(repo), EMAIL)
        saveUserRepoStats(user_stats)

    #consider whether

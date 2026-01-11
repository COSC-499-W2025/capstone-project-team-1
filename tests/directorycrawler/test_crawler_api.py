import sys
import os
from pathlib import Path
import requests
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))) #goto project directory

from src.artifactminer.directorycrawler.store_file_dict import StoreFileDict #getting class from store file dict
from src.artifactminer.directorycrawler.directory_walk import crawl_directory,user_keep_file, user_exclude_file, CURRENTPATH, userExcludeFileName, userKeepFileName #getting function from directory walk
import src.artifactminer.directorycrawler.directory_walk as dw
a = StoreFileDict() #single instance


# YOU MUST RUN > uv run api in order for this to work


def test_api_call(): 

    response = post_file("/Users/nathanhelm/Code/Projects/capstone/capstone-project-team-1/tests/directorycrawler/mocks/mockdirectory_zip_test_duplicate.zip","mockdirectory_zip_test_duplicate.zip")
    
    print(response.status_code)
    print(response.json())

    assert 0 == 0

def post_file(path : str,fileName : str):
    
    url = "http://localhost:8000/upload"
    zip_path = path
    with open(zip_path, "rb") as f:
        files = {
            "file": (fileName, f, "application/zip")
        }
        response = requests.post(url, files=files)
    return response


  
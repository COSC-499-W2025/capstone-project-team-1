import sys
import os
from pathlib import Path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))) #goto project directory

from src.artifactminer.directorycrawler.directory_walk import (
    crawl_directory,
    user_keep_file, 
    user_exclude_file,
    store_file_dictionary,
    CURRENTPATH, 
    userExcludeFileName, 
    userKeepFileName
)
import src.artifactminer.directorycrawler.directory_walk as dw

def test_gathered_files_from_oswalk():
    store_file_dictionary.remove_all_dict()
    files_dict, dirs_list = crawl_directory()
    assert len(files_dict) == 4
    

def test_include_file_user_setting():
    store_file_dictionary.remove_all_dict()
    dw.userKeepFileName = []
    dw.userExcludeFileName = []
    user_keep_file("bugbomb.gitignore")
    user_keep_file("bugbomb.log")
    files_dict, dirs_list = crawl_directory()
    assert len(files_dict) == 5
    
def test_exclude_file_user_setting():
    store_file_dictionary.remove_all_dict()
    dw.userKeepFileName = []
    dw.userExcludeFileName = []
    user_keep_file("bugbomb.gitignore")
    user_keep_file("bugbomb.log")
    user_exclude_file("bugbomb.gitignore")
    user_exclude_file("bugbomb.log")
    files_dict, dirs_list = crawl_directory()
    assert len(files_dict) == 4



    
    

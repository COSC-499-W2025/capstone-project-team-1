import sys
import os
from pathlib import Path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))) #goto project directory

from src.artifactminer.directorycrawler.store_file_dict import StoreFileDict #getting class from store file dict
from src.artifactminer.directorycrawler.directory_walk import crawl_directory,user_keep_file, user_exclude_file, CURRENTPATH, userExcludeFileName, userKeepFileName #getting function from directory walk
import src.artifactminer.directorycrawler.directory_walk as dw
a = StoreFileDict() #single instance

def test_gathered_files_from_oswalk():
    crawl_directory() #crawl the mock directory
    assert a.get_dict_len() == 4 #assuming we are getting all files from mock directory
    a.remove_all_dict() #remove all elements from dictionary

def test_include_file_user_setting():

    # two files that won't be ignored
    user_keep_file("bugbomb.gitignore")
    user_keep_file("bugbomb.log")
    crawl_directory() 
    assert a.get_dict_len() == 6
    a.remove_all_dict()
    dw.userKeepFileName = []
    dw.userExcludeFileName = [] 
#
def test_exclude_file_user_setting():
    user_keep_file("bugbomb.gitignore")
    user_keep_file("bugbomb.log")
    user_exclude_file("bugbomb.gitignore")
    user_exclude_file("bugbomb.log")
    crawl_directory()
    assert a.get_dict_len() == 4
    a.remove_all_dict()
    dw.userKeepFileName = []
    dw.userExcludeFileName = [] 


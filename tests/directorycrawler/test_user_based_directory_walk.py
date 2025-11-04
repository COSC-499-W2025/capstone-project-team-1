import sys
import os
import copy
from pathlib import Path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))) #goto project directory

from src.artifactminer.directorycrawler.user_based_directory_walk import mock_adding_user_answer, get_user_data, delete_all_users
import src.artifactminer.directorycrawler.user_based_directory_walk as ubdw
from src.artifactminer.directorycrawler.store_file_dict import StoreFileDict #getting class from store file dict
from src.artifactminer.directorycrawler.directory_walk import crawl_directory,user_keep_file, user_exclude_file, CURRENTPATH #getting function from directory walk
import src.artifactminer.directorycrawler.directory_walk as dw
a = StoreFileDict() #single instance

def test_user_based_directory_walk():
    ubdw.INCLUDE_ANSWER_TEXT_EXAMPLE  = "mock2.js, bugbomb.log, none" 
    ubdw.EXCLUDE_ANSWER_TEXT_EXAMPLE = "mock.c" 
    mock_adding_user_answer()
    get_user_data()
    delete_all_users() #run last

    crawl_directory() #crawl the mock directory
    assert a.get_dict_len() == 4 #assuming we are getting all files from mock directory
    
    a.remove_all_dict() #remove all elements from dictionary
    dw.userKeepFileName = [] #reset user config list manually 
    dw.userExcludeFileName = [] 


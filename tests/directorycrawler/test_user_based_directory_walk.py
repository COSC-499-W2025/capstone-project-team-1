import sys
import os
import copy
from pathlib import Path

from artifactminer.db.seed import seed_questions
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))) #goto project directory

from artifactminer.db.database import SessionLocal
from src.artifactminer.directorycrawler.user_based_directory_walk import get_user_data, delete_all_user_questions, add_user_answer
import src.artifactminer.directorycrawler.user_based_directory_walk as ubdw
from src.artifactminer.directorycrawler.store_file_dict import StoreFileDict #getting class from store file dict
from src.artifactminer.directorycrawler.directory_walk import crawl_directory,user_keep_file, user_exclude_file, CURRENTPATH,update_path #getting function from directory walk
import src.artifactminer.directorycrawler.directory_walk as dw
a = StoreFileDict() #single instance

def test_user_based_directory_walk():
    
    dw.MOCKNAME = "mockdirectory1" #change to a new mock directory
    

     # Initialize database schema and seed
    db = SessionLocal()
    try:
        seed_questions(db)
    finally:
        db.close()

    #NOTE the function add user is for TESTING ONLY. 
    #we should use keynames not id's 

    add_user_answer(db, 5, "keep.log, *.avi") #include
    add_user_answer(db, 6, "*.c") #exclude (remove all c files from mock)
    get_user_data(db)
    delete_all_user_questions(db)
    update_path()
    crawl_directory() #crawl the mock directory
    assert a.get_dict_len() == 2 #assuming we are getting all files from mock directory
    
    a.remove_all_dict() #remove all elements from dictionary
    dw.userKeepFileName = [] #reset user config list manually 
    dw.userExcludeFileName = [] 


import sys
import os
import copy

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))) #goto project directory

from src.artifactminer.directorycrawler.store_file_dict import StoreFileDict #getting class from store file dict
from src.artifactminer.directorycrawler.directory_walk import simple_directory_crawl

a = StoreFileDict() #single instance

def test_gathered_files_from_oswalk():
    simple_directory_crawl() 
    assert a.get_dict_len() == 4 #assuming we are getting all files from mock directory
    a.remove_all_dict() #remove all elements from dictionary

    
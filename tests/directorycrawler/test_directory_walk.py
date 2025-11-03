import sys
import os
import copy
from pathlib import Path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))) #goto project directory

from src.artifactminer.directorycrawler.store_file_dict import StoreFileDict #getting class from store file dict
from src.artifactminer.directorycrawler.directory_walk import simple_directory_crawl_from_path #getting function from directory walk

a = StoreFileDict() #single instance

def test_gathered_files_from_oswalk():
    root = Path(__file__) #get current file path
    mock_dir = root.parent / "mocks" / "mockdirectory" #get mock directory path
    simple_directory_crawl_from_path(mock_dir) #crawl the mock directory
    assert a.get_dict_len() == 4 #assuming we are getting all files from mock directory
    a.remove_all_dict() #remove all elements from dictionary

    
import sys
import os
from pathlib import Path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))) #goto project directory

from src.artifactminer.directorycrawler.store_file_dict import store_file_dict  #getting class from store file dict
from src.artifactminer.directorycrawler.directory_walk import crawl_directory, print_values_in_dict  #getting function from directory walk
import src.artifactminer.directorycrawler.directory_walk as dw
a = store_file_dict #single instance

def test_check_file_duplicate():
    a.remove_all_dict()
    dw.MOCKNAME = "mockdirectory2" #change to a new mock directory
    dw.update_path()
    crawl_directory()
    print_values_in_dict()
    assert a.get_dict_len() == 2 # 1 is readme text file, 2 is c file, other c file should be removed!

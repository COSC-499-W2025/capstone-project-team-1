import sys
import os
from pathlib import Path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.artifactminer.directorycrawler.directory_walk import crawl_directory, print_values_in_dict, store_file_dictionary
import src.artifactminer.directorycrawler.directory_walk as dw

def test_check_file_duplicate():
    store_file_dictionary.remove_all_dict()
    dw.MOCKNAME = "mockdirectory2"
    dw.update_path()
    files_dict, dirs_list = crawl_directory()
    print_values_in_dict()
    assert len(files_dict) == 2


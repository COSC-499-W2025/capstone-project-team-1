import sys
import os


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))) #goto project directory

from src.artifactminer.directorycrawler.store_file_dict import StoreFileDict #getting class from store file dict

a = StoreFileDict() #getting a single instance because we are using a singleton pattern!

def test_add():
    a.add_to_dict(1, "one") 
    a.add_to_dict(2, "two")
    assert a.get_dict_len() == 2

def test_remove():
    a.remove_from_dict(1)
    a.remove_from_dict(2)
    assert a.get_dict_len() == 0

def test_get():
    a.add_to_dict(100, "hundred")
    x = a.get_dict(100)
    assert x == "hundred"







import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))) #goto project directory

from src.artifactminer.directorycrawler.zip_file_handler import process_zip
dirname = os.path.dirname(__file__)
zipfile = os.path.join(dirname,"mocks/mockdirectory_zip.zip")
nonzipfile = os.path.join(dirname,"mocks/mockdirectory/mock.c")
assert process_zip(zipfile, True) != None
assert process_zip(nonzipfile) == None
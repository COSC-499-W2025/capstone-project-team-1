import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))) #goto project directory

from src.artifactminer.directorycrawler.zip_file_handler import process_zip
assert process_zip("./mocks/mockdirectory_zip.zip",True) != None
assert process_zip("./mocks/mockdirectory/mock.c") == None
import sys
import os
import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))) #goto project directory

from src.artifactminer.directorycrawler.zip_file_handler import process_zip
dirname = os.path.dirname(__file__)
zipfile = os.path.join(dirname,"mocks/mockdirectory_zip.zip")
nonzipfile = os.path.join(dirname,"mocks/mockdirectory/mock.c")
def test_read_zip():
    assert process_zip(zipfile, True) is not None
def test_dont_read_nonzip():
    with pytest.raises(ValueError):
        process_zip(nonzipfile)
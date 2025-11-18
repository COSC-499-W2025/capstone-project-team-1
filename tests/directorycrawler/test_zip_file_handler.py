import sys
import os
import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))) #goto project directory

from src.artifactminer.directorycrawler.zip_file_handler import process_zip, extract_directory_tree, extract_selected_to_temp
dirname = os.path.dirname(__file__)
zipfile = os.path.join(dirname,"mocks/mockdirectory_zip.zip")
nonzipfile = os.path.join(dirname,"mocks/mockdirectory/mock.c")
templocation = os.path.join(dirname,"mocks/temp")
def test_read_zip():
    assert process_zip(zipfile, True) is not None
def test_dont_read_nonzip():
    with pytest.raises(ValueError):
        process_zip(nonzipfile)
def test_extract_directory_tree():
    assert extract_directory_tree(zipfile) == ["child/"]

    # TEST REQUIRES PYTHON 3.10 OR LATER, PLEASE CHECK VERSION BEFORE REPORTING TEST FAILURE
def test_extract_selected_to_temp():
    assert len(extract_selected_to_temp(zipfile, ["mock1.js","mock.c"],templocation)) == 2
    os.remove(os.path.join(templocation,"mockdirectory_zip/mock1.js"))
    os.remove(os.path.join(templocation,"mockdirectory_zip/mock.c"))
    os.rmdir(os.path.join(templocation,"mockdirectory_zip/"))
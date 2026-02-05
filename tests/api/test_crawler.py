
from pathlib import Path
from artifactminer.directorycrawler.directory_walk import user_keep_extension
from artifactminer.FileIntelligence.file_intelligence_main import get_crawler_pdf_contents
import shutil

MOCK_CONFIG_PATH =  Path(__file__).parent/ "../directorycrawler" / "mocks" / "config_mock"
MOCKS_PATH = Path(__file__).parent/ "../directorycrawler" / "mocks"
DEFAULT_ZIP_PATH = Path(__file__).parent/ "../directorycrawler" / "mocks" / "mockdirectory_zip_test_duplicate.zip"
CONFIG_ZIP_PATH = MOCK_CONFIG_PATH.with_suffix(".zip")


def upload_zip_for_test(client, path):
    response = None
    with path.open("rb") as f:
        files = {"file": (path.name, f, "application/zip")}
        response = client.post("/zip/upload", files=files)
    return response

def directory_to_zip(dir_path: Path, output_zip: Path):
    shutil.make_archive(
        base_name=str(output_zip.with_suffix("")),
        format="zip",
        root_dir=dir_path
    )

def append_file_to_path(file_name, data=None):
    """
    Add a file to MOCK_CONFIG_PATH.
    - If `data` is provided, create the file with that content.
    - If `data` is None, try to copy it from MOCKS_PATH if it exists.
    """
    MOCK_CONFIG_PATH.mkdir(parents=True, exist_ok=True)
    dest_path = MOCK_CONFIG_PATH / file_name

    if data is not None:
        # Create the file with content
        dest_path.write_text(data)
        print(f"Created file '{dest_path}' with data.")
    else:
        # Copy/move the file from MOCKS_PATH if it exists
        source_path = MOCKS_PATH / file_name
        if source_path.exists():
            shutil.copy(source_path, dest_path)
            print(f"Copied file '{source_path}' to '{dest_path}'")
        else:
            print(f"Warning: Source file '{source_path}' does not exist.")

def test_ignore_files(client):
    
    """
    Comprehensive test, I have added filenames below, each with their own data. 
    Crawler: performs checks cleans data
    User configuration requests that ".keepme" file can stay; output reacts accordingly.
    """
    append_file_to_path('my_ignored_file.ignoreextension', "data")
    append_file_to_path('keep_this_file.keepme', "data")  #adds this file to directory based on user request.
    append_file_to_path('allowed.c', "int x = 0;") 
    append_file_to_path('allowed1.c', "int y = 0;")
    append_file_to_path('allowed2.c', "int z = 0;") 
    
    directory_to_zip(MOCK_CONFIG_PATH, CONFIG_ZIP_PATH)
    response = upload_zip_for_test(client=client, path=CONFIG_ZIP_PATH)

    user_keep_extension(".keepme") #file we are keeping

    payload = response.json()
    
    assert payload["zip_id"] == 1
    assert payload["filename"] == "config_mock.zip"
    assert response.status_code == 200

    response = client.post("/crawler", params={ "zip_id" : 1 })
    payload = response.json()
    
    expected_files = [
    #ignore data extension has been rejected...
    {'file_path': '.extracted/1/keep_this_file.keepme', 'file_name': 'keep_this_file.keepme', 'file_ext': '.keepme'},
    {'file_path': '.extracted/1/allowed.c', 'file_name': 'allowed.c', 'file_ext': '.c'},
    {'file_path': '.extracted/1/allowed1.c', 'file_name': 'allowed1.c', 'file_ext': '.c'},
    {'file_path': '.extracted/1/allowed2.c', 'file_name': 'allowed2.c', 'file_ext': '.c'},
    


    ]
    assert payload["crawl_path_and_file_name_and_ext"] == expected_files

def test_api_call(client, tmp_path, monkeypatch):
    
   # _redirect_uploads(monkeypatch=monkeypatch, tmp_path=tmp_path)
   #1) adding data to data base via upload api call...
    response = upload_zip_for_test(client=client, path=DEFAULT_ZIP_PATH)
    payload = response.json()
  
    assert payload["zip_id"] == 1
    assert payload["filename"] == "mockdirectory_zip_test_duplicate.zip"
    assert response.status_code == 200


    #2) perform api post call on crawler...
    response = client.post("/crawler", params={ "zip_id" : 1 })
    data = response.json()
    assert data["zip_id"] == 1

    # Check that the mocked values appear correctly
    expected_files = [
    
      {'file_path': '.extracted/1/mockdirectory_zip_test_duplicate/README.txt', 'file_name': 'README.txt', 'file_ext': '.txt'},
      {'file_path': '.extracted/1/mockdirectory_zip_test_duplicate/dupcopy.c', 'file_name': 'dupcopy.c', 'file_ext': '.c'}
    
    ]

    assert data["crawl_path_and_file_name_and_ext"] == expected_files

#testing file intelligence

async def test_get_crawler_content_pdf_analysis(client):
        
    pdf_path = Path(__file__).parent/ "../directorycrawler" / "mocks" / "pdfdirectory.zip"
    response = upload_zip_for_test(client=client, path=pdf_path)
    payload = response.json()
    

    assert payload["zip_id"] == 1
    assert payload["filename"] == "pdfdirectory.zip"
    assert response.status_code == 200

    zip_id = payload["zip_id"]
    response = await get_crawler_pdf_contents(zip_id=zip_id)
    payload = response.json()

    

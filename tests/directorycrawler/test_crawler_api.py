from pathlib import Path
import requests

from artifactminer.directorycrawler.store_file_dict import StoreFileDict

a = StoreFileDict()

def test_api_call():
    zip_path = Path(__file__).parent / "mocks" / "mockdirectory_zip_test_duplicate.zip"
    response = post_file(zip_path)

    assert response.status_code == 200

def post_file(zip_path: Path):
    url = "http://localhost:8000/upload"

    with zip_path.open("rb") as f:
        files = {"file": (zip_path.name, f, "application/zip")}
        return requests.post(url, files=files)

  
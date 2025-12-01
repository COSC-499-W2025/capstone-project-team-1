
def test_get_crawler_contents(client):
     
        #add data to database then call post... 

    response = client.post("/1")

    data = response.json()
    assert data["zip_id"] == 1
    assert isinstance(data["crawl_path_and_file_name"], list)
    # Check that the mocked values appear correctly
    expected_files = [
    {
      "file_path": "extracted/1/mockdirectory_zip/child/childinchild/Unknown.jpeg",
      "file_name": "Unknown.jpeg"
    }
    ]

    assert data["crawl_path_and_file_name"] == expected_files
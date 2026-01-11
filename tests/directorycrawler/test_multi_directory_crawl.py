"""Tests for crawling multiple directories (incremental portfolio upload feature)."""

import sys
import os
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src.artifactminer.directorycrawler.directory_walk import crawl_multiple_directories
from src.artifactminer.directorycrawler.store_file_dict import StoreFileDict
import src.artifactminer.directorycrawler.directory_walk as dw

MOCKS_DIR = Path(__file__).parent / "mocks"
store = StoreFileDict()


def test_crawl_multiple_directories_combines_files():
    """Test that files from multiple directories are combined."""
    store.remove_all_dict()
    dw.userKeepFileName = []
    dw.userExcludeFileName = []

    paths = [MOCKS_DIR / "mockdirectory1", MOCKS_DIR / "mockdirectory2"]
    file_dict, dir_list = crawl_multiple_directories(paths)

    file_names = [v[0] for v in file_dict.values()]
    assert "test.py" in file_names
    assert "test2.c" in file_names
    assert "README.txt" in file_names


def test_crawl_multiple_directories_deduplicates_dirs():
    """Test that duplicate directory names are not repeated."""
    store.remove_all_dict()
    dw.userKeepFileName = []
    dw.userExcludeFileName = []

    paths = [MOCKS_DIR / "mockdirectory1", MOCKS_DIR / "mockdirectory2"]
    _, dir_list = crawl_multiple_directories(paths)

    assert len(dir_list) == len(set(dir_list))


def test_crawl_multiple_directories_handles_nonexistent():
    """Test that non-existent paths are skipped gracefully."""
    store.remove_all_dict()
    dw.userKeepFileName = []
    dw.userExcludeFileName = []

    paths = [MOCKS_DIR / "mockdirectory1", MOCKS_DIR / "does_not_exist"]
    file_dict, _ = crawl_multiple_directories(paths)

    file_names = [v[0] for v in file_dict.values()]
    assert "test.py" in file_names


def test_crawl_multiple_directories_empty_list():
    """Test that empty path list returns empty results."""
    store.remove_all_dict()
    file_dict, dir_list = crawl_multiple_directories([])

    assert file_dict == {}
    assert dir_list == []


def test_crawl_multiple_directories_single_path():
    """Test that single path works same as crawl_directory."""
    store.remove_all_dict()
    dw.userKeepFileName = []
    dw.userExcludeFileName = []

    paths = [MOCKS_DIR / "mockdirectory1"]
    file_dict, _ = crawl_multiple_directories(paths)

    file_names = [v[0] for v in file_dict.values()]
    assert "test.py" in file_names
    assert "test2.c" in file_names


def test_crawl_multiple_directories_deduplicates_identical_files(tmp_path):
    """Test that identical files across different paths are deduplicated by hash."""
    store.remove_all_dict()
    dw.userKeepFileName = []
    dw.userExcludeFileName = []

    dir1 = tmp_path / "portfolio1"
    dir2 = tmp_path / "portfolio2"
    dir1.mkdir()
    dir2.mkdir()

    (dir1 / "shared.py").write_text("print('hello world')")
    (dir2 / "shared.py").write_text("print('hello world')")
    (dir2 / "unique.py").write_text("print('unique file')")

    file_dict, _ = crawl_multiple_directories([dir1, dir2])

    file_names = [v[0] for v in file_dict.values()]
    assert file_names.count("shared.py") == 1
    assert "unique.py" in file_names
    assert len(file_dict) == 2

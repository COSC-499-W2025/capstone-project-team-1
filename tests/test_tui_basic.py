"""Basic tests for TUI functionality"""
import os
import tempfile
from pathlib import Path
from artifactminer.tui.services.prefs import validate_path, load_prefs, save_prefs


def test_validate_path_empty():
    """Test validation rejects empty paths"""
    ok, msg = validate_path("")
    assert not ok
    assert "empty" in msg.lower()


def test_validate_path_relative():
    """Test validation rejects relative paths"""
    ok, msg = validate_path("relative/path")
    assert not ok
    assert "absolute" in msg.lower()


def test_validate_path_nonexistent():
    """Test validation rejects non-existent directories"""
    ok, msg = validate_path("/nonexistent/path/12345")
    assert not ok
    assert "exist" in msg.lower()


def test_validate_path_valid():
    """Test validation accepts valid directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        ok, msg = validate_path(tmpdir)
        assert ok
        assert msg == ""


def test_save_and_load_prefs():
    """Test preferences can be saved and loaded"""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_config = Path(tmpdir) / "test_config.json"

        # Temporarily replace CONFIG_PATH
        from artifactminer.tui.services import prefs
        original_path = prefs.CONFIG_PATH
        prefs.CONFIG_PATH = test_config

        try:
            test_data = {"scan_paths": ["/test/path1", "/test/path2"]}
            save_prefs(test_data)

            loaded = load_prefs()
            assert loaded == test_data
            assert len(loaded["scan_paths"]) == 2
        finally:
            prefs.CONFIG_PATH = original_path

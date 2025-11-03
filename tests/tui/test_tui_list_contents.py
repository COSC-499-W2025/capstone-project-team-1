from pathlib import Path
from types import SimpleNamespace
import zipfile

import pytest

from textual.app import active_app

import artifactminer.tui.screens.upload as upload_module
from artifactminer.tui.screens.list_contents import ListContentsScreen
from artifactminer.tui.screens.upload import MOCK_DIRS, UploadScreen, list_zip_dirs


class StatusStub:
    """Capture status updates without relying on textual widgets."""

    def __init__(self) -> None:
        self.message: str | None = None

    def update(self, message: str) -> None:
        self.message = message


class InputStub:
    """Simplified Input replacement that tracks focus calls."""

    def __init__(self, value: str) -> None:
        self.value = value
        self.focus_called = False

    def focus(self) -> None:
        self.focus_called = True


@pytest.mark.asyncio
async def test_upload_screen_pushes_mock_list_screen(tmp_path: Path) -> None:
    """Ensure UploadScreen routes to ListContentsScreen with mock directories."""
    zip_path = tmp_path / "artifact.zip"
    zip_path.touch()

    screen = UploadScreen()
    field = InputStub(str(zip_path))
    status = StatusStub()

    def fake_query_one(selector: str, _expected=None):
        if selector == "#zip-path":
            return field
        if selector == "#status":
            return status
        raise AssertionError(f"Unexpected selector: {selector}")

    screen.query_one = fake_query_one  # type: ignore[assignment]

    pushed: dict[str, object] = {}

    async def fake_push_screen(
        list_screen: ListContentsScreen, callback=None, wait_for_dismiss: bool = False
    ) -> None:
        pushed["screen"] = list_screen
        pushed["callback"] = callback
        pushed["wait_for_dismiss"] = wait_for_dismiss

    event = SimpleNamespace(button=SimpleNamespace(id="upload-btn"))

    original_use_mock = upload_module.USE_MOCK
    upload_module.USE_MOCK = True
    token = active_app.set(SimpleNamespace(push_screen=fake_push_screen))
    try:
        await screen.on_button_pressed(event)
    finally:
        active_app.reset(token)
        upload_module.USE_MOCK = original_use_mock

    assert "screen" in pushed
    list_screen = pushed["screen"]
    assert isinstance(list_screen, ListContentsScreen)
    assert list_screen.dirs == MOCK_DIRS
    assert pushed.get("callback") is not None
    assert pushed.get("wait_for_dismiss") is False


def test_list_zip_dirs_returns_expected_structure(tmp_path: Path) -> None:
    """Ensure list_zip_dirs() extracts top-level folders and files from a zip file."""
    zip_path = tmp_path / "test.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("src/main.py", "")
        zf.writestr("docs/readme.md", "")
        zf.writestr("requirements.txt", "")

    dirs = list_zip_dirs(zip_path)

    assert "src/" in dirs
    assert "docs/" in dirs
    assert "requirements.txt" in dirs
    assert len(dirs) == 3

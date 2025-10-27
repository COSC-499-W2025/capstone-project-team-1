from pathlib import Path
from types import SimpleNamespace
import zipfile

import pytest

from textual.app import active_app

from artifactminer.tui import app as tui_app
from artifactminer.tui.app import (
    ListContentsScreen,
    MOCK_DIRS,
    UploadScreen,
    list_zip_dirs,
)


class StatusStub:
    """Capture status updates without relying on textual widgets."""

    def __init__(self) -> None:
        self.message: str | None = None

    def update(self, message: str) -> None:
        self.message = message


@pytest.mark.asyncio
async def test_upload_screen_pushes_mock_list_screen(tmp_path: Path) -> None:
    """Ensure UploadScreen routes to ListContentsScreen with mock directories."""
    zip_path = tmp_path / "artifact.zip"
    zip_path.touch()

    screen = UploadScreen()
    field = SimpleNamespace(value=str(zip_path))
    status = StatusStub()

    def fake_query_one(selector: str, _expected=None):
        if selector == "#zip-path":
            return field
        if selector == "#status":
            return status
        raise AssertionError(f"Unexpected selector: {selector}")

    screen.query_one = fake_query_one  # type: ignore[assignment]

    pushed: dict[str, ListContentsScreen] = {}

    async def fake_push_screen(list_screen: ListContentsScreen) -> None:
        pushed["screen"] = list_screen

    event = SimpleNamespace(button=SimpleNamespace(id="upload-btn"))

    original_use_mock = tui_app.USE_MOCK
    tui_app.USE_MOCK = True
    token = active_app.set(SimpleNamespace(push_screen=fake_push_screen))
    try:
        await screen.on_button_pressed(event)
    finally:
        active_app.reset(token)
        tui_app.USE_MOCK = original_use_mock

    assert "screen" in pushed
    list_screen = pushed["screen"]
    assert isinstance(list_screen, ListContentsScreen)
    assert list_screen.dirs == MOCK_DIRS


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

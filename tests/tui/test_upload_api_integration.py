from pathlib import Path
from types import SimpleNamespace

import pytest

from artifactminer.tui.screens.upload import UploadScreen
from artifactminer.tui.screens.list_contents import ListContentsScreen


class LabelStub:
    def __init__(self) -> None:
        self.text = ""

    def update(self, message: str) -> None:
        self.text = message


class InputStub:
    def __init__(self, value: str) -> None:
        self.value = value

    def focus(self) -> None:  # noqa: D401
        return None


@pytest.mark.asyncio
async def test_upload_screen_uses_zip_id_and_renders_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """UploadScreen uses API zip_id to list and display dirs."""
    zip_path = tmp_path / "artifact.zip"
    zip_path.touch()

    screen = UploadScreen()
    field = InputStub(str(zip_path))
    status = LabelStub()

    def fake_query_one(selector: str, _expected=None):
        if selector == "#zip-path":
            return field
        if selector == "#status":
            return status
        raise AssertionError(f"Unexpected selector: {selector}")

    screen.query_one = fake_query_one  # type: ignore[assignment]

    pushed: dict[str, object] = {}

    async def fake_push_screen(list_screen: ListContentsScreen, callback=None, wait_for_dismiss: bool = False):
        pushed["screen"] = list_screen
        pushed["wait_for_dismiss"] = wait_for_dismiss
        pushed["callback"] = callback

    called: dict[str, object] = {}

    class FakeClient:
        async def upload_zip(self, p: Path):  # noqa: D401
            called["upload_zip_path"] = p
            return {"zip_id": 42, "filename": p.name}

        async def list_zip_directories(self, zip_id: int):  # noqa: D401
            called["list_zip_directories_zip_id"] = zip_id
            return {"zip_id": zip_id, "filename": "artifact.zip", "directories": ["src/", "README.md"]}

    import artifactminer.tui.screens.upload as upload_module

    monkeypatch.setattr(upload_module, "ApiClient", lambda: FakeClient())

    from textual.app import active_app
    token = active_app.set(SimpleNamespace(push_screen=fake_push_screen))

    event = SimpleNamespace(button=SimpleNamespace(id="upload-btn"))
    try:
        await screen.on_button_pressed(event)
    finally:
        active_app.reset(token)

    assert called.get("upload_zip_path") == zip_path
    assert called.get("list_zip_directories_zip_id") == 42

    assert isinstance(pushed.get("screen"), ListContentsScreen)
    list_screen = pushed["screen"]  # type: ignore[index]
    assert list_screen.dirs == ["src", "README.md"]


@pytest.mark.asyncio
async def test_upload_screen_handles_empty_directories_response(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Empty directories response shows message and no navigation."""
    zip_path = tmp_path / "empty.zip"
    zip_path.touch()

    screen = UploadScreen()
    field = InputStub(str(zip_path))
    status = LabelStub()

    def fake_query_one(selector: str, _expected=None):
        if selector == "#zip-path":
            return field
        if selector == "#status":
            return status
        raise AssertionError(selector)

    screen.query_one = fake_query_one  # type: ignore[assignment]

    class FakeClientEmpty:
        async def upload_zip(self, p: Path):
            return {"zip_id": 7, "filename": p.name}

        async def list_zip_directories(self, zip_id: int):
            return {"zip_id": zip_id, "filename": "empty.zip", "directories": []}

    import artifactminer.tui.screens.upload as upload_module

    monkeypatch.setattr(upload_module, "ApiClient", lambda: FakeClientEmpty())

    pushed = {"screen": None}

    async def fake_push_screen(_s, **_k):
        pushed["screen"] = _s

    from textual.app import active_app
    token = active_app.set(SimpleNamespace(push_screen=fake_push_screen))

    event = SimpleNamespace(button=SimpleNamespace(id="upload-btn"))
    try:
        await screen.on_button_pressed(event)
    finally:
        active_app.reset(token)

    assert pushed["screen"] is None
    assert status.text == "No contents found in archive."


@pytest.mark.asyncio
async def test_upload_screen_shows_error_if_api_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """An exception from the API should be surfaced to the status label."""
    zip_path = tmp_path / "bad.zip"
    zip_path.touch()

    screen = UploadScreen()
    field = InputStub(str(zip_path))
    status = LabelStub()

    def fake_query_one(selector: str, _expected=None):
        if selector == "#zip-path":
            return field
        if selector == "#status":
            return status
        raise AssertionError(selector)

    screen.query_one = fake_query_one  # type: ignore[assignment]

    class FakeClientError:
        async def upload_zip(self, p: Path):  # noqa: ARG002 - consistent signature
            raise RuntimeError("upload failed")

    import artifactminer.tui.screens.upload as upload_module

    monkeypatch.setattr(upload_module, "ApiClient", lambda: FakeClientError())

    pushed = {"screen": None}

    async def fake_push_screen(_s, **_k):
        pushed["screen"] = _s

    from textual.app import active_app
    token = active_app.set(SimpleNamespace(push_screen=fake_push_screen))

    event = SimpleNamespace(button=SimpleNamespace(id="upload-btn"))
    try:
        await screen.on_button_pressed(event)
    finally:
        active_app.reset(token)

    assert pushed["screen"] is None
    assert status.text.startswith("Error: ")

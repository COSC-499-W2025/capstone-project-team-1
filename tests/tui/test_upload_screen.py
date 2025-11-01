from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from textual.app import active_app

from artifactminer.tui.app import UploadScreen


class StatusStub:
    """Capture status updates without needing a textual Label instance."""

    def __init__(self) -> None:
        self.message: str | None = None

    def update(self, message: str) -> None:
        self.message = message


class InputStub:
    """Minimal stand-in for textual Input that records focus calls."""

    def __init__(self, value: str) -> None:
        self.value = value
        self.focus_called = False

    def focus(self) -> None:
        self.focus_called = True


def make_screen(input_value: str) -> tuple[UploadScreen, StatusStub, InputStub]:
    screen = UploadScreen()
    field = InputStub(input_value)
    status = StatusStub()

    def fake_query_one(selector: str, _expected_type):
        if selector == "#zip-path":
            return field
        if selector == "#status":
            return status
        raise AssertionError(f"Unexpected selector: {selector}")

    screen.query_one = fake_query_one  # type: ignore[assignment]
    return screen, status, field


def make_event(button_id: str = "upload-btn") -> SimpleNamespace:
    return SimpleNamespace(button=SimpleNamespace(id=button_id))


@pytest.mark.asyncio
async def test_upload_screen_requires_path() -> None:
    screen, status, _ = make_screen("   ")

    await screen.on_button_pressed(make_event())

    assert status.message == "Please enter a path."


@pytest.mark.asyncio
async def test_upload_screen_missing_file(tmp_path: Path) -> None:
    missing_path = tmp_path / "not_there.zip"
    screen, status, _ = make_screen(str(missing_path))

    await screen.on_button_pressed(make_event())

    assert status.message == f"File not found: {missing_path}"


@pytest.mark.asyncio
async def test_upload_screen_accepts_zip(tmp_path: Path) -> None:
    zip_path = tmp_path / "artifact.zip"
    zip_path.touch()
    screen, status, field = make_screen(str(zip_path))
    captured: dict[str, object] = {}

    async def _fake_push_screen(_screen, callback=None, wait_for_dismiss=False):
        captured["screen"] = _screen
        captured["callback"] = callback
        assert wait_for_dismiss is False
        return None

    token = active_app.set(SimpleNamespace(push_screen=_fake_push_screen))
    try:
        await screen.on_button_pressed(make_event())
    finally:
        active_app.reset(token)

    assert status.message == "Processing ZIP contents..."
    assert "screen" in captured
    callback = captured.get("callback")
    assert callable(callback)
    callback(None)  # type: ignore[operator]
    assert status.message == "Waiting for a file..."
    assert field.value == ""
    assert field.focus_called is True


@pytest.mark.asyncio
async def test_upload_screen_back_returns_to_userconfig() -> None:
    screen, status, field = make_screen("~/project.zip")
    status.update("Processing ZIP contents...")
    switch_calls: list[str] = []

    async def fake_switch(name, *_, **__):
        switch_calls.append(name)

    token = active_app.set(
        SimpleNamespace(push_screen=lambda *a, **k: None, switch_screen=fake_switch)
    )
    try:
        await screen.on_button_pressed(make_event("back-btn"))
    finally:
        active_app.reset(token)

    assert status.message == "Waiting for a file..."
    assert field.value == ""
    assert field.focus_called is True
    assert switch_calls == ["userconfig"]

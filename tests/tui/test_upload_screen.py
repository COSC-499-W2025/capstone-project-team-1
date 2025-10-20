from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from artifactminer.tui.app import UploadScreen


class StatusStub:
    """Capture status updates without needing a textual Label instance."""

    def __init__(self) -> None:
        self.message: str | None = None

    def update(self, message: str) -> None:
        self.message = message


def make_screen(input_value: str) -> tuple[UploadScreen, StatusStub]:
    screen = UploadScreen()
    field = SimpleNamespace(value=input_value)
    status = StatusStub()

    def fake_query_one(selector: str, _expected_type):
        if selector == "#zip-path":
            return field
        if selector == "#status":
            return status
        raise AssertionError(f"Unexpected selector: {selector}")

    screen.query_one = fake_query_one  # type: ignore[assignment]
    return screen, status


def make_event(button_id: str = "upload-btn") -> SimpleNamespace:
    return SimpleNamespace(button=SimpleNamespace(id=button_id))


@pytest.mark.asyncio
async def test_upload_screen_requires_path() -> None:
    screen, status = make_screen("   ")

    await screen.on_button_pressed(make_event())

    assert status.message == "Please enter a path."


@pytest.mark.asyncio
async def test_upload_screen_missing_file(tmp_path: Path) -> None:
    missing_path = tmp_path / "not_there.zip"
    screen, status = make_screen(str(missing_path))

    await screen.on_button_pressed(make_event())

    assert status.message == f"File not found: {missing_path}"


@pytest.mark.asyncio
async def test_upload_screen_accepts_zip(tmp_path: Path) -> None:
    zip_path = tmp_path / "artifact.zip"
    zip_path.touch()
    screen, status = make_screen(str(zip_path))

    await screen.on_button_pressed(make_event())

    assert status.message == f"Got it: {zip_path.name}"

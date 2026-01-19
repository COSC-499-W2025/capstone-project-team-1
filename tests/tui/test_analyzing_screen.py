"""Tests for AnalyzingScreen TUI component."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from textual.app import active_app

from artifactminer.tui.screens.analyzing import AnalyzingScreen


class DummyApp:
    """Stubbed app with navigation and notification hooks."""

    def __init__(self) -> None:
        self.popped = False
        self.switched_to: str | None = None
        self.notifications: list[tuple[str, dict]] = []

    def pop_screen(self) -> None:
        self.popped = True

    async def switch_screen(self, name: str) -> None:
        self.switched_to = name

    def notify(self, message: str, **kwargs) -> None:
        self.notifications.append((message, kwargs))


def make_screen(zip_id: int | None = 123) -> tuple[AnalyzingScreen, DummyApp, object]:
    """Create AnalyzingScreen with stubs."""
    screen = AnalyzingScreen(zip_id=zip_id)
    app = DummyApp()
    token = active_app.set(app)
    return screen, app, token


@pytest.mark.asyncio
async def test_analyzing_back_button_pops_screen() -> None:
    """Ensure Back button pops the screen."""
    screen, app, token = make_screen()
    try:
        await screen.on_button_pressed(SimpleNamespace(button=SimpleNamespace(id="back-btn")))
        assert app.popped is True
    finally:
        active_app.reset(token)


@pytest.mark.asyncio
async def test_analyzing_continue_navigates_to_resume() -> None:
    """Ensure Continue button navigates to resume screen."""
    screen, app, token = make_screen()
    try:
        await screen.on_button_pressed(SimpleNamespace(button=SimpleNamespace(id="continue-btn")))
        assert app.switched_to == "resume"
    finally:
        active_app.reset(token)


def test_analyzing_receives_zip_id() -> None:
    """Ensure AnalyzingScreen stores zip_id correctly."""
    screen = AnalyzingScreen(zip_id=456)
    assert screen.zip_id == 456


def test_analyzing_handles_none_zip_id() -> None:
    """Ensure AnalyzingScreen handles None zip_id."""
    screen = AnalyzingScreen(zip_id=None)
    assert screen.zip_id is None

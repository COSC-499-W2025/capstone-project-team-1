"""Tests for ResumeScreen TUI component."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from textual.app import active_app

from artifactminer.tui.screens.resume import ResumeScreen
from artifactminer.tui.helpers import group_by_project, export_to_json, export_to_text


class LabelStub:
    """Minimal label replacement for status updates."""

    def __init__(self, text: str = "") -> None:
        self.text = text
        self.classes: set[str] = set()

    def update(self, text: str) -> None:
        self.text = text

    def set_class(self, add: bool, class_name: str) -> None:
        if add:
            self.classes.add(class_name)
        else:
            self.classes.discard(class_name)


class VerticalScrollStub:
    """Stub for VerticalScroll container."""

    def __init__(self) -> None:
        self.children: list = []

    async def remove_children(self) -> None:
        self.children = []

    async def mount(self, widget) -> None:
        self.children.append(widget)


class DummyApp:
    """Stubbed app with navigation and notification hooks."""

    def __init__(self) -> None:
        self.popped = False
        self.notifications: list[tuple[str, dict]] = []
        self.user_email: str | None = None

    def pop_screen(self) -> None:
        self.popped = True

    def notify(self, message: str, **kwargs) -> None:
        self.notifications.append((message, kwargs))


def make_screen() -> tuple[ResumeScreen, LabelStub, VerticalScrollStub, DummyApp, object]:
    """Create ResumeScreen with stubs."""
    screen = ResumeScreen()
    status = LabelStub("Loading...")
    content = VerticalScrollStub()
    app = DummyApp()

    def fake_query_one(selector: str, _expected=None):
        if selector == "#resume-status":
            return status
        if selector == "#resume-content":
            return content
        raise AssertionError(f"Unexpected selector: {selector}")

    screen.query_one = fake_query_one  # type: ignore[assignment]
    screen._status_label = status
    screen._app = app  # type: ignore[attr-defined]
    token = active_app.set(app)
    return screen, status, content, app, token


@pytest.mark.asyncio
async def test_resume_back_button_pops_screen() -> None:
    """Ensure Back button pops the screen."""
    screen, _, _, app, token = make_screen()
    try:
        await screen.on_button_pressed(SimpleNamespace(button=SimpleNamespace(id="back-btn")))
        assert app.popped is True
    finally:
        active_app.reset(token)


@pytest.mark.asyncio
async def test_resume_placeholder_buttons_show_notification() -> None:
    """Ensure Projects/Skills buttons show coming soon notification."""
    screen, _, _, app, token = make_screen()
    try:
        await screen.on_button_pressed(SimpleNamespace(button=SimpleNamespace(id="projects-btn")))
        assert len(app.notifications) == 1
        assert "coming soon" in app.notifications[0][0].lower()

        await screen.on_button_pressed(SimpleNamespace(button=SimpleNamespace(id="skills-btn")))
        assert len(app.notifications) == 2
    finally:
        active_app.reset(token)


def test_group_by_project() -> None:
    """Ensure resume items are grouped by project correctly."""
    items = [
        {"title": "Item 1", "project_name": "Project A", "content": "Content 1"},
        {"title": "Item 2", "project_name": "Project B", "content": "Content 2"},
        {"title": "Item 3", "project_name": "Project A", "content": "Content 3"},
        {"title": "Item 4", "project_name": None, "content": "Content 4"},
    ]

    grouped = group_by_project(items)

    assert "Project A" in grouped
    assert "Project B" in grouped
    assert "Uncategorized" in grouped
    assert len(grouped["Project A"]) == 2
    assert len(grouped["Project B"]) == 1
    assert len(grouped["Uncategorized"]) == 1


def test_export_json_creates_file(tmp_path: Path) -> None:
    """Ensure JSON export creates a valid JSON file."""
    items = [{"title": "Test Item", "project_name": "Test Project", "content": "Test content"}]
    
    path = export_to_json(items, [], directory=tmp_path)
    
    assert path.exists()
    with path.open() as f:
        data = json.load(f)
    assert "resume_items" in data
    assert len(data["resume_items"]) == 1


def test_export_text_creates_file(tmp_path: Path) -> None:
    """Ensure text export creates a valid text file."""
    items = [{"title": "Test Item", "project_name": "Test Project", "content": "Test content"}]
    
    path = export_to_text(items, [], directory=tmp_path)
    
    assert path.exists()
    content = path.read_text()
    assert "RESUME EXPORT" in content
    assert "Test Project" in content

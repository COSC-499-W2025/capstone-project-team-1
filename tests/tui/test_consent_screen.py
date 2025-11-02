from __future__ import annotations

from types import SimpleNamespace

import pytest

import httpx

from textual.app import active_app

from artifactminer.tui.screens.consent import ConsentScreen


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


class DummyApp:
    """Stubbed app with navigation and notification hooks."""

    def __init__(self) -> None:
        self.switched: list[str] = []
        self.notifications: list[tuple[str, dict]] = []
        self.consent_state: dict | None = None

    async def switch_screen(self, name: str):
        self.switched.append(name)

    def notify(self, message: str, **kwargs) -> None:
        self.notifications.append((message, kwargs))


def make_screen() -> tuple[ConsentScreen, LabelStub, DummyApp, object]:
    screen = ConsentScreen()
    status = LabelStub(screen.DEFAULT_STATUS)
    app = DummyApp()

    def fake_query_one(selector: str, _expected=None):
        if selector == "#consent-status":
            return status
        raise AssertionError(f"Unexpected selector: {selector}")

    screen.query_one = fake_query_one  # type: ignore[assignment]
    screen._status_label = status  # prime cached label
    screen._app = app  # type: ignore[attr-defined]
    token = active_app.set(app)
    return screen, status, app, token


@pytest.mark.asyncio
async def test_consent_continue_requires_selection() -> None:
    screen, status, _, token = make_screen()
    try:
        await screen.on_button_pressed(SimpleNamespace(button=SimpleNamespace(id="continue-btn")))

        assert screen.selected_level is None
        assert status.text == screen.PROMPT_CHOOSE
        assert "error" in status.classes
    finally:
        active_app.reset(token)


@pytest.mark.asyncio
async def test_consent_selection_updates_status() -> None:
    screen, status, _, token = make_screen()
    try:
        await screen.on_button_pressed(SimpleNamespace(button=SimpleNamespace(id="consent-no-llm-btn")))

        assert screen.selected_level == "no_llm"
        assert status.text == screen.SELECTED_NO_LLM
        assert "error" not in status.classes
    finally:
        active_app.reset(token)


@pytest.mark.asyncio
async def test_consent_continue_saves_and_navigates(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict] = []

    class FakeResponse:
        def __init__(self, data: dict) -> None:
            self._data = data

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return self._data

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def put(self, url, json, timeout=None):
            calls.append(json)
            return FakeResponse({"consent_level": json["consent_level"], "accepted_at": "now"})

    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)

    screen, status, app, token = make_screen()
    try:
        await screen.on_button_pressed(SimpleNamespace(button=SimpleNamespace(id="consent-full-btn")))
        await screen.on_button_pressed(SimpleNamespace(button=SimpleNamespace(id="continue-btn")))

        assert calls == [{"consent_level": "full"}]
        assert app.consent_state == {"consent_level": "full", "accepted_at": "now"}
        assert app.switched == ["userconfig"]
        assert status.text == screen.SUCCESS_STATUS
        assert "error" not in status.classes
    finally:
        active_app.reset(token)

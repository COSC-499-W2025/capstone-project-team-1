"""Analyzing screen for displaying analysis progress."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, Static


class AnalyzingScreen(Screen[None]):
    """Screen for displaying analysis progress."""

    CSS = """
    AnalyzingScreen #analyzing-title { text-align: center; text-style: bold; }
    AnalyzingScreen #analyzing-status { text-align: center; margin: 2 0; }
    AnalyzingScreen #analyzing-actions { width: 100%; align: center middle; margin-top: 2; }
    AnalyzingScreen #analyzing-actions Button { margin: 0 1; }
    """

    def __init__(self, zip_id: int | None = None) -> None:
        super().__init__()
        self.zip_id = zip_id

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="content"):
            with Container(id="card-wrapper"):
                with Vertical(id="card"):
                    yield Static("Analyzing Repository", id="analyzing-title")
                    status_text = f"Processing ZIP ID: {self.zip_id}" if self.zip_id else "No ZIP selected - please upload first"
                    yield Label(status_text, id="analyzing-status")
                    with Container(id="analyzing-actions"):
                        yield Button("Back", id="back-btn")
                        yield Button("Continue to Results", id="continue-btn", variant="primary")
        yield Footer()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back-btn":
            self.app.pop_screen()
        elif event.button.id == "continue-btn":
            # Navigate to Resume screen (will work once resume branch merges)
            try:
                await self.app.switch_screen("resume")
            except Exception:
                self.app.notify(
                    "Resume screen will be available after analysis completes.",
                    title="Coming Soon",
                    timeout=5
                )

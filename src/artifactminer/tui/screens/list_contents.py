from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, ListItem, ListView, Static


class ListContentsScreen(Screen[None]):
    """Displays directories extracted from a ZIP archive."""

    def __init__(self, dirs: list[str] | None = None) -> None:
        super().__init__()
        self.dirs = dirs or []

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="content"):
            with Container(id="card-wrapper"):
                with Vertical(id="card"):
                    yield Static("Contents of ZIP File", id="title")
                    with Container(id="list-container"):
                        yield ListView(
                            *[ListItem(Label(name)) for name in self.dirs],
                            id="zip-contents",
                        )
                    with Horizontal(id="list-actions"):
                        yield Button("Back", id="back-btn", variant="primary")
        yield Footer()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back-btn":
            self.dismiss(None)

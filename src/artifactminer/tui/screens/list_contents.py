from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import (
    Button,
    Checkbox,
    Footer,
    Header,
    Label,
    Static,
)


class ListContentsScreen(Screen[list[str] | None]):
    """Displays directories extracted from a ZIP archive."""

    def __init__(self, dirs: list[str] | None = None) -> None:
        super().__init__()
        self.dirs = dirs or []
        self._selected: set[str] = set()

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="content", classes="list-screen"):
            with Container(id="card-wrapper"):
                with Vertical(id="card"):
                    yield Static("Contents of ZIP File", id="title")
                    with Container(id="list-container"):
                        with VerticalScroll(id="zip-contents"):
                            for name in self.dirs:
                                yield Checkbox(
                                    label=name,
                                    name=name,
                                    value=False,
                                    classes="zip-checkbox",
                                )
                    yield Label("Selected 0 files", id="selection-count")
                    with Horizontal(id="list-actions"):
                        yield Button("Back", id="back-btn", variant="primary")
                        yield Button(
                            "Select Files",
                            id="select-btn",
                            variant="success",
                            disabled=True,
                        )
        yield Footer()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back-btn":
            self.dismiss(None)
        elif event.button.id == "select-btn":
            ordered = [name for name in self.dirs if name in self._selected]
            self.dismiss(ordered)

    def _update_selection_feedback(self) -> None:
        label = self.query_one("#selection-count", Label)
        count = len(self._selected)
        noun = "file" if count == 1 else "files"
        label.update(f"Selected {count} {noun}")
        select_btn = self.query_one("#select-btn", Button)
        select_btn.disabled = count == 0

    def on_mount(self) -> None:
        self._update_selection_feedback()
        first_checkbox = self.query(Checkbox).first()
        if first_checkbox:
            first_checkbox.focus()

    async def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        file_name = event.checkbox.name or ""
        if not file_name:
            return

        if event.value:
            self._selected.add(file_name)
        else:
            self._selected.discard(file_name)

        self._update_selection_feedback()

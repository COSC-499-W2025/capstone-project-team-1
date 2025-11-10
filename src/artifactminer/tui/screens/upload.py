from __future__ import annotations

from pathlib import Path
import zipfile

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, Static

from .list_contents import ListContentsScreen
from .file_browser import FileBrowserScreen

# Toggle between mock data and real ZIP extraction
USE_MOCK = True

# Mock data for ZIP contents when mock mode is enabled.
MOCK_DIRS = [
    "src/",
    "src/utils/",
    "src/helpers/",
    "docs/",
    "tests/",
    "requirements.txt",
]


def list_zip_dirs(zip_path: Path) -> list[str]:
    """Return top-level and subdirectory names from a zip file."""
    try:
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            return sorted(
                set(
                    f.split("/")[0] + "/" if "/" in f else f
                    for f in zip_ref.namelist()
                )
            )
    except Exception as exc:  # noqa: BLE001 - show user-friendly error message
        return [f"[Error] {exc}"]


class UploadScreen(Screen[None]):
    """Screen that allows the user to select and preview a ZIP file."""

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="content"):
            with Container(id="card-wrapper"):
                with Vertical(id="card"):
                    yield Static("Enter a path to a .zip file.")
                    with Horizontal(id="zip-row"):
                        yield Input(placeholder="Path to .zip", id="zip-path")
                        yield Button("Browse", id="browse-btn")
                        yield Button("Upload", id="upload-btn", variant="primary")
                    yield Label("Waiting for a file...", id="status")
                    with Horizontal(id="actions-row"):
                        yield Button("Back", id="back-btn")
        yield Footer()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        field = self.query_one("#zip-path", Input)
        status = self.query_one("#status", Label)

        if event.button.id == "back-btn":
            status.update("Waiting for a file...")
            field.value = ""
            field.focus()
            await self.app.switch_screen("userconfig")
            return

        if event.button.id == "browse-btn":
            def handle_file_selection(selected_path: Path | None) -> None:
                """Update input field with selected file path."""
                if selected_path:
                    field.value = str(selected_path)
                    field.focus()

            await self.app.push_screen(FileBrowserScreen(), callback=handle_file_selection)
            return

        if event.button.id != "upload-btn":
            return

        text = field.value.strip()

        if not text:
            status.update("Please enter a path.")
            return

        path = Path(text).expanduser()
        if not path.exists():
            status.update(f"File not found: {path}")
            return

        if path.suffix.lower() != ".zip":
            status.update("Need a .zip file.")
            return

        status.update("Processing ZIP contents...")

        dirs = MOCK_DIRS if USE_MOCK else list_zip_dirs(path)

        def reset_form(_result: None = None) -> None:
            """Reset upload form when the contents screen closes."""
            status.update("Waiting for a file...")
            field.value = ""
            field.focus()

        await self.app.push_screen(ListContentsScreen(dirs), callback=reset_form)

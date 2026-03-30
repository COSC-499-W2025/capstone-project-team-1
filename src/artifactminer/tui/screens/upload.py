from __future__ import annotations

from pathlib import Path
import zipfile

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, Static

from .list_contents import ListContentsScreen
from .file_browser import FileBrowserScreen
from .analyzing import AnalyzingScreen
from ..api import ApiClient

USE_MOCK = False
MOCK_DIRS: list[str] = []


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
    except Exception as exc:  # noqa: BLE001
        return [f"[Error] {exc}"]


class UploadScreen(Screen[None]):
    """Select and preview a ZIP file."""

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

        status.update("Uploading and fetching contents...")

        dirs: list[str]
        zip_id: int | None = None  # Initialize before conditional
        if USE_MOCK:
            dirs = MOCK_DIRS
        else:
            try:
                client = ApiClient()
                upload = await client.upload_zip(path)
                zip_id = int(upload["zip_id"])  # type: ignore[index]
                data = await client.list_zip_directories(zip_id)
                raw_items = list(data.get("directories", []))
                cleaned = [item[:-1] if item.endswith("/") else item for item in raw_items]
                dirs = [
                    item for item in cleaned
                    if not item.startswith("__MACOSX/") and not item.split("/")[-1].startswith("._")
                ]
                if not dirs:
                    status.update("No contents found in archive.")
                    return
            except Exception as exc:  # noqa: BLE001
                status.update(f"Error: {exc}")
                return

        # Store zip_id on app for AnalyzingScreen
        self.app.current_zip_id = zip_id

        def handle_selection(result: list[str] | None) -> None:
            if result:
                # Push AnalyzingScreen with the stored zip_id
                self.app.push_screen(AnalyzingScreen(self.app.current_zip_id))
            else:
                status.update("Waiting for a file...")
            field.focus()

        await self.app.push_screen(ListContentsScreen(dirs), callback=handle_selection)

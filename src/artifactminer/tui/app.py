from __future__ import annotations
import httpx

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, ListItem, ListView, Static

from .screens.userconfig import UserConfigScreen
from .screens.consent import ConsentScreen
from .screens.file_browser import FileBrowserScreen

# Toggle between mock data and real ZIP extraction
USE_MOCK = False

# Mock data for ZIP contents
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
    except Exception as exc:
        return [f"[Error] {exc}"]


class WelcomeScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="content"):
            with Container(id="card-wrapper"):
                with Vertical(id="card"):
                    yield Static("ARTIFACT-MINER", id="title")
                    yield Static("Welcome to the artifact staging tool.", id="subtitle")
                    yield Button("Start Mining", id="begin-btn", variant="primary")
        yield Footer()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "begin-btn":
            self.app.switch_screen("consent")

class UploadScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="content"):
            with Container(id="card-wrapper"):
                with Vertical(id="card"):
                    yield Static("Enter a path to a .zip file or browse for one.")
                    with Horizontal(id="zip-row"):
                        yield Input(placeholder="Path to .zip", id="zip-path")
                        yield Button("Browse", id="browse-btn")
                        yield Button("Upload", id="upload-btn", variant="primary")
                    yield Label("Waiting for a file...", id="status")
                    with Horizontal(id="actions-row"):
                        yield Button("Back", id="back-btn")
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
            # Open file browser
            def handle_file_selected(result: Path | None) -> None:
                """Handle the file selection from the browser."""
                if result:
                    field.value = str(result)
                    status.update(f"Selected: {result.name}")

            await self.app.push_screen(FileBrowserScreen(), callback=handle_file_selected)
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


class ListContentsScreen(Screen):
    """Displays directories from a zip file (mock or real)."""

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


class ArtifactMinerApp(App):
    TITLE = "ARTIFACT-MINER"
    CSS = """
    App {
        height: 100%;
        width: 100%;
    }

    Screen {
        layout: grid;
        grid-rows: auto 1fr auto;
        height: 100%;
        width: 100%;
    }

    #content {
        layout: vertical;
        width: 100%;
        height: 100%;
        padding: 1 2;
    }

    #card-wrapper {
        width: 100%;
        height: auto;
        align: center middle;
        content-align: center middle;
    }

    #card {
        layout: vertical;
        width: 100%;
        max-width: 80;
        padding: 2 4;
        border: round $surface;
        background: $panel;
        align: center middle;
        content-align: center middle;
    }

    #title, #subtitle {
        text-align: center;
    }

    #subtitle {
        margin-top: 1;
    }

    #begin-btn {
        margin-top: 2;
    }

    #zip-row {
        width: 100%;
        margin-top: 1;
        align: center middle;
    }

    #actions-row {
        width: 100%;
        margin-top: 1;
        align: left middle;
        content-align: left middle;
    }

    #actions-row Button {
        margin-right: 1;
    }

    #zip-path {
        width: 1fr;
        margin-right: 1;
    }

    #browse-btn {
        margin-right: 1;
    }

    #status {
        margin-top: 1;
    }

    #browser-container {
        width: 100%;
        height: 25;
        margin: 1 0;
        border: round $surface;
    }

    #file-tree {
        width: 100%;
        height: 100%;
    }

    #browser-status {
        margin-top: 1;
        color: $warning;
        text-align: center;
        height: auto;
    }

    #browser-actions {
        width: 100%;
        align: center middle;
        content-align: center middle;
        margin-top: 1;
    }

    #browser-actions Button {
        margin: 0 1;
    }

    #zip-contents {
        border: round $surface;
        height: 20;
        width: 100%;
        max-width: 60;
        overflow: auto;
    }

    #list-container {
        width: 100%;
        align: center middle;
        content-align: center middle;
        margin: 1 0;
    }

    #list-actions {
        width: 100%;
        align: center middle;
        content-align: center middle;
        margin-top: 1;
    }

    #list-actions Button {
        margin: 0 1;
    }

    """
    BINDINGS = [("q", "quit", "Quit")]

    consent_state: dict | None = None

    async def on_mount(self) -> None:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get("http://127.0.0.1:8000/consent", timeout=10.0)
                resp.raise_for_status()
                data = resp.json()
                self.consent_state = {
                    "consent_level": data.get("consent_level", "none"),
                    "accepted_at": data.get("accepted_at"),
                }
        except Exception:
            self.consent_state = {"consent_level": "none", "accepted_at": None}

        self.install_screen(WelcomeScreen(), "welcome")
        self.install_screen(UserConfigScreen(), "userconfig")
        self.install_screen(UploadScreen(), "upload")
        self.install_screen(ConsentScreen(), "consent")
        self.install_screen(FileBrowserScreen(), "filebrowser")
        self.push_screen("welcome")

    def on_resize(self, event) -> None:
        self.refresh()


def run() -> None:
    ArtifactMinerApp().run()


if __name__ == "__main__":
    run()

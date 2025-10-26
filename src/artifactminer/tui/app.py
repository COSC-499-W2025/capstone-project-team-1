from __future__ import annotations
from pathlib import Path
import zipfile

import httpx
from typing import Optional

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    Static,
    ListView,
    ListItem,
)

from .userconfig import UserConfigScreen
from .screens.consent import ConsentScreen

# Toggle between mock data and real ZIP extraction
USE_MOCK = True

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
    except Exception as e:
        return [f"[Error] {e}"]


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
            await self.app.push_screen("consent")



class UploadScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="content"):
            with Container(id="card-wrapper"):
                with Vertical(id="card"):
                    yield Static("Enter a path to a .zip file.")
                    with Horizontal(id="zip-row"):
                        yield Input(placeholder="Path to .zip", id="zip-path")
                        yield Button("Upload", id="upload-btn", variant="primary")
                    yield Label("Waiting for a file...", id="status")
        yield Footer()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id != "upload-btn":
            return

        field = self.query_one("#zip-path", Input)
        status = self.query_one("#status", Label)
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

        # Get directories (mock or real)
        dirs = MOCK_DIRS if USE_MOCK else list_zip_dirs(path)

        # Show results screen
        await self.app.push_screen(ListContentsScreen(dirs))


class ListContentsScreen(Screen):
    """Displays directories from a zip file (mock or real)."""

    def __init__(self, dirs: list[str] | None = None):
        super().__init__()
        self.dirs = dirs or []

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="content"):
            with Vertical(id="card"):
                yield Static("Contents of ZIP File", id="title")
                yield ListView(
                    *[ListItem(Label(name)) for name in self.dirs],
                    id="zip-contents",
                )
                yield Button("Back", id="back-btn", variant="primary")
        yield Footer()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back-btn":
            await self.app.pop_screen()


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
        height: auto;
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

    #zip-path {
        width: 1fr;
        margin-right: 1;
    }

    #status {
        margin-top: 1;
    }

    #zip-contents {
        border: round $surface;
        height: 20;
        width: 80%;
        margin: 1 0;
        align: center middle;
        overflow: auto;
    }
    """
    BINDINGS = [("q", "quit", "Quit")]

    # App-level consent state cache loaded from the backend on startup.
    # Example: {"accepted": bool, "version": str}
    consent_state: dict | None = None

    # Current consent version expected by this client (kept in sync with API)
    CONSENT_VERSION: str = "v0"

    # Bookmarking the screen to return to after obtaining consent, good UX. 
    pending_destination: Optional[str] = None

    # Names of screens that require consent (will be superseded by per-screen flags later)
    protected_screens: set[str] = {"userconfig", "upload"}

    def is_consent_valid(self) -> bool:
        """Return True if current in-memory consent is accepted and version matches."""
        state = self.consent_state or {}
        return bool(state.get("accepted")) and state.get("version") == self.CONSENT_VERSION

    async def navigate(self, name: str, mode: str = "push") -> None:
        """Central navigation with consent guard.

        If the target is protected and consent is invalid, redirect to the consent screen
        and remember the intended destination.
        """
        requires = name in self.protected_screens
        if requires and not self.is_consent_valid():
            self.pending_destination = name
            await self.switch_screen("consent")
            return

        if mode == "switch":
            await self.switch_screen(name)
        else:
            await self.push_screen(name)

    async def back(self) -> None:
        """Navigate back in the screen stack if possible."""
        try:
            await self.pop_screen()
        except Exception:
            # If there is nothing to pop, do nothing.
            pass

    async def on_mount(self) -> None:
        # Load consent state from API; fall back to not consented on failure.
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get("http://127.0.0.1:8000/consent", timeout=10.0)
                resp.raise_for_status()
                data = resp.json()
                self.consent_state = {
                    "accepted": bool(data.get("accepted", False)),
                    "version": str(data.get("version", "")),
                }
        except Exception as ex:
            self.consent_state = {"accepted": False, "version": ""}
            # Non-blocking notice; protected navigation will be added later
            self.notify(
                f"Consent state unavailable ({str(ex)}). Proceeding with limited functionality.", # we need to figure out what the limited functionality means
                title="Consent load failed",
                severity="warning",
                timeout=8,
            )

        self.install_screen(WelcomeScreen(), "welcome")
        self.install_screen(UserConfigScreen(), "userconfig")
        self.install_screen(UploadScreen(), "upload")
        self.install_screen(ConsentScreen(), "consent")
        self.push_screen("welcome")

    def on_resize(self, event) -> None:
        self.refresh()


def run() -> None:
    ArtifactMinerApp().run()


if __name__ == "__main__":
    run()

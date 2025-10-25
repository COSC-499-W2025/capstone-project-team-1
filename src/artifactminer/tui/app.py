from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, Static

from .userconfig import UserConfigScreen
from .screens.consent import ConsentScreen


class WelcomeScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="box"):
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
        with Vertical(id="box"):
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
        status.update(f"Got it: {path.name}")


class ArtifactMinerApp(App):
    TITLE = "ARTIFACT-MINER"
    CSS = """
    Screen {
        align: center middle;
    }

    #box {
        width: 60%;
        max-width: 60;
        padding: 2;
        border: round $surface;
        background: $panel;
        align: center middle;
    }

    #title, #subtitle {
        text-align: center;
        padding-bottom: 1;
    }

    #zip-row {
        margin-top: 1;
    }

    #zip-path {
        width: 1fr;
        margin-right: 1;
    }

    #status {
        margin-top: 1;
    }
    """
    BINDINGS = [("q", "quit", "Quit")]

    def on_mount(self) -> None:
        self.install_screen(WelcomeScreen(), "welcome")
        self.install_screen(UserConfigScreen(), "userconfig")
        self.install_screen(UploadScreen(), "upload")
        self.install_screen(ConsentScreen(), "consent")
        self.push_screen("welcome")


def run() -> None:
    ArtifactMinerApp().run()


if __name__ == "__main__":
    run()

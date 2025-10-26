from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, Static


class WelcomeScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="content"):
            with Container(id="card-wrapper"):
                with Vertical(id="card"):
                    yield Static("ARTIFACT-MINER", id="title")
                    yield Static("Welcome to the artifact staging tool.", id="subtitle")
                    yield Button("Begin", id="begin-btn", variant="primary")
        yield Footer()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "begin-btn":
            await self.app.push_screen("upload")


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
        status.update(f"Got it: {path.name}")


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
    """
    BINDINGS = [("q", "quit", "Quit")]

    def on_mount(self) -> None:
        self.install_screen(WelcomeScreen(), "welcome")
        self.install_screen(UploadScreen(), "upload")
        self.push_screen("welcome")

    def on_resize(self, event) -> None:
        self.refresh()


def run() -> None:
    ArtifactMinerApp().run()


if __name__ == "__main__":
    run()

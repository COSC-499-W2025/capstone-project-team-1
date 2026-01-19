from __future__ import annotations
import httpx

from textual.app import App

from .screens.welcome import WelcomeScreen
from .screens.consent import ConsentScreen
from .screens.userconfig import UserConfigScreen
from .screens.upload import UploadScreen
from .screens.list_contents import ListContentsScreen
from .screens.file_browser import FileBrowserScreen
from .screens.resume import ResumeScreen


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
        padding: 2 4;
        border: round $surface;
        background: $panel;
        align: center middle;
        content-align: center middle;
    }

    .list-screen #card {
        width: 85%;
        max-width: 120;
        min-height: 34;
        border: heavy $surface;
        background: $panel 80%;
        align: center top;
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

    #list-container {
        width: 100%;
        align: center top;
        content-align: center top;
        margin: 1 0 2 0;
    }

    .list-screen #list-container {
        height: 1fr;
    }

    #zip-contents {
        border: round $surface;
        height: 22;
        width: 100%;
        padding: 0 1;
        background: $boost 5%;
    }

    #selection-count {
        width: 100%;
        text-align: center;
        margin-top: 1;
        color: $text-muted;
    }

    .zip-checkbox {
        width: 100%;
        padding: 1 1;
        border-bottom: solid $surface;
    }

    .zip-checkbox:last-child {
        border-bottom: none;
    }

    .zip-checkbox:hover {
        background: $surface 20%;
    }

    .zip-checkbox.-checked {
        background: $primary 20%;
    }

    #list-actions {
        width: 100%;
        align: center middle;
        content-align: center middle;
        margin-top: 1;
    }

    #list-actions Button {
        margin: 0 1;
        min-width: 16;
    }

    """
    BINDINGS = [("q", "quit", "Quit")]

    consent_state: dict | None = None
    current_zip_id: int | None = None
    user_email: str | None = None
    consent_level: str | None = None

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
        self.install_screen(ConsentScreen(), "consent")
        self.install_screen(UserConfigScreen(), "userconfig")
        self.install_screen(UploadScreen(), "upload")
        self.install_screen(ResumeScreen(), "resume")
        self.push_screen("welcome")

    def on_resize(self, event) -> None:
        self.refresh()


def run() -> None:
    ArtifactMinerApp().run()


if __name__ == "__main__":
    run()

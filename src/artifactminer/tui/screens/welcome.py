from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static


class WelcomeScreen(Screen[None]):
    """Initial landing screen presented to users."""

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

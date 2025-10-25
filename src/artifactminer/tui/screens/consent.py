from textual.screen import Screen
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Button, Footer, Header, Static

class ConsentScreen(Screen[None]):
    consent: str = "By using this tool, you consent to the collection and analysis of artifacts from the provided .zip file. Ensure you have the necessary permissions to analyze the data contained within."

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="box"):
            yield Static("Consent Required", id="title")
            yield Static(
                self.consent,
                id="consent-text"
            )
            yield Button("I Consent", id="consent-btn", variant="success")
        yield Footer()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "consent-btn":
            await self.app.switch_screen("userconfig")
        else:
            return

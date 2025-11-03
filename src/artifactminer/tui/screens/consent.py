import httpx
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, Markdown, Static

CONSENT_TEXT = """\
# Consent Required

By using **Artifact Miner**, you consent to the collection and analysis of artifacts from the provided .zip file. 

## What We Collect

- Artifact metadata (file names, paths, types)
- File contents for analysis purposes
- Timestamps of when artifacts were scanned

## Your Data Rights

You must ensure you have the necessary permissions to analyze the data contained within the uploaded files.

## LLM Processing Options

You can choose whether to allow external Large Language Models (LLMs) to process your data:

- **Consent with LLM**: Your data may be sent to external LLM services for enhanced analysis
- **Consent without LLM**: Your data will be processed locally only, without any external LLM services

Please select your preference below to continue.
"""

class ConsentScreen(Screen[None]):
    DEFAULT_STATUS = "Select a consent option to continue."
    PROMPT_CHOOSE = "Please select a consent option before continuing."
    SELECTED_FULL = "Consent with LLM selected."
    SELECTED_NO_LLM = "Consent without LLM selected."
    SAVING_STATUS = "Saving consent choice..."
    SUCCESS_STATUS = "Consent saved. Loading preferences..."
    CONNECT_ERROR_STATUS = "Cannot connect to the backend server."
    SAVE_ERROR_STATUS = "Unable to save consent. Please try again."

    CSS = """
    ConsentScreen #card {
        width: 100%;
    }

    ConsentScreen #consent-title {
        text-align: center;
        padding-bottom: 1;
        text-style: bold;
    }

    ConsentScreen #consent-content {
        width: 100%;
        max-height: 30;
        margin-bottom: 1;
    }

    ConsentScreen #consent-markdown {
        width: 100%;
        padding: 0 1;
    }

    ConsentScreen #consent-buttons {
        align: center middle;
        height: auto;
    }

    ConsentScreen #consent-buttons Button {
        margin: 0 1;
    }

    ConsentScreen #consent-status {
        margin-top: 1;
        text-align: center;
    }

    ConsentScreen #consent-status.error {
        color: $error;
    }

    ConsentScreen #consent-actions {
        align: center middle;
        margin-top: 1;
    }

    ConsentScreen #consent-actions Button {
        margin: 0 1;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self.selected_level: str | None = None
        self._status_label: Label | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="content"):
            with Container(id="card-wrapper"):
                with Vertical(id="card"):
                    yield Static("Data Usage Consent", id="consent-title")
                    with ScrollableContainer(id="consent-content"):
                        yield Markdown(CONSENT_TEXT, id="consent-markdown")
                    with Horizontal(id="consent-buttons"):
                        yield Button("Consent with LLM", id="consent-full-btn", variant="success")
                        yield Button("Consent without LLM", id="consent-no-llm-btn", variant="primary")
                    yield Label(self.DEFAULT_STATUS, id="consent-status")
                    with Horizontal(id="consent-actions"):
                        yield Button("Back", id="back-btn")
                        yield Button("Continue", id="continue-btn", variant="primary")
        yield Footer()

    async def on_mount(self) -> None:
        self._status_label = self.query_one("#consent-status", Label)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "consent-full-btn":
            self._set_selection("full")
            return
        if button_id == "consent-no-llm-btn":
            self._set_selection("no_llm")
            return
        if button_id == "back-btn":
            self.selected_level = None
            self._update_status(self.DEFAULT_STATUS, error=False)
            await self.app.switch_screen("welcome")
            return
        if button_id == "continue-btn":
            if not self.selected_level:
                self._update_status(self.PROMPT_CHOOSE, error=True)
                return
            await self._save_consent(self.selected_level)

    async def _save_consent(self, consent_level: str) -> None:
        self._update_status(self.SAVING_STATUS, error=False)
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.put(
                    "http://127.0.0.1:8000/consent",
                    json={"consent_level": consent_level},
                    timeout=10.0,
                )
                resp.raise_for_status()
                payload = resp.json()

            if isinstance(payload, dict):
                self.app.consent_state = {
                    "consent_level": payload.get("consent_level", "none"),
                    "accepted_at": payload.get("accepted_at"),
                }
            self._update_status(self.SUCCESS_STATUS, error=False)
            await self.app.switch_screen("userconfig")

        except httpx.ConnectError:
            self._update_status(self.CONNECT_ERROR_STATUS, error=True)
            self.app.notify(
                "Cannot connect to the backend server. Is it running?",
                title="Connection error",
                severity="error",
                timeout=15
            )
        except Exception as ex:
            self._update_status(self.SAVE_ERROR_STATUS, error=True)
            self.app.notify(
                f"Unable to save consent: {str(ex)}",
                title="Consent error",
                severity="error",
                timeout=15
            )

    def _set_selection(self, level: str) -> None:
        self.selected_level = level
        message = self.SELECTED_FULL if level == "full" else self.SELECTED_NO_LLM
        self._update_status(message, error=False)

    def _update_status(self, message: str, *, error: bool) -> None:
        if self._status_label is None:
            self._status_label = self.query_one("#consent-status", Label)
        self._status_label.update(message)
        self._status_label.set_class(error, "error")

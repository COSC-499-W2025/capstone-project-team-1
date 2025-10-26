import httpx
from textual.screen import Screen
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Markdown, Static

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
    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="consent-container"):
            yield Static("Data Usage Consent", id="consent-title")
            yield Markdown(CONSENT_TEXT, id="consent-markdown")
            with Horizontal(id="consent-buttons"):
                yield Button("Consent with LLM", id="consent-full-btn", variant="success")
                yield Button("Consent without LLM", id="consent-no-llm-btn", variant="primary")
        yield Footer()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "consent-full-btn":
            await self._save_consent("full")
        elif event.button.id == "consent-no-llm-btn":
            await self._save_consent("no_llm")

    async def _save_consent(self, consent_level: str) -> None:
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
            
            self.app.switch_screen("userconfig")

        except httpx.ConnectError:
            self.app.notify(
                "Cannot connect to the backend server. Is it running?",
                title="Connection error",
                severity="error",
                timeout=15
            )
        except Exception as ex:
            self.app.notify(
                f"Unable to save consent: {str(ex)}",
                title="Consent error",
                severity="error",
                timeout=15
            )

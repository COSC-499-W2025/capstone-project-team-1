from socket import timeout
import httpx
from textual.screen import Screen
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Button, Footer, Header, Static

class ConsentScreen(Screen[None]):
    consent: str = "By using this tool, you consent to the collection and analysis of artifacts from the provided .zip file. Ensure you have the necessary permissions to analyze the data contained within."
    CONSENT_VERSION: str = "v0"

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
        if event.button.id != "consent-btn":
            return

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.put(
                    "http://127.0.0.1:8000/consent",
                    json={
                        "accepted": True,
                        "version": self.CONSENT_VERSION,
                    },
                    timeout=10.0,
                )
                resp.raise_for_status()

            # Success: proceed to next screen (will be guarded once navigation abstraction is added)
            await self.app.switch_screen("userconfig")

        except httpx.HTTPStatusError as e:
            # Attempt to parse structured error detail
            detail = None
            try:
                body = e.response.json()
                detail = body.get("detail")
            except Exception:
                detail = None

            # Consent version mismatch handling
            if isinstance(detail, dict) and detail.get("code") == "CONSENT_VERSION_MISMATCH":
                server_version = detail.get("server_version", "unknown")
                self.app.notify(
                    f"Consent text updated to {server_version}. Please update your app to continue.",
                    title="Consent version out of date",
                    severity="warning",
                    timeout=8,
                )
            else:
                # Generic error notification with human readable message
                self.app.notify(
                    f"Unable to save consent. {str(e)}",
                    title="Consent error",
                    severity="error",
                    timeout=15
                )

        except httpx.ConnectError:
            # Network connectivity issue
            self.app.notify(
                "Cannot connect to the backend server. Is it running?",
                title="Connection error",
                severity="error",
                timeout=15
            )
        except Exception as ex:
            # Catch-all for unexpected errors
            self.app.notify(
                f"Unexpected error: {str(ex)}",
                title="Consent error",
                severity="error",
                timeout=15
            )

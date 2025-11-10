"""User configuration screen for collecting user preferences."""

from __future__ import annotations

import httpx
from textual.app import ComposeResult
from textual.containers import ScrollableContainer, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, Static


class UserConfigScreen(Screen):
    """Screen for collecting user configuration through questions."""

    CSS = """
    UserConfigScreen #config-box {
        width: 80%;
        max-width: 80;
        padding: 2;
        border: round $surface;
        background: $panel;
        align: center middle;
    }

    UserConfigScreen #config-title {
        text-align: center;
        padding-bottom: 1;
        text-style: bold;
    }

    UserConfigScreen .question-label {
        margin-top: 1;
        text-style: bold;
    }

    UserConfigScreen .answer-input {
        margin-bottom: 1;
    }

    UserConfigScreen #continue-btn {
        margin-top: 2;
        width: 100%;
    }

    UserConfigScreen #error-message {
        color: red;
        text-align: center;
        margin: 1;
    }
    """

    def __init__(self):
        super().__init__()
        self.questions: list[dict] = []

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="config-box"):
            yield Static("User Configuration", id="config-title")
            yield ScrollableContainer(id="questions-container")
            yield Button("Continue", id="continue-btn", variant="primary")
        yield Footer()

    async def on_mount(self) -> None:
        """Fetch questions from the API when the screen is mounted."""
        container = self.query_one("#questions-container", ScrollableContainer)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("http://127.0.0.1:8000/questions")
                response.raise_for_status()
                self.questions = response.json()
            
            if not self.questions:
                container.mount(Static("No questions available.", classes="question-label"))
            else:
                for question in self.questions:
                    # Only use keyed questions
                    key = question.get("key")
                    if not key:
                        continue
                    container.mount(Label(question["question_text"], classes="question-label"))
                    input_id = f"answer-{key}"
                    container.mount(Input(
                        placeholder="Your answer...",
                        id=input_id,
                        classes="answer-input"
                    ))
        
        except httpx.ConnectError:
            container.mount(Static(
                "Error: Cannot connect to API. Please ensure the API server is running at http://127.0.0.1:8000",
                id="error-message"
            ))
        except Exception as e:
            container.mount(Static(
                f"Error loading questions: {str(e)}",
                id="error-message"
            ))

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle the Continue button press."""
        if event.button.id != "continue-btn":
            return

        # Collect answers from input fields keyed by question key only
        keyed_answers: dict[str, str] = {}
        for question in self.questions:
            key = question.get("key")
            if not key:
                continue
            input_id = f"#answer-{key}"
            try:
                answer_input = self.query_one(input_id, Input)
                keyed_answers[key] = answer_input.value.strip()
            except Exception:
                pass

        # Submit answers to API
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://127.0.0.1:8000/answers",
                    json={"answers": keyed_answers},
                    timeout=10.0
                )
                response.raise_for_status()

            self.app.switch_screen("upload")

        except httpx.HTTPStatusError as e:
            # Show server-provided error detail when available; otherwise a generic message
            error_msg = "Please check your answers. All fields must be filled out."
            try:
                detail = e.response.json().get("detail")
                if isinstance(detail, str) and detail.strip():
                    error_msg = detail.strip()
            except Exception:
                pass

            self.app.notify(
                error_msg,
                title="Invalid Input",
                severity="error",
                timeout=10
            )

        except httpx.ConnectError:
            self.app.notify(
                "Cannot connect to server. Please ensure it is running.",
                title="Connection Error",
                severity="error",
                timeout=15
            )

        except Exception as e:
            self.app.notify(
                f"Error: {str(e)}",
                title="Submission Error",
                severity="error",
                timeout=10
            )

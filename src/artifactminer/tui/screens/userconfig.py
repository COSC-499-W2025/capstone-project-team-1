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
        self.answers: dict[int, str] = {}
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
                    container.mount(Label(question["question_text"], classes="question-label"))
                    container.mount(Input(
                        placeholder="Your answer...",
                        id=f"answer-{question['id']}",
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

        # Collect answers from input fields
        for question in self.questions:
            try:
                answer_input = self.query_one(f"#answer-{question['id']}", Input)
                self.answers[question["id"]] = answer_input.value.strip()
            except Exception:
                pass

        # Map question IDs to field names
        field_map = {
            1: "email",
            2: "artifacts_focus",
            3: "end_goal",
            4: "repository_priority",
            5: "file_patterns",
        }

        # Prepare payload with individual fields
        answers_payload = {}
        for qid, field_name in field_map.items():
            answers_payload[field_name] = self.answers.get(qid, "")

        # Submit answers to API
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://127.0.0.1:8000/answers",
                    json=answers_payload,
                    timeout=10.0
                )
                response.raise_for_status()

            self.app.switch_screen("upload")

        except httpx.HTTPStatusError as e:
            # Parse validation error for better message
            error_msg = "Please check your answers. All fields must be filled out."
            try:
                error_detail = e.response.json().get("detail", [])
                if isinstance(error_detail, list) and len(error_detail) > 0:
                    first_error = error_detail[0]
                    if "email" in first_error.get("loc", []):
                        error_msg = "Invalid email address. Please provide a valid email."
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

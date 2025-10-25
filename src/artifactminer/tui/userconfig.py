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
        
        for question in self.questions:
            try:
                answer_input = self.query_one(f"#answer-{question['id']}", Input)
                self.answers[question["id"]] = answer_input.value.strip()
            except Exception:
                pass
        
        await self.app.push_screen("upload")

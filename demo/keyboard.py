"""Simple input handling for demo."""

from rich.prompt import Prompt


def wait_for_enter(prompt: str = "Press Enter to continue...") -> None:
    """Wait for user to press Enter."""
    Prompt.ask(f"\n[dim]  {prompt}[/dim]", default="", show_default=False)

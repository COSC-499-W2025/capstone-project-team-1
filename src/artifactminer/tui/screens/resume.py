"""Resume screen for displaying resume items and summaries."""

from __future__ import annotations

from typing import Any

import httpx
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, Static

from ..api import ApiClient
from ..helpers import export_to_json, export_to_text, group_by_project, build_summaries_lookup


class ResumeScreen(Screen[None]):
    """Screen for displaying resume items grouped by project with summaries."""

    CSS = """
    ResumeScreen #resume-title { text-align: center; padding-bottom: 1; text-style: bold; }
    ResumeScreen #resume-content { width: 100%; height: 1fr; margin: 1 0; }
    ResumeScreen .project-group { width: 100%; margin-bottom: 1; padding: 1; border: round $surface; background: $boost 5%; }
    ResumeScreen .project-title { text-style: bold; color: $primary; margin-bottom: 1; }
    ResumeScreen .resume-item { padding: 0 1; margin-bottom: 1; }
    ResumeScreen .item-title { text-style: bold; }
    ResumeScreen .item-content { color: $text-muted; }
    ResumeScreen .summary-section { margin-top: 1; padding: 1; border: dashed $accent; background: $accent 10%; }
    ResumeScreen .summary-label { text-style: italic; color: $accent; }
    ResumeScreen #resume-actions { width: 100%; align: center middle; margin-top: 1; }
    ResumeScreen #resume-actions Button { margin: 0 1; }
    ResumeScreen #resume-status { margin-top: 1; text-align: center; }
    ResumeScreen #resume-status.error { color: $error; }
    ResumeScreen #resume-status.success { color: $success; }
    ResumeScreen #empty-state { text-align: center; color: $text-muted; padding: 4; }
    ResumeScreen #nav-actions { width: 100%; align: center middle; margin-top: 1; }
    ResumeScreen #nav-actions Button { margin: 0 1; }
    """

    EMPTY_MESSAGE = "No resume items found. Complete the analysis flow to generate resume content."

    def __init__(self) -> None:
        super().__init__()
        self.resume_items: list[dict[str, Any]] = []
        self.summaries: list[dict[str, Any]] = []
        self._status_label: Label | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="content", classes="list-screen"):
            with Container(id="card-wrapper"):
                with Vertical(id="card"):
                    yield Static("Resume & Summaries", id="resume-title")
                    yield VerticalScroll(id="resume-content")
                    yield Label("Loading...", id="resume-status")
                    with Horizontal(id="resume-actions"):
                        yield Button("Export JSON", id="export-json-btn", variant="primary")
                        yield Button("Export Text", id="export-text-btn", variant="primary")
                    with Horizontal(id="nav-actions"):
                        yield Button("Back", id="back-btn")
                        yield Button("Projects", id="projects-btn", disabled=True)
                        yield Button("Skills", id="skills-btn", disabled=True)
        yield Footer()

    async def on_mount(self) -> None:
        self._status_label = self.query_one("#resume-status", Label)
        await self._load_data()

    async def _load_data(self) -> None:
        self._update_status("Loading...", error=False)
        content = self.query_one("#resume-content", VerticalScroll)
        await content.remove_children()

        try:
            client = ApiClient()
            self.resume_items = await client.get_resume_items()

            user_email = getattr(self.app, "user_email", None)
            if user_email:
                try:
                    self.summaries = await client.get_summaries(user_email)
                except Exception:
                    self.summaries = []
            else:
                self.summaries = []

            if not self.resume_items:
                await content.mount(Static(self.EMPTY_MESSAGE, id="empty-state"))
                self._update_status("No resume items available.", error=False)
                return

            grouped = group_by_project(self.resume_items)
            summaries_lookup = build_summaries_lookup(self.summaries)

            for project_name, items in grouped.items():
                project_container = Vertical(classes="project-group")
                await content.mount(project_container)
                await project_container.mount(
                    Static(f"📁 {project_name or 'Uncategorized'}", classes="project-title")
                )

                for item in items:
                    item_container = Vertical(classes="resume-item")
                    await project_container.mount(item_container)
                    await item_container.mount(Static(f"• {item.get('title', 'Untitled')}", classes="item-title"))
                    content_text = item.get("content", "")
                    if content_text:
                        truncated = f"{content_text[:200]}..." if len(content_text) > 200 else content_text
                        await item_container.mount(Static(f"  {truncated}", classes="item-content"))

                if project_name and project_name in summaries_lookup:
                    summary_container = Vertical(classes="summary-section")
                    await project_container.mount(summary_container)
                    await summary_container.mount(Static("💡 AI Summary:", classes="summary-label"))
                    await summary_container.mount(Static(summaries_lookup[project_name], classes="item-content"))

            self._update_status(f"Loaded {len(self.resume_items)} items.", success=True)

        except httpx.ConnectError:
            await content.mount(Static("Cannot connect to API server.", id="empty-state"))
            self._update_status("Connection error.", error=True)
        except httpx.TimeoutException:
            await content.mount(Static("Request timed out.", id="empty-state"))
            self._update_status("Timeout error.", error=True)
        except httpx.HTTPStatusError as e:
            await content.mount(Static(f"Server error: {e.response.status_code}", id="empty-state"))
            self._update_status(f"HTTP {e.response.status_code} error.", error=True)
        except Exception as e:
            await content.mount(Static(f"Error: {e}", id="empty-state"))
            self._update_status(f"Error: {e}", error=True)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id

        if button_id == "back-btn":
            self.app.pop_screen()
        elif button_id == "export-json-btn":
            try:
                path = export_to_json(self.resume_items, self.summaries)
                self._update_status(f"Exported to {path.name}", success=True)
                self.app.notify(f"Exported to {path.name}", title="Export Complete", timeout=5)
            except Exception as e:
                self._update_status(f"Export failed: {e}", error=True)
        elif button_id == "export-text-btn":
            try:
                path = export_to_text(self.resume_items, self.summaries)
                self._update_status(f"Exported to {path.name}", success=True)
                self.app.notify(f"Exported to {path.name}", title="Export Complete", timeout=5)
            except Exception as e:
                self._update_status(f"Export failed: {e}", error=True)
        elif button_id in ("projects-btn", "skills-btn"):
            self.app.notify("This feature is coming soon!", title="Not Available", timeout=5)

    def _update_status(self, message: str, *, error: bool = False, success: bool = False) -> None:
        if self._status_label is None:
            self._status_label = self.query_one("#resume-status", Label)
        self._status_label.update(message)
        self._status_label.set_class(error, "error")
        self._status_label.set_class(success, "success")

"""Resume screen for displaying resume items and summaries."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, Markdown, Static

from ..api import ApiClient


class ResumeScreen(Screen[None]):
    """Screen for displaying resume items grouped by project with summaries."""

    CSS = """
    ResumeScreen #resume-title {
        text-align: center;
        padding-bottom: 1;
        text-style: bold;
    }

    ResumeScreen #resume-content {
        width: 100%;
        height: 1fr;
        margin: 1 0;
    }

    ResumeScreen .project-group {
        width: 100%;
        margin-bottom: 1;
        padding: 1;
        border: round $surface;
        background: $boost 5%;
    }

    ResumeScreen .project-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }

    ResumeScreen .resume-item {
        padding: 0 1;
        margin-bottom: 1;
    }

    ResumeScreen .item-title {
        text-style: bold;
    }

    ResumeScreen .item-content {
        color: $text-muted;
    }

    ResumeScreen .summary-section {
        margin-top: 1;
        padding: 1;
        border: dashed $accent;
        background: $accent 10%;
    }

    ResumeScreen .summary-label {
        text-style: italic;
        color: $accent;
    }

    ResumeScreen #resume-actions {
        width: 100%;
        align: center middle;
        content-align: center middle;
        margin-top: 1;
    }

    ResumeScreen #resume-actions Button {
        margin: 0 1;
    }

    ResumeScreen #resume-status {
        margin-top: 1;
        text-align: center;
    }

    ResumeScreen #resume-status.error {
        color: $error;
    }

    ResumeScreen #resume-status.success {
        color: $success;
    }

    ResumeScreen #empty-state {
        text-align: center;
        color: $text-muted;
        padding: 4;
    }

    ResumeScreen #nav-actions {
        width: 100%;
        align: center middle;
        content-align: center middle;
        margin-top: 1;
    }

    ResumeScreen #nav-actions Button {
        margin: 0 1;
    }
    """

    DEFAULT_STATUS = "Resume items loaded."
    LOADING_STATUS = "Loading resume data..."
    EMPTY_MESSAGE = "No resume items found. Complete the analysis flow to generate resume content."
    EXPORT_SUCCESS = "Exported successfully to {path}"
    EXPORT_ERROR = "Export failed: {error}"

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
                    yield Label(self.LOADING_STATUS, id="resume-status")
                    with Horizontal(id="resume-actions"):
                        yield Button("Export JSON", id="export-json-btn", variant="primary")
                        yield Button("Export Text", id="export-text-btn", variant="primary")
                    with Horizontal(id="nav-actions"):
                        yield Button("Back", id="back-btn")
                        yield Button("Projects", id="projects-btn", disabled=True)
                        yield Button("Skills", id="skills-btn", disabled=True)
        yield Footer()

    async def on_mount(self) -> None:
        """Fetch resume items and summaries when the screen is mounted."""
        self._status_label = self.query_one("#resume-status", Label)
        await self._load_data()

    async def _load_data(self) -> None:
        """Load resume items and summaries from the API."""
        self._update_status(self.LOADING_STATUS, error=False)
        content = self.query_one("#resume-content", VerticalScroll)

        # Clear existing content
        await content.remove_children()

        try:
            client = ApiClient()

            # Fetch resume items
            self.resume_items = await client.get_resume_items()

            # Try to get user email from app state for summaries
            user_email = getattr(self.app, "user_email", None)
            if user_email:
                try:
                    self.summaries = await client.get_summaries(user_email)
                except Exception:
                    self.summaries = []
            else:
                self.summaries = []

            # Check for empty state
            if not self.resume_items:
                await content.mount(Static(self.EMPTY_MESSAGE, id="empty-state"))
                self._update_status("No resume items available.", error=False)
                return

            # Group items by project
            grouped = self._group_by_project()

            # Build summaries lookup by repo_path
            summaries_by_path: dict[str, str] = {}
            for summary in self.summaries:
                repo_path = summary.get("repo_path", "")
                # Extract project name from repo_path
                project_name = Path(repo_path).name if repo_path else ""
                if project_name:
                    summaries_by_path[project_name] = summary.get("summary_text", "")

            # Render grouped content
            for project_name, items in grouped.items():
                project_container = Vertical(classes="project-group")
                await content.mount(project_container)

                # Project title
                await project_container.mount(
                    Static(f"📁 {project_name or 'Uncategorized'}", classes="project-title")
                )

                # Resume items in this project
                for item in items:
                    item_container = Vertical(classes="resume-item")
                    await project_container.mount(item_container)
                    await item_container.mount(
                        Static(f"• {item.get('title', 'Untitled')}", classes="item-title")
                    )
                    content_text = item.get("content", "")
                    if content_text:
                        await item_container.mount(
                            Static(f"  {content_text[:200]}{'...' if len(content_text) > 200 else ''}", classes="item-content")
                        )

                # Add summary if available for this project
                if project_name and project_name in summaries_by_path:
                    summary_container = Vertical(classes="summary-section")
                    await project_container.mount(summary_container)
                    await summary_container.mount(
                        Static("💡 AI Summary:", classes="summary-label")
                    )
                    await summary_container.mount(
                        Static(summaries_by_path[project_name], classes="item-content")
                    )

            self._update_status(
                f"Loaded {len(self.resume_items)} items across {len(grouped)} projects.",
                error=False,
                success=True
            )

        except httpx.ConnectError:
            await content.mount(Static(
                "Cannot connect to API server. Please ensure it is running.",
                id="empty-state"
            ))
            self._update_status("Connection error.", error=True)
        except Exception as e:
            await content.mount(Static(
                f"Error loading data: {str(e)}",
                id="empty-state"
            ))
            self._update_status(f"Error: {str(e)}", error=True)

    def _group_by_project(self) -> dict[str, list[dict[str, Any]]]:
        """Group resume items by project name."""
        grouped: dict[str, list[dict[str, Any]]] = {}
        for item in self.resume_items:
            project = item.get("project_name") or "Uncategorized"
            if project not in grouped:
                grouped[project] = []
            grouped[project].append(item)
        return grouped

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

        if button_id == "back-btn":
            self.app.pop_screen()
            return

        if button_id == "export-json-btn":
            await self._export_json()
            return

        if button_id == "export-text-btn":
            await self._export_text()
            return

        if button_id in ("projects-btn", "skills-btn"):
            self.app.notify(
                "This feature is coming soon!",
                title="Not Available",
                severity="information",
                timeout=5
            )
            return

    async def _export_json(self) -> None:
        """Export resume data to JSON file."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"resume_export_{timestamp}.json"
            path = Path.cwd() / filename

            export_data = {
                "exported_at": datetime.now().isoformat(),
                "resume_items": self.resume_items,
                "summaries": self.summaries,
            }

            with path.open("w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, default=str)

            self._update_status(self.EXPORT_SUCCESS.format(path=filename), success=True)
            self.app.notify(
                f"Exported to {filename}",
                title="Export Complete",
                severity="information",
                timeout=5
            )
        except Exception as e:
            self._update_status(self.EXPORT_ERROR.format(error=str(e)), error=True)

    async def _export_text(self) -> None:
        """Export resume data to plain text file."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"resume_export_{timestamp}.txt"
            path = Path.cwd() / filename

            lines: list[str] = []
            lines.append("=" * 60)
            lines.append("RESUME EXPORT")
            lines.append(f"Generated: {datetime.now().isoformat()}")
            lines.append("=" * 60)
            lines.append("")

            grouped = self._group_by_project()

            # Build summaries lookup
            summaries_by_path: dict[str, str] = {}
            for summary in self.summaries:
                repo_path = summary.get("repo_path", "")
                project_name = Path(repo_path).name if repo_path else ""
                if project_name:
                    summaries_by_path[project_name] = summary.get("summary_text", "")

            for project_name, items in grouped.items():
                lines.append(f"\n{'─' * 40}")
                lines.append(f"PROJECT: {project_name or 'Uncategorized'}")
                lines.append(f"{'─' * 40}\n")

                for item in items:
                    lines.append(f"  • {item.get('title', 'Untitled')}")
                    content = item.get("content", "")
                    if content:
                        lines.append(f"    {content}")
                    lines.append("")

                if project_name and project_name in summaries_by_path:
                    lines.append("  [AI Summary]")
                    lines.append(f"  {summaries_by_path[project_name]}")
                    lines.append("")

            with path.open("w", encoding="utf-8") as f:
                f.write("\n".join(lines))

            self._update_status(self.EXPORT_SUCCESS.format(path=filename), success=True)
            self.app.notify(
                f"Exported to {filename}",
                title="Export Complete",
                severity="information",
                timeout=5
            )
        except Exception as e:
            self._update_status(self.EXPORT_ERROR.format(error=str(e)), error=True)

    def _update_status(self, message: str, *, error: bool = False, success: bool = False) -> None:
        """Update status label with message and styling."""
        if self._status_label is None:
            self._status_label = self.query_one("#resume-status", Label)
        self._status_label.update(message)
        self._status_label.set_class(error, "error")
        self._status_label.set_class(success, "success")

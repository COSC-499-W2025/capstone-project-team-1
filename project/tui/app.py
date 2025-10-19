"""Textual client for interacting with the ingest MVP API."""

from __future__ import annotations

import asyncio
import contextlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import httpx
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Checkbox, Footer, Header, Input, Label, Static


@dataclass
class Candidate:
    """Local representation of a candidate directory."""

    path: str
    approx_files: int
    tags: list[str]


class IngestApp(App):
    """Minimal Textual front-end for this week's ingest workflow."""

    TITLE = "ARTIFACT-MINER"
    CSS = """
    Screen {
        align: center middle;
    }

    #main {
        width: 80%;
        max-width: 80;
        padding: 1 2;
        border: round $surface;
        background: $panel;
    }

    #input-row {
        height: auto;
        margin-bottom: 1;
    }

    #zip-path {
        width: 1fr;
        margin-right: 1;
    }

    #progress-label, #selection-label {
        height: auto;
        margin: 1 0;
    }

    #candidates-title {
        margin-top: 1;
        text-style: bold;
    }

    #candidate-list {
        height: 10;
        border: solid $accent;
        padding: 1;
        margin-top: 1;
    }

    Checkbox {
        margin-bottom: 1;
    }
    """

    BINDINGS = [("q", "quit", "Quit")]

    api_base: str
    http: Optional[httpx.AsyncClient]
    ingest_id: Optional[str]
    progress_task: Optional[asyncio.Task]
    _checkbox_map: dict[str, str]
    upload_button: Optional[Button]
    save_button: Optional[Button]
    zip_input: Optional[Input]
    progress_label: Optional[Label]
    selection_label: Optional[Label]
    candidate_list: Optional[VerticalScroll]

    def __init__(self) -> None:
        super().__init__()
        self.api_base = os.environ.get("API_BASE", "http://127.0.0.1:8000").rstrip("/")
        self.http = None
        self.ingest_id = None
        self.progress_task = None
        self._checkbox_map = {}
        self.upload_button = None
        self.save_button = None
        self.zip_input = None
        self.progress_label = None
        self.selection_label = None
        self.candidate_list = None

    async def on_mount(self) -> None:
        """Allocate shared HTTP client."""

        self.http = httpx.AsyncClient(base_url=self.api_base, timeout=15.0)
        # Cache widget references for later use.
        self.upload_button = self.query_one("#upload-btn", Button)
        self.save_button = self.query_one("#save-btn", Button)
        self.zip_input = self.query_one("#zip-path", Input)
        self.progress_label = self.query_one("#progress-label", Label)
        self.selection_label = self.query_one("#selection-label", Label)
        self.candidate_list = self.query_one("#candidate-list", VerticalScroll)

    async def on_shutdown(self) -> None:
        """Gracefully close background resources."""

        if self.progress_task:
            self.progress_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.progress_task
        if self.http:
            await self.http.aclose()

    def compose(self) -> ComposeResult:
        """Build the UI layout."""

        yield Header()
        with Vertical(id="main"):
            with Horizontal(id="input-row"):
                yield Input(placeholder="Path to .zip", id="zip-path")
                yield Button("Upload", id="upload-btn", variant="primary")
            yield Label("Awaiting upload.", id="progress-label")
            yield Static("Candidates", id="candidates-title")
            with VerticalScroll(id="candidate-list"):
                yield Static("Upload a zip to list candidate folders.")
            yield Button("Save Selection", id="save-btn", disabled=True, variant="success")
            yield Label("", id="selection-label")
        yield Footer()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle all button click interactions."""

        if not self.http:
            self._update_progress("Still initialising, please wait a moment.")
            return

        if event.button.id == "upload-btn":
            await self._handle_upload()
        elif event.button.id == "save-btn":
            await self._handle_save()

    async def _handle_upload(self) -> None:
        """Upload the selected zip and start polling progress."""

        if not self.http:
            self._update_progress("HTTP client unavailable.")
            return

        upload_button = self.upload_button
        save_button = self.save_button
        if upload_button:
            upload_button.disabled = True
        if save_button:
            save_button.disabled = True
        self._clear_candidates()
        self.ingest_id = None
        if not self.zip_input:
            self._update_progress("Zip input not ready.")
            if upload_button:
                upload_button.disabled = False
            return
        path_str = self.zip_input.value.strip()

        if not path_str:
            self._update_progress("Please provide a path to a .zip file.")
            if upload_button:
                upload_button.disabled = False
            return

        path = Path(path_str).expanduser()
        if not path.exists():
            self._update_progress(f"File not found: {path}")
            if upload_button:
                upload_button.disabled = False
            return
        if path.suffix.lower() != ".zip":
            self._update_progress("Only .zip files are supported this week.")
            if upload_button:
                upload_button.disabled = False
            return

        self._update_progress("Uploading archive...")
        try:
            data = await asyncio.to_thread(path.read_bytes)
        except OSError as exc:
            self._update_progress(f"Failed to read file: {exc}")
            if upload_button:
                upload_button.disabled = False
            return

        try:
            response = await self.http.post(
                "/ingest/upload",
                files={"file": (path.name, data, "application/zip")},
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = self._extract_error(exc.response)
            self._update_progress(f"Upload failed ({exc.response.status_code}): {detail}")
            if upload_button:
                upload_button.disabled = False
            return
        except httpx.HTTPError as exc:
            self._update_progress(f"Upload error: {exc}")
            if upload_button:
                upload_button.disabled = False
            return

        payload = response.json()
        self.ingest_id = payload["ingest_id"]
        self._update_progress("Upload accepted. Validating zip...")

        if self.progress_task:
            self.progress_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.progress_task
        self.progress_task = asyncio.create_task(self._progress_loop(self.ingest_id))

    async def _progress_loop(self, ingest_id: str) -> None:
        """Poll the progress endpoint until selection is ready or an error occurs."""

        assert self.http is not None

        try:
            while True:
                response = await self.http.get(f"/ingest/{ingest_id}/progress")
                response.raise_for_status()
                progress = response.json()
                phase = progress["phase"]
                message = progress.get("message") or ""
                percent = progress.get("percent", 0.0)
                self._update_progress(f"{phase.replace('_', ' ').title()} ({percent:.0f}%){' - ' + message if message else ''}")

                if phase == "waiting_for_selection":
                    await self._load_candidates(ingest_id)
                    break
                if phase == "error":
                    if self.selection_label:
                        self.selection_label.update("An error occurred during scanning. Please retry.")
                    break

                await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            raise
        except httpx.HTTPStatusError as exc:
            self._update_progress(f"Progress check failed ({exc.response.status_code}).")
        except httpx.HTTPError as exc:
            self._update_progress(f"Progress polling error: {exc}")
        except Exception as exc:  # pragma: no cover - defensive
            self._update_progress(f"Unexpected polling error: {exc}")
        finally:
            if self.upload_button:
                self.upload_button.disabled = False
            if self.progress_task is asyncio.current_task():
                self.progress_task = None

    async def _load_candidates(self, ingest_id: str) -> None:
        """Fetch candidates, retrying if the server reports they are not ready yet."""

        assert self.http is not None

        attempt = 0
        while True:
            try:
                response = await self.http.get(f"/ingest/{ingest_id}/candidates")
                response.raise_for_status()
                data = response.json()
                raw_candidates = data.get("candidates", [])
                candidates = [
                    Candidate(
                        path=item["path"],
                        approx_files=item.get("approx_files", 0),
                        tags=item.get("tags", []),
                    )
                    for item in raw_candidates
                ]
                self._display_candidates(candidates)
                self._update_progress("Candidates ready. Select the stories to keep.")
                if self.save_button:
                    self.save_button.disabled = False
                return
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 409:
                    await asyncio.sleep(0.5)
                    attempt += 1
                    continue
                detail = self._extract_error(exc.response)
                self._update_progress(f"Failed to fetch candidates: {detail}")
                return
            except httpx.HTTPError as exc:
                self._update_progress(f"Candidate fetch error: {exc}")
                return

    async def _handle_save(self) -> None:
        """Send the selected candidates back to the API."""

        if not self.http or not self.ingest_id:
            self._update_progress("Cannot save selection yet.")
            return

        selected_paths = []
        if not self.candidate_list:
            self._update_progress("No candidates to save yet.")
            return
        for checkbox in self.candidate_list.query(Checkbox):
            if checkbox.value:
                mapped = self._checkbox_map.get(checkbox.id)
                selected_paths.append(mapped if mapped is not None else str(checkbox.label))

        try:
            response = await self.http.post(
                f"/ingest/{self.ingest_id}/select",
                json={"selected_paths": selected_paths},
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = self._extract_error(exc.response)
            self._update_progress(f"Save failed ({exc.response.status_code}): {detail}")
            return
        except httpx.HTTPError as exc:
            self._update_progress(f"Save error: {exc}")
            return

        saved = response.json()
        if self.selection_label:
            self.selection_label.update(f"Selection saved ({len(saved.get('selected_paths', []))} items).")
        self._update_progress("Selection stored. Feel free to upload another zip.")

    def _display_candidates(self, candidates: list[Candidate]) -> None:
        """Render candidate checkboxes into the UI."""

        self._checkbox_map.clear()
        if not self.candidate_list:
            return
        candidate_list = self.candidate_list
        self._clear_widget_children(candidate_list)

        if not candidates:
            candidate_list.mount(Static("No candidate folders discovered."))
            return

        for index, candidate in enumerate(candidates):
            tags = ", ".join(candidate.tags) if candidate.tags else "other"
            label_text = f"{candidate.path} (~{candidate.approx_files} files) [tags: {tags}]"
            checkbox = Checkbox(label_text, id=f"candidate-{index}")
            self._checkbox_map[checkbox.id] = candidate.path
            candidate_list.mount(checkbox)

    def _clear_candidates(self) -> None:
        """Reset candidate list to an empty state."""

        self._checkbox_map.clear()
        if not self.candidate_list:
            return
        candidate_list = self.candidate_list
        self._clear_widget_children(candidate_list)
        candidate_list.mount(Static("Upload a zip to list candidate folders."))
        if self.selection_label:
            self.selection_label.update("")

    def _update_progress(self, text: str) -> None:
        """Update the progress label with the latest message."""

        if self.progress_label:
            self.progress_label.update(text)

    @staticmethod
    def _clear_widget_children(container: VerticalScroll) -> None:
        """Remove all child widgets from the given container."""

        for child in list(container.children):
            child.remove()

    @staticmethod
    def _extract_error(response: httpx.Response) -> str:
        """Safely extract a detail message from a HTTPX response."""

        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            try:
                data = response.json()
                detail = data.get("detail")
                if detail:
                    return str(detail)
            except (ValueError, AttributeError):
                return response.text or "Unknown error"
        return response.text or "Unknown error"


if __name__ == "__main__":
    IngestApp().run()

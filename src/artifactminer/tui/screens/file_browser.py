from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, DirectoryTree, Footer, Header, Label, Static


class FilteredDirectoryTree(DirectoryTree):
    """Directory tree widget that hides dot-prefixed files and directories."""

    def filter_paths(self, paths: list[Path]) -> list[Path]:
        """Return only visible (non-hidden) paths."""
        return [path for path in paths if not path.name.startswith(".")]


class FileBrowserScreen(Screen):
    """Screen for browsing and selecting .zip files from the filesystem."""

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="content"):
            with Container(id="card-wrapper"):
                with Vertical(id="card"):
                    yield Static("Select a .zip file", id="title")
                    with Container(id="browser-container"):
                        yield FilteredDirectoryTree(Path.home(), id="file-tree")
                    yield Label("", id="browser-status") # For status messages
                    with Horizontal(id="browser-actions"):
                        yield Button("Cancel", id="cancel-btn")
                        yield Button("Select", id="select-btn", variant="primary")
        yield Footer()

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        """Auto-dismiss when a `.zip` file is selected in the tree."""
        if event.path.suffix.lower() == ".zip":
            self.dismiss(event.path)
        else:
            status = self.query_one("#browser-status", Label) # query_one is a Textual method to find a widget by its ID (id of widget, type of that widget). similar to document.getElementById in JS
            status.update("Please select a .zip file")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-btn":
            self.dismiss(None)
        elif event.button.id == "select-btn":
            tree = self.query_one("#file-tree", FilteredDirectoryTree)
            if tree.cursor_node and tree.cursor_node.data:
                path = tree.cursor_node.data.path
                if path.is_file() and path.suffix.lower() == ".zip":
                    self.dismiss(path)
                else:
                    status = self.query_one("#browser-status", Label)
                    status.update("Please select a .zip file")

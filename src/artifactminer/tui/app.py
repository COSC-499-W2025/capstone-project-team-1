from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Input, Button, DataTable
from textual.screen import Screen
from textual.containers import Vertical, Horizontal
from artifactminer.tui.services.prefs import load_prefs, save_prefs, validate_path

STATE = {
    "scan_paths": [],
    "results": [
        {"name": "main.py",   "type": "code", "size": 1200, "tags": "python,project1"},
        {"name": "README.md", "type": "docs", "size": 800,  "tags": "docs,project1"},
    ],
}

class Welcome(Screen):
    BINDINGS = [("p", "go_paths", "Paths"), ("d", "go_dash", "Dashboard"), ("q", "app.quit", "Quit")]
    def compose(self) -> ComposeResult:
        yield Header()
        prefs = load_prefs()
        paths = prefs.get("scan_paths", [])
        msg = f"ARTIFACT Miner - {len(paths)} folder(s) configured\n[P] Configure Paths  [D] Dashboard  [Q] Quit"
        yield Static(msg)
        yield Footer()
    def action_go_paths(self): self.app.push_screen(Paths())
    def action_go_dash(self): self.app.push_screen(Dashboard())

class Paths(Screen):
    def compose(self):
        yield Header()
        yield Vertical(
            Static("Add an absolute folder path:"),
            Input(placeholder="/absolute/folder/path", id="path_input"),
            Button("Add Path", id="add_btn"),
            Static("Current Paths:"),
            Static("", id="paths_list"),
        )
        yield Footer()

    def on_show(self) -> None:
        prefs = load_prefs()
        STATE["scan_paths"] = prefs.get("scan_paths", [])
        self.query_one("#paths_list", Static).update("\n".join(f"- {p}" for p in STATE["scan_paths"]))

    def on_button_pressed(self, event):
        if event.button.id != "add_btn": return
        path = self.query_one("#path_input", Input).value.strip()
        ok, msg = validate_path(path)
        if not ok:
            self.app.notify(msg, severity="error"); return
        if path in STATE["scan_paths"]:
            self.app.notify("Already added.", severity="warning"); return
        STATE["scan_paths"].append(path)
        save_prefs({"scan_paths": STATE["scan_paths"]})
        self.query_one("#paths_list", Static).update("\n".join(f"- {p}" for p in STATE["scan_paths"]))
        self.app.notify("Path added.")

class Dashboard(Screen):
    def compose(self):
        yield Header()
        self.table = DataTable()
        self.table.add_columns("Name", "Type", "Size", "Tags")
        yield self.table
        yield Footer()

    def on_show(self) -> None:
        self.table.clear()
        for r in STATE["results"]:
            self.table.add_row(r["name"], r["type"], str(r["size"]), r["tags"])

class ArtifactMinerTUI(App):
    def on_mount(self): self.push_screen(Welcome())

def run():
    ArtifactMinerTUI().run()

if __name__ == "__main__":
    run()

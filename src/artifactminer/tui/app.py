from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Static
from textual.containers import Vertical

APP_CSS = """
#title {
    text-align: center;
    padding: 1;
}
#subtitle {
    text-align: center;
    color: $text-muted;
}
"""


class Welcome(Screen):
    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Vertical(
            Static("Welcome to ARTIFACT Miner", id="title"),
            Static("Code artifact discovery and analysis tool", id="subtitle"),
        )
        yield Footer()


class ArtifactMinerTUI(App):
    CSS = APP_CSS

    def on_mount(self) -> None:
        self.push_screen(Welcome())


def run():
    ArtifactMinerTUI().run()


if __name__ == "__main__":
    run()

"""Styling components and visual helpers for the demo."""

import time
from typing import List

from rich.align import Align
from rich.console import Console
from rich.columns import Columns
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.rule import Rule
from rich.text import Text
from rich.tree import Tree

from demo.requirements import REQUIREMENTS, demonstrated_requirements
from demo.theme import BANNER_ART, TEAM_INFO, STATUS_ICONS

console = Console()


def truncate(value, limit: int = 80) -> str:
    """Trim long strings for display."""
    if value is None:
        return "-"
    text = str(value)
    return text if len(text) <= limit else text[: limit - 1] + "..."


def format_timestamp(value) -> str:
    """Render ISO timestamps in compact format."""
    if not value:
        return "-"
    text = str(value)
    if "T" in text:
        text = text.replace("T", " ").split(".")[0]
    return text


def animate_spinner(message: str, duration: float = 1.5) -> None:
    """Show spinner animation for visual feedback."""
    with Progress(
        SpinnerColumn("dots"),
        TextColumn("[cyan]{task.description}[/cyan]"),
        transient=True,
    ) as progress:
        progress.add_task(message, total=None)
        time.sleep(duration)


def section_header(title: str, subtitle: str = "") -> None:
    """Print section divider with title."""
    console.print()
    console.print(Rule(f"[bold magenta]{title}[/bold magenta]", style="magenta"))
    if subtitle:
        console.print(Align.center(f"[dim italic]{subtitle}[/dim italic]"))
    console.print()


def print_splash_screen() -> None:
    """Render splash screen with banner."""
    console.clear()
    banner_panel = Panel(
        Align.center(Text(BANNER_ART, style="bold cyan")),
        border_style="blue",
        padding=(1, 2),
    )
    console.print(banner_panel)
    console.print(Align.center(f"[dim]{TEAM_INFO}[/dim]"))
    console.print()
    console.print(
        Align.center("[bold magenta]Interactive Requirements Demo[/bold magenta]")
    )
    console.print()

    features = ["20 Requirements", "Live API Calls", "Privacy-First", "Full Coverage"]
    panels = [
        Panel(f"[white]{f}[/white]", border_style="dim", padding=(0, 1))
        for f in features
    ]
    console.print(Columns(panels, equal=True, expand=True))
    console.print()


def print_requirement_banner(req_ids: List[int], section_title: str) -> None:
    """Display banner showing which requirements are being demonstrated."""
    reqs = [r for r in REQUIREMENTS if r.id in req_ids]

    for req_id in req_ids:
        demonstrated_requirements.add(req_id)

    req_parts = []
    for req in reqs:
        color = (
            "green"
            if req.status == "FULLY MET"
            else "yellow"
            if "PARTIAL" in req.status
            else "red"
        )
        icon = STATUS_ICONS.get(req.status, "?")
        req_parts.append(
            f"[bold white]REQ #{req.id}:[/bold white] [cyan]{req.short}[/cyan]\n"
            f"[{color}]{icon} {req.status} ({req.coverage}%)[/{color}]\n"
            f"[dim]{req.full}[/dim]"
        )

    panel = Panel(
        "\n\n".join(req_parts),
        title=f"[bold white on magenta] {section_title} [/bold white on magenta]",
        subtitle="[dim]Requirements Being Demonstrated[/dim]",
        border_style="magenta",
        padding=(1, 2),
    )
    console.print()
    console.print(panel)
    console.print()


def print_how_banner(req_ids: List[int]) -> None:
    """Show HOW requirements are satisfied after demonstrating."""
    reqs = [r for r in REQUIREMENTS if r.id in req_ids]

    tree = Tree("[bold cyan]How Requirements Are Satisfied[/bold cyan]")
    for req in reqs:
        branch = tree.add(f"[bold]REQ #{req.id}:[/bold] [white]{req.short}[/white]")
        branch.add(f"[green]-> {req.how}[/green]")

    console.print()
    console.print(Panel(tree, border_style="cyan", padding=(1, 2)))


def show_final_scorecard() -> None:
    """Display final compliance scorecard."""
    console.clear()
    console.print()
    console.print(
        Panel(
            Align.center(Text("REQUIREMENTS COMPLIANCE SCORECARD", style="bold white")),
            border_style="magenta",
        )
    )
    console.print()

    total = len(REQUIREMENTS)
    demonstrated = len(demonstrated_requirements)
    fully_met = sum(1 for r in REQUIREMENTS if r.status == "FULLY MET")

    stats = [
        Panel(f"[bold cyan]{total}[/bold cyan]\n[dim]Total[/dim]", border_style="cyan"),
        Panel(
            f"[bold green]{demonstrated}[/bold green]\n[dim]Demonstrated[/dim]",
            border_style="green",
        ),
        Panel(
            f"[bold green]{fully_met}[/bold green]\n[dim]Fully Met[/dim]",
            border_style="green",
        ),
    ]
    console.print(Columns(stats, equal=True, expand=True))
    console.print()

    pct = (fully_met / total) * 100
    bar_width = 50
    filled = int(bar_width * pct / 100)
    bar = "#" * filled + "-" * (bar_width - filled)

    console.print(Align.center(f"[bold]Compliance: [green]{pct:.0f}%[/green][/bold]"))
    console.print(Align.center(f"[green]{bar}[/green]"))
    console.print()

    if pct == 100:
        console.print(
            Panel(
                Align.center("[bold green]ALL REQUIREMENTS FULLY MET![/bold green]"),
                border_style="green",
            )
        )

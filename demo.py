"""Rich-powered Artifact Miner demo script.

This script exercises the FastAPI endpoints that exist on this branch using
`httpx` for HTTP calls and `rich` for polished terminal output. It walks through
the currently available flow end-to-end:

1. Check `/health`.
2. Inspect `/questions` and submit answers via `/answers`.
3. Configure consent with `/consent`.
4. Upload a ZIP file and list its directories via `/zip/upload` and
   `/zip/{id}/directories`.
5. Call the `/openai` helper (requires `OPENAI_API_KEY` in the environment).

Design documents outline additional endpoints such as `/analyze/{zip_id}`,
`/summaries`, `/resume`, `/skills/chronology`, `/projects/timeline`, and
`DELETE /projects/{id}`. Those routes are not present on this branch, so this
script includes placeholder helpers that clearly mark TODOs. Once the API grows,
fill those helpers in with real requests.

Usage:
    uv run python demo.py

Environment overrides:
    ARTIFACT_MINER_API_URL   - Base URL for the API (default 127.0.0.1:8000)
    ARTIFACT_MINER_ZIP_PATH  - Path to the demo ZIP file
    ARTIFACT_MINER_USER_EMAIL- Email stored in questionnaire answers
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import httpx
from rich import box
from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
API_URL = os.environ.get("ARTIFACT_MINER_API_URL", "http://127.0.0.1:8000")
ZIP_FILE_PATH = Path(
    os.environ.get(
        "ARTIFACT_MINER_ZIP_PATH",
        "tests/directorycrawler/mocks/mockdirectory_zip.zip",
    )
)
USER_EMAIL = os.environ.get("ARTIFACT_MINER_USER_EMAIL", "shlok10@student.ubc.ca")
OPENAI_ENABLED = bool(os.environ.get("OPENAI_API_KEY"))
DEMO_PROMPT = (
    "Summarize how Artifact Miner highlights a student's strongest projects."
)

console = Console()


# --------------------------------------------------------------------------- #
# Rich helpers
# --------------------------------------------------------------------------- #
def print_banner() -> None:
    """Render the demo banner once at startup."""
    banner_text = r"""
    _         _   _  __            _     __  __ _                  
   / \   _ __| |_(_)/ _| __ _  ___| |_  |  \/  (_)_ __   ___ _ __  
  / _ \ | '__| __| | |_ / _` |/ __| __| | |\/| | | '_ \ / _ \ '__| 
 / ___ \| |  | |_| |  _| (_| | (__| |_  | |  | | | | | |  __/ |    
/_/   \_\_|   \__|_|_|  \__,_|\___|\__| |_|  |_|_|_| |_|\___|_|    
    """
    console.clear()
    console.print(
        Panel(
            Align.center(Text(banner_text, style="bold cyan")),
            subtitle="[bold]Artifact Miner Milestone Demo[/bold]",
            subtitle_align="center",
            border_style="blue",
        )
    )
    console.print(Align.center("[dim]Team 1 • Automated Portfolio Generation[/dim]\n"))


def section(title: str, subtitle: str | None = None) -> None:
    """Print a section divider."""
    console.print()
    console.print(f"[bold magenta]━━━ {title} ━━━[/bold magenta]")
    if subtitle:
        console.print(f"[dim italic]{subtitle}[/dim italic]")
    console.print()


def exit_with_error(message: str) -> None:
    """Fail fast with a stylized error message."""
    console.print(Panel(f"[bold red]{message}[/bold red]", border_style="red"))
    raise SystemExit(1)


def ensure_zip_exists(zip_path: Path) -> Path:
    """Validate that the default ZIP file exists before uploading."""
    if not zip_path.exists():
        exit_with_error(f"Missing test ZIP file: {zip_path}")
    return zip_path


# --------------------------------------------------------------------------- #
# HTTP helpers
# --------------------------------------------------------------------------- #
def check_health(client: httpx.Client) -> Dict[str, Any]:
    response = client.get("/health")
    response.raise_for_status()
    return response.json()


def fetch_questions(client: httpx.Client) -> List[Dict[str, Any]]:
    response = client.get("/questions")
    response.raise_for_status()
    return response.json()


def submit_answers(client: httpx.Client, answers: Dict[str, str]) -> List[Dict[str, Any]]:
    payload = {"answers": answers}
    response = client.post("/answers", json=payload)
    response.raise_for_status()
    return response.json()


def update_consent(client: httpx.Client, consent_level: str) -> Dict[str, Any]:
    response = client.put("/consent", json={"consent_level": consent_level})
    response.raise_for_status()
    return response.json()


def upload_zip(client: httpx.Client, zip_path: Path) -> Dict[str, Any]:
    with zip_path.open("rb") as fp:
        files = {"file": (zip_path.name, fp, "application/zip")}
        response = client.post("/zip/upload", files=files)
    response.raise_for_status()
    return response.json()


def list_directories(client: httpx.Client, zip_id: int) -> Dict[str, Any]:
    response = client.get(f"/zip/{zip_id}/directories")
    response.raise_for_status()
    return response.json()


def call_openai(client: httpx.Client, prompt: str) -> Dict[str, Any]:
    response = client.post("/openai", json={"prompt": prompt})
    response.raise_for_status()
    return response.json()


# --------------------------------------------------------------------------- #
# Display helpers
# --------------------------------------------------------------------------- #
def show_health(status: Dict[str, Any]) -> None:
    panel = Panel.fit(
        f"[bold green]Status:[/bold green] {status.get('status', 'unknown')}\n"
        f"[bold]Timestamp:[/bold] {status.get('timestamp')}",
        title="Healthcheck",
        border_style="green",
    )
    console.print(panel)


def show_questions(questions: List[Dict[str, Any]]) -> None:
    table = Table(title="Configuration Questions", box=box.ROUNDED, border_style="blue")
    table.add_column("Key", style="cyan", no_wrap=True)
    table.add_column("Prompt", style="white")
    table.add_column("Required", justify="center")
    for question in questions:
        table.add_row(
            question.get("key") or str(question.get("id")),
            question.get("question_text", ""),
            "✅" if question.get("required") else "—",
        )
    console.print(table)


def show_answers(answers: List[Dict[str, Any]]) -> None:
    table = Table(
        title="Saved Answers",
        box=box.SIMPLE_HEAVY,
        border_style="green",
        show_lines=True,
    )
    table.add_column("Question ID", justify="center")
    table.add_column("Answer", style="white")
    for answer in answers:
        table.add_row(str(answer.get("question_id")), answer.get("answer_text", ""))
    console.print(table)


def show_consent(consent: Dict[str, Any]) -> None:
    panel = Panel(
        Align.center(
            f"[bold yellow]{consent.get('consent_level', '').upper()}[/bold yellow]\n"
            f"[dim]{consent.get('accepted_at') or 'Not accepted yet'}[/dim]"
        ),
        title="Consent Mode",
        border_style="yellow",
    )
    console.print(panel)


def show_directories_listing(directory_payload: Dict[str, Any]) -> None:
    directories = directory_payload.get("directories", [])
    table = Table(title="ZIP Directory Listing", border_style="cyan", box=box.SQUARE)
    table.add_column("Directory", style="white")
    if not directories:
        table.add_row("[dim]No directories reported.[/dim]")
    else:
        for entry in directories:
            table.add_row(f"[bold]{entry}[/bold]")
    console.print(table)


def show_openai_response(response: Dict[str, Any]) -> None:
    panel = Panel(
        response.get("response", "[dim]No response text provided[/dim]"),
        title="OpenAI Helper",
        border_style="blue",
    )
    console.print(panel)


def show_openai_placeholder() -> None:
    """Explain how to enable the OpenAI helper when API keys are absent."""
    console.print(
        Panel(
            "[italic]Skipping /openai call because OPENAI_API_KEY is not set.[/italic]\n"
            "Export your API key and re-run the demo to see an actual response.\n"
            "Example:\n[bold]export OPENAI_API_KEY=sk-yourkey[/bold]",
            title="OpenAI Helper (Disabled)",
            border_style="yellow",
        )
    )


# --------------------------------------------------------------------------- #
# Placeholder helpers for future endpoints
# --------------------------------------------------------------------------- #
def run_analysis_placeholder(zip_id: int, user_email: str) -> None:
    """Placeholder for POST /analyze/{zip_id} once implemented."""
    console.print(
        Panel(
            f"[italic]TODO: POST /analyze/{zip_id} (user_email={user_email}).[/italic]\n"
            "This route will trigger the ingestion pipeline and repository analysis.",
            title="Analysis Pipeline",
            border_style="yellow",
        )
    )


def fetch_summaries_placeholder(user_email: str) -> None:
    """Placeholder for GET /summaries."""
    console.print(
        Panel(
            f"[italic]TODO: GET /summaries?user_email={user_email}.[/italic]\n"
            "Once available, this section will display ranked project summaries.",
            title="Summaries",
            border_style="yellow",
        )
    )


def fetch_resume_placeholder() -> None:
    """Placeholder for GET /resume."""
    console.print(
        Panel(
            "[italic]TODO: GET /resume.[/italic]\n"
            "The response will populate generated résumé bullet points.",
            title="Resume Items",
            border_style="yellow",
        )
    )


def fetch_skill_chronology_placeholder() -> None:
    """Placeholder for GET /skills/chronology."""
    console.print(
        Panel(
            "[italic]TODO: GET /skills/chronology.[/italic]\n"
            "Chronological skill timelines will appear here once the endpoint exists.",
            title="Skill Chronology",
            border_style="yellow",
        )
    )


def lifecycle_placeholder() -> None:
    """Placeholder for project timeline and deletion endpoints."""
    console.print(
        Panel(
            "[italic]TODO: GET /projects/timeline and DELETE /projects/{id}.[/italic]\n"
            "Future demos will show safe deletion and lifecycle management.",
            title="Lifecycle Management",
            border_style="yellow",
        )
    )


# --------------------------------------------------------------------------- #
# Demo runner
# --------------------------------------------------------------------------- #
def build_answers(email: str) -> Dict[str, str]:
    """Construct questionnaire answers for the demo."""
    return {
        "email": email,
        "artifacts_focus": "Code Quality & Architecture",
        "end_goal": "Generate a compelling co-op portfolio",
        "repository_priority": "Focus on git repositories first",
        "file_patterns_include": "*.py,*.md",
        "file_patterns_exclude": "*.log,*.tmp",
    }


def run_demo() -> int:
    print_banner()
    ensure_zip_exists(ZIP_FILE_PATH)

    try:
        with httpx.Client(base_url=API_URL, timeout=60.0) as client:
            section("Health Check")
            health = check_health(client)
            show_health(health)

            section("Consent Management", "Configure deterministic vs LLM modes")
            consent = update_consent(client, "no_llm")
            show_consent(consent)

            section("Questionnaire", "Load prompts and submit configuration")
            questions = fetch_questions(client)
            show_questions(questions)
            answer_payload = build_answers(USER_EMAIL)
            saved_answers = submit_answers(client, answer_payload)
            show_answers(saved_answers)

            section("ZIP Upload & Directory Listing")
            upload_result = upload_zip(client, ZIP_FILE_PATH)
            console.print(
                Panel(
                    f"[bold]Uploaded:[/bold] {upload_result['filename']}\n"
                    f"[bold]zip_id:[/bold] {upload_result['zip_id']}",
                    border_style="green",
                    title="Upload Complete",
                )
            )
            directories = list_directories(client, upload_result["zip_id"])
            show_directories_listing(directories)

            section("OpenAI Helper", "Demonstrate prompt/response flow")
            if OPENAI_ENABLED:
                try:
                    openai_response = call_openai(client, DEMO_PROMPT)
                    show_openai_response(openai_response)
                except httpx.HTTPStatusError as exc:
                    console.print(
                        Panel(
                            f"OpenAI helper failed ({exc.response.status_code}). "
                            "Double-check your OPENAI_API_KEY and rerun the demo.",
                            border_style="red",
                            title="OpenAI Error",
                        )
                    )
            else:
                show_openai_placeholder()

            section("Future Milestone Hooks", "Placeholder outputs until APIs land")
            run_analysis_placeholder(upload_result["zip_id"], USER_EMAIL)
            fetch_summaries_placeholder(USER_EMAIL)
            fetch_resume_placeholder()
            fetch_skill_chronology_placeholder()
            lifecycle_placeholder()

        console.print()
        console.print(
            Panel(
                Align.center("[bold green]✨ Demo complete for current API surface ✨[/bold green]"),
                border_style="green",
            )
        )
        return 0
    except httpx.HTTPError as exc:
        exit_with_error(f"HTTP error: {exc}")
    except Exception as exc:  # pylint: disable=broad-except
        exit_with_error(f"Unexpected error: {exc}")
    return 1


if __name__ == "__main__":
    sys.exit(run_demo())

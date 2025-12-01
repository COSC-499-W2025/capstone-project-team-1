"""Rich-powered Artifact Miner demo script.

This CLI runs through the full Artifact Miner API surface using real HTTP
requests (via `httpx`) and friendly terminal output (via `rich`). The flow hits
every major endpoint now available on the backend:

1. `GET /health` – confirm the API is live.
2. `GET /questions` + `POST /answers` – seed questionnaire data.
3. `PUT /consent` – record privacy mode (`full` when OPENAI_API_KEY is set).
4. `POST /zip/upload` + `GET /zip/{id}/directories` – ingest a demo archive.
5. `POST /openai` – optional helper call (skipped if OPENAI_API_KEY missing).
6. `POST /analyze/{zip_id}` – trigger the full repository intelligence pipeline.
7. `GET /summaries`, `/resume`, `/skills/chronology` – retrieve stored insights.
8. `GET /projects/timeline` and `DELETE /projects/{id}` – lifecycle management.

Usage:
    uv run python demo.py

Environment overrides:
    ARTIFACT_MINER_API_URL    Base URL for the API (default http://127.0.0.1:8000)
    ARTIFACT_MINER_ZIP_PATH   Path to a zipped folder of git repos
                              (default tests/data/mock_projects.zip)
    ARTIFACT_MINER_USER_EMAIL Email used for questionnaire + analysis context
    OPENAI_API_KEY            Enables the `/openai` helper if provided
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
        "tests/data/mock_projects.zip",
    )
)
USER_EMAIL = os.environ.get("ARTIFACT_MINER_USER_EMAIL", "shlok10@student.ubc.ca")
OPENAI_ENABLED = bool(os.environ.get("OPENAI_API_KEY"))
DEMO_PROMPT = (
    "Summarize how Artifact Miner highlights a student's strongest projects."
)

console = Console()


# --------------------------------------------------------------------------- #
# Utility helpers
# --------------------------------------------------------------------------- #
def truncate(value: Any, limit: int = 90) -> str:
    """Trim long strings for table display."""
    if value is None:
        return "—"
    text = str(value)
    return text if len(text) <= limit else text[: limit - 1] + "…"


def format_timestamp(value: Any) -> str:
    """Render ISO timestamps in a compact format."""
    if not value:
        return "—"
    text = str(value)
    if "T" in text:
        text = text.replace("T", " ").split(".")[0]
    return text


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


def run_analysis(client: httpx.Client, zip_id: int) -> Dict[str, Any]:
    response = client.post(f"/analyze/{zip_id}")
    response.raise_for_status()
    return response.json()


def fetch_summaries(client: httpx.Client, user_email: str) -> List[Dict[str, Any]]:
    response = client.get("/summaries", params={"user_email": user_email})
    response.raise_for_status()
    return response.json()


def fetch_resume_items(
    client: httpx.Client,
    project_id: int | None = None,
) -> List[Dict[str, Any]]:
    params = {"project_id": project_id} if project_id is not None else None
    response = client.get("/resume", params=params)
    response.raise_for_status()
    return response.json()


def fetch_skill_chronology(client: httpx.Client) -> List[Dict[str, Any]]:
    response = client.get("/skills/chronology")
    response.raise_for_status()
    return response.json()


def fetch_project_timeline(client: httpx.Client) -> List[Dict[str, Any]]:
    response = client.get("/projects/timeline")
    response.raise_for_status()
    return response.json()


def delete_project(client: httpx.Client, project_id: int) -> Dict[str, Any]:
    response = client.delete(f"/projects/{project_id}")
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


def show_analysis_result(result: Dict[str, Any]) -> None:
    """Display orchestration output (repos analyzed, rankings, etc.)."""
    overview = Panel(
        "[bold]ZIP ID:[/bold] {zip}\n"
        "[bold]Extraction:[/bold] {path}\n"
        "[bold]Repositories:[/bold] {repos}\n"
        "[bold]Consent:[/bold] {consent}\n"
        "[bold]Summaries Persisted:[/bold] {summaries}".format(
            zip=result.get("zip_id"),
            path=result.get("extraction_path"),
            repos=result.get("repos_found"),
            consent=result.get("consent_level"),
            summaries=len(result.get("summaries") or []),
        ),
        title="Analysis Overview",
        border_style="cyan",
    )
    console.print(overview)

    repos_table = Table(
        title="Repository Analysis",
        box=box.MINIMAL_DOUBLE_HEAD,
        border_style="cyan",
    )
    repos_table.add_column("Project", style="bold white")
    repos_table.add_column("Contribution", justify="right")
    repos_table.add_column("Skills", justify="right")
    repos_table.add_column("Insights", justify="right")
    repos_table.add_column("Status", style="white")

    for repo in result.get("repos_analyzed") or []:
        pct = repo.get("user_contribution_pct")
        contribution = f"{pct:.1f}%" if isinstance(pct, (int, float)) else "—"
        status = (
            "[green]OK[/green]" if not repo.get("error") else f"[red]{repo['error']}[/red]"
        )
        repos_table.add_row(
            repo.get("project_name", repo.get("project_path", "unknown")),
            contribution,
            str(repo.get("skills_count", "0")),
            str(repo.get("insights_count", "0")),
            status,
        )

    if repos_table.row_count:
        console.print(repos_table)
    else:
        console.print(Panel("[dim]No repository data returned.[/dim]", border_style="yellow"))

    if result.get("rankings"):
        ranking_table = Table(
            title="Ranked Projects",
            box=box.SIMPLE_HEAVY,
            border_style="magenta",
        )
        ranking_table.add_column("Project")
        ranking_table.add_column("Score", justify="right")
        ranking_table.add_column("Commits", justify="right")
        ranking_table.add_column("User Commits", justify="right")
        for item in result["rankings"]:
            ranking_table.add_row(
                item.get("name", "unknown"),
                f"{item.get('score', 0):.1f}",
                str(item.get("total_commits", 0)),
                str(item.get("user_commits", 0)),
            )
        console.print(ranking_table)
    else:
        console.print(
            Panel("[dim]Ranking skipped or unavailable.[/dim]", border_style="yellow")
        )


def show_summaries(summaries: List[Dict[str, Any]], limit: int = 3) -> None:
    if not summaries:
        console.print(
            Panel("[dim]No summaries stored yet.[/dim]", border_style="yellow", title="Summaries")
        )
        return

    for summary in summaries[:limit]:
        console.print(
            Panel(
                summary.get("summary_text", ""),
                title=f"Summary • {summary.get('repo_path')}",
                border_style="green",
            )
        )
    remaining = len(summaries) - min(len(summaries), limit)
    if remaining > 0:
        console.print(f"[dim]… {remaining} more summaries available via the API.[/dim]")


def show_resume_items(items: List[Dict[str, Any]], limit: int = 5) -> None:
    if not items:
        console.print(
            Panel("[dim]Resume store is empty.[/dim]", border_style="yellow", title="Resume Items")
        )
        return

    table = Table(
        title=f"Resume Items (showing {min(len(items), limit)} of {len(items)})",
        border_style="green",
        box=box.ROUNDED,
    )
    table.add_column("Title", style="bold white")
    table.add_column("Project", style="cyan")
    table.add_column("Category", style="magenta")
    table.add_column("Snippet", style="white")

    for item in items[:limit]:
        table.add_row(
            item.get("title", "Untitled"),
            item.get("project_name") or "—",
            item.get("category") or "—",
            truncate(item.get("content")),
        )
    console.print(table)


def show_skill_chronology(skills: List[Dict[str, Any]], limit: int = 6) -> None:
    if not skills:
        console.print(
            Panel("[dim]No skills extracted yet.[/dim]", border_style="yellow", title="Skill Chronology")
        )
        return

    table = Table(
        title=f"Skill Chronology (first {min(len(skills), limit)})",
        border_style="cyan",
        box=box.MINIMAL,
    )
    table.add_column("Date", style="white")
    table.add_column("Skill", style="bold")
    table.add_column("Project", style="cyan")
    table.add_column("Category", style="magenta")
    table.add_column("Proficiency", justify="right")

    for entry in skills[:limit]:
        prof = entry.get("proficiency")
        prof_text = f"{prof:.2f}" if isinstance(prof, (int, float)) else "—"
        table.add_row(
            format_timestamp(entry.get("date")),
            entry.get("skill", "unknown"),
            entry.get("project", "—"),
            entry.get("category") or "—",
            prof_text,
        )
    console.print(table)


def show_project_timeline(
    timeline: List[Dict[str, Any]],
    *,
    title: str = "Project Timeline",
    limit: int = 5,
) -> None:
    if not timeline:
        console.print(Panel("[dim]Timeline is empty.[/dim]", border_style="yellow", title=title))
        return

    table = Table(title=title, border_style="blue", box=box.SIMPLE)
    table.add_column("ID", justify="right")
    table.add_column("Project", style="bold")
    table.add_column("First Commit")
    table.add_column("Last Commit")
    table.add_column("Duration (days)", justify="right")
    table.add_column("Active?", justify="center")

    for item in timeline[:limit]:
        table.add_row(
            str(item.get("id")),
            item.get("project_name", "—"),
            format_timestamp(item.get("first_commit")),
            format_timestamp(item.get("last_commit")),
            str(item.get("duration_days", "—")),
            "✅" if item.get("was_active") else "—",
        )
    console.print(table)


def show_delete_result(payload: Dict[str, Any]) -> None:
    console.print(
        Panel(
            "[bold]Deleted ID:[/bold] {id}\n[bold]Message:[/bold] {msg}".format(
                id=payload.get("deleted_id"),
                msg=payload.get("message", ""),
            ),
            border_style="red",
            title="Project Deletion",
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
        timeout = httpx.Timeout(120.0)
        with httpx.Client(base_url=API_URL, timeout=timeout) as client:
            section("Health Check")
            health = check_health(client)
            show_health(health)

            section("Consent Management", "Configure deterministic vs LLM modes")
            consent_level = "full" if OPENAI_ENABLED else "no_llm"
            consent = update_consent(client, consent_level)
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

            section("Full Analysis Pipeline", "POST /analyze/{zip_id}")
            analysis_result = run_analysis(client, upload_result["zip_id"])
            show_analysis_result(analysis_result)

            section("Summaries & Resume Builder")
            summaries = fetch_summaries(client, USER_EMAIL)
            show_summaries(summaries)
            resume_items = fetch_resume_items(client)
            show_resume_items(resume_items)

            section("Skill Chronology", "GET /skills/chronology")
            skills = fetch_skill_chronology(client)
            show_skill_chronology(skills)

            section("Project Timeline & Lifecycle")
            timeline = fetch_project_timeline(client)
            show_project_timeline(timeline)

            project_to_delete = next((item for item in timeline if item.get("id")), None)
            if project_to_delete:
                delete_info = delete_project(client, project_to_delete["id"])
                show_delete_result(delete_info)
                updated_timeline = fetch_project_timeline(client)
                show_project_timeline(
                    updated_timeline,
                    title="Project Timeline (after delete)",
                )
            else:
                console.print(
                    Panel(
                        "[dim]No projects available to delete yet.[/dim]",
                        border_style="yellow",
                    )
                )

        console.print()
        console.print(
            Panel(
                Align.center("[bold green]✨ Demo complete across the end-to-end API ✨[/bold green]"),
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

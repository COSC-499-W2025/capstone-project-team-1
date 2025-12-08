#!/usr/bin/env python3
"""Artifact Miner Demo - Requirements Compliance Showcase.

Usage: uv run python demo.py
"""

import os
import sys
import tempfile
from pathlib import Path

from rich.panel import Panel
from rich.table import Table
from rich import box

from demo import (
    console,
    print_splash_screen,
    print_requirement_banner,
    print_how_banner,
    section_header,
    show_final_scorecard,
    animate_spinner,
    truncate,
    format_timestamp,
)
from demo.api import APIClient
from demo.keyboard import wait_for_enter

API_URL = os.environ.get("ARTIFACT_MINER_API_URL", "http://127.0.0.1:8000")
ZIP_PATH = Path(
    os.environ.get("ARTIFACT_MINER_ZIP_PATH", "tests/data/mock_projects.zip")
)


def demo_health(api: APIClient) -> bool:
    section_header("Health Check", "Verifying API connectivity")
    animate_spinner("Connecting...", 0.5)
    try:
        h = api.health_check()
        console.print(
            Panel(
                f"[green]Status: {h.get('status')}[/green]\nAPI: {API_URL}",
                title="API Online",
                border_style="green",
            )
        )
        return True
    except Exception as e:
        console.print(Panel(f"[red]Failed: {e}[/red]", border_style="red"))
        return False


def demo_consent(api: APIClient) -> str:
    print_requirement_banner([1, 4, 5], "Consent & Privacy")
    section_header("Consent Management")
    console.print("[dim]Setting consent to NO_LLM (deterministic analysis)...[/dim]")
    result = api.update_consent("no_llm")
    console.print(
        Panel(
            f"[yellow]Consent: {result.get('consent_level', '').upper()}[/yellow]",
            border_style="yellow",
        )
    )
    print_how_banner([1, 4, 5])
    wait_for_enter()
    return "no_llm"


def demo_wrong_format(api: APIClient):
    print_requirement_banner([3], "File Format Validation")
    section_header("Wrong Format Error")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("not a zip")
        tmp = Path(f.name)
    try:
        resp = api.upload_file_raw(tmp)
        if resp.status_code == 400:
            console.print(
                Panel(
                    f"[green]Correctly rejected![/green]\nStatus: {resp.status_code}\nError: {resp.json().get('detail')}",
                    border_style="green",
                )
            )
    finally:
        tmp.unlink()
    print_how_banner([3])
    wait_for_enter()


def demo_questionnaire(api: APIClient) -> str:
    print_requirement_banner([6], "User Configuration")
    section_header("Questionnaire")
    questions = api.get_questions()
    answers = {
        q.get("key", str(q.get("id"))): "demo@example.com"
        if "email" in str(q.get("key", "")).lower()
        else "demo"
        for q in questions
    }
    api.submit_answers(answers)
    console.print(Panel("[green]Configuration saved![/green]", border_style="green"))
    print_how_banner([6])
    wait_for_enter()
    return answers.get("email", "demo@example.com")


def demo_zip_upload(api: APIClient) -> int:
    print_requirement_banner([2], "ZIP Parsing")
    section_header("ZIP Upload")
    if not ZIP_PATH.exists():
        console.print(f"[red]ZIP not found: {ZIP_PATH}[/red]")
        wait_for_enter()
        return -1
    animate_spinner("Uploading...", 1.0)
    result = api.upload_zip(ZIP_PATH)
    console.print(
        Panel(
            f"[green]Uploaded![/green]\nZIP ID: {result.get('zip_id')}",
            border_style="green",
        )
    )
    print_how_banner([2])
    wait_for_enter()
    return result.get("zip_id", -1)


def demo_analysis(api: APIClient, zip_id: int):
    print_requirement_banner([7, 8, 9, 10, 11, 12, 13], "Analysis Pipeline")
    section_header("Repository Analysis")
    if zip_id < 0:
        console.print("[yellow]Skipping - no ZIP uploaded[/yellow]")
        wait_for_enter()
        return {}
    animate_spinner("Analyzing repositories...", 2.0)
    result = api.run_analysis(zip_id)
    console.print(
        Panel(
            f"Repos found: {result.get('repos_found')}\nSummaries: {len(result.get('summaries') or [])}",
            title="Analysis Complete",
            border_style="cyan",
        )
    )
    print_how_banner([7, 8, 9, 10, 11, 12, 13])
    wait_for_enter()
    return result


def demo_summaries(api: APIClient, email: str):
    print_requirement_banner([14, 17], "Portfolio Summaries")
    section_header("Summaries")
    summaries = api.get_summaries(email)
    if summaries:
        for s in summaries[:2]:
            console.print(
                Panel(
                    truncate(s.get("summary_text", ""), 200),
                    title=s.get("repo_path", "Project"),
                    border_style="green",
                )
            )
    else:
        console.print("[dim]No summaries yet[/dim]")
    print_how_banner([14, 17])
    wait_for_enter()


def demo_resume(api: APIClient):
    print_requirement_banner([15], "Resume Items")
    section_header("Resume Items")
    items = api.get_resume_items()
    if items:
        t = Table(box=box.SIMPLE)
        t.add_column("Title")
        t.add_column("Content")
        for i in items[:3]:
            t.add_row(i.get("title", "-"), truncate(i.get("content", ""), 50))
        console.print(t)
    else:
        console.print("[dim]No resume items yet[/dim]")
    print_how_banner([15])
    wait_for_enter()


def demo_ranking(api: APIClient, result: dict):
    print_requirement_banner([16], "Project Ranking")
    section_header("Rankings")
    rankings = result.get("rankings") or []
    for i, r in enumerate(rankings[:3], 1):
        console.print(
            f"  #{i} [bold]{r.get('name')}[/bold] - Score: {r.get('score', 0):.1f}"
        )
    if not rankings:
        console.print("[dim]No rankings yet[/dim]")
    print_how_banner([16])
    wait_for_enter()


def demo_timeline(api: APIClient):
    print_requirement_banner([19], "Chronological Projects")
    section_header("Timeline")
    timeline = api.get_project_timeline()
    for p in timeline[:3]:
        console.print(
            f"  {p.get('project_name')} | {format_timestamp(p.get('first_commit'))} - {format_timestamp(p.get('last_commit'))}"
        )
    if not timeline:
        console.print("[dim]No projects yet[/dim]")
    print_how_banner([19])
    wait_for_enter()
    return timeline


def demo_skills(api: APIClient):
    print_requirement_banner([20], "Chronological Skills")
    section_header("Skills")
    skills = api.get_skill_chronology()
    for s in skills[:5]:
        console.print(
            f"  {s.get('skill')} - {s.get('project', '-')} ({format_timestamp(s.get('date'))})"
        )
    if not skills:
        console.print("[dim]No skills yet[/dim]")
    print_how_banner([20])
    wait_for_enter()


def demo_delete(api: APIClient, timeline: list):
    print_requirement_banner([18], "Safe Deletion")
    section_header("Delete Project")
    if timeline:
        pid = timeline[0].get("id")
        console.print(f"[dim]Soft-deleting project {pid}...[/dim]")
        result = api.delete_project(pid)
        console.print(
            Panel(
                f"[green]Deleted ID: {result.get('deleted_id')}[/green]",
                border_style="green",
            )
        )
    else:
        console.print("[dim]No projects to delete[/dim]")
    print_how_banner([18])
    wait_for_enter()


def run_demo() -> int:
    console.clear()
    print_splash_screen()
    wait_for_enter("Press Enter to begin...")

    try:
        with APIClient(API_URL) as api:
            console.clear()
            if not demo_health(api):
                return 1
            wait_for_enter()

            console.clear()
            demo_consent(api)
            console.clear()
            demo_wrong_format(api)
            console.clear()
            email = demo_questionnaire(api)
            console.clear()
            zip_id = demo_zip_upload(api)
            console.clear()
            result = demo_analysis(api, zip_id)
            console.clear()
            demo_summaries(api, email)
            console.clear()
            demo_resume(api)
            console.clear()
            demo_ranking(api, result)
            console.clear()
            timeline = demo_timeline(api)
            console.clear()
            demo_skills(api)
            console.clear()
            demo_delete(api, timeline)

        console.clear()
        show_final_scorecard()
        wait_for_enter()
        console.print("\n[bold green]Demo Complete![/bold green]\n")
        return 0
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted[/yellow]")
        return 0
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return 1


if __name__ == "__main__":
    sys.exit(run_demo())

#!/usr/bin/env python3
"""Artifact Miner Demo - Requirements Compliance Showcase.

Usage: uv run python demo.py
"""

import os
import sys
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
    from rich.prompt import Prompt
    
    print_requirement_banner([1, 4, 5], "Consent & Privacy")
    section_header("Consent Management")
    
    # Show consent options with descriptions
    console.print("[cyan]Select your consent level for data processing:[/cyan]\n")
    console.print("  [bold green]1. full[/bold green]    - Full LLM access for AI-powered summaries")
    console.print("  [bold yellow]2. no_llm[/bold yellow]  - Deterministic analysis only (no external AI)")
    console.print("  [bold red]3. none[/bold red]    - No data processing\n")
    
    consent_map = {"1": "full", "2": "no_llm", "3": "none", "full": "full", "no_llm": "no_llm", "none": "none"}
    
    while True:
        choice = Prompt.ask(
            "[cyan]Enter choice (1/2/3 or full/no_llm/none)[/cyan]",
            default="2"
        ).strip().lower()
        
        if choice in consent_map:
            consent_level = consent_map[choice]
            break
        else:
            console.print("[red]Invalid choice. Please enter 1, 2, 3 or full, no_llm, none[/red]\n")
    
    animate_spinner("Setting consent...", 0.5)
    result = api.update_consent(consent_level)
    
    # Color based on consent level
    color = "green" if consent_level == "full" else "yellow" if consent_level == "no_llm" else "red"
    console.print(
        Panel(
            f"[{color}]Consent set to: {result.get('consent_level', consent_level).upper()}[/{color}]",
            border_style=color,
        )
    )
    print_how_banner([1, 4, 5])
    wait_for_enter()
    return consent_level



def demo_questionnaire(api: APIClient) -> str:
    from rich.prompt import Prompt, Confirm
    
    print_requirement_banner([6], "User Configuration")
    section_header("Questionnaire")
    
    questions = api.get_questions()
    
    if not questions:
        console.print("[dim]No questions configured[/dim]")
        wait_for_enter()
        return "demo@example.com"
    
    while True:  # Loop until successful submission
        answers = {}
        console.print("[cyan]Please answer the following questions:[/cyan]\n")
        
        for q in questions:
            key = q.get("key", str(q.get("id")))
            question_text = q.get("question", q.get("text", key))
            default = q.get("default", "")
            
            # Provide helpful defaults based on question type
            if "email" in key.lower():
                default = default or "demo@example.com"
            
            answer = Prompt.ask(
                f"  [white]{question_text}[/white]",
                default=default if default else None
            )
            answers[key] = answer
            console.print()
        
        # Try to submit answers
        animate_spinner("Saving configuration...", 0.5)
        
        try:
            resp = api.submit_answers_raw(answers)
            
            if resp.status_code in (400, 422):
                error_detail = resp.json().get("detail", "Validation error")
                console.print(
                    Panel(
                        f"[red]❌ Configuration failed![/red]\n"
                        f"Status: {resp.status_code}\n"
                        f"Error: {error_detail}",
                        border_style="red",
                    )
                )
                if not Confirm.ask("\n[yellow]Re-enter your answers?[/yellow]", default=True):
                    console.print("[dim]Skipping questionnaire...[/dim]")
                    wait_for_enter()
                    return "demo@example.com"
                console.print()
                continue  # Retry
            
            elif resp.status_code >= 400:
                console.print(f"\n[red]❌ Server error: {resp.status_code}[/red]")
                if not Confirm.ask("[yellow]Try again?[/yellow]", default=True):
                    wait_for_enter()
                    return "demo@example.com"
                console.print()
                continue
            
            # Success!
            console.print(Panel("[green]✅ Configuration saved![/green]", border_style="green"))
            print_how_banner([6])
            wait_for_enter()
            return answers.get("email", answers.get("user_email", "demo@example.com"))
            
        except Exception as e:
            console.print(f"\n[red]❌ Error: {e}[/red]")
            if not Confirm.ask("[yellow]Try again?[/yellow]", default=True):
                wait_for_enter()
                return "demo@example.com"
            console.print()
            continue


def demo_zip_upload(api: APIClient) -> int:
    from rich.prompt import Prompt, Confirm
    from rich.table import Table
    
    print_requirement_banner([2, 3], "ZIP Parsing & Validation")
    section_header("ZIP Upload")
    
    # Show default path and allow user to change it
    default_path = str(ZIP_PATH)
    console.print(f"[dim]Default ZIP path: {default_path}[/dim]\n")
    
    while True:
        zip_path_str = Prompt.ask(
            "[cyan]Enter ZIP file path[/cyan]",
            default=default_path
        )
        zip_path = Path(zip_path_str.strip())
        
        # Check if file exists locally first
        if not zip_path.exists():
            console.print(f"\n[red]❌ File not found: {zip_path}[/red]")
            if not Confirm.ask("[yellow]Try a different path?[/yellow]", default=True):
                return -1
            console.print()
            continue
        
        # Check if it's a file (not directory)
        if not zip_path.is_file():
            console.print(f"\n[red]❌ Not a file: {zip_path}[/red]")
            if not Confirm.ask("[yellow]Try a different path?[/yellow]", default=True):
                return -1
            console.print()
            continue
        
        # Attempt upload
        animate_spinner("Uploading...", 1.0)
        
        try:
            # Use raw upload to get response status
            resp = api.upload_file_raw(zip_path)
            
            if resp.status_code in (400, 404, 422):
                error_detail = resp.json().get("detail", "Unknown error")
                console.print(
                    Panel(
                        f"[red]❌ Upload failed![/red]\n"
                        f"Status: {resp.status_code}\n"
                        f"Error: {error_detail}",
                        border_style="red",
                    )
                )
                if not Confirm.ask("\n[yellow]Try a different ZIP file?[/yellow]", default=True):
                    return -1
                console.print()
                continue
            
            elif resp.status_code >= 400:
                console.print(f"\n[red]❌ Server error: {resp.status_code}[/red]")
                if not Confirm.ask("[yellow]Try again?[/yellow]", default=True):
                    return -1
                console.print()
                continue
            
            # Success!
            result = resp.json()
            zip_id = result.get("zip_id", -1)
            
            console.print(
                Panel(
                    f"[green]✅ Uploaded successfully![/green]\nZIP ID: {zip_id}",
                    border_style="green",
                )
            )
            
            # Show directories in the uploaded ZIP
            console.print("\n[cyan]Fetching directories...[/cyan]")
            animate_spinner("Loading...", 0.5)
            
            try:
                dirs_result = api.list_directories(zip_id)
                directories = dirs_result.get("directories", [])
                
                if directories:
                    table = Table(title="📁 Directories Found", box=box.ROUNDED)
                    table.add_column("#", style="dim", width=4)
                    table.add_column("Directory Path", style="cyan")
                    
                    for i, d in enumerate(directories[:20], 1):  # Show max 20
                        dir_path = d if isinstance(d, str) else d.get("path", str(d))
                        table.add_row(str(i), dir_path)
                    
                    if len(directories) > 20:
                        table.add_row("...", f"[dim]+{len(directories) - 20} more[/dim]")
                    
                    console.print(table)
                else:
                    console.print("[dim]No directories found in ZIP[/dim]")
                    
            except Exception as e:
                console.print(f"[dim]Could not fetch directories: {e}[/dim]")
            
            print_how_banner([2])
            wait_for_enter()
            return zip_id
            
        except Exception as e:
            console.print(f"\n[red]❌ Error: {e}[/red]")
            if not Confirm.ask("[yellow]Try again?[/yellow]", default=True):
                return -1
            console.print()
            continue


def demo_analysis(api: APIClient, zip_id: int):
    from rich.tree import Tree
    from rich.text import Text
    
    print_requirement_banner([8, 9, 10, 11, 12, 13], "Analysis Pipeline")
    section_header("Repository Analysis")
    
    if zip_id < 0:
        console.print("[yellow]Skipping - no ZIP uploaded[/yellow]")
        wait_for_enter()
        return {}
    
    animate_spinner("Analyzing repositories...", 2.0)
    
    try:
        result = api.run_analysis(zip_id)
    except Exception as e:
        console.print(Panel(f"[red]Analysis failed: {e}[/red]", border_style="red"))
        wait_for_enter()
        return {}
    
    repos = result.get("repos_analyzed", [])
    rankings = result.get("rankings", [])
    summaries = result.get("summaries", [])
    
    # ═══════════════════════════════════════════════════════════════════
    # OVERVIEW PANEL
    # ═══════════════════════════════════════════════════════════════════
    console.print(
        Panel(
            f"[bold green]✅ Analysis Complete[/bold green]\n\n"
            f"[cyan]Repositories Found:[/cyan] {result.get('repos_found', 0)}\n"
            f"[cyan]Repositories Analyzed:[/cyan] {len(repos)}\n"
            f"[cyan]Projects Ranked:[/cyan] {len(rankings)}\n"
            f"[cyan]Summaries Generated:[/cyan] {len(summaries)}\n"
            f"[cyan]Consent Level:[/cyan] {result.get('consent_level', 'unknown')}\n"
            f"[cyan]User Email:[/cyan] {result.get('user_email', 'unknown')}",
            title="[bold white]📊 Analysis Overview[/bold white]",
            border_style="green",
        )
    )
    console.print()
    
    # ═══════════════════════════════════════════════════════════════════
    # DETAILED REPO ANALYSIS - Proves REQ #8, #9, #10, #11, #12
    # ═══════════════════════════════════════════════════════════════════
    for i, repo in enumerate(repos, 1):
        if repo.get("error"):
            console.print(
                Panel(
                    f"[red]Error: {repo.get('error')}[/red]",
                    title=f"[dim]#{i} {repo.get('project_name', 'Unknown')}[/dim]",
                    border_style="red",
                )
            )
            continue
        
        # Build a tree for this repository
        tree = Tree(f"[bold cyan]📁 {repo.get('project_name', 'Unknown')}[/bold cyan]")
        
        # ─── REQ #8: Languages & Frameworks ───
        langs = repo.get("languages") or []
        frameworks = repo.get("frameworks") or []
        
        tech_branch = tree.add("[bold magenta]🔧 Technologies[/bold magenta] [dim](REQ #8)[/dim]")
        if langs:
            lang_str = ", ".join(langs[:5])
            if len(langs) > 5:
                lang_str += f" [dim]+{len(langs)-5} more[/dim]"
            tech_branch.add(f"[green]Languages:[/green] {lang_str}")
        else:
            tech_branch.add("[dim]Languages: None detected[/dim]")
        
        if frameworks:
            fw_str = ", ".join(frameworks[:5])
            if len(frameworks) > 5:
                fw_str += f" [dim]+{len(frameworks)-5} more[/dim]"
            tech_branch.add(f"[green]Frameworks:[/green] {fw_str}")
        else:
            tech_branch.add("[dim]Frameworks: None detected[/dim]")
        
        # ─── REQ #9: Individual Contributions ───
        contrib_branch = tree.add("[bold yellow]👤 Your Contributions[/bold yellow] [dim](REQ #9)[/dim]")
        
        pct = repo.get("user_contribution_pct")
        if pct is not None:
            # Color based on contribution level
            if pct >= 70:
                pct_color = "green"
            elif pct >= 30:
                pct_color = "yellow"
            else:
                pct_color = "red"
            contrib_branch.add(f"Contribution: [{pct_color}]{pct:.1f}%[/{pct_color}]")
        
        commits = repo.get("user_total_commits")
        if commits is not None:
            contrib_branch.add(f"Total Commits: [cyan]{commits}[/cyan]")
        
        # ─── REQ #10: Contribution Metrics ───
        metrics_branch = tree.add("[bold blue]📈 Activity Metrics[/bold blue] [dim](REQ #10)[/dim]")
        
        first = repo.get("user_first_commit")
        last = repo.get("user_last_commit")
        freq = repo.get("user_commit_frequency")
        
        if first:
            first_str = format_timestamp(first)
            metrics_branch.add(f"First Commit: [cyan]{first_str}[/cyan]")
        
        if last:
            last_str = format_timestamp(last)
            metrics_branch.add(f"Last Commit: [cyan]{last_str}[/cyan]")
        
        if freq is not None:
            metrics_branch.add(f"Commit Frequency: [cyan]{freq:.2f}/week[/cyan]")
        
        # Calculate duration if we have both dates
        if first and last:
            try:
                from datetime import datetime
                first_dt = datetime.fromisoformat(str(first).replace("Z", "+00:00"))
                last_dt = datetime.fromisoformat(str(last).replace("Z", "+00:00"))
                days = (last_dt - first_dt).days
                metrics_branch.add(f"Duration: [cyan]{days} days[/cyan]")
            except:
                pass
        
        # ─── REQ #11: Extract Skills ───
        skills_branch = tree.add("[bold green]🎯 Skills & Insights[/bold green] [dim](REQ #11)[/dim]")
        skills_branch.add(f"Skills Extracted: [cyan]{repo.get('skills_count', 0)}[/cyan]")
        skills_branch.add(f"Resume Insights: [cyan]{repo.get('insights_count', 0)}[/cyan]")
        
        console.print(Panel(tree, border_style="cyan", padding=(0, 1)))
        console.print()
    
    # ═══════════════════════════════════════════════════════════════════
    # REQ #12: Output All Project Info - Summary Table
    # ═══════════════════════════════════════════════════════════════════
    if repos:
        console.print(
            Panel(
                "[bold]All key project information has been extracted and returned "
                "in the API response above.[/bold]\n\n"
                "Each repository shows: languages, frameworks, skills, "
                "user contributions, commit metrics, and activity timeline.",
                title="[dim]📋 REQ #12: Output Project Info[/dim]",
                border_style="dim",
            )
        )
        console.print()
    
    # ═══════════════════════════════════════════════════════════════════
    # REQ #13: Store in Database - Confirmation
    # ═══════════════════════════════════════════════════════════════════
    total_skills = sum(r.get("skills_count", 0) for r in repos if not r.get("error"))
    total_insights = sum(r.get("insights_count", 0) for r in repos if not r.get("error"))
    successful_repos = sum(1 for r in repos if not r.get("error"))
    
    console.print(
        Panel(
            f"[bold green]✅ Data Persisted to Database[/bold green]\n\n"
            f"• [cyan]{successful_repos}[/cyan] repository records saved to [white]RepoStat[/white] table\n"
            f"• [cyan]{successful_repos}[/cyan] user contribution records saved to [white]UserRepoStat[/white] table\n"
            f"• [cyan]{total_skills}[/cyan] skills saved to [white]ProjectSkill[/white] table\n"
            f"• [cyan]{total_insights}[/cyan] resume items saved to [white]ResumeItem[/white] table\n"
            f"• [cyan]{len(rankings)}[/cyan] ranking scores updated",
            title="[dim]💾 REQ #13: Store in Database[/dim]",
            border_style="green",
        )
    )
    
    print_how_banner([8, 9, 10, 11, 12, 13])
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

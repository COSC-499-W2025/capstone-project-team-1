"""
CLI for resume generation.

Two pipelines available:
  - generate (v2): Static-First, LLM-Light (original)
  - generate-v3: EXTRACT → QUERY → ASSEMBLE (new, richer data)

Usage:
    python -m artifactminer.resume generate-v3 --zip /path/to/repos.zip --email user@example.com
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from .models import UserFeedback

app = typer.Typer(add_completion=False, no_args_is_help=True)


# ---------------------------------------------------------------------------
# v3 pipeline (new default)
# ---------------------------------------------------------------------------


@app.command("generate")
def generate_v3(
    zip_path: Path = typer.Option(
        ...,
        "--zip",
        "-z",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to ZIP file containing git repositories",
    ),
    email: str = typer.Option(
        ...,
        "--email",
        "-e",
        help="User's email for git attribution",
    ),
    model: str = typer.Option(
        "qwen2.5-coder-3b-q4",
        "--model",
        "-m",
        help="Local GGUF model to use (default: qwen2.5-coder-3b-q4)",
    ),
    output_json: Optional[Path] = typer.Option(
        None,
        "--output-json",
        help="Output JSON file path",
    ),
    output_markdown: Optional[Path] = typer.Option(
        None,
        "--output-markdown",
        "--output-md",
        help="Output Markdown file path",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed progress",
    ),
) -> None:
    """
    Generate resume content from a ZIP of git repositories (v3 pipeline).

    Uses the EXTRACT → QUERY → ASSEMBLE pipeline with rich data extraction
    and focused LLM calls.

    Examples:
        python -m artifactminer.resume generate --zip ~/repos.zip --email john@example.com
        python -m artifactminer.resume generate --zip ~/repos.zip --email john@example.com --model qwen2.5-coder-3b-q4
    """
    from .pipeline import generate_resume_v3
    from .assembler import assemble_markdown, assemble_json

    def progress(msg: str) -> None:
        if verbose:
            typer.echo(msg)

    try:
        result = generate_resume_v3(
            zip_path=str(zip_path.resolve()),
            user_email=email.lower().strip(),
            llm_model=model,
            progress_callback=progress if verbose else None,
        )

        # Generate outputs
        markdown = assemble_markdown(result)
        json_str = assemble_json(result)

        # Always print markdown to stdout
        typer.echo("\n" + "=" * 60)
        typer.echo(markdown)

        # Save to files if requested
        if output_json:
            output_json.parent.mkdir(parents=True, exist_ok=True)
            output_json.write_text(json_str)
            typer.echo(f"\nJSON output written to: {output_json}")

        if output_markdown:
            output_markdown.parent.mkdir(parents=True, exist_ok=True)
            output_markdown.write_text(markdown)
            typer.echo(f"Markdown output written to: {output_markdown}")

        # Print summary
        portfolio = result.portfolio_data
        typer.echo("\n" + "=" * 60)
        typer.echo("GENERATION SUMMARY (v3)")
        typer.echo("=" * 60)
        if portfolio:
            typer.echo(f"Projects analyzed: {portfolio.total_projects}")
            typer.echo(f"Total commits: {portfolio.total_commits}")
            typer.echo(f"Skills detected: {len(portfolio.top_skills)}")
            typer.echo(f"Project types: {portfolio.project_types}")
        typer.echo(f"Model used: {result.model_used}")
        typer.echo(f"Generation time: {result.generation_time_seconds:.1f}s")

        if result.errors:
            typer.echo(f"\nWarnings ({len(result.errors)}):", err=True)
            for err in result.errors:
                typer.secho(f"  - {err}", fg=typer.colors.YELLOW, err=True)

    except Exception as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED, err=True)
        if verbose:
            import traceback

            traceback.print_exc()
        raise typer.Exit(1) from exc


# ---------------------------------------------------------------------------
# Multi-stage interactive pipeline (Strategy B)
# ---------------------------------------------------------------------------


def _display_extracted_facts(
    bundles: list,
    portfolio,
    raw_facts: dict,
) -> None:
    """Display Stage 1 extracted facts with Rich formatting."""
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    console = Console()

    # Portfolio overview
    overview = Table(title="Portfolio Overview", show_header=False, box=None)
    overview.add_column("Key", style="bold cyan")
    overview.add_column("Value")
    overview.add_row("Projects", str(portfolio.total_projects))
    overview.add_row("Total Commits", str(portfolio.total_commits))
    overview.add_row("Languages", ", ".join(portfolio.languages_used[:8]))
    if portfolio.frameworks_used:
        overview.add_row("Frameworks", ", ".join(portfolio.frameworks_used[:8]))
    if portfolio.top_skills:
        overview.add_row("Skills", ", ".join(portfolio.top_skills[:10]))
    console.print()
    console.print(
        Panel(
            overview,
            title="[bold]STAGE 1 COMPLETE: Extraction + Distillation[/bold]",
            border_style="green",
        )
    )

    # Per-project facts
    for bundle in bundles:
        facts = raw_facts.get(bundle.project_name)
        lines: list[str] = []

        # Metadata line
        meta = []
        meta.append(f"[cyan]Type:[/cyan] {bundle.project_type}")
        if bundle.primary_language:
            meta.append(f"[cyan]Language:[/cyan] {bundle.primary_language}")
        if bundle.user_contribution_pct is not None:
            meta.append(
                f"[cyan]Contribution:[/cyan] {bundle.user_contribution_pct:.0f}%"
            )
        if bundle.git_stats and bundle.git_stats.lines_added:
            meta.append(f"[cyan]Lines added:[/cyan] {bundle.git_stats.lines_added:,}")
        lines.append(" | ".join(meta))

        # Distilled context stats
        if bundle.distilled_context:
            lines.append(
                f"[dim]Distilled to ~{bundle.distilled_context.token_estimate} tokens[/dim]"
            )

        # Extracted facts from LLM
        if facts:
            lines.append("")
            if facts.summary:
                lines.append(f"[bold]Summary:[/bold] {facts.summary}")
            if facts.facts:
                lines.append("[bold]Key Facts:[/bold]")
                for f in facts.facts:
                    lines.append(f"  [green]-[/green] {f}")
            if facts.role:
                lines.append(f"[bold]Role:[/bold] {facts.role}")
        else:
            lines.append("[yellow]No facts extracted (LLM may have failed)[/yellow]")

        console.print(
            Panel(
                "\n".join(lines),
                title=f"[bold white]{bundle.project_name}[/bold white]",
                border_style="blue",
            )
        )


def _display_draft(draft_output) -> None:
    """Display Stage 2 draft resume with Rich formatting."""
    from rich.console import Console
    from rich.panel import Panel
    from rich.markdown import Markdown

    console = Console()
    console.print()
    console.print(
        Panel(
            "[bold green]STAGE 2 COMPLETE: First Draft[/bold green]",
            border_style="green",
        )
    )

    if draft_output.professional_summary:
        console.print(
            Panel(
                draft_output.professional_summary,
                title="[bold]Professional Summary[/bold]",
                border_style="cyan",
            )
        )

    if draft_output.skills_section:
        console.print(
            Panel(
                draft_output.skills_section,
                title="[bold]Technical Skills[/bold]",
                border_style="cyan",
            )
        )

    for name, section in draft_output.project_sections.items():
        lines: list[str] = []
        if section.description:
            lines.append(section.description)
        if section.bullets:
            lines.append("")
            for b in section.bullets:
                lines.append(f"  [green]-[/green] {b}")
        if section.narrative:
            lines.append(f"\n[dim]{section.narrative}[/dim]")
        console.print(
            Panel(
                "\n".join(lines) if lines else "[yellow]No content generated[/yellow]",
                title=f"[bold white]{name}[/bold white]",
                border_style="blue",
            )
        )

    if draft_output.developer_profile:
        console.print(
            Panel(
                draft_output.developer_profile,
                title="[bold]Developer Profile[/bold]",
                border_style="cyan",
            )
        )


def _collect_feedback() -> UserFeedback | None:
    """Interactively collect user feedback on the draft."""
    from rich.console import Console
    from rich.panel import Panel

    console = Console()
    console.print()
    console.print(
        Panel(
            "[bold]Review the draft above and provide your feedback.[/bold]\n\n"
            "You can:\n"
            "  [cyan]1.[/cyan] Provide general notes (e.g., 'emphasize backend work')\n"
            "  [cyan]2.[/cyan] Set a tone preference (e.g., 'more technical', 'formal', 'concise')\n"
            "  [cyan]3.[/cyan] List things to add (e.g., 'I also deployed to production')\n"
            "  [cyan]4.[/cyan] List things to remove (e.g., 'Remove the claim about ML pipeline')\n"
            "  [cyan]5.[/cyan] Press Enter with no input to skip polish and use the draft as-is",
            title="[bold yellow]YOUR FEEDBACK[/bold yellow]",
            border_style="yellow",
        )
    )

    general = typer.prompt(
        "\nGeneral feedback / instructions (or press Enter to skip)",
        default="",
        show_default=False,
    )

    if not general.strip():
        return None

    tone = typer.prompt(
        "Tone preference (e.g., 'more technical', 'formal', 'concise') (or Enter to skip)",
        default="",
        show_default=False,
    )

    additions: list[str] = []
    console.print("\n[cyan]Things to add[/cyan] (one per line, empty line to finish):")
    while True:
        line = typer.prompt("  +", default="", show_default=False)
        if not line.strip():
            break
        additions.append(line.strip())

    removals: list[str] = []
    console.print("[cyan]Things to remove[/cyan] (one per line, empty line to finish):")
    while True:
        line = typer.prompt("  -", default="", show_default=False)
        if not line.strip():
            break
        removals.append(line.strip())

    return UserFeedback(
        general_notes=general.strip(),
        tone=tone.strip(),
        additions=additions,
        removals=removals,
    )


@app.command("generate-multistage")
def generate_multistage(
    zip_path: Path = typer.Option(
        ...,
        "--zip",
        "-z",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to ZIP file containing git repositories",
    ),
    email: str = typer.Option(
        ...,
        "--email",
        "-e",
        help="User's email for git attribution",
    ),
    stage1_model: str = typer.Option(
        "lfm2-2.6b-q8",
        "--stage1-model",
        help="Model for fact extraction (Stage 1)",
    ),
    stage2_model: str = typer.Option(
        "qwen3-1.7b-q8",
        "--stage2-model",
        help="Model for draft generation (Stage 2)",
    ),
    stage3_model: str = typer.Option(
        "qwen3-1.7b-q8",
        "--stage3-model",
        help="Model for polish/refinement (Stage 3)",
    ),
    output_dir: Optional[Path] = typer.Option(
        None,
        "--output-dir",
        "-o",
        help="Directory to save all outputs (facts, draft, final). Defaults to ./resume_output/",
    ),
) -> None:
    """
    Interactive multi-stage resume generation.

    Runs 3 stages with pauses between each so you can review output
    and provide feedback before the final polish.

    Stage 1: EXTRACT + DISTILL + fact extraction (LFM2-2.6B)
    Stage 2: First draft generation (Qwen3-1.7B) — you review this
    Stage 3: Polish with your feedback (Qwen3-1.7B by default)

    Example:
        uv run python -m artifactminer.resume generate-multistage \\
            --zip ~/repos.zip --email john@example.com
    """
    import json
    from datetime import datetime
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn

    from .pipeline import extract_and_distill
    from .queries.runner import (
        run_extraction_query,
        run_draft_queries,
        run_polish_query,
    )
    from .assembler import assemble_markdown, assemble_json
    from .models import (
        RawProjectFacts,
        ResumeOutput,
        UserFeedback,
    )
    from .llm_client import ensure_model_available

    console = Console()
    start_time = datetime.now()
    errors: list[str] = []
    models_used: list[str] = []

    # Setup output directory
    out_dir = output_dir or Path("resume_output")
    out_dir.mkdir(parents=True, exist_ok=True)

    def prog(msg: str) -> None:
        console.print(f"  [dim]{msg}[/dim]")

    try:
        # ── CHECK MODELS ──────────────────────────────────────────────
        console.print(
            Panel(
                f"[bold]Multi-Stage Resume Pipeline[/bold]\n\n"
                f"  Stage 1 model: [cyan]{stage1_model}[/cyan] (fact extraction)\n"
                f"  Stage 2 model: [cyan]{stage2_model}[/cyan] (draft generation)\n"
                f"  Stage 3 model: [cyan]{stage3_model}[/cyan] (polish with feedback)\n\n"
                f"  ZIP: {zip_path}\n"
                f"  Email: {email}",
                border_style="blue",
            )
        )

        for model_name in [stage1_model, stage2_model, stage3_model]:
            ensure_model_available(model_name)

        # ── PHASE 1: EXTRACT + DISTILL ─────────────────────────────────
        console.print()
        console.rule("[bold cyan]Phase 1: Extract + Distill[/bold cyan]")

        bundles, portfolio, extract_errors = extract_and_distill(
            zip_path=str(zip_path.resolve()),
            user_email=email.lower().strip(),
            llm_model=stage1_model,
            progress_callback=prog,
        )
        errors.extend(extract_errors)

        # ── STAGE 1: LLM FACT EXTRACTION ──────────────────────────────
        console.print()
        console.rule(
            f"[bold cyan]Stage 1: Fact Extraction ({stage1_model})[/bold cyan]"
        )
        models_used.append(stage1_model)

        raw_facts: dict[str, RawProjectFacts] = {}
        for bundle in bundles:
            try:
                facts = run_extraction_query(bundle, stage1_model, progress=prog)
                raw_facts[bundle.project_name] = facts
                prog(f"  Extracted {bundle.project_name}: {len(facts.facts)} facts")
            except Exception as e:
                prog(f"  Extraction failed for {bundle.project_name}: {e}")
                errors.append(f"Stage 1 failed for {bundle.project_name}: {e}")

        if not raw_facts:
            console.print("[bold red]Stage 1 produced no results. Aborting.[/bold red]")
            raise typer.Exit(1)

        # Display Stage 1 results
        _display_extracted_facts(bundles, portfolio, raw_facts)

        # Save Stage 1 output
        stage1_data = {
            name: {"summary": f.summary, "facts": f.facts, "role": f.role}
            for name, f in raw_facts.items()
        }
        (out_dir / "stage1_facts.json").write_text(
            json.dumps(stage1_data, indent=2, default=str)
        )
        console.print(
            f"\n[dim]Stage 1 facts saved to {out_dir}/stage1_facts.json[/dim]"
        )

        # ── STAGE 2: DRAFT GENERATION ─────────────────────────────────
        console.print()
        console.rule(
            f"[bold cyan]Stage 2: Draft Generation ({stage2_model})[/bold cyan]"
        )
        models_used.append(stage2_model)

        try:
            draft_output = run_draft_queries(
                raw_facts,
                portfolio,
                stage2_model,
                progress=prog,
            )
        except Exception as e:
            console.print(f"[bold red]Stage 2 failed: {e}[/bold red]")
            errors.append(f"Stage 2 failed: {e}")
            draft_output = ResumeOutput(
                stage="draft",
                portfolio_data=portfolio,
                raw_project_facts=raw_facts,
            )

        draft_output.portfolio_data = portfolio
        draft_output.raw_project_facts = raw_facts

        # Display the draft
        _display_draft(draft_output)

        # Save draft
        draft_output_for_save = ResumeOutput(
            professional_summary=draft_output.professional_summary,
            skills_section=draft_output.skills_section,
            developer_profile=draft_output.developer_profile,
            project_sections=dict(draft_output.project_sections),
            portfolio_data=portfolio,
            model_used=stage2_model,
            stage="draft",
        )
        draft_md = assemble_markdown(draft_output_for_save)
        (out_dir / "stage2_draft.md").write_text(draft_md)
        console.print(f"\n[dim]Draft saved to {out_dir}/stage2_draft.md[/dim]")

        # ── INTERACTIVE FEEDBACK ──────────────────────────────────────
        user_feedback = _collect_feedback()

        if user_feedback is None:
            console.print(
                "\n[yellow]No feedback provided — using draft as final output.[/yellow]"
            )
            final_output = draft_output
            final_output.stage = "draft-final"
        else:
            # ── STAGE 3: POLISH ───────────────────────────────────────
            console.print()
            console.rule(f"[bold cyan]Stage 3: Polish ({stage3_model})[/bold cyan]")
            models_used.append(stage3_model)

            console.print(
                f"[dim]Applying feedback: {user_feedback.general_notes}[/dim]"
            )
            if user_feedback.tone:
                console.print(f"[dim]Tone: {user_feedback.tone}[/dim]")

            try:
                final_output = run_polish_query(
                    draft_output,
                    user_feedback,
                    stage3_model,
                    progress=prog,
                )
            except Exception as e:
                console.print(f"[bold red]Stage 3 failed, using draft: {e}[/bold red]")
                errors.append(f"Stage 3 failed: {e}")
                final_output = draft_output
                final_output.stage = "polish-fallback"

        # ── FINAL OUTPUT ───────────────────────────────────────────────
        elapsed = (datetime.now() - start_time).total_seconds()
        final_output.generation_time_seconds = elapsed
        final_output.model_used = stage2_model
        final_output.models_used = models_used
        final_output.portfolio_data = portfolio
        final_output.errors = errors

        # Display final
        console.print()
        console.rule("[bold green]FINAL RESUME[/bold green]")

        final_md = assemble_markdown(final_output)
        final_json = assemble_json(final_output)

        # Print the final markdown
        from rich.markdown import Markdown

        console.print(Markdown(final_md))

        # Save outputs
        (out_dir / "final_resume.md").write_text(final_md)
        (out_dir / "final_resume.json").write_text(final_json)

        console.print()
        console.print(
            Panel(
                f"[bold green]Generation complete![/bold green]\n\n"
                f"  Time: {elapsed:.1f}s\n"
                f"  Models: {' -> '.join(models_used)}\n"
                f"  Stage: {final_output.stage}\n"
                f"  Projects: {portfolio.total_projects}\n\n"
                f"  Output files:\n"
                f"    [cyan]{out_dir}/stage1_facts.json[/cyan]\n"
                f"    [cyan]{out_dir}/stage2_draft.md[/cyan]\n"
                f"    [cyan]{out_dir}/final_resume.md[/cyan]\n"
                f"    [cyan]{out_dir}/final_resume.json[/cyan]",
                title="[bold]Summary[/bold]",
                border_style="green",
            )
        )

        if errors:
            console.print(f"\n[yellow]Warnings ({len(errors)}):[/yellow]")
            for err in errors:
                console.print(f"  [yellow]- {err}[/yellow]")

    except typer.Exit:
        raise
    except Exception as exc:
        console.print(f"\n[bold red]Error: {exc}[/bold red]")
        import traceback

        traceback.print_exc()
        raise typer.Exit(1) from exc


# ---------------------------------------------------------------------------
# v2 pipeline (kept for rollback)
# ---------------------------------------------------------------------------


@app.command("generate-v2")
def generate_v2(
    zip_path: Path = typer.Option(
        ...,
        "--zip",
        "-z",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to ZIP file containing git repositories",
    ),
    email: str = typer.Option(
        ...,
        "--email",
        "-e",
        help="User's email for git attribution",
    ),
    model: str = typer.Option(
        "qwen3-1.7b-q8",
        "--model",
        "-m",
        help="Local GGUF model to use",
    ),
    output_json: Optional[Path] = typer.Option(
        None,
        "--output-json",
        help="Output JSON file path",
    ),
    output_markdown: Optional[Path] = typer.Option(
        None,
        "--output-markdown",
        "--output-md",
        help="Output Markdown file path",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed progress",
    ),
) -> None:
    """
    Generate resume content using the v2 pipeline (legacy).

    Kept for comparison and rollback purposes.
    """
    from .generate import generate_resume

    def progress(msg: str) -> None:
        if verbose:
            typer.echo(msg)

    try:
        result = generate_resume(
            zip_path=str(zip_path.resolve()),
            user_email=email.lower().strip(),
            llm_model=model,
            progress_callback=progress if verbose else None,
        )

        markdown = result.to_markdown()
        typer.echo("\n" + "=" * 60)
        typer.echo(markdown)

        if output_json:
            output_json.parent.mkdir(parents=True, exist_ok=True)
            output_json.write_text(result.to_json())
            typer.echo(f"\nJSON output written to: {output_json}")

        if output_markdown:
            output_markdown.parent.mkdir(parents=True, exist_ok=True)
            output_markdown.write_text(markdown)
            typer.echo(f"Markdown output written to: {output_markdown}")

        typer.echo("\n" + "=" * 60)
        typer.echo("GENERATION SUMMARY (v2)")
        typer.echo("=" * 60)
        typer.echo(f"Projects analyzed: {result.portfolio_facts.total_projects}")
        typer.echo(f"Total commits: {result.portfolio_facts.total_commits}")
        typer.echo(f"Generation time: {result.generation_time_seconds:.1f}s")

    except Exception as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED, err=True)
        if verbose:
            import traceback

            traceback.print_exc()
        raise typer.Exit(1) from exc


@app.command()
def check_models() -> None:
    """List locally available GGUF models and known model sources."""
    from .llm_client import get_available_models, MODEL_REGISTRY, MODELS_DIR

    models = get_available_models()
    if models:
        typer.secho("Installed models:", fg=typer.colors.GREEN)
        for m in models:
            typer.echo(f"  - {m}")
    else:
        typer.secho("No models installed locally.", fg=typer.colors.YELLOW)

    typer.echo(f"\nModel directory: {MODELS_DIR}")
    typer.echo(f"\nKnown models (manual download) ({len(MODEL_REGISTRY)}):")
    for name, (repo_id, filename, _) in MODEL_REGISTRY.items():
        status = "installed" if name in models else "not installed"
        typer.echo(f"  - {name} ({status}) — https://huggingface.co/{repo_id}")


@app.command()
def benchmark(
    models: Optional[list[str]] = typer.Option(
        None,
        "--models",
        "-m",
        help="Models to benchmark (default: all registered models)",
    ),
    runs: int = typer.Option(
        3,
        "--runs",
        "-r",
        help="Number of runs per prompt (1 cold + N-1 warm)",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Save markdown report to file",
    ),
) -> None:
    """Run a side-by-side model benchmark comparing speed, memory, and output quality."""
    from .benchmark import run_benchmark

    report = run_benchmark(
        models=models,
        runs=runs,
        output_path=str(output) if output else None,
    )
    typer.echo("\n" + report)


@app.command("evaluate-multistage")
def evaluate_multistage(
    zip_path: Path = typer.Option(
        ...,
        "--zip",
        "-z",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to ZIP file containing git repositories",
    ),
    email: str = typer.Option(
        ...,
        "--email",
        "-e",
        help="User's email for git attribution",
    ),
    runs: int = typer.Option(
        1,
        "--runs",
        "-r",
        min=1,
        help="Number of end-to-end evaluation runs",
    ),
    stage1_model: str = typer.Option(
        "lfm2-2.6b-q8",
        "--stage1-model",
        help="Model for fact extraction (Stage 1)",
    ),
    stage2_model: str = typer.Option(
        "qwen3-1.7b-q8",
        "--stage2-model",
        help="Model for draft generation (Stage 2)",
    ),
    stage3_model: str = typer.Option(
        "qwen3-1.7b-q8",
        "--stage3-model",
        help="Model for polish generation (Stage 3)",
    ),
    output_dir: Path = typer.Option(
        Path("resume_output/eval"),
        "--output-dir",
        "-o",
        help="Directory to save evaluation reports",
    ),
) -> None:
    """Run a metrics harness for the multi-stage local-LLM pipeline."""
    from .eval_harness import evaluate_multistage_pipeline

    def progress(msg: str) -> None:
        typer.echo(msg)

    try:
        result = evaluate_multistage_pipeline(
            zip_path=str(zip_path.resolve()),
            user_email=email.lower().strip(),
            runs=runs,
            stage1_model=stage1_model,
            stage2_model=stage2_model,
            stage3_model=stage3_model,
            output_dir=str(output_dir),
            progress_callback=progress,
        )
    except Exception as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from exc

    aggregate = result.get("aggregate", {})
    report_paths = result.get("report_paths", {})
    typer.echo("\n" + "=" * 60)
    typer.echo("EVALUATION SUMMARY")
    typer.echo("=" * 60)
    typer.echo(f"Runs: {aggregate.get('runs', 0)}")
    typer.echo(
        f"Avg generation time: {aggregate.get('avg_generation_time_seconds', 0.0):.2f}s"
    )
    typer.echo(
        f"Avg citation precision: {aggregate.get('avg_citation_precision', 0.0):.4f}"
    )
    typer.echo(f"Avg fact coverage: {aggregate.get('avg_fact_coverage', 0.0):.4f}")
    typer.echo(
        f"Avg repaired bullets: {aggregate.get('avg_repaired_bullets', 0.0):.2f}"
    )

    if report_paths:
        typer.echo("\nReports:")
        typer.echo(f"  JSON: {report_paths.get('json')}")
        typer.echo(f"  Markdown: {report_paths.get('markdown')}")


def main() -> None:
    app()

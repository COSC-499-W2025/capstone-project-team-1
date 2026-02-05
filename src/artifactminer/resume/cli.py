"""
CLI for resume generation - New architecture (Static-First, LLM-Light).

Usage:
    python -m artifactminer.resume generate --zip /path/to/repos.zip --email user@example.com
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

app = typer.Typer(add_completion=False, no_args_is_help=True)


@app.command()
def generate(
    zip_path: Path = typer.Option(
        ..., "--zip", "-z", exists=True, file_okay=True, dir_okay=False, readable=True,
        help="Path to ZIP file containing git repositories",
    ),
    email: str = typer.Option(
        ..., "--email", "-e",
        help="User's email for git attribution",
    ),
    no_llm: bool = typer.Option(
        False, "--no-llm",
        help="Disable LLM enhancement, use templates only",
    ),
    model: Optional[str] = typer.Option(
        None, "--model", "-m",
        help="Specific Ollama model to use (default: auto-select)",
    ),
    output_json: Optional[Path] = typer.Option(
        None, "--output-json",
        help="Output JSON file path",
    ),
    output_markdown: Optional[Path] = typer.Option(
        None, "--output-markdown", "--output-md",
        help="Output Markdown file path",
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v",
        help="Show detailed progress",
    ),
) -> None:
    """
    Generate resume content from a ZIP of git repositories.

    This uses the new Static-First architecture:
    - Static analysis does all the heavy lifting (skills, insights, metrics)
    - LLM (optional) just polishes the prose

    Examples:
        # Basic usage
        python -m artifactminer.resume generate --zip ~/repos.zip --email john@example.com

        # Without LLM (works on any machine)
        python -m artifactminer.resume generate --zip ~/repos.zip --email john@example.com --no-llm

        # With specific model
        python -m artifactminer.resume generate --zip ~/repos.zip --email john@example.com --model llama3:8b
    """
    from .generate import generate_resume

    def progress(msg: str) -> None:
        if verbose:
            typer.echo(msg)

    try:
        result = generate_resume(
            zip_path=str(zip_path.resolve()),
            user_email=email.lower().strip(),
            use_llm=not no_llm,
            llm_model=model,
            progress_callback=progress if verbose else None,
        )

        # Generate markdown output
        markdown = result.to_markdown()

        # Always print to stdout
        typer.echo("\n" + "=" * 60)
        typer.echo(markdown)

        # Save to files if requested
        if output_json:
            output_json.parent.mkdir(parents=True, exist_ok=True)
            output_json.write_text(result.to_json())
            typer.echo(f"\nJSON output written to: {output_json}")

        if output_markdown:
            output_markdown.parent.mkdir(parents=True, exist_ok=True)
            output_markdown.write_text(markdown)
            typer.echo(f"Markdown output written to: {output_markdown}")

        # Print summary
        typer.echo("\n" + "=" * 60)
        typer.echo("GENERATION SUMMARY")
        typer.echo("=" * 60)
        typer.echo(f"Projects analyzed: {result.portfolio_facts.total_projects}")
        typer.echo(f"Total commits: {result.portfolio_facts.total_commits}")
        typer.echo(f"Skills detected: {len(result.portfolio_facts.top_skills)}")
        typer.echo(f"LLM enhanced: {result.resume_content.llm_enhanced}")
        if result.resume_content.model_used:
            typer.echo(f"Model used: {result.resume_content.model_used}")
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


@app.command()
def check_ollama() -> None:
    """Check if Ollama is available and list installed models."""
    from .enhance import check_ollama_available, get_available_models

    if check_ollama_available():
        typer.secho("✓ Ollama is running", fg=typer.colors.GREEN)
        models = get_available_models()
        if models:
            typer.echo(f"\nAvailable models ({len(models)}):")
            for model in models:
                typer.echo(f"  - {model}")
        else:
            typer.secho("No models installed. Run: ollama pull qwen3:1.7b", fg=typer.colors.YELLOW)
    else:
        typer.secho("✗ Ollama is not running or not installed", fg=typer.colors.RED)
        typer.echo("\nTo install Ollama: https://ollama.ai")
        typer.echo("To start Ollama: ollama serve")


def main() -> None:
    app()

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
    model: str = typer.Option(
        "qwen3-1.7b", "--model", "-m",
        help="Local GGUF model to use (e.g., qwen3-1.7b, lfm2.5-1.2b)",
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

    Uses a local GGUF model via llama.cpp for LLM-enhanced prose generation.

    Examples:
        # Basic usage (uses qwen3-1.7b)
        python -m artifactminer.resume generate --zip ~/repos.zip --email john@example.com

        # With specific model
        python -m artifactminer.resume generate --zip ~/repos.zip --email john@example.com --model lfm2.5-1.2b
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
def check_models() -> None:
    """List locally available GGUF models and known downloadable models."""
    from .llm_client import get_available_models, MODEL_REGISTRY, MODELS_DIR

    models = get_available_models()
    if models:
        typer.secho("Installed models:", fg=typer.colors.GREEN)
        for m in models:
            typer.echo(f"  - {m}")
    else:
        typer.secho("No models installed locally.", fg=typer.colors.YELLOW)

    typer.echo(f"\nModel directory: {MODELS_DIR}")
    typer.echo(f"\nDownloadable models ({len(MODEL_REGISTRY)}):")
    for name, (repo_id, filename, _) in MODEL_REGISTRY.items():
        status = "installed" if name in models else "not installed"
        typer.echo(f"  - {name} ({status}) — {repo_id}")


@app.command()
def download_model(
    model: str = typer.Argument("qwen3-1.7b", help="Model name to download"),
) -> None:
    """Download a GGUF model from HuggingFace for local inference."""
    from .llm_client import ensure_model_available, check_llm_available

    if check_llm_available(model):
        typer.secho(f"Model '{model}' is already installed.", fg=typer.colors.GREEN)
        return

    typer.echo(f"Downloading model '{model}'...")
    try:
        ensure_model_available(model)
        typer.secho(f"Model '{model}' downloaded successfully.", fg=typer.colors.GREEN)
    except RuntimeError as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from exc


@app.command()
def benchmark(
    models: Optional[list[str]] = typer.Option(
        None, "--models", "-m",
        help="Models to benchmark (default: all registered models)",
    ),
    runs: int = typer.Option(
        3, "--runs", "-r",
        help="Number of runs per prompt (1 cold + N-1 warm)",
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o",
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


def main() -> None:
    app()

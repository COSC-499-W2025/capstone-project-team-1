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

app = typer.Typer(add_completion=False, no_args_is_help=True)


# ---------------------------------------------------------------------------
# v3 pipeline (new default)
# ---------------------------------------------------------------------------


@app.command("generate")
def generate_v3(
    zip_path: Path = typer.Option(
        ..., "--zip", "-z", exists=True, file_okay=True, dir_okay=False, readable=True,
        help="Path to ZIP file containing git repositories",
    ),
    email: str = typer.Option(
        ..., "--email", "-e",
        help="User's email for git attribution",
    ),
    model: str = typer.Option(
        "qwen2.5-coder-3b-q4", "--model", "-m",
        help="Local GGUF model to use (default: qwen2.5-coder-3b-q4)",
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
# v2 pipeline (kept for rollback)
# ---------------------------------------------------------------------------


@app.command("generate-v2")
def generate_v2(
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
        help="Local GGUF model to use",
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

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from artifactminer.resume.pipeline import generate_resume
from artifactminer.resume.schemas import ResumeArtifacts

app = typer.Typer(add_completion=False, no_args_is_help=True)


def _render_markdown(result: ResumeArtifacts) -> str:
    lines: list[str] = []
    lines.append("# Resume Artifacts")
    lines.append("")

    for project in result.projects:
        lines.append(f"## {project.project_name}")
        lines.append(project.one_liner)
        lines.append("")
        for bullet in project.bullet_points:
            lines.append(f"- {bullet}")
        if project.technologies:
            lines.append("")
            lines.append(f"Technologies: {', '.join(project.technologies)}")
        if project.impact_metrics:
            lines.append(f"Impact: {', '.join(project.impact_metrics)}")
        lines.append("")

    lines.append("## Portfolio Summary")
    lines.append(result.portfolio_summary.strip())
    lines.append("")
    lines.append(
        f"Generated with {result.model_used} in {result.generation_time_seconds:.2f}s"
    )

    return "\n".join(lines).strip() + "\n"


@app.command()
def generate(
    zip_path: Path = typer.Option(
        ..., "--zip", "-z", exists=True, file_okay=True, dir_okay=False, readable=True
    ),
    email: str = typer.Option(..., "--email", "-e"),
    top_files: int = typer.Option(15, "--top-files"),
    output_json: Optional[Path] = typer.Option(None, "--output-json"),
    output_markdown: Optional[Path] = typer.Option(None, "--output-markdown"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Generate resume artifacts from a ZIP of git repositories."""
    try:
        result = generate_resume(
            zip_path=zip_path,
            user_email=email,
            top_files=top_files,
            verbose=verbose,
        )
    except Exception as exc:  # noqa: BLE001
        typer.secho(f"Error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from exc

    markdown = _render_markdown(result)
    print(markdown)

    if output_json:
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(result.model_dump_json(indent=2))

    if output_markdown:
        output_markdown.parent.mkdir(parents=True, exist_ok=True)
        output_markdown.write_text(markdown)

from collections.abc import Callable

from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    MofNCompleteColumn,
)


def create_repo_progress(
    expected_total: int | None,
) -> tuple[Progress, Callable[[int, int, str], None]]:
    """Create a Rich progress bar and a callback to update it.

    Callback signature: (completed_count, total_count, repo_name).
    """
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TextColumn("{task.fields[repo_name]}"),
        transient=False,
        redirect_stdout=True,
        redirect_stderr=True,
        expand=True,
        refresh_per_second=20,
    )

    task_id: int = progress.add_task(
        "Analyzing repositories",
        total=float(expected_total) if expected_total is not None else 1,
        repo_name="Starting...",
    )

    def progress_callback(completed: int, total: int, repo_name: str) -> None:
        total_value = expected_total if expected_total is not None else total
        progress.update(
            task_id,
            total=total_value,
            completed=completed,
            repo_name=repo_name,
            refresh=True,
        )

    return progress, progress_callback

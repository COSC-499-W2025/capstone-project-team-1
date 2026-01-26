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
    )

    task_id: int | None = None

    def progress_callback(completed: int, total: int, repo_name: str) -> None:
        nonlocal task_id
        total_value = expected_total if expected_total is not None else total
        if task_id is None:
            task_id = progress.add_task(
                "Analyzing repositories",
                total=total_value,
                repo_name="Starting...",
            )
        progress.update(task_id, total=total_value, completed=completed, repo_name=repo_name)

    return progress, progress_callback


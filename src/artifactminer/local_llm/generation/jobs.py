"""Small job helpers for the local-generation happy path."""

from __future__ import annotations

import time
from typing import Any


def make_telemetry(selected_repos: list[str]) -> dict[str, Any]:
    return {
        "stage": "ANALYZE",
        "active_model": None,
        "repos_total": len(selected_repos),
        "repos_done": 0,
        "current_repo": None,
        "facts_total": 0,
        "draft_projects": 0,
        "polished_projects": 0,
        "elapsed_seconds": 0.0,
        "model_check_seconds": 0.0,
        "selected_repos": list(selected_repos),
    }


def make_job(
    *,
    job_id: str,
    intake_id: str,
    repo_ids: list[str],
    repo_names: list[str],
    user_email: str,
    stage1_model: str,
    stage2_model: str,
    stage3_model: str,
) -> dict[str, Any]:
    now = time.monotonic()
    return {
        "job_id": job_id,
        "status": "queued",
        "stage": "ANALYZE",
        "intake_id": intake_id,
        "repo_ids": list(repo_ids),
        "repo_names": list(repo_names),
        "user_email": user_email,
        "stage1_model": stage1_model,
        "stage2_model": stage2_model,
        "stage3_model": stage3_model,
        "messages": [],
        "telemetry": make_telemetry(repo_names),
        "draft": None,
        "output": None,
        "error": None,
        "generation_task": None,
        "cancel_requested": False,
        "feedback": None,
        "project_facts": [],
        "started_at_monotonic": now,
    }


def _touch_elapsed(job: dict[str, Any]) -> None:
    started = job.get("started_at_monotonic")
    if started is None:
        return
    telemetry = job.setdefault("telemetry", make_telemetry(job.get("repo_names", [])))
    telemetry["elapsed_seconds"] = max(0.0, time.monotonic() - float(started))


def append_message(job: dict[str, Any], message: str) -> None:
    if not message.strip():
        return
    job.setdefault("messages", []).append(message)
    _touch_elapsed(job)


def update_job(
    job: dict[str, Any],
    *,
    status: str | None = None,
    stage: str | None = None,
    active_model: str | None = None,
    current_repo: str | None = None,
    repos_done: int | None = None,
    facts_total: int | None = None,
    draft_projects: int | None = None,
    polished_projects: int | None = None,
    error: str | None = None,
) -> None:
    if status is not None:
        job["status"] = status
    if stage is not None:
        job["stage"] = stage

    telemetry = job.setdefault("telemetry", make_telemetry(job.get("repo_names", [])))
    if stage is not None:
        telemetry["stage"] = stage
    if active_model is not None:
        telemetry["active_model"] = active_model
    if current_repo is not None:
        telemetry["current_repo"] = current_repo
    if repos_done is not None:
        telemetry["repos_done"] = repos_done
    if facts_total is not None:
        telemetry["facts_total"] = facts_total
    if draft_projects is not None:
        telemetry["draft_projects"] = draft_projects
    if polished_projects is not None:
        telemetry["polished_projects"] = polished_projects
    if error is not None:
        job["error"] = error
    _touch_elapsed(job)


def mark_cancelled(job: dict[str, Any], *, message: str) -> None:
    job["cancel_requested"] = True
    job["status"] = "cancelled"
    job["error"] = None
    job["draft"] = None
    job["output"] = None
    job["feedback"] = None
    job["project_facts"] = []
    append_message(job, message)
    _touch_elapsed(job)


def should_stop(job: dict[str, Any]) -> bool:
    return bool(job.get("cancel_requested")) or job.get("status") == "cancelled"

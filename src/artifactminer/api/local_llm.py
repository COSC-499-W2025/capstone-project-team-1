"""Local LLM API endpoints for the OpenTUI resume-generation flow."""

from __future__ import annotations

import asyncio
import contextlib
import inspect
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Any, Callable
from zipfile import ZipFile, is_zipfile

from fastapi import APIRouter, HTTPException, Query

from ..helpers.zip_utils import safe_extract_zip
from ..local_llm.generation.jobs import (
    append_message,
    make_job,
    make_telemetry,
    mark_cancelled,
    should_stop,
    update_job,
)
from ..local_llm.generation.schemas import (
    GenerationFeedback,
    ProjectFacts,
    ResumeOutputModel,
)
from ..local_llm.generation.service import (
    build_draft_output,
    build_polished_output,
    finalize_output,
    generate_project_facts,
)
from ..local_llm.runtime.process_manager import stop_server
from ..local_llm.runtime.registry import list_supported_models
from .local_llm_schemas import (
    CancellationResponse,
    ContributorDiscoveryRequest,
    ContributorDiscoveryResponse,
    ContributorIdentity,
    GenerationStartRequest,
    GenerationStartResponse,
    GenerationStatusResponse,
    GenerationTelemetry,
    IntakeCreateRequest,
    IntakeCreateResponse,
    PolishRequest,
    PolishResponse,
    RepositoryCandidate,
)


router = APIRouter(prefix="/local-llm", tags=["local-llm"])


_active_intakes: dict[str, "IntakeContext"] = {}
_generation_jobs: dict[str, dict[str, Any]] = {}
_active_generation_id: str | None = None
_generation_cancel_hooks: dict[str, Callable[[], Any]] = {}
_JOB_LAUNCH_DELAY_SECONDS = 0.1


class IntakeContext:
    """Represents an active intake session with metadata."""

    def __init__(
        self,
        intake_id: str,
        zip_path: str,
        repos: list[RepositoryCandidate],
        extracted_dir: str,
    ):
        self.intake_id = intake_id
        self.zip_path = zip_path
        self.repos = repos
        self.extracted_dir = extracted_dir
        self.repo_id_to_path: dict[str, Path] = {
            repo.id: Path(extracted_dir) / repo.rel_path for repo in repos
        }


def register_generation_cancellation_hook(
    job_id: str, cancel_hook: Callable[[], Any]
) -> None:
    """Register optional runtime cancellation hook for a generation job."""

    _generation_cancel_hooks[job_id] = cancel_hook


async def _stop_job_runtime(job_id: str, job: dict[str, Any]) -> None:
    """Stop all runtime controls attached to a generation job."""

    generation_task = job.get("generation_task")
    if generation_task is not None and hasattr(generation_task, "cancel"):
        generation_task.cancel()

    stop_server()

    cancel_hook = _generation_cancel_hooks.get(job_id) or job.get("cancel_hook")
    if callable(cancel_hook):
        maybe_awaitable = cancel_hook()
        if inspect.isawaitable(maybe_awaitable):
            await maybe_awaitable

    if generation_task is not None and hasattr(generation_task, "__await__"):
        with contextlib.suppress(asyncio.CancelledError, TimeoutError, Exception):
            await asyncio.wait_for(generation_task, timeout=1.5)


def _is_git_repo(path: Path) -> bool:
    git_dir = path / ".git"
    return git_dir.is_dir() and (git_dir / "HEAD").is_file()


def _is_macos_metadata(path: Path, base_path: Path) -> bool:
    try:
        parts = path.relative_to(base_path).parts
    except ValueError:
        parts = path.parts
    return any(part == "__MACOSX" or part.startswith("._") for part in parts)


def _discover_repos_in_zip(zip_path: str) -> tuple[list[RepositoryCandidate], str]:
    if not Path(zip_path).exists():
        raise ValueError(f"ZIP file not found: {zip_path}")
    if not is_zipfile(zip_path):
        raise ValueError(f"Invalid ZIP file: {zip_path}")

    candidates: list[RepositoryCandidate] = []
    seen_repos: set[str] = set()
    temp_extracted_dir = tempfile.mkdtemp(prefix="zip_extract_")

    try:
        try:
            with ZipFile(zip_path, "r") as zf:
                safe_extract_zip(zf, Path(temp_extracted_dir))
        except Exception as exc:
            shutil.rmtree(temp_extracted_dir)
            raise ValueError(f"Failed to extract ZIP file: {exc}") from exc

        extracted_root = Path(temp_extracted_dir)
        if _is_git_repo(extracted_root) and not _is_macos_metadata(
            extracted_root, extracted_root
        ):
            candidates.append(
                RepositoryCandidate(
                    id=".",
                    name=extracted_root.name,
                    rel_path=".",
                )
            )
            seen_repos.add(".")

        for path in extracted_root.rglob("*"):
            if not path.is_dir() or _is_macos_metadata(path, extracted_root):
                continue
            if not _is_git_repo(path):
                continue

            is_nested = any(
                _is_git_repo(parent)
                for parent in path.parents
                if parent != extracted_root and parent.is_relative_to(extracted_root)
            )
            if is_nested:
                continue

            repo_rel_path = path.relative_to(extracted_root).as_posix()
            if repo_rel_path in seen_repos:
                continue
            seen_repos.add(repo_rel_path)
            candidates.append(
                RepositoryCandidate(
                    id=repo_rel_path,
                    name=path.name,
                    rel_path=repo_rel_path,
                )
            )
    except ValueError:
        raise
    except Exception as exc:
        if Path(temp_extracted_dir).exists():
            shutil.rmtree(temp_extracted_dir)
        raise RuntimeError(f"Failed to discover repositories: {exc}") from exc

    return sorted(candidates, key=lambda repo: repo.name), temp_extracted_dir


def _discover_contributors_in_repos(repo_paths: list[Path]) -> list[ContributorIdentity]:
    contributors_map: dict[str, dict[str, Any]] = {}
    for repo_path in repo_paths:
        if not repo_path.exists() or not _is_git_repo(repo_path):
            raise ValueError(f"Invalid git repository: {repo_path}")

        try:
            result = subprocess.run(
                ["git", "log", "--format=%ae|%an"],
                cwd=str(repo_path),
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                continue
            for line in result.stdout.strip().split("\n"):
                if not line.strip():
                    continue
                parts = line.split("|", 1)
                if len(parts) != 2:
                    continue
                email = parts[0].strip()
                name = parts[1].strip() or None
                if not email:
                    continue

                contributor = contributors_map.setdefault(
                    email,
                    {"name": name, "repos": set(), "commit_count": 0},
                )
                contributor["repos"].add(repo_path.name)
                contributor["commit_count"] += 1
                if name and (not contributor["name"] or len(name) > len(contributor["name"])):
                    contributor["name"] = name
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"Git operation timed out for {repo_path}") from exc
        except Exception as exc:
            raise RuntimeError(
                f"Failed to analyze git repository {repo_path}: {exc}"
            ) from exc

    identities = [
        ContributorIdentity(
            email=email,
            name=data["name"],
            repo_count=len(data["repos"]),
            commit_count=data["commit_count"],
            candidate_username=email.split("@")[0],
        )
        for email, data in contributors_map.items()
    ]
    return sorted(identities, key=lambda item: (-item.commit_count, item.email))


def _resolve_context(intake_id: str | None) -> IntakeContext:
    if intake_id:
        context = _active_intakes.get(intake_id)
        if context is None:
            raise ValueError(f"No active intake context found for intake_id: {intake_id}")
        return context
    if not _active_intakes:
        raise ValueError("No active intake context found")
    return list(_active_intakes.values())[-1]


def _resolve_repo_paths(
    context: IntakeContext, repo_ids: list[str]
) -> tuple[list[str], list[Path]]:
    valid_repo_ids = {repo.id for repo in context.repos}
    invalid_ids = set(repo_ids) - valid_repo_ids
    if invalid_ids:
        raise ValueError(
            f"Invalid repository IDs for active intake: {', '.join(sorted(invalid_ids))}"
        )

    selected_repos = [repo for repo in context.repos if repo.id in repo_ids]
    return [repo.name for repo in selected_repos], [
        context.repo_id_to_path[repo.id] for repo in selected_repos
    ]


def _default_telemetry_for_job(job_data: dict[str, Any]) -> dict[str, Any]:
    telemetry_data = job_data.get("telemetry", {})
    if telemetry_data:
        return telemetry_data
    return make_telemetry(job_data.get("repo_names", job_data.get("repo_ids", [])))


def _validate_requested_models(*models: str) -> None:
    supported = {descriptor.name for descriptor in list_supported_models()}
    for model in models:
        if model not in supported:
            supported_names = ", ".join(sorted(supported))
            raise ValueError(
                f"Model '{model}' is not a supported local model. "
                f"Supported model names: {supported_names}."
            )


async def _cancel_superseded_job() -> None:
    global _active_generation_id

    existing_job_id = _active_generation_id
    if existing_job_id is None:
        return

    existing_job = _generation_jobs.get(existing_job_id)
    if existing_job is None:
        _active_generation_id = None
        return

    if existing_job.get("status") in {"cancelled", "complete", "error"}:
        return

    await _stop_job_runtime(existing_job_id, existing_job)
    mark_cancelled(existing_job, message="Superseded by a new pipeline run.")
    _generation_cancel_hooks.pop(existing_job_id, None)
    _active_generation_id = None


async def _run_generation_job(job_id: str, repo_paths: list[Path]) -> None:
    job = _generation_jobs.get(job_id)
    if job is None:
        return

    facts_total = 0
    project_facts = []
    snapshots: list[dict] = []

    try:
        update_job(job, status="running", stage="ANALYZE", current_repo=None)
        append_message(job, "Starting local repository analysis.")

        for index, repo_path in enumerate(repo_paths, start=1):
            if should_stop(job):
                raise asyncio.CancelledError

            update_job(
                job,
                status="running",
                stage="FACTS",
                active_model=job["stage1_model"],
                current_repo=repo_path.name,
                repos_done=index - 1,
                facts_total=facts_total,
            )
            append_message(job, f"Compiling facts for {repo_path.name}")
            fact, snapshot = await generate_project_facts(
                repo_path,
                user_email=job["user_email"],
                model=job["stage1_model"],
                progress=lambda message: append_message(job, message),
            )
            project_facts.append(fact)
            snapshots.append(snapshot)
            facts_total += len(fact.highlights) + len(fact.evidence)
            update_job(
                job,
                status="running",
                stage="FACTS",
                active_model=job["stage1_model"],
                current_repo=repo_path.name,
                repos_done=index,
                facts_total=facts_total,
            )

        if should_stop(job):
            raise asyncio.CancelledError

        update_job(
            job,
            status="running",
            stage="DRAFT",
            active_model=job["stage2_model"],
            current_repo=None,
            repos_done=len(repo_paths),
            facts_total=facts_total,
        )
        append_message(job, "Writing grounded draft resume.")
        draft_output = await build_draft_output(
            project_facts,
            snapshots=snapshots,
            user_email=job["user_email"],
            model=job["stage2_model"],
            progress=lambda message: append_message(job, message),
        )
        draft_payload = finalize_output(
            draft_output,
            facts=project_facts,
            stage="draft",
            models_used=[job["stage1_model"], job["stage2_model"]],
            generation_time_seconds=float(
                _default_telemetry_for_job(job).get("elapsed_seconds", 0.0)
            ),
            errors=[],
        )
        job["project_facts"] = [fact.model_dump() for fact in project_facts]
        job["draft"] = draft_payload
        update_job(
            job,
            status="draft_ready",
            stage="DRAFT",
            active_model=job["stage2_model"],
            current_repo=None,
            draft_projects=len(draft_payload.get("projects", [])),
            facts_total=facts_total,
        )
        append_message(job, "Draft ready for review.")
    except asyncio.CancelledError:
        if job.get("status") != "cancelled":
            mark_cancelled(job, message="Pipeline cancelled.")
    except Exception as exc:
        error_message = f"{type(exc).__name__}: {exc}"
        update_job(job, status="error", error=error_message)
    finally:
        job["generation_task"] = None
        stop_server()


async def _deferred_run_generation_job(job_id: str, repo_paths: list[Path]) -> None:
    await asyncio.sleep(_JOB_LAUNCH_DELAY_SECONDS)
    await _run_generation_job(job_id, repo_paths)


async def _run_polish_job(job_id: str) -> None:
    job = _generation_jobs.get(job_id)
    if job is None:
        return

    try:
        if should_stop(job):
            raise asyncio.CancelledError

        feedback = GenerationFeedback.model_validate(job.get("feedback") or {})
        draft_output = ResumeOutputModel.model_validate(job.get("draft") or {})
        project_facts_models = [
            ProjectFacts.model_validate(item) for item in job.get("project_facts", [])
        ]

        update_job(
            job,
            status="polishing",
            stage="POLISH",
            active_model=job["stage3_model"],
            current_repo=None,
        )
        append_message(job, "Applying polish feedback.")
        final_output = await build_polished_output(
            draft_output,
            feedback,
            model=job["stage3_model"],
            facts=project_facts_models,
        )
        output_payload = finalize_output(
            final_output,
            facts=project_facts_models,
            stage="polish",
            models_used=[job["stage1_model"], job["stage2_model"], job["stage3_model"]],
            generation_time_seconds=float(
                _default_telemetry_for_job(job).get("elapsed_seconds", 0.0)
            ),
            errors=[],
        )
        job["output"] = output_payload
        update_job(
            job,
            status="complete",
            stage="POLISH",
            active_model=job["stage3_model"],
            current_repo=None,
            polished_projects=len(output_payload.get("projects", [])),
        )
        append_message(job, "Polish complete.")
    except asyncio.CancelledError:
        if job.get("status") != "cancelled":
            mark_cancelled(job, message="Pipeline cancelled.")
    except Exception as exc:
        error_message = f"{type(exc).__name__}: {exc}"
        update_job(job, status="error", error=error_message)
    finally:
        job["generation_task"] = None
        stop_server()


@router.post("/context", response_model=IntakeCreateResponse)
async def create_intake(request: IntakeCreateRequest) -> IntakeCreateResponse:
    temp_extracted_dir = None
    try:
        repos, temp_extracted_dir = _discover_repos_in_zip(request.zip_path)
        if not repos:
            raise ValueError("No git repositories found in ZIP")

        intake_id = str(uuid.uuid4())
        _active_intakes[intake_id] = IntakeContext(
            intake_id=intake_id,
            zip_path=request.zip_path,
            repos=repos,
            extracted_dir=temp_extracted_dir,
        )
        return IntakeCreateResponse(
            intake_id=intake_id,
            zip_path=request.zip_path,
            repos=repos,
        )
    except ValueError as exc:
        if temp_extracted_dir and Path(temp_extracted_dir).exists():
            shutil.rmtree(temp_extracted_dir)
        if "not found" in str(exc).lower():
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        if temp_extracted_dir and Path(temp_extracted_dir).exists():
            shutil.rmtree(temp_extracted_dir)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create intake: {exc}",
        ) from exc


@router.post(
    "/context/contributors", response_model=ContributorDiscoveryResponse
)
async def discover_contributors(
    request: ContributorDiscoveryRequest,
) -> ContributorDiscoveryResponse:
    try:
        context = _resolve_context(None)
        _, repo_paths = _resolve_repo_paths(context, request.repo_ids)
        contributors = _discover_contributors_in_repos(repo_paths)
        return ContributorDiscoveryResponse(contributors=contributors)
    except ValueError as exc:
        error_message = str(exc)
        if "no active intake" in error_message.lower():
            raise HTTPException(status_code=404, detail=error_message) from exc
        raise HTTPException(status_code=422, detail=error_message) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to discover contributors: {exc}",
        ) from exc


@router.post("/generation/start", response_model=GenerationStartResponse)
async def start_generation(
    request: GenerationStartRequest,
) -> GenerationStartResponse:
    global _active_generation_id

    try:
        context = _resolve_context(request.intake_id)
        repo_names, repo_paths = _resolve_repo_paths(context, request.repo_ids)
        _validate_requested_models(
            request.stage1_model,
            request.stage2_model,
            request.stage3_model,
        )
        await _cancel_superseded_job()

        job_id = str(uuid.uuid4())
        job = make_job(
            job_id=job_id,
            intake_id=context.intake_id,
            repo_ids=list(request.repo_ids),
            repo_names=repo_names,
            user_email=str(request.user_email),
            stage1_model=request.stage1_model,
            stage2_model=request.stage2_model,
            stage3_model=request.stage3_model,
        )
        _generation_jobs[job_id] = job
        _active_generation_id = job_id

        task = asyncio.create_task(_deferred_run_generation_job(job_id, repo_paths))
        job["generation_task"] = task
        return GenerationStartResponse(job_id=job_id, status="queued")
    except ValueError as exc:
        error_message = str(exc)
        if "no active intake" in error_message.lower():
            raise HTTPException(status_code=404, detail=error_message) from exc
        raise HTTPException(status_code=422, detail=error_message) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start generation: {exc}",
        ) from exc


@router.post("/generation/cancel", response_model=CancellationResponse)
async def cancel_generation(
    job_id: str | None = Query(
        default=None,
        description="Job ID to cancel. Defaults to the current active job.",
    )
) -> CancellationResponse:
    global _active_generation_id

    target_id = job_id if job_id is not None else _active_generation_id
    if target_id is None:
        raise HTTPException(status_code=404, detail="No active generation job found")

    target_job = _generation_jobs.get(target_id)
    if target_job is None:
        if target_id == _active_generation_id:
            _active_generation_id = None
        raise HTTPException(
            status_code=404,
            detail=f"No generation job found with ID: {target_id}",
        )

    if target_job.get("status") == "cancelled":
        if target_id == _active_generation_id:
            _active_generation_id = None
        return CancellationResponse(ok=True, status="cancelled")

    try:
        await _stop_job_runtime(target_id, target_job)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cancel generation runtime: {exc}",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cancel generation runtime: {exc}",
        ) from exc

    mark_cancelled(target_job, message="Pipeline cancelled by user.")
    if target_id == _active_generation_id:
        _active_generation_id = None
    _generation_cancel_hooks.pop(target_id, None)
    return CancellationResponse(ok=True, status="cancelled")


@router.get("/generation/status", response_model=GenerationStatusResponse)
async def get_generation_status(
    job_id: str | None = None,
) -> GenerationStatusResponse:
    global _active_generation_id

    try:
        target_job_id = job_id if job_id else _active_generation_id
        if not target_job_id or target_job_id not in _generation_jobs:
            raise ValueError(
                "No generation job found"
                + (f" with ID: {target_job_id}" if target_job_id else "")
            )

        job_data = _generation_jobs[target_job_id]
        telemetry = GenerationTelemetry(**_default_telemetry_for_job(job_data))
        return GenerationStatusResponse(
            status=job_data.get("status", "queued"),
            stage=job_data.get("stage", "ANALYZE"),
            messages=job_data.get("messages", []),
            telemetry=telemetry,
            draft=job_data.get("draft"),
            output=job_data.get("output"),
            error=job_data.get("error"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve generation status: {exc}",
        ) from exc


@router.post("/generation/polish", response_model=PolishResponse)
async def polish_generation(request: PolishRequest) -> PolishResponse:
    global _active_generation_id

    try:
        job_id = _active_generation_id
        if not job_id or job_id not in _generation_jobs:
            raise ValueError("No active generation found. Start generation first.")

        job = _generation_jobs[job_id]
        if job["status"] not in {"draft_ready", "complete"}:
            raise ValueError(
                f"Pipeline must be in draft_ready or complete state to polish, "
                f"but is currently in '{job['status']}' state"
            )

        normalized_notes = str(request.general_notes or "").strip()
        normalized_tone = str(request.tone or "").strip()
        normalized_additions = [
            str(item).strip() for item in request.additions if str(item).strip()
        ]
        normalized_removals = [
            str(item).strip() for item in request.removals if str(item).strip()
        ]

        if not (
            normalized_notes
            or normalized_tone
            or normalized_additions
            or normalized_removals
        ):
            raise ValueError(
                "No feedback provided. Add General Notes, Tone, Additions, "
                "or Removals before starting polish."
            )

        feedback = GenerationFeedback(
            general_notes=normalized_notes,
            tone=normalized_tone,
            additions=normalized_additions,
            removals=normalized_removals,
        )
        job["feedback"] = feedback.model_dump()
        update_job(
            job,
            status="polishing",
            stage="POLISH",
            active_model=job["stage3_model"],
            current_repo=None,
        )
        append_message(job, "Polish requested.")
        task = asyncio.create_task(_run_polish_job(job_id))
        job["generation_task"] = task
        return PolishResponse(ok=True, status="polishing")
    except ValueError as exc:
        error_message = str(exc)
        if "no active generation" in error_message.lower():
            raise HTTPException(status_code=404, detail=error_message) from exc
        if "pipeline must be in" in error_message.lower():
            raise HTTPException(status_code=409, detail=error_message) from exc
        if "no feedback provided" in error_message.lower():
            raise HTTPException(status_code=422, detail=error_message) from exc
        raise HTTPException(status_code=422, detail=error_message) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process polish request: {exc}",
        ) from exc

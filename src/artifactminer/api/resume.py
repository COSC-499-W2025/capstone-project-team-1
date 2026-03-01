"""Resume generation endpoints and local ephemeral pipeline API."""

from __future__ import annotations

import json
import multiprocessing
import queue
import shutil
import subprocess
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, cast

import git
from email_validator import EmailNotValidError, validate_email
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db, ProjectEvidence, RepoStat, ResumeItem
from .schemas import (
    PipelineCancelResponse,
    PipelineContributorIdentity,
    PipelineContributorsRequest,
    PipelineContributorsResponse,
    PipelineIntakeCreateRequest,
    PipelineIntakeCreateResponse,
    PipelineJobStatus,
    PipelinePolishRequest,
    PipelinePolishResponse,
    PipelineRepoCandidate,
    PipelineStage,
    PipelineStartRequest,
    PipelineStartResponse,
    PipelineStatusResponse,
    PipelineTelemetry,
    ResumeGenerationRequest,
    ResumeGenerationResponse,
)
from .analyze import get_consent_level, get_user_email
from ..evidence.orchestrator import persist_insights_as_project_evidence
from ..RepositoryIntelligence.repo_intelligence_user import collect_user_additions
from ..resume.assembler import assemble_json
from ..resume.llm_client import ensure_model_available, unload_model
from ..resume.models import ResumeOutput, UserFeedback
from ..resume.pipeline import extract_and_distill_for_repos
from ..resume.queries.runner import (
    compile_project_data_card,
    run_draft_queries,
    run_polish_query,
)
from ..resume.generate import discover_git_repos, extract_zip
from ..skills.deep_analysis import DeepRepoAnalyzer
from ..skills.persistence import persist_extracted_skills

router = APIRouter(
    prefix="/resume",
    tags=["resume"],
)

local_llm_router = APIRouter(
    prefix="/local-llm",
    tags=["local-llm"],
)


JobPhase = Literal["phase1", "phase3", "none"]
_TERMINATE_TIMEOUT_SECONDS = 1.0
_RESOURCE_GUARD_MAX_RAM_MB = 6144.0


@dataclass
class RepoCandidate:
    """A discovered repository in an intake."""

    id: str
    name: str
    rel_path: str
    abs_path: str


@dataclass
class IntakeState:
    """Ephemeral intake metadata and discovered repositories."""

    intake_id: str
    zip_path: str
    extract_dir: str
    repos: list[RepoCandidate]
    created_at: datetime
    updated_at: datetime


@dataclass
class JobState:
    """Ephemeral pipeline job state held in-memory only."""

    job_id: str
    intake_id: str
    status: PipelineJobStatus
    phase: JobPhase = "none"
    process: multiprocessing.Process | None = None
    event_queue: multiprocessing.Queue | None = None
    messages: list[str] = field(default_factory=list)
    stage: PipelineStage = "ANALYZE"
    telemetry: dict[str, Any] = field(default_factory=dict)
    draft_output: ResumeOutput | None = None
    draft_json: dict[str, Any] | None = None
    final_json: dict[str, Any] | None = None
    last_error: str | None = None
    selected_repo_ids: list[str] = field(default_factory=list)
    selected_repo_names: list[str] = field(default_factory=list)
    selected_repo_paths: list[str] = field(default_factory=list)
    user_email: str = ""
    stage1_model: str = "qwen2.5-coder-3b-q4"
    stage2_model: str = "lfm2.5-1.2b-bf16"
    stage3_model: str = "lfm2.5-1.2b-bf16"
    created_at: datetime = field(
        default_factory=lambda: datetime.now(UTC).replace(tzinfo=None)
    )
    updated_at: datetime = field(
        default_factory=lambda: datetime.now(UTC).replace(tzinfo=None)
    )


# Ephemeral in-memory stores
_intakes: dict[str, IntakeState] = {}
_jobs: dict[str, JobState] = {}
_active_intake_id: str | None = None
_active_job_id: str | None = None
_lock = threading.Lock()


def _now_utc_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _safe_queue_put(
    event_queue: multiprocessing.Queue, payload: dict[str, Any]
) -> None:
    """Best-effort queue push from worker processes."""
    try:
        event_queue.put(payload)
    except Exception:
        pass


def _serialize_resume_output(output: ResumeOutput) -> dict[str, Any]:
    """Serialize ResumeOutput into the frontend contract as a dict."""
    serialized = assemble_json(output)
    try:
        payload = json.loads(serialized)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Failed to serialize resume output: {exc}") from exc

    if not isinstance(payload, dict):
        raise RuntimeError("Resume serialization returned a non-object payload")
    return payload


def _new_telemetry(
    selected_repo_names: list[str],
    *,
    stage: PipelineStage,
    active_model: str | None,
) -> dict[str, Any]:
    return {
        "stage": stage,
        "active_model": active_model,
        "repos_total": len(selected_repo_names),
        "repos_done": 0,
        "current_repo": None,
        "facts_total": 0,
        "draft_projects": 0,
        "polished_projects": 0,
        "elapsed_seconds": 0.0,
        "model_check_seconds": 0.0,
        "selected_repos": list(selected_repo_names),
    }


def _append_message(job: JobState, message: str) -> None:
    if message.strip():
        job.messages.append(message)
    job.updated_at = _now_utc_naive()


def _release_process_handle(job: JobState) -> None:
    process = job.process
    if process is None:
        return
    try:
        process.join(timeout=0.05)
    except Exception:
        pass
    job.process = None


def _clear_job_runtime_payloads(job: JobState) -> None:
    """Drop heavyweight in-memory payloads for hard stop paths."""
    job.draft_output = None
    job.draft_json = None
    job.final_json = None

    event_queue = job.event_queue
    if event_queue is not None:
        while True:
            try:
                event_queue.get_nowait()
            except queue.Empty:
                break
            except Exception:
                break
    job.event_queue = None


def _stop_local_model_server() -> None:
    """Best-effort llama-server teardown used by cancel and safety guard paths."""
    try:
        unload_model()
    except Exception:
        pass


def _get_process_rss_mb(process: multiprocessing.Process) -> float | None:
    """Read RSS memory for a process in megabytes using `ps`."""
    pid = getattr(process, "pid", None)
    if not isinstance(pid, int) or pid <= 0:
        return None

    try:
        proc = subprocess.run(
            ["ps", "-o", "rss=", "-p", str(pid)],
            capture_output=True,
            text=True,
            check=False,
            timeout=0.2,
        )
    except Exception:
        return None

    if proc.returncode != 0:
        return None

    output = proc.stdout.strip()
    if not output:
        return None

    try:
        rss_kb = int(output.splitlines()[-1].strip().split()[0])
    except (ValueError, IndexError):
        return None

    return rss_kb / 1024.0


def _enforce_resource_guard(job: JobState, process: multiprocessing.Process) -> bool:
    """Kill runaway local generation when process RAM exceeds safety threshold."""
    if job.status not in {"queued", "running", "polishing"}:
        return False

    rss_mb = _get_process_rss_mb(process)
    if rss_mb is None or rss_mb <= _RESOURCE_GUARD_MAX_RAM_MB:
        return False

    try:
        _terminate_process_now(process)
    except Exception:
        pass

    _stop_local_model_server()
    _release_process_handle(job)
    _clear_job_runtime_payloads(job)

    job.phase = "none"
    job.status = "failed_resource_guard"
    job.last_error = (
        f"Resource guard triggered: process RAM {rss_mb:.1f} MB exceeded "
        f"{_RESOURCE_GUARD_MAX_RAM_MB:.0f} MB limit."
    )
    _append_message(job, job.last_error)
    return True


def _drain_events_once(job: JobState) -> None:
    if job.event_queue is None:
        return

    while True:
        try:
            event = job.event_queue.get_nowait()
        except queue.Empty:
            break
        except Exception:
            break

        event_type = event.get("type")

        if event_type == "message":
            message = str(event.get("message", "")).strip()
            if message:
                _append_message(job, message)

        elif event_type == "telemetry":
            telemetry = event.get("telemetry")
            if isinstance(telemetry, dict):
                job.telemetry.update(telemetry)
                stage = telemetry.get("stage")
                if isinstance(stage, str):
                    job.stage = stage  # type: ignore[assignment]

        elif event_type == "draft_ready":
            draft_output = event.get("draft_output")
            draft_json = event.get("draft_json")
            if isinstance(draft_output, ResumeOutput):
                job.draft_output = draft_output
            if isinstance(draft_json, dict):
                job.draft_json = draft_json

            telemetry = event.get("telemetry")
            if isinstance(telemetry, dict):
                job.telemetry.update(telemetry)

            job.status = "draft_ready"
            job.phase = "none"
            job.stage = "DRAFT"
            _append_message(job, "Draft complete. Ready for feedback.")

        elif event_type == "complete":
            output_json = event.get("output_json")
            if isinstance(output_json, dict):
                job.final_json = output_json

            telemetry = event.get("telemetry")
            if isinstance(telemetry, dict):
                job.telemetry.update(telemetry)

            job.status = "complete"
            job.phase = "none"
            job.stage = "POLISH"
            _append_message(job, "Polish complete. Final resume is ready.")

        elif event_type == "error":
            error_message = str(event.get("error", "Pipeline failed"))
            job.status = "error"
            job.phase = "none"
            job.last_error = error_message
            _append_message(job, error_message)


def _drain_job_events(job: JobState) -> None:
    _drain_events_once(job)

    process = job.process
    if process is None:
        return

    if process.is_alive():
        if _enforce_resource_guard(job, process):
            return
        return

    # Final queue drain after process exits.
    _drain_events_once(job)

    if job.status in {"running", "polishing", "queued"}:
        exit_code = process.exitcode
        if exit_code not in (0, None):
            job.status = "error"
            job.phase = "none"
            job.last_error = f"Worker exited unexpectedly with code {exit_code}."
            _append_message(job, job.last_error)

    if job.phase == "none" or job.status in {
        "draft_ready",
        "complete",
        "error",
        "cancelled",
        "failed_resource_guard",
    }:
        _release_process_handle(job)


def _terminate_process_now(process: multiprocessing.Process) -> None:
    if not process.is_alive():
        return

    process.terminate()
    process.join(timeout=_TERMINATE_TIMEOUT_SECONDS)

    if process.is_alive():
        process.kill()
        process.join(timeout=0.25)


def _coerce_telemetry(job: JobState) -> PipelineTelemetry:
    defaults = _new_telemetry(
        job.selected_repo_names,
        stage=job.stage,
        active_model=job.telemetry.get("active_model") if job.telemetry else None,
    )
    defaults.update(job.telemetry)
    defaults["selected_repos"] = list(job.selected_repo_names)

    try:
        return PipelineTelemetry(**defaults)
    except Exception:
        # Fallback to resilient minimal payload if telemetry shape gets corrupted.
        return PipelineTelemetry(selected_repos=list(job.selected_repo_names))


def _validate_zip_path(raw_zip_path: str) -> Path:
    zip_path = Path(raw_zip_path).expanduser()
    if not zip_path.exists():
        raise HTTPException(status_code=404, detail="ZIP path does not exist")
    if not zip_path.is_file():
        raise HTTPException(status_code=400, detail="ZIP path must point to a file")
    if not zip_path.suffix.lower().endswith("zip"):
        raise HTTPException(
            status_code=400, detail="Provided file must be a .zip archive"
        )
    return zip_path.resolve()


def _normalize_email_or_422(email: str) -> str:
    try:
        validated = validate_email(email, check_deliverability=False)
    except EmailNotValidError as exc:
        raise HTTPException(status_code=422, detail="Invalid user email") from exc
    return validated.normalized.lower()


def _resolve_selected_repos(
    intake: IntakeState,
    repo_ids: list[str],
) -> list[RepoCandidate]:
    repo_map = {repo.id: repo for repo in intake.repos}

    ordered_ids: list[str] = []
    seen_ids: set[str] = set()
    for repo_id in repo_ids:
        if repo_id in seen_ids:
            continue
        seen_ids.add(repo_id)
        ordered_ids.append(repo_id)

    missing = [repo_id for repo_id in ordered_ids if repo_id not in repo_map]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown repo_ids for intake {intake.intake_id}: {missing}",
        )

    return [repo_map[repo_id] for repo_id in ordered_ids]


def _collect_contributors(repo_paths: list[str]) -> list[PipelineContributorIdentity]:
    aggregates: dict[str, dict[str, Any]] = {}

    for repo_path in repo_paths:
        repo = git.Repo(repo_path)
        seen_in_repo: set[str] = set()

        for commit in repo.iter_commits():
            author = getattr(commit, "author", None)
            email = (getattr(author, "email", "") or "").strip().lower()
            if not email:
                continue

            name = (getattr(author, "name", "") or "").strip() or None
            if email not in aggregates:
                aggregates[email] = {
                    "name": name,
                    "repo_count": 0,
                    "commit_count": 0,
                }

            entry = aggregates[email]
            entry["commit_count"] += 1

            if email not in seen_in_repo:
                entry["repo_count"] += 1
                seen_in_repo.add(email)

            if not entry["name"] and name:
                entry["name"] = name

    contributors: list[PipelineContributorIdentity] = []
    for email, stats in aggregates.items():
        contributors.append(
            PipelineContributorIdentity(
                email=email,
                name=stats["name"],
                repo_count=int(stats["repo_count"]),
                commit_count=int(stats["commit_count"]),
                candidate_username=email.split("@", 1)[0],
            )
        )

    contributors.sort(
        key=lambda item: (-item.commit_count, -item.repo_count, item.email)
    )
    return contributors


def _phase1_worker(
    repo_paths: list[str],
    selected_repo_names: list[str],
    user_email: str,
    stage1_model: str,
    stage2_model: str,
    event_queue: multiprocessing.Queue,
) -> None:
    started = time.monotonic()
    telemetry = _new_telemetry(
        selected_repo_names,
        stage="ANALYZE",
        active_model=stage1_model,
    )

    def push_telemetry() -> None:
        telemetry["elapsed_seconds"] = round(time.monotonic() - started, 2)
        _safe_queue_put(
            event_queue, {"type": "telemetry", "telemetry": dict(telemetry)}
        )

    def emit(message: str) -> None:
        _safe_queue_put(event_queue, {"type": "message", "message": message})

    try:
        model_check_started = time.monotonic()
        emit(f"Checking model '{stage1_model}'...")
        ensure_model_available(stage1_model)
        emit(f"Checking model '{stage2_model}'...")
        ensure_model_available(stage2_model)
        telemetry["model_check_seconds"] = round(
            time.monotonic() - model_check_started,
            2,
        )
        push_telemetry()

        def repo_progress(done: int, total: int, current_repo: str) -> None:
            telemetry["repos_total"] = total
            telemetry["repos_done"] = done
            telemetry["current_repo"] = current_repo
            push_telemetry()

        emit("Pipeline started: ANALYZE → FACTS → DRAFT")
        telemetry["stage"] = "ANALYZE"
        telemetry["active_model"] = stage1_model
        push_telemetry()

        bundles, portfolio, extract_errors = extract_and_distill_for_repos(
            [Path(repo_path) for repo_path in repo_paths],
            user_email,
            llm_model=stage1_model,
            progress_callback=emit,
            repo_progress_callback=repo_progress,
        )

        for extraction_error in extract_errors:
            emit(f"ANALYZE warning: {extraction_error}")

        telemetry["stage"] = "FACTS"
        telemetry["active_model"] = stage1_model
        telemetry["facts_total"] = 0
        push_telemetry()

        raw_facts = {}
        stage_errors: list[str] = list(extract_errors)
        for bundle in bundles:
            try:
                telemetry["current_repo"] = bundle.project_name
                push_telemetry()
                facts = compile_project_data_card(bundle, progress=emit)
                raw_facts[bundle.project_name] = facts
                telemetry["facts_total"] += len(facts.facts)
                emit(f"Compiled {bundle.project_name}: {len(facts.facts)} facts")
                push_telemetry()
            except Exception as exc:
                error_msg = f"FACTS failed for {bundle.project_name}: {exc}"
                stage_errors.append(error_msg)
                emit(error_msg)

        if not raw_facts:
            raise RuntimeError("FACTS stage produced no results")

        telemetry["stage"] = "DRAFT"
        telemetry["active_model"] = stage2_model
        telemetry["current_repo"] = None
        push_telemetry()
        emit(f"DRAFT: generating with {stage2_model}...")

        try:
            draft_output = run_draft_queries(
                raw_facts,
                portfolio,
                stage2_model,
                progress=emit,
            )
        except Exception as exc:
            stage_errors.append(f"DRAFT failed: {exc}")
            emit(f"DRAFT failed: {exc}")
            draft_output = ResumeOutput(
                stage="draft",
                portfolio_data=portfolio,
                raw_project_facts=raw_facts,
            )

        draft_output.stage = "draft"
        draft_output.portfolio_data = portfolio
        draft_output.raw_project_facts = raw_facts
        draft_output.model_used = stage2_model
        draft_output.models_used = [stage2_model]
        draft_output.generation_time_seconds = round(time.monotonic() - started, 2)

        merged_errors = list(dict.fromkeys([*draft_output.errors, *stage_errors]))
        draft_output.errors = merged_errors

        telemetry["draft_projects"] = len(draft_output.project_sections)
        push_telemetry()

        draft_json = _serialize_resume_output(draft_output)
        _safe_queue_put(
            event_queue,
            {
                "type": "draft_ready",
                "draft_output": draft_output,
                "draft_json": draft_json,
                "telemetry": dict(telemetry),
            },
        )

    except Exception as exc:
        _safe_queue_put(
            event_queue,
            {
                "type": "error",
                "error": f"Phase 1 pipeline failed: {type(exc).__name__}: {exc}",
            },
        )


def _phase3_worker(
    draft_output: ResumeOutput,
    selected_repo_names: list[str],
    stage3_model: str,
    feedback_payload: dict[str, Any],
    event_queue: multiprocessing.Queue,
) -> None:
    started = time.monotonic()
    telemetry = _new_telemetry(
        selected_repo_names,
        stage="POLISH",
        active_model=stage3_model,
    )
    telemetry["repos_done"] = telemetry["repos_total"]

    def push_telemetry() -> None:
        telemetry["elapsed_seconds"] = round(time.monotonic() - started, 2)
        _safe_queue_put(
            event_queue, {"type": "telemetry", "telemetry": dict(telemetry)}
        )

    def emit(message: str) -> None:
        _safe_queue_put(event_queue, {"type": "message", "message": message})

    try:
        model_check_started = time.monotonic()
        emit(f"Checking model '{stage3_model}'...")
        ensure_model_available(stage3_model)
        telemetry["model_check_seconds"] = round(
            time.monotonic() - model_check_started,
            2,
        )
        push_telemetry()

        feedback = UserFeedback(
            general_notes=str(feedback_payload.get("general_notes") or "").strip(),
            tone=str(feedback_payload.get("tone") or "").strip(),
            additions=[
                str(item).strip()
                for item in (feedback_payload.get("additions") or [])
                if str(item).strip()
            ],
            removals=[
                str(item).strip()
                for item in (feedback_payload.get("removals") or [])
                if str(item).strip()
            ],
        )

        emit("POLISH started: refining draft from saved output")
        push_telemetry()

        final_output = run_polish_query(
            draft_output,
            feedback,
            stage3_model,
            progress=emit,
        )

        final_output.stage = "polish"
        final_output.portfolio_data = draft_output.portfolio_data
        final_output.raw_project_facts = draft_output.raw_project_facts
        final_output.model_used = stage3_model
        final_output.models_used = [stage3_model]
        final_output.generation_time_seconds = round(time.monotonic() - started, 2)

        telemetry["polished_projects"] = len(final_output.project_sections)
        telemetry["stage"] = "POLISH"
        push_telemetry()

        output_json = _serialize_resume_output(final_output)
        _safe_queue_put(
            event_queue,
            {
                "type": "complete",
                "output_json": output_json,
                "telemetry": dict(telemetry),
            },
        )

    except Exception as exc:
        _safe_queue_put(
            event_queue,
            {
                "type": "error",
                "error": f"Stage 3 polish failed: {type(exc).__name__}: {exc}",
            },
        )


@local_llm_router.post("/context", response_model=PipelineIntakeCreateResponse)
async def create_pipeline_intake(
    request: PipelineIntakeCreateRequest,
) -> PipelineIntakeCreateResponse:
    """Create an intake from a local ZIP path and discover candidate repos."""
    zip_path = _validate_zip_path(request.zip_path)

    extraction_parent = Path(tempfile.mkdtemp(prefix="artifactminer-intake-"))

    try:
        extracted_dir = extract_zip(str(zip_path), extract_to=str(extraction_parent))
        discovered = discover_git_repos(extracted_dir)
    except HTTPException:
        shutil.rmtree(extraction_parent, ignore_errors=True)
        raise
    except Exception as exc:
        shutil.rmtree(extraction_parent, ignore_errors=True)
        raise HTTPException(
            status_code=400,
            detail=f"Failed to read ZIP: {type(exc).__name__}: {exc}",
        ) from exc

    if not discovered:
        shutil.rmtree(extraction_parent, ignore_errors=True)
        raise HTTPException(status_code=400, detail="No git repositories found in ZIP")

    extract_root = extracted_dir.resolve()
    sorted_repos = sorted(
        [repo.resolve() for repo in discovered],
        key=lambda repo_path: str(repo_path.relative_to(extract_root)).lower(),
    )

    repo_candidates: list[RepoCandidate] = []
    for idx, repo_path in enumerate(sorted_repos, start=1):
        repo_candidates.append(
            RepoCandidate(
                id=f"r{idx}",
                name=repo_path.name,
                rel_path=str(repo_path.relative_to(extract_root)),
                abs_path=str(repo_path),
            )
        )

    intake_id = str(uuid.uuid4())
    now = _now_utc_naive()
    intake_state = IntakeState(
        intake_id=intake_id,
        zip_path=str(zip_path),
        extract_dir=str(extract_root),
        repos=repo_candidates,
        created_at=now,
        updated_at=now,
    )

    global _active_intake_id, _active_job_id
    with _lock:
        _intakes[intake_id] = intake_state
        _active_intake_id = intake_id
        _active_job_id = None

    return PipelineIntakeCreateResponse(
        intake_id=intake_id,
        zip_path=str(zip_path),
        repos=[
            PipelineRepoCandidate(id=repo.id, name=repo.name, rel_path=repo.rel_path)
            for repo in repo_candidates
        ],
    )


@local_llm_router.post(
    "/context/contributors",
    response_model=PipelineContributorsResponse,
)
async def list_pipeline_contributors(
    request: PipelineContributorsRequest,
) -> PipelineContributorsResponse:
    """Return contributor identities from selected repositories only."""
    with _lock:
        intake = _intakes.get(_active_intake_id or "")
        if intake is None:
            raise HTTPException(
                status_code=404,
                detail="No active context found. Create context first.",
            )
        selected_repos = _resolve_selected_repos(intake, request.repo_ids)

    try:
        contributors = _collect_contributors([repo.abs_path for repo in selected_repos])
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to collect contributors: {type(exc).__name__}: {exc}",
        ) from exc

    return PipelineContributorsResponse(contributors=contributors)


@local_llm_router.post("/generation/start", response_model=PipelineStartResponse)
async def start_resume_pipeline(request: PipelineStartRequest) -> PipelineStartResponse:
    """Start phase 1 pipeline for selected repos and identity."""
    user_email = _normalize_email_or_422(request.user_email)

    global _active_job_id
    with _lock:
        intake_id = request.intake_id or _active_intake_id
        intake = _intakes.get(intake_id or "")
        if intake is None:
            raise HTTPException(
                status_code=404,
                detail="No active context found. Create context first.",
            )

        selected_repos = _resolve_selected_repos(intake, request.repo_ids)

        job_id = str(uuid.uuid4())
        now = _now_utc_naive()
        selected_repo_names = [repo.name for repo in selected_repos]
        selected_repo_paths = [repo.abs_path for repo in selected_repos]
        event_queue: multiprocessing.Queue = multiprocessing.Queue()

        job_state = JobState(
            job_id=job_id,
            intake_id=intake.intake_id,
            status="running",
            phase="phase1",
            event_queue=event_queue,
            messages=["Pipeline request accepted. Waiting for worker updates."],
            stage="ANALYZE",
            telemetry=_new_telemetry(
                selected_repo_names,
                stage="ANALYZE",
                active_model=request.stage1_model,
            ),
            selected_repo_ids=[repo.id for repo in selected_repos],
            selected_repo_names=selected_repo_names,
            selected_repo_paths=selected_repo_paths,
            user_email=user_email,
            stage1_model=request.stage1_model,
            stage2_model=request.stage2_model,
            stage3_model=request.stage3_model,
            created_at=now,
            updated_at=now,
        )
        _jobs[job_id] = job_state
        _active_job_id = job_id

    process = multiprocessing.Process(
        target=_phase1_worker,
        args=(
            selected_repo_paths,
            selected_repo_names,
            user_email,
            request.stage1_model,
            request.stage2_model,
            event_queue,
        ),
        daemon=True,
    )

    try:
        process.start()
    except Exception as exc:
        with _lock:
            _jobs.pop(job_id, None)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start pipeline process: {type(exc).__name__}: {exc}",
        ) from exc

    with _lock:
        job = _jobs.get(job_id)
        if job is not None:
            job.process = process
            _append_message(job, "Phase 1 worker started.")

    return PipelineStartResponse(job_id=job_id, status="running")


@local_llm_router.get("/generation/status", response_model=PipelineStatusResponse)
async def get_resume_pipeline_status() -> PipelineStatusResponse:
    """Poll current status for a pipeline job."""
    with _lock:
        job = _jobs.get(_active_job_id or "")
        if job is None:
            raise HTTPException(
                status_code=404,
                detail="No active generation found. Start generation first.",
            )

        _drain_job_events(job)
        telemetry = _coerce_telemetry(job)

        return PipelineStatusResponse(
            status=job.status,
            stage=job.stage,
            messages=list(job.messages),
            telemetry=telemetry,
            draft=job.draft_json,
            output=job.final_json,
            error=job.last_error,
        )


@local_llm_router.post("/generation/polish", response_model=PipelinePolishResponse)
async def polish_resume_pipeline(
    request: PipelinePolishRequest,
) -> PipelinePolishResponse:
    """Run Stage 3 polish from the saved Stage 2 draft."""
    with _lock:
        job = _jobs.get(_active_job_id or "")
        if job is None:
            raise HTTPException(
                status_code=404,
                detail="No active generation found. Start generation first.",
            )

        _drain_job_events(job)

        if job.status not in {"draft_ready", "complete"}:
            raise HTTPException(
                status_code=409,
                detail="Pipeline must be in draft_ready or complete state to polish",
            )

        if job.draft_output is None:
            raise HTTPException(
                status_code=409,
                detail="No Stage 2 draft available for polishing",
            )

        if job.process is not None and job.process.is_alive():
            raise HTTPException(
                status_code=409,
                detail="A pipeline worker is already running for this job",
            )

        if job.event_queue is None:
            job.event_queue = multiprocessing.Queue()

        job.status = "polishing"
        job.phase = "phase3"
        job.stage = "POLISH"
        job.last_error = None
        job.final_json = None
        job.telemetry.update(
            {
                "stage": "POLISH",
                "active_model": job.stage3_model,
                "polished_projects": 0,
            }
        )
        _append_message(job, "Polish requested.")

        feedback_payload = request.model_dump()
        process = multiprocessing.Process(
            target=_phase3_worker,
            args=(
                job.draft_output,
                list(job.selected_repo_names),
                job.stage3_model,
                feedback_payload,
                job.event_queue,
            ),
            daemon=True,
        )

    try:
        process.start()
    except Exception as exc:
        with _lock:
            current_job = _jobs.get(_active_job_id or "")
            if current_job is not None:
                current_job.status = "error"
                current_job.phase = "none"
                current_job.last_error = (
                    f"Failed to start Stage 3 process: {type(exc).__name__}: {exc}"
                )
                _append_message(current_job, current_job.last_error)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start Stage 3 process: {type(exc).__name__}: {exc}",
        ) from exc

    with _lock:
        current_job = _jobs.get(_active_job_id or "")
        if current_job is not None:
            current_job.process = process
            current_job.updated_at = _now_utc_naive()

    return PipelinePolishResponse(ok=True, status="polishing")


@local_llm_router.post("/generation/cancel", response_model=PipelineCancelResponse)
async def cancel_resume_pipeline() -> PipelineCancelResponse:
    """Cancel a running or paused pipeline immediately."""
    process: multiprocessing.Process | None = None

    with _lock:
        job = _jobs.get(_active_job_id or "")
        if job is None:
            raise HTTPException(
                status_code=404,
                detail="No active generation found. Start generation first.",
            )

        _drain_job_events(job)

        if job.status == "cancelled":
            return PipelineCancelResponse(ok=True, status="cancelled")

        if job.status == "complete" and (
            job.process is None or not job.process.is_alive()
        ):
            return PipelineCancelResponse(ok=True, status="complete")

        process = job.process

    if process is not None and process.is_alive():
        try:
            _terminate_process_now(process)
        except Exception:
            pass

    _stop_local_model_server()

    with _lock:
        job = _jobs.get(_active_job_id or "")
        if job is None:
            return PipelineCancelResponse(ok=True, status="cancelled")

        _release_process_handle(job)
        _clear_job_runtime_payloads(job)

        # TODO: add a graceful-stop mode that preserves partial draft output.
        job.phase = "none"
        job.status = "cancelled"
        job.last_error = None
        _append_message(job, "Pipeline cancelled by user.")

        return PipelineCancelResponse(ok=True, status="cancelled")


async def generate_resume_for_project(
    db: Session,
    repo_stat: RepoStat,
    user_email: str,
    consent_level: str,
    regenerate: bool = False,
) -> tuple[int, list[str], list[str]]:
    """Generate resume items for a single project.

    Extracts logic from analyze.py to allow on-demand resume generation.
    Runs DeepRepoAnalyzer on a project and persists insights as project evidence.

    Args:
        db: Database session
        repo_stat: RepoStat model for the project
        user_email: User's email for contribution tracking
        consent_level: Consent level for LLM usage ('full', 'no_llm', or 'none')
        regenerate: If True, delete existing generated evidence and legacy resume items first

    Returns:
        Tuple of (count of evidence items generated, critical errors, warnings)
    """
    errors = []
    warnings = []
    project_name = str(getattr(repo_stat, "project_name", "unknown-project"))
    project_path = str(getattr(repo_stat, "project_path", "") or "")
    repo_stat_id = cast(int, repo_stat.id)
    repo_last_commit = getattr(repo_stat, "last_commit", None)
    if not isinstance(repo_last_commit, datetime):
        repo_last_commit = None

    # Delete existing generated rows if regenerate is requested
    if regenerate:
        deleted_resume_items = (
            db.query(ResumeItem)
            .filter(ResumeItem.repo_stat_id == repo_stat_id)
            .delete()
        )
        deleted_evidence_items = (
            db.query(ProjectEvidence)
            .filter(ProjectEvidence.repo_stat_id == repo_stat_id)
            .delete()
        )
        if deleted_resume_items > 0 or deleted_evidence_items > 0:
            print(
                f"[resume_generate] Deleted {deleted_resume_items} ResumeItem and "
                f"{deleted_evidence_items} ProjectEvidence rows for {project_name}"
            )

    # Collect user additions for analysis context
    additions_text = ""
    if project_path and Path(project_path).exists():
        try:
            user_additions = collect_user_additions(
                repo_path=project_path,
                user_email=user_email,
                max_commits=500,
            )
            additions_text = "\n".join(user_additions)
        except Exception as e:
            warning_msg = f"Could not collect additions for {project_name}: {e}"
            print(f"[resume_generate] Warning: {warning_msg}")
            warnings.append(warning_msg)

    # Run deep analysis to extract insights
    analyzer = DeepRepoAnalyzer(enable_llm=False)

    try:
        deep_result = analyzer.analyze(
            repo_path=project_path,
            repo_stat=repo_stat,
            user_email=user_email,
            user_contributions={"additions": additions_text},
            consent_level=consent_level,
        )

        # Persist skills
        persist_extracted_skills(
            db=db,
            repo_stat_id=repo_stat_id,
            extracted=deep_result.skills,
            user_email=user_email,
            commit=False,
        )

        persisted_evidence = persist_insights_as_project_evidence(
            db=db,
            repo_stat_id=repo_stat_id,
            insights=deep_result.insights,
            repo_last_commit=repo_last_commit,
            commit=False,
        )

        # /resume/generate no longer creates Deep Insight ResumeItem rows.
        # Insights are persisted as ProjectEvidence instead.
        # Count actual evidence rows persisted after filtering/dedupe/max-cap rules.
        evidence_count = len(persisted_evidence)
        print(
            f"[resume_generate] Generated {evidence_count} evidence items for {project_name}"
        )

        return evidence_count, errors, warnings

    except Exception as e:
        error_msg = f"Failed to analyze {project_name}: {type(e).__name__}: {str(e)}"
        print(f"[resume_generate] Error: {error_msg}")
        errors.append(error_msg)
        return 0, errors, warnings


@router.post("/generate", response_model=ResumeGenerationResponse)
async def generate_resume_items(
    request: ResumeGenerationRequest,
    db: Session = Depends(get_db),
) -> ResumeGenerationResponse:
    """Generate resume items for selected projects.

    This endpoint triggers on-demand resume item generation by running
    DeepRepoAnalyzer on specified projects and persisting the extracted insights
    as project evidence.

    ## How to Get Project IDs

    Project IDs are the database primary keys for RepoStat entries. To retrieve them:

    1. **List all projects**: `GET /projects` returns all projects with their IDs
    2. **Get specific project**: `GET /projects/{project_id}` returns details for one project
    3. **After analysis**: When you call `POST /analyze/repo` or upload a ZIP via `POST /zip`,
       the response includes the project ID in the `repo_stat_id` field

    Example workflow:
    ```
    # Step 1: Analyze a repository
    POST /analyze/repo -> {"id": 1, "project_name": "my-app", ...}

    # Step 2: Generate resume items using the project ID
    POST /resume/generate {"project_ids": [1], "regenerate": false}
    ```

    ## Generation Process

    1. Validates that all project IDs exist and are not soft-deleted
    2. Retrieves user email and consent level
    3. For each project:
       - Optionally deletes existing ProjectEvidence and legacy ResumeItem rows (if regenerate=True)
       - Collects user contributions from git history
       - Runs DeepRepoAnalyzer to extract skills and insights
       - Persists insights as project evidence (not ResumeItem rows)
    4. Returns generation results with evidence count

    ## Success Semantics

    **Important**: This endpoint persists insights as `ProjectEvidence` rows, not
    `ResumeItem` rows. The `success` field indicates whether the generation
    completed without critical errors (not whether resume_items list is non-empty).
    The `items_generated` field reflects the count of evidence items created.

    Args:
        request: ResumeGenerationRequest with project_ids and regenerate flag
        db: Database session (injected)

    Returns:
        ResumeGenerationResponse with evidence count, metadata, and success status.
        The `success` field is True if generation completed without critical errors.

    Raises:
        HTTPException 400: If user email not configured
        HTTPException 404: If any project_id not found or soft-deleted
        HTTPException 500: If database commit fails

    Milestone Requirement: #331 - POST /resume/generate endpoint
    """
    # Get user email and consent level
    user_email = get_user_email(db)
    consent_level = get_consent_level(db)

    print(
        f"[resume_generate] Starting generation for {len(request.project_ids)} projects "
        f"(user={user_email}, consent={consent_level}, regenerate={request.regenerate})"
    )

    # Validate all project IDs exist and are not soft-deleted
    projects = (
        db.query(RepoStat)
        .filter(
            RepoStat.id.in_(request.project_ids),
            RepoStat.deleted_at.is_(None),
        )
        .all()
    )

    if len(projects) != len(request.project_ids):
        found_ids = {cast(int, p.id) for p in projects}
        missing_ids = set(request.project_ids) - found_ids
        raise HTTPException(
            status_code=404,
            detail=f"Projects not found or deleted: {sorted(missing_ids)}",
        )

    # Generate evidence items for each project
    total_evidence_count = 0
    all_errors = []
    all_warnings = []

    for project in projects:
        evidence_count, errors, warnings = await generate_resume_for_project(
            db=db,
            repo_stat=project,
            user_email=user_email,
            consent_level=consent_level,
            regenerate=request.regenerate,
        )
        total_evidence_count += evidence_count
        all_errors.extend(errors)
        all_warnings.extend(warnings)

    # Commit all changes
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save resume items: {type(e).__name__}: {str(e)}",
        ) from e

    # Determine success: True if no critical errors occurred
    # Note: We no longer check resume_items list length since evidence is
    # persisted separately. Success means the operation completed cleanly.
    is_success = len(all_errors) == 0

    print(
        f"[resume_generate] Completed: {total_evidence_count} evidence items generated, "
        f"{len(all_errors)} errors, {len(all_warnings)} warnings, success={is_success}"
    )

    return ResumeGenerationResponse(
        success=is_success,
        items_generated=total_evidence_count,
        resume_items=[],
        consent_level=consent_level,
        errors=all_errors,
        warnings=all_warnings,
    )

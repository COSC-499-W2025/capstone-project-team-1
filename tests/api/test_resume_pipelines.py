"""Tests for /resume/pipelines ephemeral local pipeline endpoints."""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

import git
import pytest

import artifactminer.api.resume as resume_api
from artifactminer.resume.models import ResumeOutput


def _create_git_repo(
    repo_dir: Path,
    *,
    email: str,
    name: str,
    commit_message: str,
) -> None:
    repo_dir.mkdir(parents=True, exist_ok=True)
    repo = git.Repo.init(repo_dir)

    readme_path = repo_dir / "README.md"
    readme_path.write_text(f"# {repo_dir.name}\n", encoding="utf-8")

    repo.index.add(["README.md"])
    actor = git.Actor(name=name, email=email)
    repo.index.commit(commit_message, author=actor, committer=actor)


def _zip_directory(root_dir: Path, zip_path: Path) -> None:
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for file_path in root_dir.rglob("*"):
            if file_path.is_file():
                archive.write(file_path, arcname=file_path.relative_to(root_dir))


@pytest.fixture(autouse=True)
def clear_pipeline_state() -> None:
    """Isolate module-level in-memory job/intake stores between tests."""
    for intake in list(resume_api._intakes.values()):
        shutil.rmtree(intake.extract_dir, ignore_errors=True)
    resume_api._intakes.clear()
    resume_api._jobs.clear()

    yield

    for intake in list(resume_api._intakes.values()):
        shutil.rmtree(intake.extract_dir, ignore_errors=True)
    resume_api._intakes.clear()
    resume_api._jobs.clear()


def test_pipeline_intake_discovers_repositories(client, tmp_path: Path) -> None:
    root = tmp_path / "repos"
    _create_git_repo(
        root / "repo-a",
        email="alice@example.com",
        name="Alice",
        commit_message="init repo a",
    )
    _create_git_repo(
        root / "nested" / "repo-b",
        email="bob@example.com",
        name="Bob",
        commit_message="init repo b",
    )

    zip_path = tmp_path / "repos.zip"
    _zip_directory(root, zip_path)

    response = client.post(
        "/resume/pipelines/intakes",
        json={"zip_path": str(zip_path)},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["intake_id"]
    assert payload["zip_path"] == str(zip_path.resolve())

    repo_names = sorted(repo["name"] for repo in payload["repos"])
    assert repo_names == ["repo-a", "repo-b"]


def test_contributors_endpoint_filters_selected_repositories(
    client,
    tmp_path: Path,
) -> None:
    root = tmp_path / "repos"
    _create_git_repo(
        root / "repo-a",
        email="alice@example.com",
        name="Alice",
        commit_message="init repo a",
    )
    _create_git_repo(
        root / "repo-b",
        email="bob@example.com",
        name="Bob",
        commit_message="init repo b",
    )

    zip_path = tmp_path / "repos.zip"
    _zip_directory(root, zip_path)

    intake_response = client.post(
        "/resume/pipelines/intakes",
        json={"zip_path": str(zip_path)},
    )
    assert intake_response.status_code == 200
    intake_payload = intake_response.json()

    repo_id_by_name = {repo["name"]: repo["id"] for repo in intake_payload["repos"]}
    repo_a_id = repo_id_by_name["repo-a"]
    repo_b_id = repo_id_by_name["repo-b"]

    contributors_a = client.post(
        f"/resume/pipelines/intakes/{intake_payload['intake_id']}/contributors",
        json={"repo_ids": [repo_a_id]},
    )
    assert contributors_a.status_code == 200
    emails_a = [item["email"] for item in contributors_a.json()["contributors"]]
    assert emails_a == ["alice@example.com"]

    contributors_both = client.post(
        f"/resume/pipelines/intakes/{intake_payload['intake_id']}/contributors",
        json={"repo_ids": [repo_a_id, repo_b_id]},
    )
    assert contributors_both.status_code == 200
    emails_both = sorted(
        item["email"] for item in contributors_both.json()["contributors"]
    )
    assert emails_both == ["alice@example.com", "bob@example.com"]


def test_pipeline_start_poll_polish_flow_with_inline_process(
    client,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "repos"
    _create_git_repo(
        root / "repo-a",
        email="alice@example.com",
        name="Alice",
        commit_message="init repo a",
    )
    zip_path = tmp_path / "repos.zip"
    _zip_directory(root, zip_path)

    intake_response = client.post(
        "/resume/pipelines/intakes",
        json={"zip_path": str(zip_path)},
    )
    assert intake_response.status_code == 200
    intake_payload = intake_response.json()
    repo_id = intake_payload["repos"][0]["id"]

    class InlineProcess:
        def __init__(self, target, args=(), daemon=None):
            self._target = target
            self._args = args
            self._alive = False
            self.exitcode = None

        def start(self):
            self._alive = True
            self._target(*self._args)
            self._alive = False
            self.exitcode = 0

        def is_alive(self):
            return self._alive

        def join(self, timeout=None):
            return None

        def terminate(self):
            self._alive = False

        def kill(self):
            self._alive = False

    def fake_phase1_worker(*args):
        event_queue = args[-1]
        event_queue.put({"type": "message", "message": "fake phase1 complete"})
        event_queue.put(
            {
                "type": "draft_ready",
                "draft_output": ResumeOutput(stage="draft"),
                "draft_json": {
                    "professional_summary": "draft summary",
                    "skills_section": "draft skills",
                    "developer_profile": "draft profile",
                    "projects": [],
                    "metadata": {
                        "model_used": "lfm2.5-1.2b-bf16",
                        "models_used": ["lfm2.5-1.2b-bf16"],
                        "stage": "draft",
                        "generation_time_seconds": 0.1,
                        "errors": [],
                        "quality_metrics": {},
                    },
                },
                "telemetry": {
                    "stage": "DRAFT",
                    "repos_total": 1,
                    "repos_done": 1,
                    "facts_total": 3,
                    "draft_projects": 1,
                    "selected_repos": ["repo-a"],
                },
            }
        )

    def fake_phase3_worker(*args):
        event_queue = args[-1]
        event_queue.put({"type": "message", "message": "fake phase3 complete"})
        event_queue.put(
            {
                "type": "complete",
                "output_json": {
                    "professional_summary": "final summary",
                    "skills_section": "final skills",
                    "developer_profile": "final profile",
                    "projects": [],
                    "metadata": {
                        "model_used": "lfm2.5-1.2b-bf16",
                        "models_used": ["lfm2.5-1.2b-bf16"],
                        "stage": "polish",
                        "generation_time_seconds": 0.2,
                        "errors": [],
                        "quality_metrics": {},
                    },
                },
                "telemetry": {
                    "stage": "POLISH",
                    "repos_total": 1,
                    "repos_done": 1,
                    "polished_projects": 1,
                    "selected_repos": ["repo-a"],
                },
            }
        )

    monkeypatch.setattr(resume_api.multiprocessing, "Process", InlineProcess)
    monkeypatch.setattr(resume_api, "_phase1_worker", fake_phase1_worker)
    monkeypatch.setattr(resume_api, "_phase3_worker", fake_phase3_worker)

    start_response = client.post(
        "/resume/pipelines",
        json={
            "intake_id": intake_payload["intake_id"],
            "repo_ids": [repo_id],
            "user_email": "alice@example.com",
            "stage1_model": "qwen2.5-coder-3b-q4",
            "stage2_model": "lfm2.5-1.2b-bf16",
            "stage3_model": "lfm2.5-1.2b-bf16",
        },
    )
    assert start_response.status_code == 200
    job_id = start_response.json()["job_id"]

    status_after_start = client.get(f"/resume/pipelines/{job_id}")
    assert status_after_start.status_code == 200
    status_payload = status_after_start.json()
    assert status_payload["status"] == "draft_ready"
    assert status_payload["draft"] is not None

    polish_response = client.post(
        f"/resume/pipelines/{job_id}/polish",
        json={
            "general_notes": "emphasize backend work",
            "tone": "more technical",
            "additions": ["Deployed to production"],
            "removals": [],
        },
    )
    assert polish_response.status_code == 200
    assert polish_response.json()["status"] == "polishing"

    status_after_polish = client.get(f"/resume/pipelines/{job_id}")
    assert status_after_polish.status_code == 200
    polished_payload = status_after_polish.json()
    assert polished_payload["status"] == "complete"
    assert polished_payload["output"] is not None

import subprocess
import zipfile
from pathlib import Path

import pytest

from artifactminer.helpers.zip_utils import safe_extract_zip


ROOT = Path(__file__).resolve().parents[2]
V1_ZIP = ROOT / "tests" / "data" / "mock_projects.zip"
V2_ZIP = ROOT / "tests" / "data" / "mock_projects_v2.zip"

SELECTED_REPOS = ["sensor-fleet-backend", "go-task-runner"]


def _repo_names(zip_path: Path) -> set[str]:
    repos: set[str] = set()
    with zipfile.ZipFile(zip_path, "r") as zf:
        for name in zf.namelist():
            parts = [p for p in name.split("/") if p]
            if len(parts) >= 2 and parts[0] == "projects":
                repos.add(parts[1])
    return repos


def _extract(zip_path: Path, out_dir: Path) -> Path:
    with zipfile.ZipFile(zip_path, "r") as zf:
        safe_extract_zip(zf, out_dir)
    return out_dir / "projects"


def _commit_count(repo_path: Path) -> int:
    output = subprocess.check_output(
        ["git", "-C", str(repo_path), "rev-list", "--count", "HEAD"],
        text=True,
    ).strip()
    return int(output)


@pytest.mark.skipif(not V1_ZIP.exists(), reason="mock_projects.zip not found")
@pytest.mark.skipif(not V2_ZIP.exists(), reason="mock_projects_v2.zip not found")
def test_v2_contains_same_project_set_as_v1() -> None:
    assert _repo_names(V1_ZIP) == _repo_names(V2_ZIP)


@pytest.mark.skipif(not V1_ZIP.exists(), reason="mock_projects.zip not found")
@pytest.mark.skipif(not V2_ZIP.exists(), reason="mock_projects_v2.zip not found")
def test_v2_has_expected_new_files() -> None:
    expected_new_files = [
        "projects/sensor-fleet-backend/app/snapshot_v2_support.py",
        "projects/sensor-fleet-backend/doc/snapshot_v2_notes.md",
        "projects/sensor-fleet-backend/test/incremental_upload_check.md",
        "projects/go-task-runner/doc/incremental_upload_notes.md",
        "projects/go-task-runner/tests/incremental_snapshot_test.go",
    ]

    with zipfile.ZipFile(V1_ZIP, "r") as zf_v1:
        v1_names = set(zf_v1.namelist())
    with zipfile.ZipFile(V2_ZIP, "r") as zf_v2:
        v2_names = set(zf_v2.namelist())

    for path in expected_new_files:
        assert path in v2_names
        assert path not in v1_names


@pytest.mark.skipif(not V1_ZIP.exists(), reason="mock_projects.zip not found")
@pytest.mark.skipif(not V2_ZIP.exists(), reason="mock_projects_v2.zip not found")
def test_v2_has_extended_git_history_for_selected_projects(tmp_path: Path) -> None:
    v1_root = _extract(V1_ZIP, tmp_path / "v1")
    v2_root = _extract(V2_ZIP, tmp_path / "v2")

    for repo_name in SELECTED_REPOS:
        v1_count = _commit_count(v1_root / repo_name)
        v2_count = _commit_count(v2_root / repo_name)
        assert v2_count > v1_count, f"{repo_name} should have more commits in v2"

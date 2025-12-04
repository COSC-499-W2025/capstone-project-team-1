"""API client for Artifact Miner backend."""

from pathlib import Path
from typing import Any, Dict, List, Optional
import httpx


class APIClient:
    """HTTP client wrapper for Artifact Miner API."""

    def __init__(self, base_url: str, timeout: float = 120.0):
        self.base_url = base_url
        self.timeout = httpx.Timeout(timeout)
        self._client: Optional[httpx.Client] = None

    def __enter__(self) -> "APIClient":
        self._client = httpx.Client(base_url=self.base_url, timeout=self.timeout)
        return self

    def __exit__(self, *args) -> None:
        if self._client:
            self._client.close()

    @property
    def client(self) -> httpx.Client:
        if not self._client:
            raise RuntimeError("APIClient must be used as context manager")
        return self._client

    def health_check(self) -> Dict[str, Any]:
        return self.client.get("/health").json()

    def get_consent(self) -> Dict[str, Any]:
        return self.client.get("/consent").json()

    def update_consent(self, level: str) -> Dict[str, Any]:
        return self.client.put("/consent", json={"consent_level": level}).json()

    def get_questions(self) -> List[Dict[str, Any]]:
        return self.client.get("/questions").json()

    def submit_answers(self, answers: Dict[str, str]) -> List[Dict[str, Any]]:
        return self.client.post("/answers", json={"answers": answers}).json()

    def upload_zip(self, path: Path) -> Dict[str, Any]:
        with path.open("rb") as f:
            return self.client.post(
                "/zip/upload", files={"file": (path.name, f, "application/zip")}
            ).json()

    def upload_file_raw(self, path: Path) -> httpx.Response:
        with path.open("rb") as f:
            return self.client.post(
                "/zip/upload",
                files={"file": (path.name, f, "application/octet-stream")},
            )

    def list_directories(self, zip_id: int) -> Dict[str, Any]:
        return self.client.get(f"/zip/{zip_id}/directories").json()

    def run_analysis(self, zip_id: int) -> Dict[str, Any]:
        return self.client.post(f"/analyze/{zip_id}").json()

    def get_summaries(self, email: str) -> List[Dict[str, Any]]:
        return self.client.get("/summaries", params={"user_email": email}).json()

    def get_resume_items(self) -> List[Dict[str, Any]]:
        return self.client.get("/resume").json()

    def get_skill_chronology(self) -> List[Dict[str, Any]]:
        return self.client.get("/skills/chronology").json()

    def get_project_timeline(self) -> List[Dict[str, Any]]:
        return self.client.get("/projects/timeline").json()

    def delete_project(self, project_id: int) -> Dict[str, Any]:
        return self.client.delete(f"/projects/{project_id}").json()

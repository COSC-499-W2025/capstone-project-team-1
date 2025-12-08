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

    def _get(self, url: str, **kwargs) -> Any:
        """Helper method for GET requests with error handling."""
        response = self.client.get(url, **kwargs)
        response.raise_for_status()
        return response.json()

    def _post(self, url: str, **kwargs) -> Any:
        """Helper method for POST requests with error handling."""
        response = self.client.post(url, **kwargs)
        response.raise_for_status()
        return response.json()

    def _put(self, url: str, **kwargs) -> Any:
        """Helper method for PUT requests with error handling."""
        response = self.client.put(url, **kwargs)
        response.raise_for_status()
        return response.json()

    def _delete(self, url: str, **kwargs) -> Any:
        """Helper method for DELETE requests with error handling."""
        response = self.client.delete(url, **kwargs)
        response.raise_for_status()
        return response.json()

    def health_check(self) -> Dict[str, Any]:
        return self._get("/health")

    def get_consent(self) -> Dict[str, Any]:
        return self._get("/consent")

    def update_consent(self, level: str) -> Dict[str, Any]:
        return self._put("/consent", json={"consent_level": level})

    def get_questions(self) -> List[Dict[str, Any]]:
        return self._get("/questions")

    def submit_answers(self, answers: Dict[str, str]) -> List[Dict[str, Any]]:
        return self._post("/answers", json={"answers": answers})

    def upload_zip(self, path: Path) -> Dict[str, Any]:
        with path.open("rb") as f:
            return self._post(
                "/zip/upload", files={"file": (path.name, f, "application/zip")}
            )

    def upload_file_raw(self, path: Path) -> httpx.Response:
        """Returns raw response for custom handling."""
        with path.open("rb") as f:
            response = self.client.post(
                "/zip/upload",
                files={"file": (path.name, f, "application/octet-stream")},
            )
            response.raise_for_status()
            return response

    def list_directories(self, zip_id: int) -> Dict[str, Any]:
        return self._get(f"/zip/{zip_id}/directories")

    def run_analysis(self, zip_id: int) -> Dict[str, Any]:
        return self._post(f"/analyze/{zip_id}")

    def get_summaries(self, email: str) -> List[Dict[str, Any]]:
        return self._get("/summaries", params={"user_email": email})

    def get_resume_items(self) -> List[Dict[str, Any]]:
        return self._get("/resume")

    def get_skill_chronology(self) -> List[Dict[str, Any]]:
        return self._get("/skills/chronology")

    def get_project_timeline(self) -> List[Dict[str, Any]]:
        return self._get("/projects/timeline")

    def delete_project(self, project_id: int) -> Dict[str, Any]:
        return self._delete(f"/projects/{project_id}")

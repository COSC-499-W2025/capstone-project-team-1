from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv


# Load env config so TUI follows the .env single source of truth
load_dotenv()
DEFAULT_API_BASE = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


class ApiClient:
    """Client for TUI to call Artifact Miner API."""

    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (base_url or DEFAULT_API_BASE).rstrip("/")

    async def upload_zip(self, zip_path: Path) -> dict[str, Any]:
        """POST /zip/upload; returns {"zip_id", "filename"}."""
        url = f"{self.base_url}/zip/upload"
        async with httpx.AsyncClient(timeout=30.0) as client:
            with zip_path.open("rb") as f:
                files = {"file": (zip_path.name, f, "application/zip")}
                resp = await client.post(url, files=files)
        resp.raise_for_status()
        return resp.json()

    async def list_zip_directories(self, zip_id: int) -> dict[str, Any]:
        """GET /zip/{zip_id}/directories; returns directories list."""
        url = f"{self.base_url}/zip/{zip_id}/directories"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url)
        resp.raise_for_status()
        return resp.json()

    async def get_resume_items(self, project_id: int | None = None) -> list[dict[str, Any]]:
        """GET /resume with optional project_id filter."""
        url = f"{self.base_url}/resume"
        params: dict[str, Any] = {}
        if project_id is not None:
            params["project_id"] = project_id
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, params=params if params else None)
        resp.raise_for_status()
        return resp.json()

    async def get_summaries(self, user_email: str) -> list[dict[str, Any]]:
        """GET /summaries for a specific user."""
        url = f"{self.base_url}/summaries"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, params={"user_email": user_email})
        resp.raise_for_status()
        return resp.json()

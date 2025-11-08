from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx


DEFAULT_API_BASE = "http://127.0.0.1:8000"


class ApiClient:
    """Minimal API client for Artifact Miner endpoints used by the TUI."""

    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = base_url or DEFAULT_API_BASE

    async def upload_zip(self, zip_path: Path) -> dict[str, Any]:
        """POST /zip/upload with a multipart file.

        Returns: {"zip_id": int, "filename": str}
        """
        url = f"{self.base_url}/zip/upload"
        # Stream file as bytes; httpx will build multipart for (name, (filename, fileobj, content_type))
        async with httpx.AsyncClient(timeout=30.0) as client:
            with zip_path.open("rb") as f:
                files = {"file": (zip_path.name, f, "application/zip")}
                resp = await client.post(url, files=files)
        resp.raise_for_status()
        return resp.json()

    async def list_zip_directories(self, zip_id: int) -> dict[str, Any]:
        """GET /zip/{zip_id}/directories.

        Returns: {"zip_id": int, "filename": str, "directories": list[str]}
        """
        url = f"{self.base_url}/zip/{zip_id}/directories"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url)
        resp.raise_for_status()
        return resp.json()


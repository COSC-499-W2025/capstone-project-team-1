"""Simplistic in-memory storage helpers for the ingest MVP."""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from io import BytesIO
from typing import Any, Dict, Iterable, Literal
from zipfile import BadZipFile, ZipFile

from fastapi import HTTPException, status

from .models import CandidateDir, Progress

PhaseLiteral = Literal[
    "validating_zip",
    "scanning",
    "listing_candidates",
    "waiting_for_selection",
    "error",
]

MAX_ZIP_BYTES = 300 * 1024 * 1024  # 300 MB
ROOT_SYNTHETIC_NAME = "root_files"

logger = logging.getLogger(__name__)


class IngestState(Dict[str, Any]):
    """Type alias for per-ingest state dict to aid readability."""


STATE: dict[str, IngestState] = {}
_state_lock = asyncio.Lock()


async def create_ingest(zip_bytes: bytes) -> str:
    """Create a new ingest entry with the provided zip bytes and initial progress."""

    if len(zip_bytes) > MAX_ZIP_BYTES:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Archive exceeds {MAX_ZIP_BYTES // (1024 * 1024)}MB limit.",
        )

    safe_zip_check(zip_bytes)

    ingest_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc)
    async with _state_lock:
        STATE[ingest_id] = {
            "zip_bytes": zip_bytes,
            "progress": {
                "ingest_id": ingest_id,
                "phase": "validating_zip",
                "percent": 5.0,
                "message": "Zip validated, queued for scanning.",
            },
            "candidates": [],
            "selection": None,
            "created_at": now,
        }
    logger.info("Ingest %s created at %s", ingest_id, now.isoformat())
    return ingest_id


async def get_ingest(ingest_id: str) -> IngestState:
    """Return ingest state or raise HTTP 404."""

    try:
        return STATE[ingest_id]
    except KeyError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Unknown ingest_id") from exc


async def set_progress(
    ingest_id: str,
    phase: PhaseLiteral,
    percent: float,
    message: str | None = None,
) -> None:
    """Update progress for the given ingest."""

    async with _state_lock:
        ingest = STATE.get(ingest_id)
        if ingest is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Unknown ingest_id")
        ingest["progress"] = {
            "ingest_id": ingest_id,
            "phase": phase,
            "percent": float(max(0.0, min(percent, 100.0))),
            "message": message,
        }
    logger.debug(
        "Ingest %s transitioned to %s (%.1f%%): %s",
        ingest_id,
        phase,
        percent,
        message,
    )


async def record_candidates(ingest_id: str, candidates: Iterable[CandidateDir]) -> None:
    """Persist the discovered candidates for the ingest."""

    candidate_models = [candidate.model_dump() for candidate in candidates]
    async with _state_lock:
        ingest = STATE.get(ingest_id)
        if ingest is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Unknown ingest_id")
        ingest["candidates"] = candidate_models
    logger.info("Ingest %s stored %d candidates", ingest_id, len(candidate_models))


async def get_progress(ingest_id: str) -> Progress:
    """Return the current progress."""

    ingest = await get_ingest(ingest_id)
    return Progress(**ingest["progress"])


async def get_candidates(ingest_id: str) -> list[CandidateDir]:
    """Return candidates as CandidateDir models."""

    ingest = await get_ingest(ingest_id)
    return [CandidateDir(**candidate) for candidate in ingest.get("candidates", [])]


async def record_selection(ingest_id: str, selection: list[str]) -> None:
    """Persist the chosen candidate paths for the ingest."""

    async with _state_lock:
        ingest = STATE.get(ingest_id)
        if ingest is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Unknown ingest_id")
        ingest["selection"] = list(selection)
    logger.info("Ingest %s saved selection (%d items)", ingest_id, len(selection))


def safe_zip_check(zip_bytes: bytes) -> None:
    """Best-effort validation of a zip archive without extraction."""

    try:
        with ZipFile(BytesIO(zip_bytes)) as zf:
            # Test integrity; returns name of bad file if present.
            bad_member = zf.testzip()
            if bad_member:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    detail=f"Corrupt archive member: {bad_member}",
                )
    except BadZipFile as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid zip archive") from exc


def scan_top_level_dirs(zf: ZipFile) -> list[CandidateDir]:
    """Inspect the zip file and enumerate top-level directories."""

    tag_mapping = {
        "code": {".py", ".js", ".ts", ".java", ".go", ".rs", ".cpp", ".c", ".cs", ".rb"},
        "docs": {".md", ".rst", ".pdf", ".docx", ".txt"},
        "config": {".json", ".yaml", ".yml", ".toml", ".ini", ".env"},
    }

    def classify(ext: str) -> str:
        for tag, extensions in tag_mapping.items():
            if ext in extensions:
                return tag
        return "other"

    file_counts: dict[str, int] = defaultdict(int)
    tag_sets: dict[str, set[str]] = defaultdict(set)

    for info in zf.infolist():
        name = info.filename
        if name.endswith("/"):
            continue  # directory placeholder, handled via files below
        top_level = name.split("/", 1)[0]
        candidate = top_level if "/" in name else ROOT_SYNTHETIC_NAME
        file_counts[candidate] += 1
        ext = "." + name.rsplit(".", 1)[-1] if "." in name else ""
        if ext:
            tag_sets[candidate].add(classify(ext.lower()))
        else:
            tag_sets[candidate].add("other")

    # Ensure directories without files still appear
    for name in zf.namelist():
        normalized = name.rstrip("/")
        if not normalized:
            continue
        parts = normalized.split("/", 1)
        top_level = parts[0]
        if not name.endswith("/") and len(parts) == 1:
            # Single root-level file already covered.
            continue
        file_counts.setdefault(top_level, 0)
        tag_sets.setdefault(top_level, set())

    candidates: list[CandidateDir] = []
    for path, count in sorted(file_counts.items()):
        tags = sorted(tag_sets[path]) if tag_sets[path] else ["other"]
        candidates.append(
            CandidateDir(
                path=path,
                approx_files=count,
                tags=tags,
            )
        )

    logger.info("Discovered %d top-level candidates", len(candidates))
    return candidates


def load_zip_bytes(ingest_id: str) -> bytes:
    """Return raw zip bytes for the ingest."""

    ingest = STATE.get(ingest_id)
    if not ingest:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Unknown ingest_id")
    return ingest["zip_bytes"]


def open_zipfile(ingest_id: str) -> ZipFile:
    """Convenience helper to reopen the stored archive."""

    return ZipFile(BytesIO(load_zip_bytes(ingest_id)))

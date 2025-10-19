"""FastAPI application exposing the ingest MVP endpoints."""

from __future__ import annotations

import asyncio
import logging
import time

from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from .models import CandidatesResponse, IngestCreateResponse, Progress, SelectionRequest, SelectionResponse
from .storage import (
    create_ingest,
    get_candidates,
    get_progress,
    open_zipfile,
    record_candidates,
    record_selection,
    scan_top_level_dirs,
    set_progress,
)

logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

app = FastAPI(title="ARTIFACT-MINER", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def log_startup() -> None:
    """Log API startup to help operators confirm service readiness.

    Returns:
        None: Always returns None once the log has been emitted.
    """

    logger.info("FastAPI ingest service starting up.")


@app.post("/ingest/upload", response_model=IngestCreateResponse, status_code=status.HTTP_201_CREATED)
async def upload_zip(file: UploadFile = File(...)) -> IngestCreateResponse:
    """Handle an uploaded zip archive for ingest.

    Args:
        file: The uploaded zip file provided via multipart form-data.

    Returns:
        IngestCreateResponse: The created ingest metadata.

    Raises:
        HTTPException: If upload validation fails or the ingest cannot be created.
    """

    logger.info("Upload initiated for filename='%s'", file.filename)
    contents = await file.read()
    ingest_id = await create_ingest(contents)
    logger.info("Upload stored for ingest_id=%s", ingest_id)

    asyncio.create_task(background_scan(ingest_id))
    logger.info("Background scan scheduled for ingest_id=%s filename='%s'", ingest_id, file.filename)

    return IngestCreateResponse(ingest_id=ingest_id, status="validating_zip")


@app.get("/ingest/{ingest_id}/progress", response_model=Progress)
async def read_progress(ingest_id: str) -> Progress:
    """Fetch current progress for an ingest session.

    Args:
        ingest_id: The ingest identifier to query.

    Returns:
        Progress: The latest progress snapshot for the ingest.

    Raises:
        HTTPException: If the ingest identifier is unknown.
    """

    return await get_progress(ingest_id)


@app.get("/ingest/{ingest_id}/candidates", response_model=CandidatesResponse)
async def read_candidates(ingest_id: str) -> CandidatesResponse:
    """Retrieve candidate directories for a completed ingest scan.

    Args:
        ingest_id: The ingest identifier that has completed scanning.

    Returns:
        CandidatesResponse: The available candidate directories.

    Raises:
        HTTPException: If candidates are requested before scanning completes or ingest is missing.
    """

    progress = await get_progress(ingest_id)
    if progress.phase != "waiting_for_selection":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"Candidates not ready. Current phase={progress.phase}",
        )
    candidates = await get_candidates(ingest_id)
    logger.info("Returning %d candidates for ingest_id=%s", len(candidates), ingest_id)
    return CandidatesResponse(ingest_id=ingest_id, candidates=candidates)


@app.post("/ingest/{ingest_id}/select", response_model=SelectionResponse)
async def save_selection(ingest_id: str, payload: SelectionRequest) -> SelectionResponse:
    """Persist the selected candidate directories in memory.

    Args:
        ingest_id: The ingest identifier targeted for selection.
        payload: The selection payload listing chosen candidate paths.

    Returns:
        SelectionResponse: The confirmation that selections were recorded.

    Raises:
        HTTPException: If selection is attempted before candidates are ready or ingest is unknown.
    """

    progress = await get_progress(ingest_id)
    if progress.phase not in {"waiting_for_selection", "error"}:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Selection not accepted until candidates are ready.",
        )

    # TODO: Hook ingestion workflow here in future sprints.
    await record_selection(ingest_id, payload.selected_paths)
    logger.info("Selection saved for ingest_id=%s paths=%s", ingest_id, payload.selected_paths)
    logger.info("Updating ingest_id=%s to phase='waiting_for_selection'", ingest_id)
    await set_progress(
        ingest_id,
        "waiting_for_selection",
        percent=100.0,
        message="Selection saved.",
    )
    return SelectionResponse(
        ingest_id=ingest_id,
        saved=True,
        selected_paths=payload.selected_paths,
    )


async def background_scan(ingest_id: str) -> None:
    """Scan the stored zip and populate candidate information.

    Args:
        ingest_id: The ingest identifier whose archive should be scanned.

    Returns:
        None: This is a background task without a return payload.

    Raises:
        HTTPException: Propagated if validation fails; converted to progress updates and logged.
    """

    try:
        logger.info("Updating ingest_id=%s to phase='scanning'", ingest_id)
        await set_progress(ingest_id, "scanning", percent=35.0, message="Scanning archive...")
        scan_started = time.perf_counter()
        with open_zipfile(ingest_id) as zf:
            candidates = scan_top_level_dirs(zf)
        scan_duration = time.perf_counter() - scan_started
        logger.info(
            "Ingest_id=%s scanning completed in %.2fs with %d candidates",
            ingest_id,
            scan_duration,
            len(candidates),
        )
        logger.info("Updating ingest_id=%s to phase='listing_candidates'", ingest_id)
        await set_progress(
            ingest_id,
            "listing_candidates",
            percent=70.0,
            message="Preparing candidate list...",
        )
        await record_candidates(ingest_id, candidates)
        if not candidates:
            logger.info("No candidates discovered for ingest_id=%s", ingest_id)
            logger.info("Updating ingest_id=%s to phase='waiting_for_selection'", ingest_id)
            await set_progress(
                ingest_id,
                "waiting_for_selection",
                percent=100.0,
                message="No directories found. Nothing to select.",
            )
        else:
            logger.info("Updating ingest_id=%s to phase='waiting_for_selection'", ingest_id)
            await set_progress(
                ingest_id,
                "waiting_for_selection",
                percent=100.0,
                message=f"{len(candidates)} candidates ready.",
            )
    except HTTPException as exc:
        logger.info("Updating ingest_id=%s to phase='error'", ingest_id)
        await set_progress(
            ingest_id,
            "error",
            percent=100.0,
            message=str(exc.detail),
        )
        logger.exception("HTTP error while scanning ingest %s: %s", ingest_id, exc, exc_info=exc)
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.info("Updating ingest_id=%s to phase='error'", ingest_id)
        await set_progress(
            ingest_id,
            "error",
            percent=100.0,
            message="Unexpected error during scanning.",
        )
        logger.exception("Unexpected error while scanning ingest %s", ingest_id, exc_info=exc)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server.server:app", host="127.0.0.1", port=8000, reload=True)

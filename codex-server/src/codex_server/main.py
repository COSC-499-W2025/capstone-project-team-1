from __future__ import annotations

import logging
import tempfile
import zipfile
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from codex_server.process import CodexProcess

logging.basicConfig(level=logging.INFO)

codex = CodexProcess()


@asynccontextmanager
async def lifespan(application: FastAPI):
    await codex.start()
    yield
    await codex.stop()


app = FastAPI(title="Codex Server", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/codex/status")
async def codex_status() -> dict:
    return {
        "state": codex.state.value,
        "error": codex.error,
    }


@app.get("/codex/account")
async def read_account():
    return await codex.read_account()


@app.post("/codex/account/login")
async def login():
    return await codex.login_chatgpt()


@app.post("/codex/account/logout")
async def logout():
    return await codex.logout()


class ThreadRequest(BaseModel):
    instructions: str | None = None


class TurnRequest(BaseModel):
    thread_id: str
    message: str


@app.post("/codex/threads")
async def create_thread(body: ThreadRequest | None = None):
    instructions = body.instructions if body else None
    thread_id = await codex.start_thread(instructions)
    return {"thread_id": thread_id}


@app.post("/codex/turns")
async def create_turn(body: TurnRequest):
    result = await codex.send_turn(body.thread_id, body.message)
    return {
        "text": result.text,
        "status": result.status,
        "error": result.error,
    }


RESUME_PROMPT = """\
You are a resume writer. Analyze ALL the code, commits, README files, and \
project structure in the current working directory. Then produce a polished \
developer resume in Markdown format.

The resume MUST include:
- A professional summary (2-3 sentences)
- A technical skills section grouped by category
- A projects section with: name, description, technologies used, and \
  key contributions (as bullet points)

Output ONLY the Markdown resume — no explanations, no commentary.
"""


class GenerateRequest(BaseModel):
    zip_path: str


def _safe_extract(zip_path: Path, dest: Path) -> None:
    """Extract a ZIP file, guarding against zip-slip attacks."""
    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.namelist():
            target = (dest / member).resolve()
            if not str(target).startswith(str(dest.resolve())):
                raise HTTPException(400, f"Unsafe path in ZIP: {member}")
        zf.extractall(dest)


@app.post("/codex/generate")
async def generate_resume(body: GenerateRequest):
    zip_file = Path(body.zip_path)
    if not zip_file.exists():
        raise HTTPException(404, f"ZIP file not found: {body.zip_path}")
    if not zipfile.is_zipfile(zip_file):
        raise HTTPException(400, f"Not a valid ZIP file: {body.zip_path}")

    # Extract to a temporary directory
    tmp = tempfile.mkdtemp(prefix="codex-gen-")
    _safe_extract(zip_file, Path(tmp))

    # Create a thread pointed at the extracted directory
    thread_id = await codex.start_thread(cwd=tmp)

    # Send the resume generation prompt
    result = await codex.send_turn(thread_id, RESUME_PROMPT)

    # Strip any preamble before the first markdown heading
    text = result.text
    heading_pos = text.find("\n#")
    if heading_pos != -1:
        text = text[heading_pos + 1:]

    return {
        "markdown": text,
        "status": result.status,
        "error": result.error,
    }


def main() -> None:
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8100)


if __name__ == "__main__":
    main()

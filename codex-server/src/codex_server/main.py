from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
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


def main() -> None:
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8100)


if __name__ == "__main__":
    main()

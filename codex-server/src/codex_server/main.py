from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

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


def main() -> None:
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8100)


if __name__ == "__main__":
    main()

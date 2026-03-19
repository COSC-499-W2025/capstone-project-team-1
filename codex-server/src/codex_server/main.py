from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(title="Codex Server", version="0.1.0")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


def main() -> None:
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8100)


if __name__ == "__main__":
    main()

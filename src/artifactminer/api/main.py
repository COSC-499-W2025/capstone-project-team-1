"""CLI entrypoint for running backend setup tasks and the FastAPI server."""

from __future__ import annotations

import argparse

import uvicorn

from artifactminer.bootstrap import ensure_database_ready


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="api",
        description="Artifact Miner backend utilities",
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=("run", "bootstrap"),
        default="run",
        help="`run` starts the FastAPI dev server, `bootstrap` only prepares the database.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind the API server to.")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind the API server to.")
    parser.add_argument(
        "--reload",
        dest="reload",
        action="store_true",
        default=True,
        help="Enable auto-reload while developing (default: enabled).",
    )
    parser.add_argument(
        "--no-reload",
        dest="reload",
        action="store_false",
        help="Disable auto-reload.",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    """Run the FastAPI development server or just bootstrap local state."""

    args = _build_parser().parse_args(argv)
    ensure_database_ready()

    if args.command == "bootstrap":
        print("Artifact Miner database is ready.")
        return

    uvicorn.run(
        "artifactminer.api.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()

"""CLI entrypoint for running the FastAPI development server."""
import uvicorn


def main():
    """Run the FastAPI development server with auto-reload."""
    uvicorn.run(
        "artifactminer.api.app:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    main()

from __future__ import annotations

from artifactminer.api.main import main


def test_api_cli_defaults_to_run_command(monkeypatch) -> None:
    recorded: dict[str, object] = {}

    def fake_run(app: str, *, host: str, port: int, reload: bool) -> None:
        recorded.update(
            {
                "app": app,
                "host": host,
                "port": port,
                "reload": reload,
            }
        )

    monkeypatch.setattr("artifactminer.api.main.uvicorn.run", fake_run)

    main([])

    assert recorded == {
        "app": "artifactminer.api.app:app",
        "host": "127.0.0.1",
        "port": 8000,
        "reload": True,
    }


def test_api_cli_accepts_explicit_run_command_and_overrides(monkeypatch) -> None:
    recorded: dict[str, object] = {}

    def fake_run(app: str, *, host: str, port: int, reload: bool) -> None:
        recorded.update(
            {
                "app": app,
                "host": host,
                "port": port,
                "reload": reload,
            }
        )

    monkeypatch.setattr("artifactminer.api.main.uvicorn.run", fake_run)

    main(["run", "--host", "0.0.0.0", "--port", "8011", "--no-reload"])

    assert recorded == {
        "app": "artifactminer.api.app:app",
        "host": "0.0.0.0",
        "port": 8011,
        "reload": False,
    }

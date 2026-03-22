"""Tests for server reuse, restart, crash detection, and runtime status."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from artifactminer.local_llm.models import ModelDescriptor, RuntimeStatus
from artifactminer.local_llm.runtime import process_manager
from artifactminer.local_llm.runtime.errors import ModelServerCrashedError


@pytest.fixture(autouse=True)
def _reset_module_state():
    """Ensure module-level state is clean before and after every test."""

    process_manager._reset_state()
    process_manager._atexit_registered = False
    yield
    process_manager._reset_state()
    process_manager._atexit_registered = False


@pytest.fixture()
def stub_descriptor(tmp_path: Path) -> ModelDescriptor:
    """A descriptor pointing at a real temp file so path assertions work."""

    model_file = tmp_path / "stub-model.gguf"
    model_file.write_bytes(b"GGUF")
    return ModelDescriptor(
        name="stub-model",
        filename="stub-model.gguf",
        context_window=4096,
        path=model_file,
    )


@pytest.fixture()
def alt_descriptor(tmp_path: Path) -> ModelDescriptor:
    """A second descriptor for model-switch restart tests."""

    model_file = tmp_path / "alt-model.gguf"
    model_file.write_bytes(b"GGUF")
    return ModelDescriptor(
        name="alt-model",
        filename="alt-model.gguf",
        context_window=8192,
        path=model_file,
    )


def _inject_running_server(model: str = "stub-model", port: int = 9999) -> MagicMock:
    """Simulate a healthy running server by setting module-level state."""

    mock_proc = MagicMock(spec=subprocess.Popen)
    mock_proc.pid = 12345
    mock_proc.poll.return_value = None  # still alive
    process_manager._server_process = mock_proc
    process_manager._server_port = port
    process_manager._server_model = model
    return mock_proc


# -- _is_process_alive -------------------------------------------------------


class TestIsProcessAlive:
    """Tests for process liveness detection."""

    def test_alive_when_process_running(self) -> None:
        """Returns True when the managed process has not exited."""

        _inject_running_server()
        assert process_manager._is_process_alive() is True

    def test_dead_when_process_exited(self) -> None:
        """Returns False when the managed process has exited."""

        mock_proc = _inject_running_server()
        mock_proc.poll.return_value = 1
        assert process_manager._is_process_alive() is False

    def test_dead_when_no_process(self) -> None:
        """Returns False when no server has been started."""

        assert process_manager._is_process_alive() is False


# -- _detect_crash -----------------------------------------------------------


class TestDetectCrash:
    """Tests for crash detection."""

    def test_raises_on_crashed_process(self) -> None:
        """Raises ModelServerCrashedError when the process has exited."""

        mock_proc = _inject_running_server(model="stub-model")
        mock_proc.poll.return_value = 137
        mock_proc.returncode = 137

        with pytest.raises(ModelServerCrashedError) as exc_info:
            process_manager._detect_crash()

        assert exc_info.value.model == "stub-model"
        assert exc_info.value.exit_code == 137
        # State is cleaned up after crash detection
        assert process_manager._server_process is None

    def test_noop_when_process_alive(self) -> None:
        """Does nothing when the process is still running."""

        _inject_running_server()
        process_manager._detect_crash()  # should not raise

    def test_noop_when_no_process(self) -> None:
        """Does nothing when no server has been started."""

        process_manager._detect_crash()  # should not raise


# -- ensure_server -----------------------------------------------------------


class TestEnsureServer:
    """Tests for the ensure_server reuse/restart entry point."""

    def test_cold_start(self, stub_descriptor: ModelDescriptor) -> None:
        """Starts a fresh server when nothing is running."""

        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.pid = 12345

        with (
            patch.object(
                process_manager, "_find_llama_server", return_value="/bin/llama-server"
            ),
            patch.object(
                process_manager,
                "resolve_model_descriptor",
                return_value=stub_descriptor,
            ),
            patch.object(process_manager, "_pick_free_port", return_value=9999),
            patch("subprocess.Popen", return_value=mock_proc),
            patch.object(process_manager, "poll_until_healthy"),
            patch("atexit.register"),
        ):
            process_manager.ensure_server("stub-model", models_dir=Path("/tmp"))

        assert process_manager._server_process is mock_proc
        assert process_manager._server_model == "stub-model"

    def test_reuses_healthy_server(self) -> None:
        """Returns immediately when the same model is already loaded."""

        _inject_running_server(model="stub-model")

        with (
            patch.object(process_manager, "check_health", return_value=True),
            patch("subprocess.Popen") as mock_popen,
        ):
            process_manager.ensure_server("stub-model")
            mock_popen.assert_not_called()

    def test_restarts_same_model_when_unhealthy(
        self, stub_descriptor: ModelDescriptor
    ) -> None:
        """Restarts the current model when the process is alive but unhealthy."""

        old_proc = _inject_running_server(model="stub-model")

        new_proc = MagicMock(spec=subprocess.Popen)
        new_proc.pid = 67890

        with (
            patch.object(process_manager, "check_health", return_value=False),
            patch.object(
                process_manager, "_find_llama_server", return_value="/bin/llama-server"
            ),
            patch.object(
                process_manager,
                "resolve_model_descriptor",
                return_value=stub_descriptor,
            ),
            patch.object(process_manager, "_pick_free_port", return_value=8888),
            patch("subprocess.Popen", return_value=new_proc),
            patch.object(process_manager, "poll_until_healthy"),
            patch("atexit.register"),
        ):
            process_manager.ensure_server("stub-model", models_dir=Path("/tmp"))

        old_proc.terminate.assert_called_once()
        assert process_manager._server_process is new_proc
        assert process_manager._server_model == "stub-model"
        assert process_manager._server_port == 8888

    def test_restarts_for_different_model(
        self, alt_descriptor: ModelDescriptor
    ) -> None:
        """Stops old server and starts new when a different model is requested."""

        old_proc = _inject_running_server(model="stub-model")

        new_proc = MagicMock(spec=subprocess.Popen)
        new_proc.pid = 67890

        with (
            patch.object(
                process_manager, "_find_llama_server", return_value="/bin/llama-server"
            ),
            patch.object(
                process_manager,
                "resolve_model_descriptor",
                return_value=alt_descriptor,
            ),
            patch.object(process_manager, "_pick_free_port", return_value=8888),
            patch("subprocess.Popen", return_value=new_proc),
            patch.object(process_manager, "poll_until_healthy"),
            patch("atexit.register"),
        ):
            process_manager.ensure_server("alt-model", models_dir=Path("/tmp"))

        old_proc.terminate.assert_called_once()
        assert process_manager._server_process is new_proc
        assert process_manager._server_model == "alt-model"
        assert process_manager._server_port == 8888

    def test_raises_on_crashed_server(self) -> None:
        """Raises ModelServerCrashedError if the previous server crashed."""

        mock_proc = _inject_running_server(model="stub-model")
        mock_proc.poll.return_value = 1
        mock_proc.returncode = 1

        with pytest.raises(ModelServerCrashedError):
            process_manager.ensure_server("stub-model")

    def test_same_model_twice_no_duplicate(self) -> None:
        """Calling ensure_server twice with the same model does not spawn two servers."""

        _inject_running_server(model="stub-model", port=9999)

        with (
            patch.object(process_manager, "check_health", return_value=True),
            patch("subprocess.Popen") as mock_popen,
        ):
            process_manager.ensure_server("stub-model")
            process_manager.ensure_server("stub-model")
            mock_popen.assert_not_called()

        assert process_manager._server_port == 9999


# -- restart_server ----------------------------------------------------------


class TestRestartServer:
    """Tests for explicit restart."""

    def test_restart_stops_and_starts(self, stub_descriptor: ModelDescriptor) -> None:
        """Restart stops the current server then starts a new one."""

        old_proc = _inject_running_server(model="stub-model")

        new_proc = MagicMock(spec=subprocess.Popen)
        new_proc.pid = 99999

        with (
            patch.object(
                process_manager, "_find_llama_server", return_value="/bin/llama-server"
            ),
            patch.object(
                process_manager,
                "resolve_model_descriptor",
                return_value=stub_descriptor,
            ),
            patch.object(process_manager, "_pick_free_port", return_value=7777),
            patch("subprocess.Popen", return_value=new_proc),
            patch.object(process_manager, "poll_until_healthy"),
            patch("atexit.register"),
        ):
            process_manager.restart_server("stub-model", models_dir=Path("/tmp"))

        old_proc.terminate.assert_called_once()
        assert process_manager._server_process is new_proc
        assert process_manager._server_port == 7777

    def test_restart_from_cold(self, stub_descriptor: ModelDescriptor) -> None:
        """Restart works even when no server is currently running."""

        mock_proc = MagicMock(spec=subprocess.Popen)

        with (
            patch.object(
                process_manager, "_find_llama_server", return_value="/bin/llama-server"
            ),
            patch.object(
                process_manager,
                "resolve_model_descriptor",
                return_value=stub_descriptor,
            ),
            patch.object(process_manager, "_pick_free_port", return_value=6666),
            patch("subprocess.Popen", return_value=mock_proc),
            patch.object(process_manager, "poll_until_healthy"),
            patch("atexit.register"),
        ):
            process_manager.restart_server("stub-model", models_dir=Path("/tmp"))

        assert process_manager._server_process is mock_proc


# -- get_server_status -------------------------------------------------------


class TestGetServerStatus:
    """Tests for the runtime status snapshot."""

    def test_idle_status(self) -> None:
        """Returns idle status when no server is running."""

        status = process_manager.get_server_status()

        assert isinstance(status, RuntimeStatus)
        assert status.is_running is False
        assert status.is_healthy is False
        assert status.loaded_model is None
        assert status.server_pid is None
        assert status.server_port is None

    def test_running_healthy_status(self) -> None:
        """Returns full status when server is running and healthy."""

        _inject_running_server(model="stub-model", port=9999)

        with patch.object(process_manager, "check_health", return_value=True):
            status = process_manager.get_server_status()

        assert status.is_running is True
        assert status.is_healthy is True
        assert status.loaded_model == "stub-model"
        assert status.server_pid == 12345
        assert status.server_port == 9999

    def test_running_unhealthy_status(self) -> None:
        """Reports unhealthy when server is running but health check fails."""

        _inject_running_server(model="stub-model", port=9999)

        with patch.object(process_manager, "check_health", return_value=False):
            status = process_manager.get_server_status()

        assert status.is_running is True
        assert status.is_healthy is False

    def test_crashed_status(self) -> None:
        """Reports not running when the process has exited."""

        mock_proc = _inject_running_server(model="stub-model", port=9999)
        mock_proc.poll.return_value = 1

        status = process_manager.get_server_status()

        assert status.is_running is False
        assert status.is_healthy is False
        assert status.server_pid is None
        assert status.server_port is None
        # Model name preserved for debugging
        assert status.loaded_model == "stub-model"

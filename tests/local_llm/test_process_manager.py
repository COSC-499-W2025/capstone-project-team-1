"""Tests for the llama-server process lifecycle manager."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from artifactminer.local_llm.models import ModelDescriptor
from artifactminer.local_llm.runtime import process_manager
from artifactminer.local_llm.runtime.errors import (
    LlamaServerNotFoundError,
    LocalLLMRuntimeError,
    ModelServerCrashedError,
    ModelStartupTimeoutError,
)


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


# -- _find_llama_server -------------------------------------------------------


class TestFindLlamaServer:
    """Tests for binary discovery."""

    def test_returns_path_when_found(self) -> None:
        """shutil.which hit returns the resolved path."""

        with patch("shutil.which", return_value="/usr/local/bin/llama-server"):
            assert process_manager._find_llama_server() == "/usr/local/bin/llama-server"

    def test_raises_when_missing(self) -> None:
        """shutil.which miss raises LlamaServerNotFoundError."""

        with patch("shutil.which", return_value=None):
            with pytest.raises(LlamaServerNotFoundError):
                process_manager._find_llama_server()


# -- _pick_free_port ----------------------------------------------------------


def test_pick_free_port_binds_to_loopback() -> None:
    """Returned port is a positive integer from a loopback bind."""

    port = process_manager._pick_free_port()
    assert isinstance(port, int)
    assert port > 0


# -- start_server --------------------------------------------------------------


class TestStartServer:
    """Tests for the start_server public function."""

    def test_spawns_and_polls_health(self, stub_descriptor: ModelDescriptor) -> None:
        """Happy path: spawns process, polls health, sets module state."""

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
            patch("subprocess.Popen", return_value=mock_proc) as mock_popen,
            patch.object(process_manager, "poll_until_healthy") as mock_poll,
            patch("atexit.register") as mock_atexit,
        ):
            process_manager.start_server(
                "stub-model", models_dir=Path("/tmp"), timeout=10.0
            )

            mock_popen.assert_called_once()
            cmd = mock_popen.call_args[0][0]
            assert cmd[0] == "/bin/llama-server"
            assert "--model" in cmd
            assert str(stub_descriptor.path) in cmd
            host_idx = cmd.index("--host")
            assert cmd[host_idx + 1] == "127.0.0.1"

            mock_poll.assert_called_once_with(9999, "stub-model", timeout=10.0)
            mock_atexit.assert_called_once_with(process_manager.stop_server)

            assert process_manager._server_process is mock_proc
            assert process_manager._server_port == 9999
            assert process_manager._server_model == "stub-model"

    def test_uses_defaults(self, stub_descriptor: ModelDescriptor) -> None:
        """Calling with no arguments uses the default model and timeout."""

        mock_proc = MagicMock(spec=subprocess.Popen)

        with (
            patch.object(
                process_manager, "_find_llama_server", return_value="/bin/llama-server"
            ),
            patch.object(
                process_manager,
                "resolve_model_descriptor",
                return_value=stub_descriptor,
            ) as mock_resolve,
            patch.object(process_manager, "_pick_free_port", return_value=8888),
            patch("subprocess.Popen", return_value=mock_proc),
            patch.object(process_manager, "poll_until_healthy"),
            patch("atexit.register"),
        ):
            process_manager.start_server()

            mock_resolve.assert_called_once_with(
                process_manager.DEFAULT_MODEL_NAME,
                process_manager.DEFAULT_MODELS_DIR,
            )

    def test_command_includes_gpu_and_context(
        self, stub_descriptor: ModelDescriptor
    ) -> None:
        """Spawned command includes --n-gpu-layers and --ctx-size flags."""

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
            patch.object(process_manager, "_pick_free_port", return_value=7777),
            patch("subprocess.Popen", return_value=mock_proc) as mock_popen,
            patch.object(process_manager, "poll_until_healthy"),
            patch("atexit.register"),
        ):
            process_manager.start_server("stub-model", models_dir=Path("/tmp"))

            cmd = mock_popen.call_args[0][0]
            assert "--n-gpu-layers" in cmd
            assert "--ctx-size" in cmd
            assert str(stub_descriptor.context_window) in cmd

    def test_raises_when_already_running(self) -> None:
        """Starting while a process exists raises LocalLLMRuntimeError."""

        process_manager._server_process = MagicMock(spec=subprocess.Popen)

        with patch("subprocess.Popen") as mock_popen:
            with pytest.raises(LocalLLMRuntimeError, match="already running"):
                process_manager.start_server()
            mock_popen.assert_not_called()

    def test_propagates_timeout_when_process_alive(
        self, stub_descriptor: ModelDescriptor
    ) -> None:
        """Timeout re-raised when the server process is still running."""

        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.poll.return_value = None  # still alive

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
            patch.object(
                process_manager,
                "poll_until_healthy",
                side_effect=ModelStartupTimeoutError("stub-model", 10.0),
            ),
            patch("atexit.register"),
        ):
            with pytest.raises(ModelStartupTimeoutError):
                process_manager.start_server(
                    "stub-model", models_dir=Path("/tmp"), timeout=10.0
                )

            assert process_manager._server_process is None
            assert process_manager._server_port is None
            assert process_manager._server_model is None

    def test_raises_crashed_when_process_exits(
        self, stub_descriptor: ModelDescriptor
    ) -> None:
        """Crashed error raised when the process has already exited."""

        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.poll.return_value = 1
        mock_proc.returncode = 1

        with (
            patch.object(
                process_manager, "_find_llama_server", return_value="/bin/llama-server"
            ),
            patch.object(
                process_manager,
                "resolve_model_descriptor",
                return_value=stub_descriptor,
            ),
            patch.object(process_manager, "_pick_free_port", return_value=5555),
            patch("subprocess.Popen", return_value=mock_proc),
            patch.object(
                process_manager,
                "poll_until_healthy",
                side_effect=ModelStartupTimeoutError("stub-model", 10.0),
            ),
            patch("atexit.register"),
        ):
            with pytest.raises(ModelServerCrashedError):
                process_manager.start_server(
                    "stub-model", models_dir=Path("/tmp"), timeout=10.0
                )

            assert process_manager._server_process is None

    def test_state_is_none_after_failed_start(self) -> None:
        """Any start failure leaves all globals as None."""

        with patch.object(
            process_manager,
            "_find_llama_server",
            side_effect=LlamaServerNotFoundError(),
        ):
            with pytest.raises(LlamaServerNotFoundError):
                process_manager.start_server()

        assert process_manager._server_process is None
        assert process_manager._server_port is None
        assert process_manager._server_model is None


# -- stop_server ---------------------------------------------------------------


class TestStopServer:
    """Tests for the stop_server public function."""

    def test_terminates_and_waits(self) -> None:
        """Graceful stop: terminate then wait."""

        mock_proc = MagicMock(spec=subprocess.Popen)
        process_manager._server_process = mock_proc
        process_manager._server_port = 9999
        process_manager._server_model = "stub-model"

        process_manager.stop_server()

        mock_proc.terminate.assert_called_once()
        mock_proc.wait.assert_called_once_with(
            timeout=process_manager._TERMINATE_TIMEOUT_SECONDS
        )
        assert process_manager._server_process is None
        assert process_manager._server_port is None
        assert process_manager._server_model is None

    def test_kills_on_timeout(self) -> None:
        """Forced kill when terminate wait times out."""

        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.wait.side_effect = [
            subprocess.TimeoutExpired("llama-server", 5),
            None,
        ]
        process_manager._server_process = mock_proc
        process_manager._server_port = 9999
        process_manager._server_model = "stub-model"

        process_manager.stop_server()

        mock_proc.terminate.assert_called_once()
        mock_proc.kill.assert_called_once()
        assert process_manager._server_process is None

    def test_noop_when_not_running(self) -> None:
        """No error and no method calls when nothing is running."""

        process_manager.stop_server()

        assert process_manager._server_process is None

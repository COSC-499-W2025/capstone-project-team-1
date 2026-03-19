"""Manage the codex app-server subprocess (stdio transport)."""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
from enum import Enum

log = logging.getLogger(__name__)


class ProcessState(str, Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    ERROR = "error"


class TurnResult:
    """Accumulates streamed output for a single turn."""

    def __init__(self) -> None:
        self.text: str = ""
        self.status: str = "inProgress"
        self.error: str | None = None
        self._done: asyncio.Event = asyncio.Event()

    def append_delta(self, delta: str) -> None:
        self.text += delta

    def complete(self, status: str, error: str | None = None) -> None:
        self.status = status
        self.error = error
        self._done.set()

    async def wait(self) -> None:
        await self._done.wait()


class CodexProcess:
    """Lifecycle wrapper around `codex app-server` over stdio."""

    def __init__(self) -> None:
        self._proc: asyncio.subprocess.Process | None = None
        self._state: ProcessState = ProcessState.STOPPED
        self._error: str | None = None
        self._request_id: int = 0
        self._pending: dict[int, asyncio.Future[dict]] = {}
        self._reader_task: asyncio.Task | None = None
        # track active turns: turn_id -> TurnResult
        self._turns: dict[str, TurnResult] = {}
        # login flow synchronization
        self._login_event: asyncio.Event = asyncio.Event()
        self._login_result: dict = {}

    # -- public properties ---------------------------------------------------

    @property
    def state(self) -> ProcessState:
        return self._state

    @property
    def error(self) -> str | None:
        return self._error

    # -- lifecycle ------------------------------------------------------------

    async def start(self) -> None:
        if self._state == ProcessState.RUNNING:
            return

        codex_bin = shutil.which("codex")
        if codex_bin is None:
            self._state = ProcessState.ERROR
            self._error = "codex binary not found on PATH"
            raise FileNotFoundError(self._error)

        self._state = ProcessState.STARTING
        self._error = None

        # Spawn codex app-server with stdio transport.
        # codex_bin is resolved via shutil.which (not user input),
        # and "app-server" is a fixed argument — no injection risk.
        self._proc = await asyncio.create_subprocess_exec(
            codex_bin,
            "app-server",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        self._reader_task = asyncio.create_task(self._read_loop())

        # Handshake: send initialize request
        resp = await self.send_request(
            "initialize",
            {
                "clientInfo": {"name": "codex-server", "version": "0.1.0"},
            },
        )
        log.info("initialize response: %s", resp)

        # Send initialized notification (no response expected)
        await self._send_notification("initialized")

        self._state = ProcessState.RUNNING

    async def stop(self) -> None:
        if self._proc is None:
            self._state = ProcessState.STOPPED
            return

        if self._reader_task and not self._reader_task.done():
            self._reader_task.cancel()

        self._proc.terminate()
        try:
            await asyncio.wait_for(self._proc.wait(), timeout=5)
        except asyncio.TimeoutError:
            self._proc.kill()
            await self._proc.wait()

        self._proc = None
        self._state = ProcessState.STOPPED
        self._pending.clear()

    # -- authentication -------------------------------------------------------

    async def read_account(self) -> dict:
        """Return the current account state from Codex."""
        resp = await self.send_request("account/read", {})
        return resp.get("result", {})

    async def login_chatgpt(self) -> dict:
        """Start the ChatGPT OAuth login flow managed by Codex.

        Codex opens a browser for the user to authenticate. The response
        returns immediately with a login ID; completion arrives via the
        account/login/completed notification.
        """
        self._login_event = asyncio.Event()
        self._login_result: dict = {}
        resp = await self.send_request(
            "account/login/start",
            {"type": "chatgpt"},
        )
        result = resp.get("result", {})
        log.info("login/start response: %s", result)

        # Wait for the account/login/completed notification
        await self._login_event.wait()
        return self._login_result

    async def logout(self) -> dict:
        """Log out of the current Codex account."""
        resp = await self.send_request("account/logout", {})
        return resp.get("result", {})

    # -- high-level thread / turn API -----------------------------------------

    async def start_thread(self, instructions: str | None = None) -> str:
        """Create a new conversation thread. Returns the thread ID."""
        params: dict = {"approvalPolicy": "never"}
        if instructions:
            params["baseInstructions"] = instructions
        resp = await self.send_request("thread/start", params)
        thread = resp["result"]["thread"]
        thread_id: str = thread["id"]
        log.info("thread started: %s", thread_id)
        return thread_id

    async def send_turn(self, thread_id: str, message: str) -> TurnResult:
        """Send a user message and wait for the full agent response."""
        resp = await self.send_request(
            "turn/start",
            {
                "threadId": thread_id,
                "input": [{"type": "text", "text": message}],
            },
        )
        turn = resp["result"]["turn"]
        turn_id: str = turn["id"]

        result = TurnResult()
        self._turns[turn_id] = result

        # Wait for turn/completed notification
        await result.wait()

        # Clean up
        self._turns.pop(turn_id, None)
        return result

    # -- JSON-RPC communication -----------------------------------------------

    async def send_request(self, method: str, params: dict | None = None) -> dict:
        """Send a JSON-RPC request and wait for the response."""
        self._request_id += 1
        req_id = self._request_id

        msg: dict = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
        }
        if params is not None:
            msg["params"] = params

        future: asyncio.Future[dict] = asyncio.get_event_loop().create_future()
        self._pending[req_id] = future

        await self._write(msg)
        return await future

    async def _send_notification(self, method: str, params: dict | None = None) -> None:
        """Send a JSON-RPC notification (no response expected)."""
        msg: dict = {
            "jsonrpc": "2.0",
            "method": method,
        }
        if params is not None:
            msg["params"] = params
        await self._write(msg)

    async def _write(self, msg: dict) -> None:
        assert self._proc and self._proc.stdin
        line = json.dumps(msg) + "\n"
        self._proc.stdin.write(line.encode())
        await self._proc.stdin.drain()
        log.debug("-> %s", line.rstrip())

    async def _read_loop(self) -> None:
        """Read newline-delimited JSON from stdout and dispatch."""
        assert self._proc and self._proc.stdout
        try:
            while True:
                raw = await self._proc.stdout.readline()
                if not raw:
                    break
                line = raw.decode().strip()
                if not line:
                    continue
                log.debug("<- %s", line)
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    log.warning("non-JSON from codex: %s", line)
                    continue
                self._dispatch(msg)
        except asyncio.CancelledError:
            return
        except Exception:
            log.exception("reader loop crashed")
            self._state = ProcessState.ERROR

    def _dispatch(self, msg: dict) -> None:
        """Route a parsed JSON-RPC message."""
        # Response to a request we sent
        if "id" in msg and ("result" in msg or "error" in msg):
            req_id = msg["id"]
            future = self._pending.pop(req_id, None)
            if future and not future.done():
                future.set_result(msg)
            return

        # Server notification
        method = msg.get("method", "")
        params = msg.get("params", {})

        if method == "item/agentMessage/delta":
            turn_id = params.get("turnId", "")
            turn_result = self._turns.get(turn_id)
            if turn_result:
                turn_result.append_delta(params.get("delta", ""))

        elif method == "account/login/completed":
            self._login_result = params
            self._login_event.set()

        elif method == "turn/completed":
            turn = params.get("turn", {})
            turn_id = turn.get("id", "")
            turn_result = self._turns.get(turn_id)
            if turn_result:
                status = turn.get("status", "completed")
                error = None
                if turn.get("error"):
                    error = turn["error"].get("message", "unknown error")
                turn_result.complete(status, error)

        else:
            log.debug("notification: %s", method)

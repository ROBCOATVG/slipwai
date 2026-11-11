# Written by scripts/shared-modules.py from src/slipwai/acp.py. Do not edit: edit the keel's module,
# run `make shared`, and commit both. A generated project has no slipwai to import, and both runtimes need
# this one — so there is one source and this copy, and `make check-shared` refuses a copy that has drifted.
"""The Agent Client Protocol's client half: one session of whichever coding agent a person has.

The protocol (agentclientprotocol.com, wire version 1) is JSON-RPC 2.0 over an agent's stdin and stdout, one
object per line, the agent a subprocess of the client. This is the client, and only as much of it as the
board needs: spawn, `initialize`, `session/new` or `session/load`, `session/prompt`, `session/cancel`, one
config option set, and the two things an agent asks a client for — permission before a tool call, and an
answer to a question. It offers the agent no file system and no terminal: the agent's own tools write the
folder, and the permission request is where the board holds the line. Read from the v1 schema and the
prompt-turn and tool-call pages on 2026-11-05; `docs/acp-plan.md` section 2 is the same reading in prose.

Written with the standard library on purpose: the keel ships with no dependencies, and the half it needs is
small. The protocol's own Python SDK is what this is checked against, not what it imports.

Errors are values where the agent is concerned and `Fault` where the session is: an agent that exits, a line
that is not JSON, a response carrying `error`, a call that outlives its ceiling, each a `Fault` with the
agent's stderr tail, raised to the caller of the one call it broke and nothing else. A reader thread never
raises past itself.
"""
from __future__ import annotations

import contextlib
import itertools
import json
import subprocess
import threading
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

#: The wire version this client speaks. The agent answers with the one it speaks; a mismatch is a `Fault`.
PROTOCOL = 1
#: How long one call waits for its answer before the session is given up on. A prompt turn can run as long
#: as a drawing takes; the caller passes its own ceiling for that one.
TIMEOUT = 60.0
#: The handshake's ceiling for an agent launched as a package: `npx` fetches it the first time, and a cold
#: fetch on a slow line is minutes, not seconds. The settings page's "make ready" step is the better answer;
#: this is the floor under it.
FETCHING = 300.0
#: The one kind of permission option the policy picks without asking: this call, this once.
ALLOW_ONCE = "allow_once"
#: Where a session keeps its id and the agent's stderr, under the working directory it was given.
KEPT = ".acp"
#: How an agent's pipes are read and written: UTF-8, which is what every agent speaks. Left to the platform,
#: Windows reads them as cp1252, where five bytes mean nothing: the first `❌` or `”` in a file the agent
#: read ended the reader, and the page showed a session stopped that was still running.
AGENT_TEXT: dict[str, Any] = {"encoding": "utf-8", "errors": "replace"}

Update = dict[str, Any]
OnUpdate = Callable[[Update], None]
#: Given the tool call and the agent's options, the option id to select, or `None` to answer `cancelled`.
OnPermission = Callable[[dict[str, Any], list[dict[str, Any]]], "str | None"]
#: Given the question's params, the action (`accept`, `decline`, `cancel`) and the content for an accept.
OnQuestion = Callable[[dict[str, Any]], "tuple[str, dict[str, Any] | None]"]


class Fault(RuntimeError):
    """The session cannot go on: the agent is gone, or answered with an error, or did not answer in time.
    `code` is the error's own, where the agent gave one: `SIGNED_OUT` is the protocol's for nobody signed in."""

    code = 0


SIGNED_OUT = -32000  # the protocol's error code for a request refused because nobody is signed in
#: Said at `initialize`: this client can have a terminal sign-in run. An agent told nothing offers none, which
#: for one with no other is no way to sign in. The `_meta` spelling has the agent name the whole command.
TERMINAL_SIGN_IN: dict[str, Any] = {"auth": {"terminal": True}, "_meta": {"terminal-auth": True}}


@dataclass
class Agent:
    """What the agent said about itself at `initialize`, and what the session offered when it began."""

    name: str = ""
    version: str = ""
    load_session: bool = False
    auth_methods: list[dict[str, Any]] = field(default_factory=list)
    config_options: list[dict[str, Any]] = field(default_factory=list)
    modes: dict[str, Any] | None = None


def within(cwd: Path, tool_call: dict[str, Any]) -> bool:
    """Whether every location a tool call names is under the working directory. A call that names none is
    not within it: the policy allows a write it can place, and asks about one it cannot."""
    locations = tool_call.get("locations") or []
    if not locations:
        return False
    root = cwd.resolve()
    for one in locations:
        path = Path(str(one.get("path") or "")).expanduser()
        try:
            path.resolve().relative_to(root)
        except ValueError:
            return False
    return True


def once(options: list[dict[str, Any]]) -> str | None:
    """The id of the agent's `allow_once` option, or `None` where it offered no such kind."""
    return next((str(one["optionId"]) for one in options if one.get("kind") == ALLOW_ONCE and "optionId" in one), None)


def policy(cwd: Path, ask: OnPermission) -> OnPermission:
    """The board's permission policy: a call within the working directory is allowed this once without a
    word; anything else, and any call the agent offers no `allow_once` for, goes to `ask`."""
    def decide(tool_call: dict[str, Any], options: list[dict[str, Any]]) -> str | None:
        allowed = once(options)
        if allowed is not None and within(cwd, tool_call):
            return allowed
        return ask(tool_call, options)
    return decide


class Session:
    """One session of one agent, from spawn to close. Calls are made from the board's threads; the agent's
    lines are read on one of this session's own, and its requests answered on another, so a question that
    waits on a person does not stop the reader."""

    def __init__(self, argv: Sequence[str], cwd: Path, on_update: OnUpdate, on_permission: OnPermission,
                 on_question: OnQuestion, env: dict[str, str] | None = None, kept: Path | None = None) -> None:
        self.argv, self.cwd, self.env = list(argv), Path(cwd), env
        self.kept = Path(kept) if kept is not None else self.cwd / KEPT  # the session's id and the agent's stderr
        self.on_update, self.on_permission, self.on_question = on_update, on_permission, on_question
        self.agent = Agent()
        self.session_id = ""
        self.child: subprocess.Popen[str] | None = None
        self.ids = itertools.count(1)
        self.waiting: dict[int, tuple[threading.Event, dict[str, Any]]] = {}
        self.open: dict[Any, str] = {}  # the agent's own requests not yet answered, by id, with their method
        self.lock = threading.Lock()  # over `waiting`, `open` and the write side of the pipe
        self.busy = False
        self.exited: int | None = None
        self.log = self.kept / "agent.log"
        self.errors: Any = None  # the log, open while the agent runs

    # -- the pipe ---------------------------------------------------------------------------------------

    def start(self, handshake: float | None = None) -> Agent:
        """Spawn the agent and shake hands. The agent's stderr goes to a log beside the session's id. A
        launch over `npx` is given `FETCHING` for its handshake, since the first one fetches the package."""
        waits = handshake if handshake is not None else (FETCHING if Path(self.argv[0]).name == "npx" else TIMEOUT)
        self.log.parent.mkdir(parents=True, exist_ok=True)
        self.errors = self.log.open("a", encoding="utf-8")
        try:
            self.child = subprocess.Popen(self.argv, cwd=self.cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                          stderr=self.errors, text=True, bufsize=1, env=self.env,
                                          start_new_session=True, **AGENT_TEXT)
        except OSError as fault:
            self.errors.close()
            raise Fault(f"the agent could not be started: {fault}") from fault
        threading.Thread(target=self.read, daemon=True).start()
        said = self.call("initialize", {"protocolVersion": PROTOCOL, "clientInfo": {"name": "slipwai", "version": "2"},
                                        "clientCapabilities": {"fs": {"readTextFile": False, "writeTextFile": False},
                                                               "terminal": False, **TERMINAL_SIGN_IN}}, waits)
        if said.get("protocolVersion") != PROTOCOL:
            raise Fault(f"the agent speaks protocol version {said.get('protocolVersion')!r}, not {PROTOCOL}")
        able = said.get("agentCapabilities") or {}
        info = said.get("agentInfo") or {}
        self.agent = Agent(name=str(info.get("name") or self.argv[0]), version=str(info.get("version") or ""),
                           load_session=bool(able.get("loadSession")), auth_methods=list(said.get("authMethods") or []))
        return self.agent

    def authenticate(self, method_id: str) -> dict[str, Any]:
        """Sign in by one of the methods the agent offered at `initialize`. An agent-type method is the
        agent's own doing — a browser it opens, a token it keeps — and this waits on it; a `Fault` where
        it refused or did not finish within the fetching ceiling."""
        return self.call("authenticate", {"methodId": method_id}, FETCHING)

    def write(self, message: dict[str, Any]) -> None:
        child = self.child
        if child is None or child.stdin is None or self.exited is not None:
            raise Fault(self.gone())
        line = json.dumps({"jsonrpc": "2.0", **message}, separators=(",", ":"))
        with self.lock:
            try:
                child.stdin.write(line + "\n")
                child.stdin.flush()
            except (OSError, ValueError) as fault:
                raise Fault(self.gone()) from fault

    def call(self, method: str, params: dict[str, Any], timeout: float = TIMEOUT) -> dict[str, Any]:
        """One request, and its result; a `Fault` where the answer is an error, late, or never coming."""
        number = next(self.ids)
        done, box = threading.Event(), {}  # type: threading.Event, dict[str, Any]
        with self.lock:
            self.waiting[number] = (done, box)
        try:
            self.write({"id": number, "method": method, "params": params})
            if not done.wait(timeout):
                raise Fault(f"the agent did not answer {method} within {timeout:.0f}s")
        finally:
            with self.lock:
                self.waiting.pop(number, None)
        if "error" in box:
            error = box["error"] or {}
            fault = Fault(f"the agent refused {method}: {error.get('message') or error}")
            code = error.get("code") if isinstance(error, dict) else None
            fault.code = code if isinstance(code, int) else 0
            raise fault
        if "gone" in box:
            raise Fault(self.gone())
        return dict(box.get("result") or {})

    def notify(self, method: str, params: dict[str, Any]) -> None:
        self.write({"method": method, "params": params})

    def reply(self, number: Any, result: dict[str, Any] | None = None, error: dict[str, Any] | None = None) -> None:
        with self.lock:
            if self.open.pop(number, None) is None:
                return  # already answered — a cancel got there first
        with contextlib.suppress(Fault):  # the agent left before its question was answered; the reader says so
            self.write({"id": number, "result": result} if error is None else {"id": number, "error": error})

    def read(self) -> None:
        """Every line the agent writes, routed: an answer to its waiter, an update to the page, a request to
        a thread of its own. Ends by waking every waiter with `gone`."""
        child = self.child
        try:
            for line in child.stdout if child is not None and child.stdout is not None else []:
                try:
                    message = json.loads(line)
                except ValueError:
                    continue  # a banner or a warning on stdout: not the protocol
                if not isinstance(message, dict):
                    continue
                if "method" not in message and "id" in message:
                    with self.lock:
                        waiter = self.waiting.get(message["id"])
                    if waiter is not None:
                        waiter[1].update({k: message[k] for k in ("result", "error") if k in message})
                        waiter[0].set()
                elif "id" in message:
                    with self.lock:
                        self.open[message["id"]] = str(message.get("method"))
                    threading.Thread(target=self.serve, args=(message,), daemon=True).start()
                elif message.get("method") == "session/update":
                    self.on_update(dict((message.get("params") or {}).get("update") or {}))
        finally:
            if child is not None:
                child.wait()
                self.exited = child.returncode
                for pipe in (child.stdin, child.stdout):  # the agent is gone: nothing more to say or read
                    with contextlib.suppress(OSError, ValueError):
                        if pipe is not None:
                            pipe.close()
            self.errors.close()
            with self.lock:
                waiters = list(self.waiting.values())
            for done, box in waiters:
                box["gone"] = True
                done.set()

    def serve(self, message: dict[str, Any]) -> None:
        """One request from the agent: a permission, a question, or something this client does not offer."""
        number, method, params = message.get("id"), str(message.get("method")), dict(message.get("params") or {})
        try:
            if method == "session/request_permission":
                chosen = self.on_permission(dict(params.get("toolCall") or {}), list(params.get("options") or []))
                outcome = {"outcome": "cancelled"} if chosen is None else {"outcome": "selected", "optionId": chosen}
                self.reply(number, {"outcome": outcome})
            elif method == "elicitation/create":
                action, content = self.on_question(params)
                self.reply(number, {"action": action, "content": content} if action == "accept" else {"action": action})
            else:
                self.reply(number, error={"code": -32601, "message": f"{method} is not offered by this client"})
        except Exception as fault:  # noqa: BLE001 — a callback's fault must not leave the agent waiting
            self.reply(number, error={"code": -32603, "message": str(fault)})

    def gone(self) -> str:
        tail = ""
        with contextlib.suppress(OSError):
            tail = "".join(self.log.read_text(encoding="utf-8").splitlines(keepends=True)[-5:]).strip()
        status = f"exited {self.exited}" if self.exited is not None else "is not running"
        return f"the agent {status}" + (f"; the last it said: {tail}" if tail else "")

    # -- the session ------------------------------------------------------------------------------------

    def new(self) -> str:
        """A new session in the working directory, with no MCP servers. The id is kept beside the log."""
        said = self.call("session/new", {"cwd": str(self.cwd.resolve()), "mcpServers": []})
        self.began(said)
        return self.session_id

    def load(self, session_id: str) -> bool:
        """The session with this id, where the agent can load one: it replays the history as updates before
        answering. False, and nothing sent, where it cannot."""
        if not self.agent.load_session:
            return False
        said = self.call("session/load", {"sessionId": session_id, "cwd": str(self.cwd.resolve()), "mcpServers": []})
        self.began({**said, "sessionId": session_id})
        return True

    def began(self, said: dict[str, Any]) -> None:
        self.session_id = str(said.get("sessionId") or "")
        self.agent.config_options = list(said.get("configOptions") or [])
        self.agent.modes = said.get("modes")
        (self.kept / "session").write_text(self.session_id + "\n", encoding="utf-8")

    def prompt(self, text: str, timeout: float = TIMEOUT) -> str:
        """One turn: the text as the prompt, the stop reason when the agent is done. Updates arrive on
        `on_update` as it works. One at a time: a second while one runs is a refusal, not a queue."""
        with self.lock:
            if self.busy:
                raise ValueError("the agent is still answering")
            self.busy = True
        try:
            said = self.call("session/prompt", {"sessionId": self.session_id,
                                                "prompt": [{"type": "text", "text": text}]}, timeout)
            return str(said.get("stopReason") or "end_turn")
        finally:
            with self.lock:
                self.busy = False

    def cancel(self) -> None:
        """Stop the turn under way. The agent is told, and every permission it is waiting on is answered
        `cancelled`, as the protocol requires; the prompt then returns `cancelled`."""
        with self.lock:
            asked = [number for number, method in self.open.items() if method == "session/request_permission"]
        try:
            self.notify("session/cancel", {"sessionId": self.session_id})
        except Fault:
            return
        for number in asked:
            self.reply(number, {"outcome": {"outcome": "cancelled"}})

    def set_option(self, option_id: str, value: Any) -> list[dict[str, Any]]:
        """One of the config options the agent offered — a model among them — set to one of its values."""
        said = self.call("session/set_config_option",
                         {"sessionId": self.session_id, "configId": option_id, "value": value})
        self.agent.config_options = list(said.get("configOptions") or self.agent.config_options)
        return self.agent.config_options

    def close(self) -> None:
        child = self.child
        if child is None or self.exited is not None:
            return
        try:
            if child.stdin is not None:
                child.stdin.close()
            child.wait(timeout=5)
        except (OSError, ValueError, subprocess.TimeoutExpired):
            child.kill()


def kept_session(kept: Path) -> str:
    """The id of the session last begun with this folder as its keep, or `''`."""
    try:
        return (Path(kept) / "session").read_text(encoding="utf-8").strip()
    except OSError:
        return ""

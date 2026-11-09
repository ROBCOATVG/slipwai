#!/usr/bin/env python3
"""A stage's session over the Agent Client Protocol, with a process's face, for the captain and the skipper.

The captain watches a `/sail` session the way it watches any child: `poll`, `returncode`, `wait`, and an
`end` that reaches everything the session started. A session over the protocol (`acp.py`, the client carried
from the keel) is a thread here that spawns the agent, opens a session in the berth, sets the model where the
agent offers it, asks the one prompt and reads the stop reason — and shows that face to the watch, so the
deck log stays the only thing the captain believes. The agent's words and tool calls are printed a line at a
time, as the stream-json session's lines were, into the stream the fleet keeps.

Nobody is in the berth: a permission for a write inside it is allowed this once, one outside it is refused
with a line saying so, and a question is declined — a stage that must ask a person parks on a `question`
line in the deck log, as it did. The stop is the protocol's cancel, then the agent's own end.

Opt-in, per project: `sessions: protocol` in `.specify/cruise.json`, which the board's *Who answers* card
sets, or `SLIPWAI_ACP` in the environment — `1` takes the initialised harness's launch row where this
machine can make it, any other value is the command that starts an agent (the suite's stand-in; a harness
the registry does not know). Neither set, every drive runs in the harness's print mode as it did.
"""
from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import harness  # noqa: E402

VARIABLE = "SLIPWAI_ACP"
ON = ("1", "true", "yes", "on")
#: The project's own switch, set from the board: `sessions: protocol` in `.specify/cruise.json`.
CONFIG = ".specify/cruise.json"


def switched_on() -> bool:
    """Whether this project asked for its captains' sessions over the protocol, on the board or by
    `/cruise-settings`; the variable, where set, still says first. Read under the project the harness
    module names now, which the suite points elsewhere."""
    try:
        return json.loads((harness.ROOT / CONFIG).read_text(encoding="utf-8")).get("sessions") == "protocol"
    except (OSError, ValueError, AttributeError):
        return False
#: A turn's ceiling, nominal: the captain's watch on the deck log is what ends a drive that stopped writing.
TURN = 7 * 24 * 3600.0


def acp_launch(row: dict[str, Any] | None) -> list[str]:
    """The argv that starts this harness as an agent on this machine, or nothing where the registry records
    no launch row for it or the machine lacks what the row needs (`npx`, or the binary on PATH)."""
    launch = row.get("acp") if isinstance(row, dict) else None
    if not isinstance(launch, dict):
        return []
    npx, binary = launch.get("npx"), launch.get("binary")
    if isinstance(npx, dict):
        found = shutil.which("npx")
        return [found, "--yes", str(npx["package"]), *[str(a) for a in npx.get("args") or []]] if found else []
    if isinstance(binary, dict):
        found = shutil.which(str(binary.get("cmd") or ""))
        return [found, *[str(a) for a in binary.get("args") or []]] if found else []
    return []


def acp_environment(row: dict[str, Any] | None) -> dict[str, str]:
    """What the launch row says to set in the agent's environment, if anything."""
    launch = row.get("acp") if isinstance(row, dict) else None
    npx = launch.get("npx") if isinstance(launch, dict) else None
    return {str(k): str(v) for k, v in ((npx or {}).get("env") or {}).items()} if isinstance(npx, dict) else {}


def protocol() -> tuple[list[str], dict[str, Any] | None, str] | None:
    """Where this run takes the protocol: (the launch, the harness row or `None` for a named command, what was
    chosen) — or `None` where `SLIPWAI_ACP` is unset and every session runs headless as it did."""
    named = os.environ.get(VARIABLE, "").strip()
    if not named and switched_on():
        named = "1"
    if not named:
        return None
    if named.lower() not in ON:
        # A Windows path is backslashes, which POSIX splitting reads as escapes and drops: kept as written.
        words = shlex.split(named.replace("\\", "\\\\") if os.name == "nt" else named)
        return words, None, f"{VARIABLE}: {named}, over the Agent Client Protocol"
    rows = harness.registry()
    for key in harness.installed_keys():
        argv = acp_launch(rows.get(key))
        if argv:
            return argv, rows[key], f"agent: {rows[key]['name']}, over the Agent Client Protocol"
    raise harness.NoHarness(f"sessions over the protocol were asked for ({VARIABLE}, or `sessions: protocol` in "
                            f".specify/cruise.json), and no initialised harness has a launch row this machine can "
                            f"make (scripts/agents/registry.json, `acp`)")


def say(line: str, err: bool = False) -> None:
    print(line, file=sys.stderr if err else sys.stdout, flush=True)


class Drive:
    """One stage over the protocol, started on its own thread, watched like a process."""

    def __init__(self, argv: list[str], cwd: Path | str, env: dict[str, str], prompt: str,
                 model: str | None = None, kept: Path | None = None) -> None:
        import acp  # noqa: PLC0415 — carried beside this; imported here so a project without it fails at the drive, not the captain
        self.cwd, self.words, self.model = Path(cwd), prompt, model
        self.session = acp.Session(argv, self.cwd, self.update, acp.policy(self.cwd, self.refuse), self.decline,
                                   env=env, kept=Path(kept) if kept is not None else self.cwd / ".slipwai" / "acp")
        self.held = ""  # the message chunk not yet ended by a newline
        self.text = ""  # everything the agent said this turn, for a refusal's words
        self.code: int | None = None
        self.refusal: harness.Refusal | None = None
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    # -- a process's face --------------------------------------------------------------------------------

    @property
    def pid(self) -> int:
        child = self.session.child
        return child.pid if child is not None else 0

    @property
    def returncode(self) -> int | None:
        return self.code

    def poll(self) -> int | None:
        return self.code

    def wait(self, timeout: float | None = None) -> int | None:
        self.thread.join(timeout)
        if self.thread.is_alive():
            raise subprocess.TimeoutExpired(self.session.argv, timeout or 0)
        return self.code

    def terminate(self) -> None:
        self.session.cancel()

    def kill(self) -> None:
        self.session.close()

    def end(self) -> None:
        """The stop: the turn cancelled, then the agent closed where it did not end on that."""
        self.terminate()
        try:
            self.wait(30)
        except subprocess.TimeoutExpired:
            self.kill()
            self.wait()

    # -- the session -------------------------------------------------------------------------------------

    def run(self) -> None:
        try:
            self.session.start()
            self.session.new()
            self.pick()
            stop = self.session.prompt(self.words, TURN)
            self.flush()
            say(f"session: the agent ended its turn: {stop}")
            if stop == "refusal":
                self.refusal = harness.refusal(self.text[-2000:])
            self.code = 0 if stop == "end_turn" else 1
        except Exception as fault:  # noqa: BLE001 — a drive that raised would leave the captain polling for ever
            self.flush()
            say(f"session: {fault}", err=True)
            self.refusal = harness.refusal(str(fault))
            self.code = 1
        finally:
            self.session.close()
            if self.code is None:
                self.code = 1

    def pick(self) -> None:
        """The model `cruise.json` names, set where the agent offers it as a config option; the agent's own
        default otherwise, and said."""
        if not self.model:
            return
        for option in self.session.agent.config_options:
            if option.get("category") != "model":
                continue
            for value in option.get("options") or []:
                if self.model in (value.get("value"), value.get("name")):
                    self.session.set_option(str(option.get("id")), value.get("value"))
                    say(f"session: model {self.model}")
                    return
        say(f"session: the agent offers no model named {self.model}; its own default runs")

    def update(self, update: dict[str, Any]) -> None:
        kind = update.get("sessionUpdate")
        if kind == "agent_message_chunk":
            content = update.get("content") or {}
            if content.get("type") == "text":
                chunk = str(content.get("text") or "")
                self.held += chunk
                self.text += chunk
                while "\n" in self.held:
                    line, self.held = self.held.split("\n", 1)
                    say(line)
        elif kind == "tool_call":
            self.flush()
            say(f"· {update.get('title') or update.get('kind') or 'tool'}")

    def flush(self) -> None:
        if self.held.strip():
            say(self.held)
        self.held = ""

    def refuse(self, tool_call: dict[str, Any], options: list[dict[str, Any]]) -> str | None:
        say(f"session: refused {tool_call.get('title') or 'a tool call'} — outside the berth, and nobody is here "
            f"to allow it")
        return next((str(one["optionId"]) for one in options if one.get("kind") == "reject_once" and "optionId" in one),
                    None)

    def decline(self, params: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
        say(f"session: declined a question — {params.get('message') or ''} — nobody is here; what a person must "
            f"decide is a `question` line in the deck log")
        return "decline", None

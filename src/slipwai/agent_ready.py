"""Making an agent ready from the settings page: the handshake done once, ahead of the first conversation, and
the sign-in.

An agent launched with `npx` is fetched the first time it is started — a download that would otherwise be
the first turn of somebody's first conversation. *Make ready* starts the agent exactly as a session will,
through the keel's own client, in a folder of the board's under `~/.slipwai/ready/`, and keeps what the
handshake said: the agent's name and version, how long it took, whether it can load a session, and the
ways it offers to sign in, and — from a session opened and closed at once — the models it offers, so the
page can show them to pick from before the first conversation. Nothing is guessed from a manifest; the agent
itself answers, which is also the proof a launch row wants. The sign-in is the same session calling
`authenticate` with a method of the agent's own kind; a method of the terminal kind is a command a person
runs, and the page says which.

Nothing here installs the board, Python, Node or a cloud target: where the machine lacks what a launch
needs, the row already says so, and this does not start.
"""
from __future__ import annotations

import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from . import acp
from .assets import SLIPWAI
from .board_settings import Launch, launches, offered, read, write
from .harness import acp_environment
from .shell_environment import login_environment

#: Where the handshake's session lives, one folder per agent: its cwd, and under it the client's keep.
HOME = SLIPWAI / "ready"
#: What the page keeps of a sign-in method: enough to show it and to run it, nothing the agent did not say.
METHOD_FIELDS = ("id", "name", "description", "type", "args", "env")


class Readying:
    """One make-ready run — the handshake, and the sign-in where a method was named — on a thread of its own,
    said as lines for the page to poll."""

    def __init__(self, key: str, launch: Launch, method: str = "", home: Path | None = None,
                 settings_path: Path | None = None) -> None:
        self.key, self.launch, self.method = key, launch, method
        self.home = (HOME if home is None else home) / key
        self.settings_path = settings_path
        self.lines: list[str] = []
        self.done = False
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self.run, daemon=True)

    def say(self, line: str) -> None:
        with self.lock:
            self.lines.append(line)

    def run(self) -> None:
        self.home.mkdir(parents=True, exist_ok=True)
        env = {**login_environment(), **acp_environment(self.key)}
        session = acp.Session(self.launch.argv, self.home, lambda update: None, lambda call, options: None,
                              lambda params: ("decline", None), env=env, kept=self.home / acp.KEPT)
        record: dict[str, Any] = {"at": datetime.now(UTC).strftime("%Y-%m-%d"), "fault": ""}
        started = time.monotonic()
        self.say(f"Starting {self.launch.name}: {' '.join(self.launch.argv)}")
        try:
            agent = session.start()
            seconds = round(time.monotonic() - started, 1)
            record.update({"agent": agent.name, "version": agent.version, "seconds": seconds,
                           "load_session": agent.load_session,
                           "auth": [{k: one[k] for k in METHOD_FIELDS if k in one} for one in agent.auth_methods]})
            self.say(f"{agent.name} {agent.version} answered the handshake in {seconds} s.".replace("  ", " "))
            self.say("It can pick a conversation up where it left off." if agent.load_session
                     else "It starts every conversation afresh.")
            # A session too, closed at once: it is where the agent says which models it offers, and the
            # settings page shows those to pick from before the first conversation rather than after it.
            session.new()
            settings = read(self.settings_path)
            offered(settings, self.key, session.agent.config_options, self.settings_path)
            models = settings.offered.get(self.key) or []
            self.say(f"It offers {len(models[0].get('values') or [])} models to pick from on this page."
                     if models else "It offers no model to pick; its own runs.")
            if self.method:
                session.authenticate(self.method)
                record.setdefault("signed_in", {})
                record["signed_in"] = {**record.get("signed_in", {}), self.method: record["at"]}
                self.say(f"Signed in, by {self.method}.")
        except acp.Fault as fault:
            record["fault"] = str(fault)
            self.say(f"! {fault}")
        finally:
            session.close()
            settings = read(self.settings_path)
            settings.ready[self.key] = {**settings.ready.get(self.key, {}), **record}
            write(settings, self.settings_path)
            with self.lock:
                self.done = True

    def state(self) -> dict[str, Any]:
        with self.lock:
            return {"key": self.key, "lines": list(self.lines), "done": self.done}


RUNNING: dict[str, Readying] = {}


def launch_for(key: str, path: str | None = None) -> Launch | None:
    """The launch the page's row stands for, or `None` where the registry has no such agent."""
    return next((one for one in launches(path) if one.key == key), None)


def begin(key: str, method: str = "", home: Path | None = None, settings_path: Path | None = None) -> Readying | str:
    """Start making an agent ready, or say why not: a key the registry has no agent for, one this machine
    cannot launch, or one being made ready already."""
    launch = launch_for(key)
    if launch is None:
        return f"{key} is not a harness the registry can launch"
    if not launch.able:
        return f"{launch.name} cannot be made ready here: {launch.said}"
    held = RUNNING.get(key)
    if held is not None and not held.state()["done"]:
        return f"{launch.name} is being made ready now"
    readying = Readying(key, launch, method, home, settings_path)
    RUNNING[key] = readying
    readying.thread.start()
    return readying


def state(key: str) -> dict[str, Any]:
    held = RUNNING.get(key)
    return held.state() if held is not None else {"key": key, "lines": [], "done": True}


def sign_in_line(launch: Launch, method: dict[str, Any]) -> str:
    """What a person runs for a method of the terminal kind: the agent's own command with the method's
    arguments in place of the launch's, as the registry's authentication page says."""
    head = launch.argv[0] if launch.argv else launch.key
    return " ".join([head, *[str(a) for a in method.get("args") or []]])

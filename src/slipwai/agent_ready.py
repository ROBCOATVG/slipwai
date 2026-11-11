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

import os
import shlex
import shutil
import subprocess
import sys
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from . import acp
from .assets import SLIPWAI
from .board_settings import Launch, launches, offered, read, write
from .harness import acp_environment, acp_keys, acp_row
from .shell_environment import login_environment

#: Where the handshake's session lives, one folder per agent: its cwd, and under it the client's keep.
HOME = SLIPWAI / "ready"
#: What the page keeps of a sign-in method: enough to show it and to run it, nothing the agent did not say.
METHOD_FIELDS = ("id", "name", "description", "type", "args", "env", "_meta")
#: Where the board can open a window for a sign-in that is a terminal's; elsewhere the page says the line.
WINDOWED = sys.platform in ("win32", "darwin")
#: How long a sign-in in a window is waited on: a browser, an account, perhaps a code pasted back.
SIGN_IN_LIMIT = 900.0


class Readying:
    """One make-ready run — the handshake, and the sign-in where a method was named — on a thread of its own,
    said as lines for the page to poll."""

    def __init__(self, key: str, launch: Launch, method: str = "", home: Path | None = None,
                 settings_path: Path | None = None) -> None:
        self.key, self.launch, self.method = key, launch, method
        self.home = (HOME if home is None else home) / key
        self.settings_path = settings_path
        self.lines: list[str] = []
        self.done = self.failed = False
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self.run, daemon=True)

    def say(self, line: str) -> None:
        with self.lock:
            self.lines.append(line)

    def terminal(self, method: dict[str, Any]) -> None:
        """A sign-in that is a command of the agent's, run in a window of its own and waited on: the agent
        opens the browser from there, and takes a pasted code there where the browser cannot call back."""
        name = str(method.get("name") or method.get("id"))
        env = {**login_environment(), **acp_environment(self.key),
               **{str(k): str(v) for k, v in (method.get("env") or {}).items()},
               **{str(k): str(v) for k, v in (((method.get("_meta") or {}).get("terminal-auth") or {}).get("env")
                                              or {}).items()}}
        self.say(f"A window is open to sign in: {name}. Finish there and in the browser it opens; this page waits.")
        signed = False
        try:
            argv = sign_in_argv(self.launch, method, env.get("PATH"))
            status = in_a_window(argv, env, self.home)
            signed = status == 0
            self.say(f"Signed in, by {name}." if signed
                     else f"! The sign-in ended with status {status}: nobody is signed in. Press it again to retry.")
        except (OSError, subprocess.SubprocessError) as fault:
            self.say(f"! The sign-in could not be run: {fault}")
        finally:
            if signed:
                settings = read(self.settings_path)
                found = settings.ready.get(self.key, {})
                today = datetime.now(UTC).strftime("%Y-%m-%d")
                settings.ready[self.key] = {**found, "signed_out": False,
                                            "signed_in": {**found.get("signed_in", {}), self.method: today}}
                write(settings, self.settings_path)
            with self.lock:
                self.done, self.failed = True, not signed

    def run(self) -> None:
        self.home.mkdir(parents=True, exist_ok=True)
        kept = read(self.settings_path).ready.get(self.key, {}).get("auth") or []
        method = next((one for one in kept if one.get("id") == self.method and terminal_kind(one)), None)
        if method is not None:
            self.terminal(method)
            return
        env = {**login_environment(), **acp_environment(self.key)}
        session = acp.Session(self.launch.argv, self.home, lambda update: None, lambda call, options: None,
                              lambda params: ("decline", None), env=env, kept=self.home / acp.KEPT)
        record: dict[str, Any] = {"at": datetime.now(UTC).strftime("%Y-%m-%d"), "fault": ""}
        started = time.monotonic()
        self.say(f"Starting {self.launch.name}: {' '.join(self.launch.argv)}")
        try:
            agent = session.start()
            seconds = round(time.monotonic() - started, 1)
            # An agent that gives no name of its own (Grok, CodeBuddy, Cursor) is called by the registry's.
            name = self.launch.name if agent.name == self.launch.argv[0] else agent.name
            record.update({"agent": name, "version": agent.version, "seconds": seconds,
                           "load_session": agent.load_session,
                           "auth": [{k: one[k] for k in METHOD_FIELDS if k in one} for one in agent.auth_methods]})
            self.say(f"{name} {agent.version} answered the handshake in {seconds} s.".replace("  ", " "))
            self.say("It can pick a conversation up where it left off." if agent.load_session
                     else "It starts every conversation afresh.")
            # A session too, closed at once: it is where the agent says which models it offers, and the
            # settings page shows those to pick from before the first conversation rather than after it.
            try:
                session.new()
                record["signed_out"] = False
            except acp.Fault as fault:  # an agent that opens no session until somebody signs in: not a fault
                if fault.code != acp.SIGNED_OUT:
                    raise
                record["signed_out"] = True
                self.say(f"Nobody is signed in to it yet: {fault}")  # its own words: Droid's carry a code to enter
                self.say("Press a Sign in below, then Make ready again for its models.")
            settings = read(self.settings_path)
            offered(settings, self.key, session.agent.config_options, self.settings_path)
            models = settings.offered.get(self.key) or []
            if not record["signed_out"]:
                self.say(f"It offers {len(models[0].get('values') or [])} models to pick from on this page."
                         if models else "It offers no model to pick; its own runs.")
            if self.method:
                session.authenticate(self.method)
                kept = settings.ready.get(self.key, {}).get("signed_in", {})
                record.update(signed_in={**kept, self.method: record["at"]}, signed_out=False)
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
                self.done, self.failed = True, bool(record["fault"])

    def state(self) -> dict[str, Any]:
        with self.lock:
            return {"key": self.key, "lines": list(self.lines), "done": self.done, "failed": self.failed}


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
    return held.state() if held is not None else {"key": key, "lines": [], "done": True, "failed": False}


def terminal_kind(method: dict[str, Any]) -> bool:
    """Whether the sign-in is a command somebody runs: said by its type, or — Copilot gives no type — by
    its naming a command. Asked of the agent as an `authenticate`, such a method does nothing."""
    return method.get("type") == "terminal" or bool((method.get("_meta") or {}).get("terminal-auth"))


def launched_as(launch: Launch) -> list[str]:
    """The launch without the arguments that make it an agent: `npx --yes <package>`, or the binary."""
    row = acp_row(launch.key) or {}
    how = row.get("npx") if isinstance(row.get("npx"), dict) else row.get("binary")
    drop = len((how or {}).get("args") or []) if row else len(launch.argv) - 1
    return list(launch.argv[:len(launch.argv) - drop]) or [launch.key]


def sign_in_argv(launch: Launch, method: dict[str, Any], path: str | None = None) -> list[str]:
    """The command of a method of the terminal kind, found on `path`.

    The protocol's way is the agent's own launch with the method's arguments in place of the launch's. An
    agent may also name a whole command (`_meta`'s `terminal-auth`), and agents differ in which of the two
    is right: OpenCode's arguments are not ones its command takes and its named command is; Qoder names
    `node login`, and pi a `pi-acp` that `npx` never put on the path. So the named command is taken where
    it says something the arguments do not and can be found; otherwise the launch with the arguments."""
    args = [str(a) for a in method.get("args") or []]
    named = (method.get("_meta") or {}).get("terminal-auth") or {}
    theirs = [str(a) for a in named.get("args") or []]
    found = shutil.which(str(named["command"]), path=path) if named.get("command") else None
    if found and Path(found).name in others(launch.key):  # Kilo names `opencode`: another agent's sign-in
        return [*launched_as(launch), *theirs]
    if found and (theirs != args or "args" not in method):
        return [found, *theirs]
    return [*launched_as(launch), *(args if "args" in method else theirs)]


def others(key: str) -> set[str]:
    """The commands the registry's other agents are launched as."""
    rows = {one: acp_row(one) or {} for one in acp_keys() if one != key}
    return {str(row["binary"]["cmd"]) for row in rows.values() if isinstance(row.get("binary"), dict)}


def sign_in_line(launch: Launch, method: dict[str, Any]) -> str:
    """What a person runs for a method of the terminal kind, where the board has no window to run it in."""
    return " ".join(sign_in_argv(launch, method))


def in_a_window(argv: list[str], env: dict[str, str], home: Path, limit: float = SIGN_IN_LIMIT) -> int:
    """`argv` run in a terminal window of its own, waited on; its exit status. On Windows a console of the
    child's own; on a Mac a script Terminal opens, which leaves the status in a file for this to find."""
    if sys.platform == "win32":
        child = subprocess.Popen(argv, env=env, cwd=home,  # noqa: S603 — the agent's own sign-in command
                                 creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0))
        try:
            return child.wait(limit)
        except subprocess.TimeoutExpired:
            child.kill()
            raise
    if sys.platform != "darwin":
        raise OSError(f"there is no window to open here; run it in a terminal: {' '.join(argv)}")
    script, status = home / "sign-in.command", home / "sign-in.status"
    status.unlink(missing_ok=True)
    sets = "".join(f"export {name}={shlex.quote(value)}\n" for name, value in env.items()
                   if name == "PATH" or name not in os.environ)
    script.write_text(f"#!/bin/sh\n{sets}{shlex.join(argv)}\necho $? > {shlex.quote(str(status))}\n", encoding="utf-8")
    script.chmod(0o700)
    subprocess.run(["/usr/bin/open", str(script)], check=True)  # noqa: S603 — Terminal, on the board's own script
    ends = time.monotonic() + limit
    while time.monotonic() < ends:
        if status.is_file() and status.read_text(encoding="utf-8").strip():
            return int(status.read_text(encoding="utf-8").strip())
        time.sleep(0.5)
    raise subprocess.TimeoutExpired(argv, limit)

#!/usr/bin/env python3
"""The captain's own session: one per stream, woken by an event, acting only through `orders.py`.

Three ways to run it, chosen once per captain process:

- **A command named in `SLIPWAI_CAPTAIN`**, run once per event with the event file's path after it. The suite's
  stand-in is one, and so is any command a person points at it.
- **Over the Agent Client Protocol**, where `drive.protocol` takes it — the machinery a slice's driver uses,
  held open across events, started in the project's root, its conversation `talk/<fairway>/_captain/` and
  its session saved and loaded like a slice's. Its policy lets it read and run `orders.py`, and nothing else.
- **Headless otherwise**, the same brief run once per event through the harness print mode would use.

Each wake-up hands it the event and the stream's state as the log says it now (`events/<fairway>/state.json`),
never what it remembers, so a cold start answers as a warm one would. Each is bounded: `captain.bound` in
`harbour.json` from when the session is ready to take the event, and the headless path — which starts a
session every time and cannot say when it is ready — its own, longer `captain.headless_bound`.

**For the evals**: `python3 scripts/agents/captain_agent.py decide <event file> [--bound N]`, run in the
project, wakes the captain this project would run, once, with that event and the `state.json` beside it,
lets it write its orders under `.slipwai/run/orders/<fairway>/` through `orders.py`, and ends it at the bound.
It prints `{"exit", "timed_out", "tokens", "seconds", "orders"}` as one JSON line. Nothing reads the orders
back: that is the eval's. As a command it fits `command_captain` exactly, which appends the event's path.

Standalone and dependency-free: this runs inside a generated project, which has no slipwai to import.
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import drive  # noqa: E402
import harness  # noqa: E402
import logs  # noqa: E402
import orders as order_door  # noqa: E402
import talk  # noqa: E402

COMMAND = "SLIPWAI_CAPTAIN"
#: Seconds a decision may take from when the session is ready, and from launch where that cannot be told.
BOUND, HEADLESS_BOUND = 60.0, 180.0
BRIEF = "agents/drive-captain.md"


def project_root() -> Path:
    for candidate in HERE.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return HERE.parents[1]


ROOT = project_root()


def settings(held: dict[str, Any]) -> dict[str, Any]:
    """`harbour.json`'s `captain`: whether the stream's captain is an agent, and its two bounds. Absent or
    anything but `agent: true` is the program alone, exactly as before there was an agent. `SLIPWAI_CAPTAIN`
    says first, as `SLIPWAI_ACP` does for a slice's session: `off` is the program alone whatever the file
    says, and any other value is the command to run as the captain."""
    said = held.get("captain") if isinstance(held.get("captain"), dict) else {}

    def seconds(name: str, fallback: float) -> float:
        value = said.get(name)
        return float(value) if isinstance(value, int | float) and not isinstance(value, bool) and value > 0 else fallback
    named = os.environ.get(COMMAND, "").strip()
    agent = named != "off" and (said.get("agent") is True or bool(named))
    return {"agent": agent, "bound": seconds("bound", BOUND),
            "headless_bound": seconds("headless_bound", HEADLESS_BOUND)}


def prompt(fairway: str, event: Path, state: Path, held: dict[str, Any]) -> str:
    """What the captain's session is asked at each wake-up: the brief, the event, the state, the one door."""
    def where(path: Path) -> str:
        return path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path)
    return (f"You are the captain of the `{fairway}` stream in this project. Read {BRIEF} for what you are asked "
            f"and what you may do. Event {held['id']} ({held['kind']}) needs you: read {where(event)}. The "
            f"stream's state, as its log says it now, is {where(state)} — believe it over anything you remember. "
            f"Act only by running `python3 scripts/agents/orders.py <verb> … --event {held['id']}`; this event "
            f"takes {', '.join(held.get('may') or [])}. Say what you did in one sentence a person can read, with "
            f"`say`, where it is worth saying, and end your turn.")


# -- a turn, however it runs ------------------------------------------------------------------------------------


class Process:
    """A captain run once per event as a process: the named command, or a headless session. What it prints
    goes to a file beside the stream's events, never a pipe a talkative agent could fill and stall on."""

    def __init__(self, argv: list[str], env: dict[str, str], kind: str, out: Path) -> None:
        self.kind = kind
        self.started = time.monotonic()
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("ab") as said:
            self.child = subprocess.Popen(argv, cwd=ROOT, env=env, stdin=subprocess.DEVNULL, stdout=said,
                                          stderr=subprocess.STDOUT, start_new_session=os.name != "nt")

    def finished(self) -> bool:
        return self.child.poll() is not None

    def ready(self) -> float | None:
        return self.started  # a process cannot say when it is ready: the bound runs from its launch

    def end(self) -> None:
        if self.child.poll() is not None:
            return
        try:
            if os.name != "nt":
                os.killpg(self.child.pid, signal.SIGTERM)
            else:  # pragma: no cover - the other platform's branch
                self.child.terminate()
            self.child.wait(timeout=10)
        except (ProcessLookupError, subprocess.TimeoutExpired):
            self.child.kill()
            self.child.wait()


class Held:
    """One event put to the captain's held session over the protocol."""

    kind = "protocol"

    def __init__(self, driver: drive.Drive) -> None:
        self.driver = driver
        self.launched = time.monotonic()
        self.began: float | None = None

    def finished(self) -> bool:
        return self.driver.poll() is not None

    def ready(self) -> float | None:
        # Ready once its turn has begun: the agent is up, its session open, and the prompt with it. Before
        # that the bound would be measuring a package fetch, not a decision.
        if self.began is None and (self.driver.turning or self.driver.poll() is not None):
            self.began = time.monotonic()
        if self.began is None and time.monotonic() - self.launched > drive_start_ceiling():
            self.began = self.launched  # it never became ready: the bound runs from launch after all
        return self.began

    def end(self) -> None:
        self.driver.terminate()  # the turn is cancelled; the session stays for the next event


def drive_start_ceiling() -> float:
    """How long the protocol session may take to start before its start is counted against the decision."""
    return 300.0


# -- the runner ----------------------------------------------------------------------------------------------------


def permit(tool_call: dict[str, Any], options: list[dict[str, Any]]) -> str | None:
    """The captain session's policy: reading is allowed, and running `orders.py` alone; nothing else, wherever
    it is. Its hands are the orders, which the program checks; a captain that edits a file is a slice's
    session with no gate."""
    allowed = next((str(one["optionId"]) for one in options if one.get("kind") == "allow_once" and "optionId" in one), None)
    refused = next((str(one["optionId"]) for one in options if one.get("kind") == "reject_once" and "optionId" in one), None)
    kind = str(tool_call.get("kind") or "")
    if kind in ("read", "search", "think") and allowed:
        return allowed
    if kind == "execute" and allowed and ordering(tool_call):
        return allowed
    return refused


def ordering(tool_call: dict[str, Any]) -> bool:
    """Whether a command is one run of `orders.py` and nothing beside it."""
    raw = tool_call.get("rawInput") or {}
    command = str(raw.get("command") or "") if isinstance(raw, dict) else ""
    command = command or str(tool_call.get("title") or "")
    if any(mark in command for mark in (";", "&", "|", ">", "<", "`", "$(", "\n")):
        return False
    try:
        words = shlex.split(command)
    except ValueError:
        return False
    return len(words) >= 2 and Path(words[0]).name.startswith("python") and \
        words[1].replace("\\", "/").endswith("scripts/agents/orders.py")


class Runner:
    """How this stream's captain is woken, chosen once; a protocol session that will not start is given up
    for the headless path, and a stream with no way to run one at all runs every decision on the rule."""

    def __init__(self, fairway: str, run: Path, bounds: dict[str, Any]) -> None:
        self.fairway, self.run, self.bounds = fairway, Path(run), bounds
        self.driver: drive.Drive | None = None
        self.no_protocol = False

    def bound(self, turn: Any) -> float:
        return float(self.bounds["headless_bound"] if getattr(turn, "kind", "") == "headless" else self.bounds["bound"])

    def wake(self, event: Path, state: Path, held: dict[str, Any], env: dict[str, str]) -> Any:
        named = os.environ.get(COMMAND, "").strip()
        clean = {key: value for key, value in os.environ.items() if not key.startswith("SLIPWAI_SLICE")}
        if named:
            try:
                return Process([*shlex.split(named), str(event)], {**clean, **env, "SLIPWAI_CAPTAIN_EVENT": held["id"]},
                               "named", event.parent / "agent.out")
            except OSError as fault:
                return f"`{named}` could not be started ({fault})"
        text = prompt(self.fairway, event, state, held)
        try:
            over = None if self.no_protocol else drive.protocol()
        except harness.NoHarness:
            over = None
        if over is not None:
            return self.held(over, text, env)
        try:
            row, _said = harness.choose()
        except harness.NoHarness as none:
            return str(none)
        template, _ = harness.template(row)
        line = template.replace("{prompt}", shlex.quote(text))
        try:
            return Process(shlex.split(line), {**harness.child_environment(row), **env}, "headless",
                           event.parent / "agent.out")
        except OSError as fault:
            return f"the harness could not be started ({fault})"

    def held(self, over: tuple[list[str], dict[str, Any] | None, str], text: str, env: dict[str, str]) -> Any:
        launch, row, _said = over
        if self.driver is not None and self.driver.unlaunched:
            self.no_protocol, self.driver = True, None
            return "its session would not start over the protocol, so it runs headless from now on"
        if self.driver is not None and self.driver.alive:
            self.driver.prompt(text)
            return Held(self.driver)
        home = talk.place(self.run, self.fairway, talk.CAPTAIN)
        environment = {**harness.child_environment(row), **drive.acp_environment(row), **env}
        self.driver = drive.Drive(launch, ROOT, environment, text, kept=self.run / "acp" / f"_captain-{self.fairway}",
                                  conversation=home, activity=self.run / "activity" / self.fairway / "_captain.jsonl",
                                  harness_key=str((row or {}).get("key") or ""), inbox=False, permit=permit)
        return Held(self.driver)

    def close(self) -> None:
        if self.driver is not None:
            self.driver.end()


# -- the evals' door -------------------------------------------------------------------------------------------------


def evaluate(event: Path, bound: float | None = None) -> dict[str, Any]:
    """Wake this project's captain once with a recorded event, and say how it ended. The orders are files."""
    import secrets
    fairway = event.parent.name
    run = logs.run_dir(ROOT)
    held = json.loads(event.read_text(encoding="utf-8"))
    state = event.parent / "state.json"
    if not state.is_file():
        state.write_text(json.dumps({"v": 1, "fairway": fairway}) + "\n", encoding="utf-8")
    bounds = settings(json.loads((ROOT / "harbour.json").read_text(encoding="utf-8"))
                      if (ROOT / "harbour.json").is_file() else {})
    runner = Runner(fairway, run, bounds)
    env = {order_door.KEY: secrets.token_hex(32), order_door.FAIRWAY: fairway, order_door.EVENTS: str(event.parent),
           order_door.ORDERS: str(run / "orders" / fairway), "SLIPWAI_STAGE": "captain", "SLIPWAI_EVAL": "1"}
    began = time.monotonic()
    before = {path.name for path in (run / "orders" / fairway).glob("*.json")} if (run / "orders" / fairway).is_dir() else set()
    turn = runner.wake(event, state, held, env)
    if isinstance(turn, str):
        return {"exit": None, "timed_out": False, "tokens": None, "seconds": 0.0, "orders": [], "why": turn}
    limit = bound if bound is not None else runner.bound(turn)
    timed_out = False
    while not turn.finished():
        ready = turn.ready()
        if ready is not None and time.monotonic() - ready > limit:
            turn.end()
            timed_out = True
            break
        time.sleep(0.1)
    runner.close()
    code = getattr(getattr(turn, "child", None), "returncode", None)
    after = sorted(path.stem for path in (run / "orders" / fairway).glob("*.json")
                   if path.name not in before and not path.name.endswith(".result.json")) \
        if (run / "orders" / fairway).is_dir() else []
    return {"exit": code, "timed_out": timed_out, "tokens": None, "seconds": round(time.monotonic() - began, 3),
            "orders": after}


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="captain_agent", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="what", required=True)
    decide = sub.add_parser("decide", help="wake this project's captain once with an event file, for an eval")
    decide.add_argument("event", type=Path)
    decide.add_argument("--bound", type=float, default=None, help="seconds; the project's own bound otherwise")
    parsed = parser.parse_args(argv)
    print(json.dumps(evaluate(parsed.event.resolve(), parsed.bound)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

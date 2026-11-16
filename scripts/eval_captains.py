"""The captain under test: the one function an eval calls, and the two ways it is given one.

**The contract is small on purpose.** A captain under test is a callable taking `(project, event, bound)`:
`project` is a throwaway directory laid out as a project's state, `event` the event file in it that wakes
the captain, `bound` the seconds it has. It answers by writing order files under
`project/.slipwai/run/orders/<fairway>/` — by running `python3 scripts/agents/orders.py`, as the real one
does — and returns a `Ran` once it is finished or the bound has passed. The runner reads the orders; it
never asks the callable what it decided. Anything with that shape can be put under test: the agent stream E
builds, a stand-in in the suite, or a command a person names.

**By default it is the project's own harness, run headless** with the captain's brief and the event, which
is decision 18's path. Started through `scripts/agents/harness.py` — the same knowledge every headless
session in a project is started from — so the eval names no harness and works with whichever the project
has initialised.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import shlex
import signal
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any, NamedTuple


class Ran(NamedTuple):
    """How a captain under test ended: its exit status, whether the bound ended it, and tokens where known."""
    exit: int | None
    timed_out: bool
    tokens: int | None = None


Captain = Callable[[Path, Path, float], Ran]


class CannotRun(RuntimeError):
    """The captain under test cannot be started here, said as the sentence a person acts on."""


def prompt(project: Path, event: Path, brief: str) -> str:
    """What the captain's session is asked: who it is, what woke it, and the one way it may answer."""
    held = json.loads(event.read_text(encoding="utf-8"))
    fairway = event.parent.name
    return (f"You are the captain of the `{fairway}` stream in this project, woken by one event. Read {brief} "
            f"for who you are and what you may do. The event is {event.relative_to(project).as_posix()}: its "
            f"`facts` are the stream's state as the program folded it, and its `may` lists the only orders "
            f"the program will accept for it ({', '.join(held.get('may') or [])}). Decide, then act only by "
            f"running `python3 scripts/agents/orders.py <verb> …` once for each order you give, and end your "
            f"turn. Write no log line and no file yourself. Where no order fits, run `python3 "
            f"scripts/agents/orders.py none --why \"<why>\"` and the program applies its fixed rule.")


def tokens_in(output: str) -> int | None:
    """Tokens a session reported on its own output, where it writes one JSON event a line and says them.

    A `result` line's `usage` (a stream-json session) or a `turn.completed` line's (a JSON-lines one): the
    `*_tokens` counts in it, summed. `None` where nothing was said, which is most harnesses' plain output.
    """
    total, seen = 0, False
    for line in output.splitlines():
        try:
            held = json.loads(line)
        except ValueError:
            continue
        usage = held.get("usage") if isinstance(held, dict) and held.get("type") in ("result",
                                                                                     "turn.completed") else None
        if isinstance(usage, dict):
            counts = [value for key, value in usage.items() if key.endswith("_tokens") and isinstance(value, int)]
            total, seen = total + sum(counts), seen or bool(counts)
    return total if seen else None


def harness_module(project: Path) -> Any:
    """The project's `harness.py`, loaded from the project, so that the project it reads is that one."""
    path = project / "scripts/agents/harness.py"
    spec = importlib.util.spec_from_file_location(f"eval_harness_{abs(hash(project))}", path)
    if spec is None or spec.loader is None:
        raise CannotRun(f"{path} is not there to start a session with")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def harness_captain(brief: str = "agents/drive-captain.md", model: str | None = None) -> Captain:
    """The default captain under test: one headless session of the project's harness, once per event."""

    def run(project: Path, event: Path, bound: float) -> Ran:
        if not (project / "scripts/agents/orders.py").is_file():
            raise CannotRun("scripts/agents/orders.py is not in this keel's toolkit yet, so a captain has no way "
                            "to give an order; it arrives with the captain agent (stream E)")
        harness = harness_module(project)
        try:
            chosen, _said = harness.choose()
        except harness.NoHarness as refusal:
            raise CannotRun(str(refusal)) from None
        template, _why = harness.template(chosen)
        line = template.replace("{prompt}", shlex.quote(prompt(project, event, brief)))
        line += harness.model_flags(chosen, model)
        environment = {**harness.child_environment(chosen), "SLIPWAI_STAGE": "captain", "SLIPWAI_EVAL": "1"}
        # The session's stream passes through `sys.stdout`; held here for the tokens it reports, then shown.
        raw = io.BytesIO()
        held = io.TextIOWrapper(raw, encoding="utf-8", errors="replace", write_through=True)
        with contextlib.redirect_stdout(held):
            exited, expired = harness.run_bounded(shlex.split(line), project, environment, bound)
        output = raw.getvalue().decode("utf-8", errors="replace")
        sys.stdout.write(output)
        return Ran(exited, expired, tokens_in(output))

    return run


def command_captain(command: str) -> Captain:
    """A captain under test named as a command: run in the project with the event's path after it.

    `SLIPWAI_EVAL_EVENT` carries the same path, and the bound is enforced here — the command and whatever it
    started are ended together when it runs out, as a session at its budget is.
    """

    def run(project: Path, event: Path, bound: float) -> Ran:
        argv = [*shlex.split(command), str(event)]
        environment = {**os.environ, "SLIPWAI_EVAL_EVENT": str(event), "SLIPWAI_EVAL": "1"}
        try:
            child = subprocess.Popen(argv, cwd=project, env=environment, stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT, start_new_session=os.name != "nt")
        except OSError as fault:
            raise CannotRun(f"`{command}` could not be started: {fault}") from None
        try:
            output, _ = child.communicate(timeout=bound)
            # Ended with the command, too: whatever it left running in the background would otherwise outlive
            # the run and go on writing into a folder that is about to be taken away.
            end_group(child)
            return Ran(child.returncode, False, tokens_in(output.decode("utf-8", errors="replace")))
        except subprocess.TimeoutExpired:
            end_group(child)
            child.kill()
            child.communicate()
            return Ran(None, True)

    return run


def end_group(child: subprocess.Popen[bytes]) -> None:
    """Kill the command's whole process group: it and everything it started."""
    if os.name != "nt":
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.killpg(child.pid, signal.SIGKILL)


def named(captain: str | None, brief: str, model: str | None) -> tuple[Captain, str]:
    """The captain a person asked for on the command line, and the words the report uses for it."""
    if captain:
        return command_captain(captain), f"`{captain}`"
    print("evals: the captain under test is the project's harness, run headless with the captain's brief",
          file=sys.stderr)
    return harness_captain(brief, model), f"the project's harness with {brief}"

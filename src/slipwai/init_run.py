"""`./init` in a project that has just been generated: the step that hands a new tree to its coding agent.

`generate` wrote a repository, printed where it had put it, and stopped. The next step was a sentence in the
guide — change directory, run `./init` — and it is the step that installs Spec Kit, projects the skills and
commands into the agent, and reaches the network. Nothing in the tree works until it has run, so leaving it
to prose was leaving the project half made and the person holding the other half.

**Two faces, because everything here has two.** The terminal runs it as a child of the terminal, sharing its
standard input: `specify init` asks which agent when nobody has said, and there is somebody sitting there to
answer. The board has nobody to ask, so it names the agent up front — a thirty-six-row list is a question a
browser asks well and a terminal cannot — and the child outlives the request that started it, because
installing Spec Kit takes minutes and a POST that blocks for minutes is a page that looks broken.

**A failure here is not a failure of generation.** The repository is written and committed before any of this
runs, so a source that is down costs the project nothing: the exit status is reported and never raised. That
is the rule `adopt` already has for the same step (`cli_init.run_init`), and it is why this runs last.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .shell_environment import login_environment

#: What a child writes when it believes it is on a terminal — which, through a pseudo-terminal, it does.
#: Stripped rather than rendered: the card is a log of what was said, not a terminal emulator.
ANSI = re.compile(r"\x1b\[[0-9;?]*[a-zA-Z]|\x1b\][^\x07]*\x07|\x1b[=>()][0-9A-B]?")

#: What the child is told about where it is writing. A pseudo-terminal buys line-buffering and costs
#: animation — pip and Spec Kit redraw progress bars at a terminal — so it is given one and then told, in
#: the four spellings between them, not to paint.
PLAIN = {"TERM": "dumb", "NO_COLOR": "1", "FORCE_COLOR": "0", "PYTHONUNBUFFERED": "1", "COLUMNS": "100"}

#: How many lines of one run are kept. Spec Kit's install is a few hundred; a child that found a way to
#: loop is not going to fill this machine with the board's own card.
KEPT = 4000

#: What the board says where nobody chose an agent to hand the project to. `./init` is still the next step,
#: and the project is still where the board is now looking: declining the run is not declining the landing.
DECLINED = ("./init was not run. It is the next step, in a terminal: `./init` asks which coding agent gets "
            "the skills and commands, installs Spec Kit, and then `make verify` is the gate.")

#: What a generated project calls it, at its root. `adopt` reaches a delivery directory's copy and spells the
#: path itself; a project the keel generated has this one and no other.
SCRIPT = "init"


def command(harness: str | None = None, repository: str | None = None) -> list[str]:
    """`./init`, with the agent named where somebody has named one, and the forge where somebody has.

    Unnamed, Spec Kit keeps its own question — which is right where there is a terminal to ask it in and
    wrong everywhere else, so the caller that has no terminal is the one that passes a harness. The
    repository is the same shape of answer for the same reason: a project with a production target
    configures its pipeline on the repository it is pushed to, and `./init` asks for that over `/dev/tty`.
    """
    return [f"./{SCRIPT}", *(["--integration", harness] if harness else []),
            *(["--repository", repository] if repository else [])]


def announced(root: Path, harness: str | None, repository: str | None = None) -> str:
    """The line said before it starts, wherever it is about to start."""
    return (f"Running {' '.join(command(harness, repository))} in {root} — it installs Spec Kit for the "
            f"coding agent, so it reaches the network once, here.")


def ended(code: int, harness: str | None, repository: str | None = None) -> str:
    """The line said after it stops, which is a different line when it did not work."""
    said = " ".join(command(harness, repository))
    if code == 0:
        return f"`{said}` is done. `make verify` is the gate, and it is green on a new tree."
    return (f"`{said}` exited {code}, and the project is written and committed either way: it is a step of "
            f"its own, which is why it runs after. Run it again when whatever stopped it is fixed.")


def here(root: Path, harness: str | None = None) -> int:
    """`./init` as a child of this terminal, sharing its standard input so Spec Kit can ask its question."""
    print(f"\n{announced(root, harness)}")
    done = subprocess.run(command(harness), cwd=root, check=False)
    print(ended(done.returncode, harness))
    return done.returncode


@dataclass(frozen=True)
class Step:
    """One command the board runs in the project, with the line said before it and the one said after."""

    argv: list[str]
    announced: str
    ended: Callable[[int], str]
    #: Which step this is — `init`, `draft`, `launch` — for the page that says what stage the project is on.
    key: str = ""


def init_step(where: Path, harness: str, repository: str | None) -> Step:
    return Step(command(harness, repository), announced(where, harness, repository),
                lambda code: ended(code, harness, repository), "init")


def folded_line(line: str) -> list[str]:
    """Claude Code's print mode writes one JSON event per line, and a person watching the card wants the
    words: an assistant event's text, one line per tool it reaches for, the result's first line with what it
    cost. System events and tool results are the harness talking to itself and are dropped. A line that is
    not JSON is said as it came."""
    if not line.startswith("{"):
        return [line]
    try:
        event = json.loads(line)
    except ValueError:
        return [line]
    if not isinstance(event, dict):
        return [line]
    kind = event.get("type")
    if kind == "assistant":
        said: list[str] = []
        message = event.get("message")
        for block in (message.get("content") if isinstance(message, dict) else None) or []:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text":
                said += [f"• {part}" for part in str(block.get("text", "")).splitlines() if part.strip()]
            elif block.get("type") == "tool_use":
                said.append(f"→ {block.get('name', 'tool')}")
        return said
    if kind == "result":
        text = str(event.get("result") or "").strip().splitlines()
        usage = event.get("usage")
        tokens = usage.get("output_tokens") if isinstance(usage, dict) else None
        cost = f" — {tokens:,} output tokens" if isinstance(tokens, int) else ""
        return [f"result: {text[0] if text else event.get('subtype', 'ended')}{cost}"]
    return []


#: The step after `./init` where a PRD came with the answers: the constitution and the first specification,
#: drafted by the agent in a headless session (`make draft`, `scripts/agents/draft.py`), and then a stop.
#: The board shows the specification's existence as a button, and nothing is built until it is pressed —
#: a specification somebody has read is the line between what the agent drafts and what runs unattended.
DRAFT = ["make", "draft"]
DRAFTING = ("Drafting the constitution and the first specification from docs/prd.md — `make draft`, a headless "
            "session of the coding agent in the project. It stops at the specification: read it, then "
            "Continue the build.")
#: What the button runs: the chart and the split in a second session, `/cruise` enabled, the fleet cast off.
LAUNCH = ["make", "launch"]
LAUNCHING = ("Continuing the build — `make launch`: the chart and the split in a headless session, then /cruise "
             "enabled and the fleet cast off. The streams on this board are the fleet; a captain that parks is "
             "waiting on you.")


def drafted(code: int) -> str:
    if code == 0:
        return ("`make draft` is done. The specification is under specs/: read it, and Continue the build charts "
                "and splits it and casts off.")
    return (f"`make draft` exited {code}; the project is made and `./init` has run either way. Fix what it named "
            f"and run `make draft` in the project, or write the specification with the agent.")


def launched(code: int) -> str:
    if code == 0:
        return "`make launch` is done: the fleet is cast off. `make cruise-watch` is the seat beside it."
    return f"`make launch` exited {code}; nothing was cast off. Its last lines say why."


class Fitting:
    """The board's one child running somewhere nobody is watching the terminal, and everything it has said.

    `./init`, and after it whatever steps the answers asked for, each a command run in the project. Lines
    rather than a stream: the board polls, and a poll answers with what has been said since the line the
    asker last had. The lock is around the list and the status because the reader is the server's thread
    and the writer is this one, and a tail that occasionally lost its last line would be the kind of fault
    nobody can reproduce.
    """

    def __init__(self, where: Path, steps: list[Step] | None = None, said: list[str] | None = None) -> None:
        self.where = where
        self.steps = list(steps or [])
        self.lines: list[str] = [*(said or []), self.steps[0].announced if self.steps else DECLINED]
        self.dropped = 0  # lines said and since let go of, so `since` keeps meaning the same thing
        self.step = self.steps[0].key if self.steps else ""
        self.code: int | None = None
        self.began = time.monotonic()
        self.stopped: float | None = None
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self.run, daemon=True)

    def child(self, argv: list[str]) -> tuple[subprocess.Popen[bytes], int, bool]:
        """The child, the descriptor its output is read from, and whether that descriptor is ours to close.

        Through a pseudo-terminal wherever this machine has one, which is not a nicety. `./init` is a shell
        script that shells out to pip, to uv and to Spec Kit, and every one of those line-buffers to a
        terminal and block-buffers to a pipe: down a pipe the card showed two lines for two minutes and then
        everything at once, which is the opposite of watching something run. Windows has no pty and gets the
        pipe it always had.
        """
        # The login shell's environment, as `generate`'s child is given it: a board started by a login
        # service has `PATH=/usr/bin:/bin`, and `./init` run with that found neither brew nor uv nor the
        # cloud's own tools on a machine that had every one of them, and fell through to the system pip.
        env = {**login_environment(), **PLAIN}
        shape: dict = {"cwd": self.where, "stdin": subprocess.DEVNULL, "stderr": subprocess.STDOUT, "env": env}
        if sys.platform == "win32":  # pragma: no cover — the pty path is what every other platform takes
            child = subprocess.Popen(argv, stdout=subprocess.PIPE, **shape)
            return child, child.stdout.fileno() if child.stdout else -1, False
        import pty  # noqa: PLC0415 — POSIX only, and only this method opens one
        reader, writer = pty.openpty()
        # Its own session, which is the difference between a question and a hang. `./init` asks two of its
        # questions over `/dev/tty` rather than over standard input — the repository a production target
        # pushes to, and the extension menu — and `/dev/tty` is the *controlling* terminal, which a child of
        # this server would otherwise inherit from whoever started the board. The prompt then printed into
        # this log while the read blocked on a terminal nobody was looking at. With no controlling terminal
        # the open fails, and both of those questions do what they already do for a scripted run: nothing.
        child = subprocess.Popen(argv, stdout=writer, close_fds=True, start_new_session=True, **shape)
        os.close(writer)  # ours no longer: the child holds the only other end, so reading sees its exit
        return child, reader, True

    def read(self, reading: int) -> None:
        """Everything the child says, a line at a time, as it says it.

        Split on a carriage return as well as a newline: a child that thinks it is on a terminal redraws its
        last line rather than ending it, and a progress bar that arrived as one line a megabyte long would
        be the tail showing nothing until it finished.
        """
        held = ""
        while True:
            try:
                chunk = os.read(reading, 4096)
            except OSError:  # how a pseudo-terminal says end of file, rather than an empty read
                break
            if not chunk:
                break
            *lines, held = re.split(r"\r\n|\r|\n", held + chunk.decode("utf-8", "replace"))
            for line in lines:
                for said in folded_line(ANSI.sub("", line).rstrip()):
                    self.say(said)
        if held.strip():
            for said in folded_line(ANSI.sub("", held).rstrip()):
                self.say(said)

    def run(self) -> None:
        """Each step's child, read a line at a time until it ends; a step that fails ends the run there. A
        child's own failure to start is a line like any other: a board that showed nothing where `./init`
        could not be executed would be a board hiding the answer.

        Nothing to run is also a finished run: the board still lands in the project and still says what was
        made, and a receipt that only appeared when a child happened to be started would be the one thing
        missing on the path somebody chose deliberately.
        """
        if not self.steps:
            self.stop(0)
            return
        for index, step in enumerate(self.steps):
            with self.lock:
                self.step = step.key
            if index:
                self.say(step.announced)
            last = index == len(self.steps) - 1
            try:
                child, reading, ours = self.child(step.argv)
            except OSError as fault:
                self.say(f"{' '.join(step.argv)} could not be run here: {fault}", code=1)
                return
            with child:  # closed and waited on by the context manager, so a long run leaks no pipe
                self.read(reading)
                code = child.wait()
            if ours:
                os.close(reading)
            self.say(step.ended(code), code=code if code or last else None)
            if code:
                return

    def say(self, line: str, code: int | None = None) -> None:
        with self.lock:
            self.lines.append(line)
            if len(self.lines) > KEPT:
                self.dropped += len(self.lines) - KEPT
                del self.lines[:-KEPT]
            if code is not None:
                self.code = code
                self.stopped = time.monotonic()

    def stop(self, code: int) -> None:
        """Finished with nothing more to say, which is what declining looks like."""
        with self.lock:
            self.code = code
            self.stopped = time.monotonic()

    def said(self, since: int = 0) -> dict:
        """What has been said after the `since`th line, how many there are now, how long it has been going,
        and whether it has stopped.

        `at` counts every line this run has ever said, the let-go-of ones included, so a page that polls with
        the number it last had is answered with what came after it however long it has been away.
        """
        with self.lock:
            kept = max(since - self.dropped, 0)
            return {"where": str(self.where), "lines": self.lines[kept:], "step": self.step,
                    "at": self.dropped + len(self.lines),
                    "seconds": round((self.stopped or time.monotonic()) - self.began, 1),
                    "done": self.code is not None, "code": self.code}


def start(where: Path, harness: str | None = None, said: list[str] | None = None,
          repository: str | None = None, prd: bool = False) -> Fitting:
    """`./init` begun in the background — and the draft after it, where a PRD came with the answers and an
    agent was named to draft with. Returned rather than awaited: what it says is read by polling."""
    steps = [init_step(where, harness, repository)] if harness else []
    if steps and prd:
        steps.append(Step(DRAFT, DRAFTING, drafted, "draft"))
    fitting = Fitting(where, steps, said)
    fitting.thread.start()
    return fitting


def launch(where: Path, said: list[str] | None = None) -> Fitting:
    """The build continued, in the background: what the board's button starts, carrying the receipt so far."""
    fitting = Fitting(where, [Step(LAUNCH, LAUNCHING, launched, "launch")], said)
    fitting.thread.start()
    return fitting


def init_flag(parser: argparse.ArgumentParser) -> None:
    """`generate --init` / `--no-init`, declared where the run itself is.

    `default=None` on both halves, so that "nobody said" is one value rather than two — the same shape, and
    for the same reason, as `adopt`'s pair: a store_false defaulting to True and a store_true defaulting to
    None would share a destination and whichever argparse applied last would decide what unset looked like.
    """
    init = parser.add_mutually_exclusive_group()
    init.add_argument(
        "--init", action="store_true", dest="run_init", default=None,
        help="run ./init in the new project when it is made (the default when the questions were asked here). "
             "It installs Spec Kit, so it needs the network",
    )
    init.add_argument(
        "--no-init", action="store_false", dest="run_init", default=None,
        help="do not run ./init; leave it as the next step (the default for a scripted run)",
    )

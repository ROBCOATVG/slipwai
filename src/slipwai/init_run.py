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
import os
import re
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .process_alive import alive
from .session_log import Folder
from .shell_environment import login_environment

# budget: 540 — one runner for every child the board starts: assessment of a feature, and runs of steps that go on
# and an adopted repository's ./init
# through: `./init`, the draft, the surfaces, the launch and the fleet's cast-off and stop. Each is four
# lines of command, prose and verdict beside the others, which is what makes them comparable; split by
# step they would be five modules of twelve lines and one import list each.
# it: `./init`, the draft, the launch and the cast-off. A module per step would be four copies of the pty,
# the tail and the receipt, which is the duplication the steps were made one runner to avoid.

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


def command(harness: str | None = None, repository: str | None = None,
            extensions: tuple[str, ...] = ()) -> list[str]:
    """`./init`, with the agent named where somebody has named one, the forge where somebody has, and the
    extensions somebody checked.

    Unnamed, Spec Kit keeps its own question — which is right where there is a terminal to ask it in and
    wrong everywhere else, so the caller that has no terminal is the one that passes a harness. The
    repository is the same shape of answer for the same reason: a project with a production target
    configures its pipeline on the repository it is pushed to, and `./init` asks for that over `/dev/tty`.

    **The extensions are the third of those and the one nothing was passing.** `./init`'s menu reads
    `/dev/tty` and prints nothing where there is none, so every `./init` this board has ever run elected
    nothing — silently, because an empty capture is indistinguishable from a person checking no boxes.
    A `--extension` given here is an explicit answer, and `./init` never second-guesses one.
    """
    return [f"./{SCRIPT}", *(["--integration", harness] if harness else []),
            *(["--repository", repository] if repository else []),
            *(word for key in extensions for word in ("--extension", key))]


def announced(root: Path, harness: str | None, repository: str | None = None,
              extensions: tuple[str, ...] = ()) -> str:
    """The line said before it starts, wherever it is about to start.

    The whole command, extensions included, because that is what makes an election visible: a person who
    checked three boxes sees the three flags go by, and one who checked none sees that too.
    """
    return (f"Running {' '.join(command(harness, repository, extensions))} in {root} — it installs Spec Kit "
            f"for the coding agent, so it reaches the network once, here.")


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
    #: Whether a failure ends the run there. The gate's does not: the baseline its red first run writes is
    #: still committed, and the run still ends failed.
    stops: bool = True


def init_step(where: Path, harness: str, repository: str | None,
              extensions: tuple[str, ...] = ()) -> Step:
    return Step(command(harness, repository, extensions), announced(where, harness, repository, extensions),
                lambda code: ended(code, harness, repository), "init")


#: The step after `./init` where a PRD came with the answers: the constitution and the first specification,
#: drafted by the agent in a headless session (`make draft`, `scripts/agents/draft.py`), and then a stop.
#: The board shows the specification's existence as a button, and nothing is built until it is pressed —
#: a specification somebody has read is the line between what the agent drafts and what runs unattended.
DRAFT = ["make", "draft"]
DRAFTING = ("Drafting the constitution and the first specification from docs/prd.md — `make draft`, a headless "
            "session of the coding agent in the project. It stops at the specification: read it, then "
            "Continue the build.")
#: What the Draw the surfaces button runs: the first half of `/mockups` — the research, the wireframes and
#: the storyboard — in a headless session, and then a stop. The second half is a person looking at one
#: surface at a time, which is the stage rather than a step on the way to it, and is why nothing here marks
#: anything approved. Before the model deliberately: `project/ladder.py` has the review there, because a
#: surface nobody has seen becomes a read model, a route and a set of tests, and all three cost more to
#: move than a drawing does.
SURFACES = ["make", "surfaces"]
#: What approving a storyboard starts on an event-modelling project: the model, and then a stop. The chart
#: is drawn from the model, so this does not launch.
MODEL = ["make", "model-next"]
MODELLING = ("Modelling — `make model-next`: the event model from the approved storyboard, in a headless "
             "session. It stops at the model. The chart waits until that exists.")
DRAWING = ("Drawing the surfaces — `make surfaces`: the research, the wireframes and the storyboard in a "
           "headless session of the coding agent. It stops at the storyboard, which is where you come in: "
           "nothing is approved by a session nobody was in.")
ASSESS = ["make", "assess"]
ASSESSING = ("Assessing the next feature — `make assess`: Spec Kit decides whether the idea handed to /sail "
             "deserves a specification, and writes one only when the verdict is go.")
#: What the button runs: the chart and the split in a second session, `/cruise` enabled, the fleet cast off.
LAUNCH = ["make", "launch"]
LAUNCHING = ("Continuing the build — `make launch`: the chart and the split in a headless session, then /cruise "
             "enabled and the fleet cast off. The streams on this board are the fleet; a captain that parks is "
             "waiting on you.")


#: What the Cast off button runs: `fleet.py start`, through the Makefile — the harbourmaster and a captain
#: per fairway the telegraph allows, and the lines that say which were lit and which are waiting for a berth.
CRUISE = ["make", "cruise"]
CRUISING = ("Casting off — `make cruise`: the harbourmaster and a captain per fairway, as many at once as the "
            "telegraph allows. What was lit, and what waits for a berth, is said below.")


#: What the Stop button runs: `fleet.py stop`, through the Makefile. Asking, not killing — a captain stops
#: at its next boundary, which is what leaves the worktree, the branch and the deck log in a state the next
#: cast-off can pick up. A fleet killed mid-stage is a slice half typed with nothing saying so.
STOP = ["make", "cruise-stop"]
STOPPING = ("Stopping the fleet — `make cruise-stop`: the harbourmaster and every captain are asked to stop. "
            "A captain finishes the stage it is on and stops at the boundary, so this is not instant and "
            "nothing is lost. Cast off again when you want it going.")


def cruised(code: int) -> str:
    if code == 0:
        return "`make cruise` is done. The streams below are the fleet; `make cruise-watch` is the seat beside it."
    return f"`make cruise` exited {code}; nothing was cast off. Its last lines say why — the telegraph, usually."


def stopped(code: int) -> str:
    if code == 0:
        return ("`make cruise-stop` is done: every captain has been asked to stop and will, at its next "
                "boundary. The Streams card says when each has.")
    return (f"`make cruise-stop` exited {code}. Its last lines say why; `make cruise-status` in the project "
            f"says what is still running.")


def drafted(code: int) -> str:
    if code == 0:
        return ("`make draft` is done. The specification is under specs/: read it, and Continue the build charts "
                "and splits it and casts off.")
    return (f"`make draft` exited {code}; the project is made and `./init` has run either way. Fix what it named "
            f"and run `make draft` in the project, or write the specification with the agent.")


def drew(code: int) -> str:
    if code == 0:
        return ("`make surfaces` is done. The storyboard is below: open it, then Approve or Disapprove it "
                "on this page. That verdict is what the model and the chart read.")
    return (f"`make surfaces` exited {code}; nothing was drawn and nothing was approved. Its last lines say "
            f"why. **No rule to make target** means this project was generated before the stage had one: "
            f"`slipwai migrate` carries it in, and `/mockups` in the agent does the whole stage by hand "
            f"meanwhile.")


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
        # One per child, rooted at the project, so a path reads as it sits there and a run of writes lists
        # under one name: `session_log` says what the card is told and why.
        folder = Folder(self.where)
        while True:
            try:
                chunk = os.read(reading, 4096)
            except OSError:  # how a pseudo-terminal says end of file, rather than an empty read
                break
            if not chunk:
                break
            *lines, held = re.split(r"\r\n|\r|\n", held + chunk.decode("utf-8", "replace"))
            for line in lines:
                for said in folder.fold(ANSI.sub("", line).rstrip()):
                    self.say(said)
        if held.strip():
            for said in folder.fold(ANSI.sub("", held).rstrip()):
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
        self.run_steps(self.steps)

    def run_steps(self, steps: list[Step], final: bool = True, announced: bool = True) -> int:
        """`steps` run in order, ending at the first that fails; the exit status. With `final` the last one's end
        is this run's end — a run that goes on to more steps after these passes False."""
        failed = 0
        for index, step in enumerate(steps):
            with self.lock:
                self.step = step.key
            if index or not announced:
                self.say(step.announced)
            last = final and index == len(steps) - 1
            try:
                child, reading, ours = self.child(step.argv)
            except OSError as fault:
                self.say(f"{' '.join(step.argv)} could not be run here: {fault}", code=1)
                return 1
            with child:  # closed and waited on by the context manager, so a long run leaks no pipe
                self.read(reading)
                code = child.wait()
            if ours:
                os.close(reading)
            ends = bool(code) and step.stops
            self.say(step.ended(code), code=(code or failed) if ends or last else None)
            if ends:
                return code
            failed = failed or code
        return failed

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
          repository: str | None = None, prd: bool = False, extensions: tuple[str, ...] = ()) -> Fitting:
    """`./init` begun in the background — and the draft after it, where a PRD came with the answers and an
    agent was named to draft with. Returned rather than awaited: what it says is read by polling."""
    steps = [init_step(where, harness, repository, extensions)] if harness else []
    if steps and prd:
        steps.append(Step(DRAFT, DRAFTING, drafted, "draft"))
    fitting = Fitting(where, steps, said)
    fitting.thread.start()
    return fitting


def adopted(where: Path, delivery: str, harness: str | None, said: list[str] | None = None,
            extensions: tuple[str, ...] = ()) -> Fitting:
    """`./<delivery>/init` begun in a repository the board has just adopted, as `start` begins a generated
    project's: the adoption is committed already, and this is the step after it that needs the network. The
    `extensions` checked are elected here, because `./init`'s own menu reads a terminal a child has none of."""
    script = f"./{delivery}/{SCRIPT}" if delivery not in ("", ".") else f"./{SCRIPT}"
    steps = []
    if harness:
        argv = [script, "--integration", harness, *(word for key in extensions for word in ("--extension", key))]
        steps.append(Step(argv, f"Running {' '.join(argv)} in {where} — it installs Spec Kit for the coding "
                                "agent, so it reaches the network once, here.",
                          lambda code: ("" if code == 0 else
                                        f"`{' '.join(argv)}` exited {code}, and the adoption is committed and "
                                        "unaffected. Run it again when whatever stopped it is fixed."), "init"))
        # Committed as one change of its own: left uncommitted, every later step that generates refused the tree
        # (`add-service` undoes itself with `git clean`, so it will not run over files nobody committed).
        steps.append(Step(["git", "add", "-A"], "", lambda code: "", "init"))
        steps.append(Step(["git", "commit", "-q", "-m", f"Install Spec Kit and the agent's projections ({script})"],
                          "", lambda code: (f"`{' '.join(argv)}` is done, and what it wrote is committed as one "
                                            "change. `slipwai adopt --next` says what is left."
                                            if code == 0 else f"Committing what `{' '.join(argv)}` wrote stopped "
                                            f"({code}); commit it yourself before the next step."), "init"))
    fitting = Fitting(where, steps, said)
    fitting.thread.start()
    return fitting


def cast_off(where: Path, said: list[str] | None = None) -> Fitting:
    """The fleet started, in the background: what the board's Cast off button starts."""
    fitting = Fitting(where, [Step(CRUISE, CRUISING, cruised, "cruise")], said)
    fitting.thread.start()
    return fitting


def stop(where: Path, said: list[str] | None = None) -> Fitting:
    """The fleet asked to stop, in the background: what the board's Stop button starts."""
    fitting = Fitting(where, [Step(STOP, STOPPING, stopped, "stop")], said)
    fitting.thread.start()
    return fitting


def assessed(code: int) -> str:
    if code == 0:
        return "`make assess` is done. Read the verdict, and the specification when one was written."
    return (f"`make assess` exited {code}. Its last lines say why; `make assess SLUG=<slug>` in the project "
            "retries it.")


def assess(where: Path, slug: str, said: list[str] | None = None) -> Fitting:
    """One captured idea assessed, in the background: what the voyage's next-feature button starts."""
    fitting = Fitting(where, [Step([*ASSESS, f"SLUG={slug}"], ASSESSING, assessed, "assess")], said)
    fitting.thread.start()
    return fitting


TRIAGE = ["make", "triage"]
TRIAGING = ("Reading your feedback — `make triage`: a headless session proposes where each thing you said goes. "
            "It changes nothing; each proposal waits for you on the Feedback card.")


def triaged(code: int) -> str:
    if code == 0:
        return "`make triage` is done. Each proposal is on the Feedback card, waiting for you to confirm it."
    return f"`make triage` exited {code}. Its last lines say why; Triage on the Feedback card tries again."


def triage(where: Path, said: list[str] | None = None) -> Fitting:
    """The feedback nobody has proposed a route for, read in the background: what Send on the board starts."""
    fitting = Fitting(where, [Step(TRIAGE, TRIAGING, triaged, "triage")], said)
    fitting.thread.start()
    return fitting


def draw(where: Path, said: list[str] | None = None, feature: str = "") -> Fitting:
    """The surfaces drawn, in the background: what the board's Draw the surfaces button starts.

    `feature` names the one to draw, which a redraw after a disapproval needs: `make surfaces` on its own
    draws the first specification, and the storyboard turned down may not be that one.
    """
    argv = [*SURFACES, f"FEATURE={feature}"] if feature else SURFACES
    fitting = Fitting(where, [Step(argv, DRAWING, drew, "surfaces")], said)
    fitting.thread.start()
    return fitting


def began_model(code: int) -> str:
    if code == 0:
        return ("`make model-next` is done. The model is under docs/event-model/. Continue the build charts "
                "it once a slice is named there.")
    return (f"`make model-next` exited {code}. Its last lines say why. **No rule to make target** means this "
            f"project was generated before approving a storyboard started the model: `slipwai migrate` "
            f"carries the target in.")


#: The steps a project runs on its own and says it is running, by the pid file each writes: which step, and
#: what a window that did not start it can say about it.
OUTSIDE = (("model-next.pid", "model", "Modelling is running in this project. This window has not got its log."),
           ("surfaces.pid", "surfaces", "Drawing the surfaces is running in this project. This window has not got "
                                        "its log."))


def outside_session(root: Path) -> dict | None:
    """A model or drawing step still alive in this project, read from the pid file its script writes.

    The board that started it may have gone, or a person or another session ran `make model-next` or `make
    surfaces` without one. The lines it printed are not this window's, so what this returns is that the step
    is running — which is what keeps a page from reading a storyboard being redrawn as one that is stuck.
    """
    for name, step, said in OUTSIDE:
        # The first line is the pid; the drawing writes when it started on the next, so its seconds are real.
        try:
            lines = (root / ".slipwai" / name).read_text(encoding="utf-8").split()
            pid = int(lines[0])
        except (OSError, ValueError, IndexError):
            continue
        try:
            seconds = round(max(0.0, time.time() - float(lines[1])), 1)
        except (ValueError, IndexError):
            seconds = 0
        if alive(pid):
            return {"where": str(root), "lines": [said], "step": step, "at": 1, "seconds": seconds,
                    "done": False, "code": None}
    return None


def begin_model(where: Path, said: list[str] | None = None) -> Fitting:
    """The model begun, in the background: what approving a storyboard starts on an event-modelling project."""
    fitting = Fitting(where, [Step(MODEL, MODELLING, began_model, "model")], said)
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

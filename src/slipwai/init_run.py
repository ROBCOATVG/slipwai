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
import subprocess
import threading
from pathlib import Path

#: What the board says where nobody chose an agent to hand the project to. `./init` is still the next step,
#: and the project is still where the board is now looking: declining the run is not declining the landing.
DECLINED = ("./init was not run. It is the next step, in a terminal: `./init` asks which coding agent gets "
            "the skills and commands, installs Spec Kit, and then `make verify` is the gate.")

#: What a generated project calls it, at its root. `adopt` reaches a delivery directory's copy and spells the
#: path itself; a project the keel generated has this one and no other.
SCRIPT = "init"


def command(harness: str | None = None) -> list[str]:
    """`./init`, with the agent named where somebody has named one.

    Unnamed, Spec Kit keeps its own question — which is right where there is a terminal to ask it in and
    wrong everywhere else, so the caller that has no terminal is the one that passes a harness.
    """
    return [f"./{SCRIPT}", *(["--integration", harness] if harness else [])]


def announced(root: Path, harness: str | None) -> str:
    """The line said before it starts, wherever it is about to start."""
    return (f"Running {' '.join(command(harness))} in {root} — it installs Spec Kit for the coding agent, "
            f"so it reaches the network once, here.")


def ended(code: int, harness: str | None) -> str:
    """The line said after it stops, which is a different line when it did not work."""
    if code == 0:
        return f"`{' '.join(command(harness))}` is done. `make verify` is the gate, and it is green on a new tree."
    return (f"`{' '.join(command(harness))}` exited {code}, and the project is written and committed either way: "
            f"it is a step of its own, which is why it runs after. Run it again when whatever stopped it is fixed.")


def here(root: Path, harness: str | None = None) -> int:
    """`./init` as a child of this terminal, sharing its standard input so Spec Kit can ask its question."""
    print(f"\n{announced(root, harness)}")
    done = subprocess.run(command(harness), cwd=root, check=False)
    print(ended(done.returncode, harness))
    return done.returncode


class Fitting:
    """One `./init` running somewhere nobody is watching the terminal, and everything it has said so far.

    Lines rather than a stream: the board polls, and a poll answers with what has been said since the line
    the asker last had. The lock is around the list and the status because the reader is the server's thread
    and the writer is this one, and a tail that occasionally lost its last line would be the kind of fault
    nobody can reproduce.
    """

    def __init__(self, where: Path, harness: str | None = None, said: list[str] | None = None) -> None:
        self.where = where
        self.harness = harness
        self.lines: list[str] = [*(said or []),
                                 announced(where, harness) if harness else DECLINED]
        self.code: int | None = None
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self.run, daemon=True)

    def run(self) -> None:
        """The child, read a line at a time until it ends. Its own failure to start is a line like any other:
        a board that showed nothing where `./init` could not be executed would be a board hiding the answer.

        Nothing to run is also a finished run: the board still lands in the project and still says what was
        made, and a receipt that only appeared when a child happened to be started would be the one thing
        missing on the path somebody chose deliberately.
        """
        if not self.harness:
            with self.lock:
                self.code = 0
            return
        try:
            child = subprocess.Popen(command(self.harness), cwd=self.where, stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT, text=True, bufsize=1, errors="replace")
        except OSError as fault:
            self.say(f"{' '.join(command(self.harness))} could not be run here: {fault}", code=1)
            return
        with child:  # closed and waited on by the context manager, so a long run leaks no pipe
            for line in child.stdout or []:
                self.say(line.rstrip("\n"))
            code = child.wait()
        self.say(ended(code, self.harness), code=code)

    def say(self, line: str, code: int | None = None) -> None:
        with self.lock:
            self.lines.append(line)
            if code is not None:
                self.code = code

    def said(self, since: int = 0) -> dict:
        """What has been said after the `since`th line, how many there are now, and whether it has stopped."""
        with self.lock:
            return {"where": str(self.where), "lines": self.lines[max(since, 0):], "at": len(self.lines),
                    "done": self.code is not None, "code": self.code}


def start(where: Path, harness: str | None = None, said: list[str] | None = None) -> Fitting:
    """`./init` begun in the background. Returned rather than awaited: what it says is read by polling."""
    fitting = Fitting(where, harness, said)
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

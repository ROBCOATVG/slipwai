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
from pathlib import Path

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


class Fitting:
    """One `./init` running somewhere nobody is watching the terminal, and everything it has said so far.

    Lines rather than a stream: the board polls, and a poll answers with what has been said since the line
    the asker last had. The lock is around the list and the status because the reader is the server's thread
    and the writer is this one, and a tail that occasionally lost its last line would be the kind of fault
    nobody can reproduce.
    """

    def __init__(self, where: Path, harness: str | None = None, said: list[str] | None = None,
                 repository: str | None = None) -> None:
        self.where = where
        self.harness = harness
        self.repository = repository
        self.lines: list[str] = [*(said or []),
                                 announced(where, harness, repository) if harness else DECLINED]
        self.dropped = 0  # lines said and since let go of, so `since` keeps meaning the same thing
        self.code: int | None = None
        self.began = time.monotonic()
        self.stopped: float | None = None
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self.run, daemon=True)

    def child(self) -> tuple[subprocess.Popen[bytes], int, bool]:
        """The child, the descriptor its output is read from, and whether that descriptor is ours to close.

        Through a pseudo-terminal wherever this machine has one, which is not a nicety. `./init` is a shell
        script that shells out to pip, to uv and to Spec Kit, and every one of those line-buffers to a
        terminal and block-buffers to a pipe: down a pipe the card showed two lines for two minutes and then
        everything at once, which is the opposite of watching something run. Windows has no pty and gets the
        pipe it always had.
        """
        env = {**os.environ, **PLAIN}
        shape: dict = {"cwd": self.where, "stdin": subprocess.DEVNULL, "stderr": subprocess.STDOUT, "env": env}
        argv = command(self.harness, self.repository)
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
                self.say(ANSI.sub("", line).rstrip())
        if held.strip():
            self.say(ANSI.sub("", held).rstrip())

    def run(self) -> None:
        """The child, read a line at a time until it ends. Its own failure to start is a line like any other:
        a board that showed nothing where `./init` could not be executed would be a board hiding the answer.

        Nothing to run is also a finished run: the board still lands in the project and still says what was
        made, and a receipt that only appeared when a child happened to be started would be the one thing
        missing on the path somebody chose deliberately.
        """
        if not self.harness:
            self.stop(0)
            return
        try:
            child, reading, ours = self.child()
        except OSError as fault:
            self.say(f"{' '.join(command(self.harness, self.repository))} could not be run here: {fault}",
                     code=1)
            return
        with child:  # closed and waited on by the context manager, so a long run leaks no pipe
            self.read(reading)
            code = child.wait()
        if ours:
            os.close(reading)
        self.say(ended(code, self.harness, self.repository), code=code)

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
            return {"where": str(self.where), "lines": self.lines[kept:],
                    "at": self.dropped + len(self.lines),
                    "seconds": round((self.stopped or time.monotonic()) - self.began, 1),
                    "done": self.code is not None, "code": self.code}


def start(where: Path, harness: str | None = None, said: list[str] | None = None,
          repository: str | None = None) -> Fitting:
    """`./init` begun in the background. Returned rather than awaited: what it says is read by polling."""
    fitting = Fitting(where, harness, said, repository)
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

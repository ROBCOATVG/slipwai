"""A stage of the voyage run as a session over the Agent Client Protocol, in the project, from the board.

The draft, the surfaces, the model and the rest are each one prompt to the project's coding agent: "run
the /draft command". Headless, that prompt is a child process the board tails — one line at a time, no way
to be asked anything, a kill to stop. Over the protocol it is a session the board can see into and speak
to: the agent's words and tool calls as lines on the receipt the board already shows, a permission the
policy cannot grant and a question from the agent as cards the person answers, and a stop that is the
protocol's cancel. A stage that can ask does not have to assume, which is the number this phase chases.

One rule goes with every stage's prompt: ask the person what only they can decide, one thing at a time;
assume what the folder already settles, and write either down. The toolkit's headless path is untouched —
`make draft` from a terminal runs as it did — and a project whose agent has no launch row runs its stages
through it from the board as well.
"""
from __future__ import annotations

import contextlib
import os
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .board_agent import BoardAgent
from .board_settings import Launch, chosen, read
from .harness import acp_environment
from .logs import run_dir
from .shell_environment import login_environment

#: Where the project keeps a stage's session: its id and the agent's stderr, under the board's own folder.
KEPT = "stages"
#: Turns kept for the page; a stage says less than a conversation does.
HELD = 400
#: What every stage is told beside its command, so that it asks instead of assuming where only a person can say.
ASKING = ("Where a choice is only the person's to make — what the product is for, who it is for, what must not "
          "change — ask them, one question at a time, and write down what they decide. Where the documents in "
          "this project already settle a question, do not ask it; where they are silent on something you must "
          "decide to go on, decide it, and write it down as an assumption where the command says to.")
#: And what every stage is told about where it is: a session the board started, after `./init` projected
#: this harness's commands, skills and delegate types. AGENTS.md's first step — check, `make agents`, start
#: a new session — read as an order to stop, and one agent stopped at it before drafting a line.
SET_UP = ("This session was started by the board after `./init` projected this harness's commands, skills "
          "and delegate types, so AGENTS.md's first step is already met: do not run `make agents`, and do not "
          "stop to start a new session. Do the command's work here, in this session.")


def prompt_for(command: str, argument: str = "") -> str:
    """What a stage asks: the words that make any agent read the command's file and follow it. The slash form
    is the one harness's and the protocol has no flag for it, so every agent is asked the long way."""
    tail = f", with `{argument}` as its argument" if argument else "; it is given no argument"
    return (f"Run the /{command} command: read commands/{command}.md and follow it exactly as written{tail}."
            f"\n\n{ASKING}\n\n{SET_UP}")


def launchable(root: Path) -> Launch | None:
    """The agent a stage in this project would run through, or `None` where the headless path is the way."""
    found = chosen(read(), root, login_environment().get("PATH"))
    return found if found is not None and found.able else None


class StageSession:
    """One stage over the protocol: run by a step in place of a child, said into the step's lines, and its
    cards kept here for the page."""

    def __init__(self, root: Path, command: str, argument: str = "", launch: Launch | None = None,
                 limit: float = 1800.0, prompt: str = "", before: Callable[[], str] | None = None,
                 after: Callable[[], str] | None = None, pid: str = "", stage: str | None = None) -> None:
        self.root, self.command, self.argument, self.limit = Path(root), command, argument, limit
        self.launch = launch
        #: The words to ask with, for a stage whose script carries its own prompt rather than a command file;
        #: empty, the stage is asked to run its command. Either way the asking rule rides under them.
        self.prompt = prompt
        #: Why the stage cannot start, asked before anything is launched; and what the stage left undone,
        #: asked after the agent ended its turn. Each answers a sentence, or nothing where all is well.
        self.before, self.after = before, after
        #: A pid file under `.slipwai/run/`, as the toolkit's script writes one, so another window of this
        #: project sees the stage running; and what the session is told it is, for the hooks it fires.
        self.pid, self.stage = pid, command if stage is None else stage
        self.turns: list[dict[str, Any]] = []
        self.dropped = 0
        self.lock = threading.Lock()
        self.agent: BoardAgent | None = None
        self.lines: Any = None  # the fitting's `say`, while the stage runs
        self.done = False

    def say(self, role: str, kind: str, text: str, more: dict[str, Any] | None) -> None:
        """A turn from the agent: kept for the page's cards, and the ones that are words or work said as
        lines on the receipt, where the board's step log already is."""
        with self.lock:
            self.turns.append({"role": role, "kind": kind, "text": text, **(more or {})})
            if len(self.turns) > HELD:
                cut = len(self.turns) - HELD
                del self.turns[:cut]
                self.dropped += cut
        if self.lines is None:
            return
        if kind == "text":
            self.lines(text)
        elif kind == "tool":
            path = (more or {}).get("tool", {}).get("path", "")
            self.lines(f"· {text}" + (f"  {self.short(path)}" if path else ""))
        elif kind == "error":
            self.lines(f"! {text}")
        elif kind == "permission":
            self.lines(f"? {text} — waiting on you, on the board")
        elif kind == "question":
            self.lines(f"? {text} — waiting on your answer, on the board")

    def short(self, path: str) -> str:
        try:
            return Path(path).resolve().relative_to(self.root.resolve()).as_posix()
        except ValueError:
            return path

    def run(self, fitting: Any) -> int:
        """The stage to its end: the exit status a child would have given. Zero where the agent ended its turn,
        one where it was stopped, faulted or refused."""
        launch = self.launch or launchable(self.root)
        if launch is None:
            fitting.say("No agent this board can launch; the stage would have run headless.")
            return 2
        if (refused := self.before() if self.before else ""):
            fitting.say(refused)
            self.done = True
            return 2
        self.lines = fitting.say
        fitting.stage = self
        return self.session(fitting, launch, self.words(), first=True)

    def follow(self, fitting: Any, message: str) -> int:
        """What the person said after the stage ended — an answer to a question the agent asked in its words
        rather than on a card, or one more thing to do — as one more turn of the same session, loaded from
        where the stage kept it, its lines on the same receipt."""
        launch = self.launch or launchable(self.root)
        if launch is None:
            fitting.say("No agent this board can launch, so there is no session to say that to.")
            return 2
        self.done = False
        self.lines = fitting.say
        return self.session(fitting, launch, message, first=False)

    def session(self, fitting: Any, launch: Launch, words: str, first: bool) -> int:
        """The session begun or loaded, one turn of `words`, and closed: zero where the agent ended its turn."""
        marker = run_dir(self.root) / self.pid if self.pid else None
        try:
            if marker is not None:
                marker.parent.mkdir(parents=True, exist_ok=True)
                marker.write_text(f"{os.getpid()}\n{time.time():.0f}\n", encoding="utf-8")
            env = {**login_environment(root=self.root), **acp_environment(launch.key)}
            if self.stage:
                env["SLIPWAI_STAGE"] = self.stage
            self.agent = BoardAgent(launch, self.root, "agent", self.say, kept=run_dir(self.root) / KEPT / self.command,
                                    env=env)
            if first:
                self.agent.begin()
                model = self.agent.model
                fitting.say(f"On {self.agent.named}, over the Agent Client Protocol"
                            + (f", model {model}." if model else "."))
            else:
                # A load replays the conversation, which the receipt already shows; it is kept off the lines.
                self.lines = None
                loaded = self.agent.begin()
                self.lines = fitting.say
                if not loaded:
                    fitting.say("! The stage's session could not be loaded; this reply starts a new one.")
            stop = self.agent.turn(words, self.limit)
            if stop == "end_turn" and self.after and (left := self.after()):
                fitting.say(f"! {left}")
                stop = "short"
        except Exception as fault:  # noqa: BLE001 — a stage that raised would leave the run with no end
            fitting.say(f"! The session could not run: {fault}")
            stop = "fault"
        finally:
            if self.agent is not None:
                self.agent.close()
            if marker is not None:
                with contextlib.suppress(OSError):
                    marker.unlink()
            self.done = True
        return 0 if stop == "end_turn" else 1

    def words(self) -> str:
        return f"{self.prompt}\n\n{ASKING}\n\n{SET_UP}" if self.prompt else prompt_for(self.command, self.argument)

    def answer(self, number: str, answer: str | None) -> bool:
        return self.agent is not None and self.agent.answer(number, answer)

    def cancel(self) -> str:
        if self.agent is not None:
            self.agent.cancel()
        return "stopped"

    def said(self, since: int = 0) -> dict[str, Any]:
        with self.lock:
            held = max(since - self.dropped, 0)
            return {"turns": self.turns[held:], "at": self.dropped + len(self.turns), "done": self.done,
                    "command": self.command}


EMPTY = {"turns": [], "at": 0, "done": True, "command": ""}


def kept_stage(root: Path) -> str:
    """The stage whose session this project kept most recently, by its command; empty where none was kept.
    A board restarted after a stage has lost the run, and this is what it can still carry on."""
    try:
        kept = [one for one in (run_dir(root) / KEPT).iterdir() if (one / "session").is_file()]
    except OSError:
        return ""
    return max(kept, key=lambda one: (one / "session").stat().st_mtime).name if kept else ""


def running(bridge: Any) -> StageSession | None:
    fitting = bridge.fitting
    return getattr(fitting, "stage", None) if fitting is not None else None


def route_get(bridge: Any, where: str, query: str) -> bool:
    """`/stage.json`: the running stage's turns after `since`, for the cards on the board."""
    if where != "/stage.json":
        return False
    import json
    from urllib.parse import parse_qs

    since = int((parse_qs(query).get("since") or ["0"])[0] or 0)
    stage = running(bridge)
    bridge.send(200, json.dumps(stage.said(since) if stage else EMPTY), "application/json; charset=utf-8")
    return True


def route_post(bridge: Any, where: str, held: dict) -> bool:
    """A card's answer, a stop for the running stage, or a reply to one that has ended, from the board."""
    if where not in ("/stage/answer", "/stage/cancel", "/stage/say"):
        return False
    stage = running(bridge)
    if stage is None:
        bridge.send(400, "no stage is running", "text/plain; charset=utf-8")
        return True
    if where == "/stage/say":
        message = str(held.get("message") or "").strip()
        if not message:
            bridge.send(400, "say something first", "text/plain; charset=utf-8")
        elif not bridge.fitting.reply(message):
            bridge.send(409, "the stage is still going; what it asks is answered on its cards",
                        "text/plain; charset=utf-8")
        else:
            bridge.send(200, "said", "text/plain; charset=utf-8")
        return True
    if where == "/stage/cancel":
        bridge.send(200, stage.cancel(), "text/plain; charset=utf-8")
        return True
    given = None if held.get("decline") else held.get("option") or held.get("answer")
    if not stage.answer(str(held.get("id") or ""), None if given is None else str(given)):
        bridge.send(400, "nothing is waiting on that answer", "text/plain; charset=utf-8")
        return True
    bridge.send(200, "answered", "text/plain; charset=utf-8")
    return True

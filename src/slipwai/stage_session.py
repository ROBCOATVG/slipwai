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

# budget: 410 — a stage run, a turn of conversation and a message queued for one, and the routes that answer them
# — the card, the stop, what is said, Carry on and Discard — beside the session they act on; and what a stage
# says where its agent's handshake is refused for want of a sign-in, which names that agent and how to switch.
import contextlib
import os
import re
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from . import drawing_budget, stage_talk
from .acp import SIGNED_OUT, Fault
from .board_agent import BoardAgent
from .board_settings import Launch, chosen, read
from .drawn import fingerprints, withdraw
from .harness import acp_environment, from_spec_kit
from .logs import run_dir
from .review_reading import DECLARE
from .shell_environment import login_environment
from .stage_talk import KEPT

# `KEPT` is where the project keeps a stage's session — its id, the agent's stderr, and what was said to it.
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
#: What rides under a person's words once the stage has run: a turn of conversation records what is decided
#: rather than only saying it, and a verdict stays the person's. After a rule and beginning `The board`, so a
#: stand-in agent and a person reading the replay both see the person's words first and whole.
TALKING = ("The board started this turn because the person said the above to you about the stage you ran. "
           "Answer it. Where they ask to see or change something, change it now, in the files the stage "
           "wrote. Where they decide something — answer a question you left open, settle a finding — write "
           "it down in this turn where the command says such things are kept, and mark the question "
           "answered where you asked it; saying it is not recording it. Never mark anything approved: "
           "that verdict is the person's, given on the board.")


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


def signed_out(root: Path, launch: Launch, fault: Exception) -> str:
    """What a stage says where its agent refused the handshake for want of a sign-in: which agent, why it is
    that one, and the two ways on. The agent's own words — "Authentication required" — said neither, and the
    step ended on them with nothing to press."""
    said = (f"{launch.name} refused to start the session: it is not signed in for the board ({fault}). Open "
            f"Settings and press Sign in under {launch.name} (press Make ready there first, if it shows no Sign "
            "in), then run the step again.")
    recorded, board = from_spec_kit(root), chosen(read())
    if recorded is not None and recorded.harness == launch.key and board is not None and board.key != launch.key:
        said += (f" {launch.name} is this project's agent because `./init` was run for it, and that comes before "
                 f"the {board.name} this board runs on: `./{init_of(root)} --integration {board.key}` hands the "
                 f"project's stages to {board.name} instead.")
    return said


def init_of(root: Path) -> str:
    """The project's `init`, as a path from its root: under the delivery folder in an adopted repository."""
    import json

    try:
        delivery = json.loads((root / "project.json").read_text(encoding="utf-8"))["layout"]["delivery"]
    except (OSError, ValueError, KeyError, TypeError):
        delivery = ""
    return f"{delivery}/init" if isinstance(delivery, str) and delivery not in ("", ".") else "init"


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
        #: A turn of conversation under way, whose turns are kept in the stage's file; and a load replaying
        #: one, whose turns are not, being kept already.
        self.talking = self.loading = False
        #: What the person said while the stage ran: kept, and said to it when its turn ends.
        self.queue: list[dict[str, Any]] = []
        #: Whether the turn that ended last was ended by the person's Stop: then nothing starts by itself.
        self.cancelled = False

    def say(self, role: str, kind: str, text: str, more: dict[str, Any] | None) -> None:
        """A turn from the agent: kept for the page's cards, and the ones that are words or work said as
        lines on the receipt, where the board's step log already is."""
        with self.lock:
            self.turns.append({"role": role, "kind": kind, "text": text, **(more or {})})
            if len(self.turns) > HELD:
                cut = len(self.turns) - HELD
                del self.turns[:cut]
                self.dropped += cut
        if self.talking and not self.loading:
            stage_talk.add(self.root, self.command, {"role": role, "kind": kind, "text": text, **(more or {})})
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
        self.cancelled = False
        return self.session(fitting, launch, self.words(), first=True)

    def follow(self, fitting: Any, message: str, kept: bool = False) -> int:
        """What the person said after the stage ended — an answer to a question the agent asked in its words
        rather than on a card, or one more thing to do — as one more turn of the same session, loaded from
        where the stage kept it, its lines on the same receipt. `kept` where the words are in the stage's file
        already, having been queued while it ran.

        Every turn is kept beside the session (`stage_talk`), and a page the turn changed loses its verdict:
        a state approved before somebody asked for it to be drawn differently is a state nobody has seen."""
        if not kept:
            stage_talk.said(self.root, self.command, message)
        # Every message a person's — delivered now or queued before — holds the board again, whatever was
        # said to carry on in between: an Approve pressed while it waited is not an answer to it.
        stage_talk.hold(self.root, self.command)
        self.cancelled = False
        launch = self.launch or launchable(self.root)
        if launch is None:
            nobody = "No agent this board can launch, so there is no session to say that to."
            fitting.say(nobody)
            stage_talk.add(self.root, self.command, {"role": "agent", "kind": "error", "text": nobody})
            return 2
        self.done, self.talking = False, True
        self.lines = fitting.say
        before = fingerprints(self.root)
        try:
            return self.session(fitting, launch, f"{message}\n\n---\n{TALKING}", first=False)
        finally:
            self.talking = False
            gone = withdraw(self.root, before)
            if gone:
                said = ("The verdict on what this changed no longer stands, so it waits on yours again: "
                        + "; ".join(gone) + ".")
                fitting.say(f"! {said}")
                stage_talk.add(self.root, self.command, {"role": "agent", "kind": "error", "text": said})

    def queued(self, message: str) -> None:
        """What the person said while the stage was still going: kept, shown as waiting, said at its end.
        Called under the run's lock, so the run cannot end between the asking and the keeping."""
        self.queue.append(stage_talk.said(self.root, self.command, message, queued=True))

    def requeue(self, ident: str, message: str) -> None:
        """A message kept and not delivered — after a Stop, or a restart — put back to be said under its id."""
        if all(one["id"] != ident for one in self.queue):
            self.queue.append({"id": ident, "text": message})
        stage_talk.hold(self.root, self.command)

    def waiting(self) -> str:
        """What was queued, taken for the turn that says it: the person's messages in the order said."""
        held, self.queue = self.queue, []
        if held:
            stage_talk.add(self.root, self.command, {"kind": "delivered", "ids": [one["id"] for one in held]})
        return "\n\n".join(one["text"] for one in held)

    def doing(self) -> str:
        """What the stage is doing now, in a line: its latest call, or the start of what it last said."""
        with self.lock:
            for turn in reversed(self.turns):
                if turn["kind"] in ("tool", "tool_update") and turn["text"]:
                    path = turn.get("tool", {}).get("path", "")
                    return turn["text"][:120] + (f" · {self.short(path)}" if path else "")
                if turn["kind"] == "text" and turn["role"] != "person":
                    return turn["text"].splitlines()[0][:120] if turn["text"] else ""
        return ""

    def session(self, fitting: Any, launch: Launch, words: str, first: bool) -> int:
        """The session begun or loaded, one turn of `words`, and closed: zero where the agent ended its turn."""
        marker = run_dir(self.root) / self.pid if self.pid else None
        try:
            if marker is not None:
                marker.parent.mkdir(parents=True, exist_ok=True)
                # The ceiling on the third line, as the project's script writes it, so the board's clock can
                # say how far into its minutes a drawing is.
                marker.write_text(f"{os.getpid()}\n{time.time():.0f}\n{self.limit:.0f}\n", encoding="utf-8")
            env = {**login_environment(root=self.root), **acp_environment(launch.key)}
            if self.stage:
                env["SLIPWAI_STAGE"] = self.stage
            if self.command == "mockups":  # told its minutes, as the headless drawing is: it plans to them
                env.update(drawing_budget.told(self.limit))
            self.agent = BoardAgent(launch, self.root, "agent", self.say, kept=run_dir(self.root) / KEPT / self.command,
                                    env=env)
            if first:
                self.agent.begin()
                model = self.agent.model
                fitting.say(f"On {self.agent.named}, over the Agent Client Protocol"
                            + (f", model {model}." if model else "."))
            else:
                # A load replays the conversation, which the receipt already shows; it is kept off the lines,
                # and out of the conversation's own file, which has it.
                self.lines, self.loading = None, True
                try:
                    loaded = self.agent.begin()
                finally:
                    self.lines, self.loading = fitting.say, False
                if not loaded:
                    fitting.say("! The stage's session could not be loaded; this reply starts a new one.")
            stop = self.agent.turn(words, self.limit)
            if stop == "end_turn" and self.after and (left := self.after()):
                fitting.say(f"! {left}")
                stop = "short"
        except Fault as fault:
            fitting.say(f"! {signed_out(self.root, launch, fault)}" if fault.code == SIGNED_OUT else
                        f"! The session could not run: {fault}")
            stop = "fault"
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
        if self.prompt:
            return f"{self.prompt}\n\n{ASKING}\n\n{SET_UP}"
        # The drawing is told the two lines here as well as in `/mockups`, so a project whose command page is
        # older than this board's still writes them.
        return prompt_for(self.command, self.argument) + (f"\n\n{DECLARE}" if self.command == "mockups" else "")

    def answer(self, number: str, answer: str | None) -> bool:
        return self.agent is not None and self.agent.answer(number, answer)

    def cancel(self) -> str:
        self.cancelled = True
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
    """A card's answer, a stop for the running stage, something said to a stage — while it runs, queued for the
    end of its turn — or the person's word to carry on, from the board."""
    if where == "/stage/carry-on":
        if waiting := stage_talk.waiting_anywhere(bridge.root):  # the same rule as Approve
            stage, fitting = running(bridge), bridge.fitting
            going = ({one["id"] for one in stage.queue} if stage is not None and fitting is not None
                     and not fitting.said(10 ** 9)["done"] else set())
            behind = all(one["id"] in going for one in waiting)
            bridge.send(409, "something you said is queued behind the turn under way: it will be said when this "
                             "turn ends, and you can carry on after that" if behind else
                             "something you said has not been said to the stage yet: say it now, or discard it, "
                             "before you carry on", "text/plain; charset=utf-8")
            return True
        let = stage_talk.release(bridge.root)
        bridge.send(200, "carrying on" if let else "nothing was held", "text/plain; charset=utf-8")
        return True
    if where == "/stage/discard":
        command, ident = str(held.get("command") or ""), str(held.get("id") or "")
        if not stage_talk.known(command) or not stage_talk.discard(bridge.root, command, ident):
            bridge.send(400, "nothing waiting to be said goes by that id", "text/plain; charset=utf-8")
            return True
        stage = running(bridge)
        if stage is not None and stage.command == command:
            stage.queue = [one for one in stage.queue if one["id"] != ident]
        bridge.send(200, "discarded", "text/plain; charset=utf-8")
        return True
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
        else:  # `resend` is a kept message's id, said again by the person's Say it now
            resend = str(held.get("resend") or "")
            resend = resend if re.fullmatch(r"[0-9a-f]{12}", resend) else ""
            bridge.send(200, bridge.fitting.tell(message, resend) or "said", "text/plain; charset=utf-8")
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

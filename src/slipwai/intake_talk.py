"""Handing over a further feature on the board: one conversation with the project's agent, ending in one idea.

A project with its first feature had no way, on the board, to hand over the next document: the person left for
a terminal and gave it to `/sail`. This is that step as a conversation on the Next features tab, on the
console's shape (`console.py`) — turns behind a lock, a poll with `since`, the agent's session over the Agent
Client Protocol through `board_agent.py` — and on whichever agent the Settings tab names. There is no print-mode
path: with nothing the board can launch it says so, and `/sail` is still there.

**It does what `/sail` does at intake and no more.** The agent reads what the person said and attached, reads
the project to see what is already specified, asks what only the person can say, and says when the idea is one
clear thing. It does not assess, specify, chart, split or implement, and it does not answer whether this is a
new feature: that yes is the *Continue the next feature* button's, afterwards.

**It can read and it cannot write.** The session is the console's kind: every tool call the agent asks leave
for that is not a read or a search is refused by the board's policy (`BoardAgent.refuse`). What reaches
`docs/intake/` is written by the board, through `project/intake.py`'s `capture` and nothing else, when the
person presses *Capture this idea* after the agent has said the idea is ready: the request in the person's own
first words, the documents they attached, and the rest of the conversation where there was one.

**It outlives the page and the board.** What was said is kept under the run's folder beside the session's id,
so a reopened window shows it again and the agent's session is loaded for the next turn.
"""
from __future__ import annotations

import json
import shutil
import threading
from pathlib import Path

from .acp import kept_session
from .board_agent import BoardAgent
from .board_settings import Launch, chosen, read
from .errors import Busy
from .feedback import became_idea
from .harness import acp_environment
from .intake_document import TRANSCRIPT, held, staged, text_of
from .intake_overlap import overlap, warning
from .logs import run_dir
from .project.intake import PLACE, capture
from .shell_environment import login_environment, with_tools

#: Where a project keeps the hand-over under its run folder: the session's id, what was said, the documents.
KEPT = "handover"
SAID, DOCUMENTS = "said.jsonl", "documents"
#: How long one answer may take: a document read, a few of the project's files, a question.
LIMIT = 900
HELD = 400
#: The line the agent ends on when the idea is one clear thing; the page offers the capture once it is said.
READY = "The idea is ready to capture."
#: How the two things the board puts ahead of a person's words begin, so a replay shows only theirs.
ROLE_HEAD, ATTACHED_HEAD = "You are taking a further feature", "The person attached"
#: What the log says where no agent can be launched: not a turn of a conversation, and it says there is none.
NOBODY = ("There is no agent this board can run, so nobody reads this with you: nothing on the Settings tab can "
          "be launched. What you said and attached is kept. Capture it as an idea marked not discussed, which "
          "the assessment is told to ask about first; or make an agent ready on the Settings tab and say it "
          "again; or hand the feature to /sail in the agent.")
ROLE = f"""{ROLE_HEAD} for this project from a person at its board, as `/sail` does at intake, and no more.

Read what they say and any document they attach. Read `docs/prd.md` and `specs/` only as far as you need to see
what this project already has. Where what they handed over is more than one feature, or you cannot tell what is
being asked for, ask them: one question at a time, in plain words. Do not ask whether this is a new feature or a
change to an existing one, and do not decide it: say what you noticed, and leave the answer to them and to the
assessment that follows.

You can read and search this project and nothing else. Do not write, edit or run anything; do not assess,
specify, plan, chart, split or implement. The board writes the idea down, from the person's words and their
documents, when they press Capture this idea.

When what they handed over is one clear idea, say in two or three sentences what you understand it to be, and
end your reply with this line exactly: {READY}"""


def brought(name: str) -> str:
    """What stands for a person's words where they attached a document and typed nothing."""
    return f"Here is a document for a further feature: {name}. Read it first."


class Handover:
    """One conversation: what has been said and attached, whether the idea is ready, and the session behind it."""

    def __init__(self, root: Path, launch: Launch | None = None) -> None:
        self.root = root
        self.home = run_dir(root) / KEPT
        self.launch = launch  # a test hands one in; the board reads its settings
        self.agent: BoardAgent | None = None
        self.on = ""
        self.turns: list[dict] = []
        self.dropped = 0
        self.busy = self.ready = self.loading = False
        self.raw = False  # whether the board can launch no agent, as last looked: the capture is then a raw idea
        self.looked = threading.Event()  # set once that has been looked for
        self.looking = False
        self.overlap = ""  # what the documents share with the specifications, by id: said, never a refusal
        self.source = ""  # the feedback item this conversation was started from, where it was
        self.told = False  # whether a session that could not load the last one has been given the role again
        self.tried = False  # whether this object has tried to pick its kept session up
        self.login: dict[str, str] | None = None
        self.lock = threading.Lock()
        for one in self.kept():  # a board restarted: the conversation as it was kept
            self.show(one["role"], one["text"], one.get("kind", "text"))
            self.source = self.source or str(one.get("feedback") or "")
        self.weigh()

    def weigh(self) -> None:
        """The ids the documents held share with the specifications, read when a document arrives and not at
        every poll."""
        self.overlap = warning(overlap(self.root, held(self.home / DOCUMENTS)))

    def environment(self) -> dict[str, str]:
        if self.login is None:
            self.login = login_environment(root=self.root)
        return with_tools(self.login)

    def chosen(self) -> Launch | None:
        return self.launch or chosen(read(), self.root, self.environment().get("PATH"))

    def kept(self) -> list[dict]:
        """What was said, as the run folder keeps it: each person's and agent's words, and each attachment."""
        try:
            lines = (self.home / SAID).read_text(encoding="utf-8").splitlines()
        except OSError:
            return []
        return [json.loads(line) for line in lines if line.startswith("{")]

    def show(self, role: str, text: str, kind: str = "text", more: dict | None = None) -> None:
        """A turn for the page, and the ready line read off it: said by the agent, and unsaid by whatever
        the person says next."""
        with self.lock:
            self.turns.append({"role": role, "kind": kind, "text": text, **(more or {})})
            if len(self.turns) > HELD:
                cut = len(self.turns) - HELD
                del self.turns[:cut]
                self.dropped += cut
            if kind == "text":
                self.ready = role == "agent" and READY in text

    def say(self, role: str, text: str, kind: str = "text", **more: str) -> None:
        """A turn shown and kept: words, or an attachment's name."""
        self.home.mkdir(parents=True, exist_ok=True)
        with (self.home / SAID).open("a", encoding="utf-8") as out:
            out.write(json.dumps({"role": role, "kind": kind, "text": text, **more}) + "\n")
        self.show(role, text, kind)

    def heard(self, role: str, kind: str, text: str, more: dict | None) -> None:
        """A turn from the agent. A load replays the conversation, which the run folder already kept; a
        person's words are never taken from the agent's echo of them."""
        if self.loading or role == "person":
            return
        if kind == "text":
            self.say(role, text)
        else:
            self.show(role, text, kind, more)

    def said(self, since: int = 0) -> dict:
        with self.lock:
            at = max(since - self.dropped, 0)
            return {"turns": self.turns[at:], "at": self.dropped + len(self.turns), "busy": self.busy,
                    "ready": self.ready and not self.busy, "open": bool(self.turns), "agent": self.on,
                    "thinking": bool(self.agent is not None and self.agent.thinking),
                    "model": self.agent.model if self.agent is not None else "", "feedback": self.source,
                    "overlap": self.overlap, "raw": self.raw,
                    "documents": [one.name for one in held(self.home / DOCUMENTS)]}

    def ask(self, message: str, document: dict | None = None, feedback: str = "") -> str:
        """Say something to the session, with a document or without: checked whole before anything is kept.
        `feedback` is the item whose words these are, where Feedback's *New scope* opened the conversation."""
        message = text_of(message.strip(), "what you typed")
        name, text = (str(document.get("name") or ""), str(document.get("text") or "")) if document else ("", "")
        if not message and not (name or text):
            raise ValueError("say what the feature is, or choose its document")
        with self.lock:
            if self.busy:
                raise Busy("the last answer is still being written")
            path = staged(self.home / DOCUMENTS, name, text) if document else None
            self.busy = True
        first = not any(one["role"] == "person" for one in self.kept())
        # A document handed over with no words is the request: the idea is called what the document is.
        request = {"request": path.stem} if path is not None and not message and first else {}
        if feedback and first:
            request["feedback"], self.source = feedback, feedback
        self.say("person", message or brought(path.name if path else ""), **request)
        if path is not None:
            self.say("person", path.name, "attached")
            self.weigh()
        launch = self.chosen()
        self.raw = launch is None or not launch.able
        self.looked.set()
        if self.raw:
            self.show("agent", NOBODY, "error")
            with self.lock:
                self.busy = False
            return "no agent"
        note = (f"{ATTACHED_HEAD} a document, kept for you to read at `{path.relative_to(self.root).as_posix()}`."
                if path is not None else "")
        said = message or brought(path.name if path else "")
        threading.Thread(target=self.drive, args=(launch, said, note), daemon=True).start()
        return "asked"

    def begin(self, launch: Launch) -> None:
        """The agent started, read-only, and the kept session loaded where there is one."""
        if self.agent is None:
            self.agent = BoardAgent(launch, self.root, "agent", self.heard, reads_only=True, kept=self.home,
                                    env={**self.environment(), **acp_environment(launch.key)})
            self.on = launch.name
        if self.agent.session is None:
            self.loading = True
            try:
                self.agent.begin()
            finally:
                self.loading = False
        self.on = self.agent.named

    def drive(self, launch: Launch, message: str, note: str) -> None:
        """One turn over the protocol: the role at the head of a new session's first prompt, an attachment's
        place ahead of the words it came with. Never raises."""
        try:
            self.begin(launch)
            assert self.agent is not None
            role = "" if self.agent.loaded or self.told else ROLE
            head = "\n\n".join(one for one in (role, note) if one)
            self.told = True
            self.agent.turn(f"{head}\n\n---\n\n{message}" if head else message, LIMIT)
        except Exception as fault:  # noqa: BLE001 — a conversation stuck on busy is one nobody can type in
            self.show("agent", f"The session could not be started: {fault}", "error")
            self.agent = None
        finally:
            with self.lock:
                self.busy = False

    def resume(self) -> bool:
        """After a restart: the kept session loaded at once, so the window says which agent and model the
        conversation is on before the next message. True where a load was started."""
        with self.lock:
            if self.busy or self.tried or self.agent is not None or not self.turns or not kept_session(self.home):
                return False
            self.busy = self.tried = True  # once: a load that found no agent is not tried again at every poll
        threading.Thread(target=self.reload, daemon=True).start()
        return True

    def reload(self) -> None:
        try:
            launch = self.chosen()
            if launch is not None and launch.able:
                self.begin(launch)
        except Exception as fault:  # noqa: BLE001 — as `drive`
            self.show("agent", f"The conversation could not be picked up again: {fault}", "error")
            self.agent = None
        finally:
            with self.lock:
                self.busy = False

    def agentless(self) -> bool:
        """Whether the board can launch no agent, looked for now. Never raises: a machine that cannot be
        asked has not said there is nothing, and the conversation stays the way in."""
        try:
            launch = self.chosen()
            self.raw = launch is None or not launch.able
        except Exception:  # noqa: BLE001 — as `drive`
            self.raw = False
        self.looked.set()
        return self.raw

    def look(self) -> None:
        """Once, off the request, for a window nobody has typed in: the form says before the first word that
        there will be no conversation. A turn and a capture look again for themselves."""
        with self.lock:
            if self.looking or self.looked.is_set():
                return
            self.looking = True
        threading.Thread(target=self.agentless, daemon=True).start()

    def answer(self, number: str, answer: str | None) -> bool:
        return self.agent is not None and self.agent.answer(number, answer)

    def cancel(self) -> str:
        if self.agent is not None:
            self.agent.cancel()
        return "stopped"

    def reset(self) -> str:
        """End the conversation and let go of everything it held: the session, the words, the documents."""
        if self.agent is not None:
            self.agent.cancel()
            self.agent.forget()
            self.agent = None
        shutil.rmtree(self.home, ignore_errors=True)
        with self.lock:
            self.turns, self.dropped, self.ready, self.told = [], self.dropped + len(self.turns), False, False
            self.on = self.source = self.overlap = ""
        return "cleared"

    def capture(self) -> str:
        """The idea written under `docs/intake/`, by the one function that writes one, and the conversation
        let go of. Never `confirmed`: that is the person's next press."""
        with self.lock:
            if self.busy:
                raise Busy("the last answer is still being written")
            discussed = self.ready
        kept = [one for one in self.kept() if one.get("kind", "text") == "text"]
        mine = [one for one in kept if one["role"] == "person"]
        if not mine:
            raise ValueError("nothing to capture yet: say what the feature is, or attach its document")
        if not discussed:  # with an agent the conversation is the only way in: no capture skips it
            was = self.raw
            if not self.agentless():
                raise ValueError("an agent can be launched now: say it again, and capture it once the agent says "
                                 "the idea is ready" if was else "nothing to capture yet: capture it once the "
                                 "agent says the idea is ready")
        sources = held(self.home / DOCUMENTS)
        if len(mine) > 1:  # the person answered something: what was asked and said goes with the idea
            page = self.home / TRANSCRIPT
            page.write_text("# The hand-over conversation\n\n" + "".join(
                f"**{'Person' if one['role'] == 'person' else 'Agent'}:** {one['text']}\n\n" for one in kept),
                encoding="utf-8")
            sources.append(page)
        folder, _ = capture(self.root, mine[0].get("request") or mine[0]["text"], sources, discussed)
        marked = "" if discussed else (", marked not discussed: no agent read it with you, and the assessment "
                                       "is told to ask first")
        linked = became_idea(self.root, str(mine[0].get("feedback") or ""), folder)
        warned = f" {self.overlap}" if self.overlap else ""
        self.reset()
        return (f"captured {PLACE}/{folder.name}{marked}.{linked} Continue the next feature confirms it is a new "
                f"feature, and then assesses it.{warned}")


TALKS: dict[Path, Handover] = {}
_HELD = threading.Lock()


def for_root(root: Path) -> Handover:
    """One hand-over per project, as the console keeps one conversation per project."""
    with _HELD:
        return TALKS.setdefault(root.resolve(), Handover(root.resolve()))

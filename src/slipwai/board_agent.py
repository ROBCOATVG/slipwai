"""The session behind a board page, over the Agent Client Protocol: its updates as turns, its asks as cards.

A page's conversation — the first page's, the console's — keeps its own shape: turns behind a lock, a poll
with `since`. This is what sits between that shape and `acp.Session`. It begins or loads the agent's
session in the page's folder, puts each turn as a prompt, and turns every `session/update` into a turn
the page can draw: text as the agent's own words — a thought is not, its reasoning being its own, and only
sets `thinking` while it streams — a tool call as a card that its updates change in place, a plan as a
list. The two things the agent asks a client for become cards too — a permission the policy could not
grant on its own, a question — and the page answers them through
`answer`, which is what the protocol's callback was waiting on. A cancel is the protocol's, and every
card still open is answered with nothing.

What the page calls `say` is handed in: this never knows whose log it is writing to, only that a turn is
a role, a kind, a text and whatever else the kind carries.
"""
from __future__ import annotations

import itertools
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .acp import KEPT, Fault, Session, kept_session, once, policy
from .board_settings import Launch, offered, read

#: role, kind, text, and the fields the kind carries (`tool`, `plan`, `ask`).
Say = Callable[[str, str, str, "dict[str, Any] | None"], None]
#: How long a card waits for the person before it is answered with nothing. A permission left for an hour
#: is a turn nobody is coming back to.
ASK_LIMIT = 3600.0
#: The tool kinds a read-only session is allowed without asking; every other kind it is refused, and told.
READS = ("read", "search", "think", "fetch")


def located(tool_call: dict[str, Any]) -> str:
    """The first path a tool call names, or `''`."""
    for one in tool_call.get("locations") or []:
        if one.get("path"):
            return str(one["path"])
    return ""


#: The one field of a tool call's input that says what it is about, in the order it is looked for: a
#: command, a file, a name (a skill's), a pattern, a query, an address.
TELLING = ("command", "cmd", "filePath", "file_path", "path", "name", "skill", "pattern", "query", "url", "description")


def telling(update: dict[str, Any]) -> str:
    """What the call's input says it is about, in one short string, or `''`. An agent that titles a call
    with its tool's name — `shell`, `skill` — still sends the command or the name here."""
    given = update.get("rawInput")
    if not isinstance(given, dict):
        return ""
    for key in TELLING:
        value = given.get(key)
        if isinstance(value, (str, int, float)) and str(value).strip():
            return str(value).strip().splitlines()[0][:200]
    return ""


def tool_fields(update: dict[str, Any]) -> dict[str, Any]:
    return {"id": str(update.get("toolCallId") or ""), "kind": str(update.get("kind") or ""),
            "status": str(update.get("status") or ""), "path": located(update), "what": telling(update)}


class BoardAgent:
    """One agent session for one page's folder."""

    def __init__(self, launch: Launch, home: Path, who: str, say: Say, env: dict[str, str] | None = None,
                 kept: Path | None = None, reads_only: bool = False) -> None:
        self.launch, self.home, self.who, self.say, self.env = launch, Path(home), who, say, env
        self.kept = Path(kept) if kept is not None else self.home / KEPT
        self.reads_only = reads_only  # the console: a session that can read and cannot do, and says so
        self.session: Session | None = None
        self.loaded = False
        self.text: list[str] = []  # the agent's message under way, flushed at the next card or the turn's end
        #: Whether the last thing the agent streamed was a thought. Its reasoning is its own and is not a
        #: turn on the page; the page says "Thinking…" while this holds, so the wait is explained.
        self.thinking = False
        self.person: list[str] = []  # what the person said, as the agent replays it on a load
        self.asks: dict[str, dict[str, Any]] = {}
        self.count = itertools.count(1)
        self.lock = threading.Lock()

    # -- the session --------------------------------------------------------------------------------------

    def begin(self) -> bool:
        """Start the agent and load the session this folder kept, or begin a new one. True where loaded,
        which is the caller's cue that the role was already given. Raises `Fault` where the agent will not."""
        decide = self.refuse if self.reads_only else policy(self.home, self.permission)
        session = Session(list(self.launch.argv), self.home, self.update, decide, self.question, env=self.env,
                          kept=self.kept)
        session.start()
        kept = kept_session(self.kept)
        self.loaded = bool(kept) and session.load(kept)
        if not self.loaded:
            session.new()
        self.session = session
        self.flush()
        settings = read()
        offered(settings, self.launch.key, session.agent.config_options)
        wanted = settings.models.get(self.launch.key)
        shown = settings.offered.get(self.launch.key) or []
        if wanted and shown and wanted != shown[0].get("current"):
            try:
                session.set_option(str(shown[0].get("id")), wanted)
            except Fault as refused:
                self.say(self.who, "error", f"The model could not be set: {refused}", None)
        return self.loaded

    @property
    def named(self) -> str:
        """The agent as it named itself at the handshake, with its version, or the launch's name before that."""
        session = self.session
        if session is None or not session.agent.name:
            return self.launch.name
        return f"{session.agent.name} {session.agent.version}".strip()

    @property
    def model(self) -> str:
        """The model the session runs on, as the agent names it, or `''` where it offered no choice."""
        session = self.session
        if session is None:
            return ""
        for option in session.agent.config_options:
            if option.get("category") != "model":
                continue
            current = option.get("currentValue")
            for row in option.get("options") or []:
                for inner in (row.get("options") if "options" in row else [row]):
                    if inner.get("value") == current:
                        return str(inner.get("name") or current or "")
            return str(current or "")
        return ""

    def turn(self, text: str, timeout: float) -> str:
        """One prompt, and the stop reason; a fault is said as an error and the session let go of."""
        try:
            if self.session is None:
                self.begin()
            assert self.session is not None
            stop = self.session.prompt(text, timeout)
        except Fault as fault:
            self.flush()
            self.say(self.who, "error", str(fault), None)
            self.close()
            return "fault"
        self.flush()
        if stop == "cancelled":
            self.say(self.who, "error", "Stopped.", None)
        elif stop != "end_turn":
            self.say(self.who, "error", f"The agent stopped early: {stop.replace('_', ' ')}.", None)
        return stop

    def cancel(self) -> None:
        if self.session is not None:
            self.session.cancel()
        with self.lock:
            waiting = list(self.asks.values())
        for one in waiting:
            one["answer"] = None
            one["event"].set()

    def close(self) -> None:
        if self.session is not None:
            self.session.close()
            self.session = None

    def forget(self) -> None:
        """Close, and drop the kept id, so the next begin is a new session."""
        self.close()
        (self.kept / "session").unlink(missing_ok=True)

    def refuse(self, tool_call: dict[str, Any], options: list[dict[str, Any]]) -> str | None:
        """A read-only session's policy: a read or a search is allowed this once; anything else is refused
        with the agent's own reject option, and the page is told why."""
        if str(tool_call.get("kind") or "") in READS:
            return once(options)
        self.flush()
        self.say(self.who, "error", f"Refused: {tool_call.get('title') or 'a change'}. This session can read "
                 "and cannot do; what needs doing, you do from the board.", None)
        return next((str(o["optionId"]) for o in options if str(o.get("kind", "")).startswith("reject")), None)

    # -- updates ------------------------------------------------------------------------------------------

    def update(self, update: dict[str, Any]) -> None:
        kind = update.get("sessionUpdate")
        content = update.get("content") or {}
        if kind == "agent_thought_chunk":
            self.thinking = True
            return
        self.thinking = False
        if kind in ("agent_message_chunk", "user_message_chunk"):
            if content.get("type") == "text" and content.get("text"):
                {"agent_message_chunk": self.text, "user_message_chunk": self.person}[str(kind)].append(
                    str(content["text"]))
        elif kind == "tool_call":
            self.flush()
            self.say(self.who, "tool", str(update.get("title") or update.get("name") or "a tool"),
                     {"tool": tool_fields(update)})
        elif kind == "tool_call_update":
            self.flush()
            self.say(self.who, "tool_update", str(update.get("title") or ""), {"tool": tool_fields(update)})
        elif kind == "plan":
            self.flush()
            entries = [{"content": str(e.get("content") or ""), "status": str(e.get("status") or ""),
                        "priority": str(e.get("priority") or "")} for e in update.get("entries") or []]
            self.say(self.who, "plan", "\n".join(e["content"] for e in entries), {"plan": entries})
        elif kind == "notice":
            self.flush()
            self.say(self.who, "error", f"{update.get('title')}: {update.get('description') or ''}".strip(": "), None)

    def flush(self) -> None:
        """The words gathered so far, said as one turn each. Called at every card and at the turn's end,
        so a message arrives in the pieces the agent's own work divides it into."""
        self.thinking = False
        for role, kind, held in (("person", "text", self.person), (self.who, "text", self.text)):
            if held:
                words = "".join(held).strip()
                held.clear()
                if words:
                    self.say(role, kind, words, None)

    # -- the asks -----------------------------------------------------------------------------------------

    def wait(self, number: str) -> Any:
        waiting: dict[str, Any] = {"event": threading.Event(), "answer": None}
        with self.lock:
            self.asks[number] = waiting
        waiting["event"].wait(ASK_LIMIT)
        with self.lock:
            self.asks.pop(number, None)
        self.say(self.who, "answered", "", {"ask": {"id": number}})
        return waiting["answer"]

    def permission(self, tool_call: dict[str, Any], options: list[dict[str, Any]]) -> str | None:
        """A permission the policy did not grant: a card, and the option the person chose, or nothing."""
        number = f"p{next(self.count)}"
        self.flush()
        self.say(self.who, "permission", str(tool_call.get("title") or "The agent asks to go on"),
                 {"ask": {"id": number, "path": located(tool_call), "options": [
                     {"id": str(o.get("optionId")), "name": str(o.get("name") or o.get("optionId")),
                      "kind": str(o.get("kind") or "")} for o in options if o.get("optionId")]}})
        chosen = self.wait(number)
        return str(chosen) if chosen else None

    def question(self, params: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
        """A question from the agent: a card, and the person's answer under the field the agent named."""
        number = f"q{next(self.count)}"
        schema = params.get("requestedSchema") or {}
        field = next(iter((schema.get("properties") or {}).keys()), "answer")
        self.flush()
        self.say(self.who, "question", str(params.get("message") or "The agent has a question"),
                 {"ask": {"id": number, "field": str(field)}})
        answer = self.wait(number)
        if answer is None:
            return "decline", None
        return "accept", {str(field): str(answer)}

    def answer(self, number: str, answer: str | None) -> bool:
        """The person's answer to a card, by its id: an option id, a question's text, or nothing."""
        with self.lock:
            waiting = self.asks.get(number)
        if waiting is None:
            return False
        waiting["answer"] = answer
        waiting["event"].set()
        return True

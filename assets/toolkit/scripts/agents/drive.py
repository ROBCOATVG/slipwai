#!/usr/bin/env python3
"""A slice's session over the Agent Client Protocol, held open, with a process's face for the captain.

The captain watches a `/sail` session the way it watches any child: `poll`, `returncode`, `wait`, and an
`end` that reaches everything the session started. A session over the protocol (`acp.py`, the client carried
from the keel) is a thread here that spawns the agent, opens a session in the berth, sets the model where the
agent offers it, and asks — and shows that face to the watch, so the deck log stays the only thing the captain
believes. The agent's words and tool calls are printed a line at a time into the stream the fleet keeps.

**Held open.** A drive given a conversation (`talk.py`'s folder for its slice) does not close after its
prompt. One session, many prompts: the captain's retry is the next prompt into the same session rather than a
new agent reading the slice cold, and what a person says to the slice is delivered by this thread and nothing
else — `wait` when the turn under way ends, `interrupt` by cancelling it first. To the captain a turn's end is
`poll()` answering while the agent stays up: the end of *its* prompt, after any message that waited on it,
so the gate is read once the person has been answered. It closes when told to, when the agent dies, or on a
`pause` (once the turn is done) or a `stop` (at once), saving the session's id beside the conversation so the
next drive loads it where the agent can — and a stage that reviews starts fresh, because a reviewer that
carries the author's context has read nothing fresh. Without a conversation a drive is one prompt and
closes, which is the skipper's round.

**What the agent does is written down**: its tool calls as they finish, its plan, its last sentence to a
person, into the slice's activity log in the kinds the board reads — and every fact about a message on the
conversation's thread, of which this is the one writer.

Nobody is in the berth: a permission for a write inside it is allowed this once, and the rest goes through
`ruling`, which today refuses a permission outside it and declines a question — a stage that must ask a
person parks on a `question` line in the deck log, as it did. `ruling` is the seam the captain's own answer
replaces; the `ask` and its `answer` are on the thread either way.

The protocol is the default where the harness print mode would run has a launch the registry marks proven
and this machine can make; `sessions: print` in `.specify/cruise.json` keeps print mode, `sessions: protocol`
asks for it on any launch row, and `SLIPWAI_ACP` in the environment says first — `1` for the initialised
harness's row, any other value the command that starts an agent (the suite's stand-in).
"""
from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
import threading
from collections import deque
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import harness  # noqa: E402
import logs  # noqa: E402 — carried beside this script; it owns where the run's state lives
import talk  # noqa: E402 — the conversation's files, carried from the keel

VARIABLE = "SLIPWAI_ACP"
ON = ("1", "true", "yes", "on")
#: The project's own switch, set from the board: `sessions` in `.specify/cruise.json`.
CONFIG = ".specify/cruise.json"
#: A turn's ceiling, nominal: the captain's watch on the deck log is what ends a drive that stopped writing.
TURN = 7 * 24 * 3600.0
#: How often a held drive looks in its inbox. Short, because a person who pressed Interrupt is watching.
LOOK = 0.5
#: The most of a reply the thread keeps: an answer to a person, not the turn's whole transcript.
REPLY = 4000
#: The stages that start a fresh session when a drive opens on them, by `benchmark.py`'s names and the ones
#: they were renamed from: the reviews, the attacks and the hand's walk, each of which is meant to read the
#: slice with no memory of building it.
REVIEWS = ("gaps-lookout", "gaps", "review-mate", "review", "adversary-privateer", "adversary",
           "mutation-shipworm", "mutation", "demo-hand", "hand")
#: The tool kinds that change a file, said as an `edit` with its path; every other finished call is `ran`.
EDITS = ("edit", "delete", "move")
#: The size past which an activity log is cut back to its newest lines, as `session.py` does with its own.
ACTIVITY_LIMIT, ACTIVITY_KEEP = 1_000_000, 2000


def setting() -> str:
    """`sessions` in this project's `.specify/cruise.json`, `''` where it says nothing. Read under the project
    the harness module names now, which the suite points elsewhere."""
    try:
        said = json.loads((harness.ROOT / CONFIG).read_text(encoding="utf-8")).get("sessions")
    except (OSError, ValueError, AttributeError):
        return ""
    return said if isinstance(said, str) else ""


def switched_on() -> bool:
    """Whether this project asked for its captains' sessions over the protocol, on the board or by
    `/cruise-settings`; the variable, where set, still says first."""
    return setting() == "protocol"


def acp_launch(row: dict[str, Any] | None) -> list[str]:
    """The argv that starts this harness as an agent on this machine, or nothing where the registry records
    no launch row for it or the machine lacks what the row needs (`npx`, or the binary on PATH)."""
    launch = row.get("acp") if isinstance(row, dict) else None
    if not isinstance(launch, dict):
        return []
    npx, binary = launch.get("npx"), launch.get("binary")
    if isinstance(npx, dict):
        found = shutil.which("npx")
        return [found, "--yes", str(npx["package"]), *[str(a) for a in npx.get("args") or []]] if found else []
    if isinstance(binary, dict):
        found = shutil.which(str(binary.get("cmd") or ""))
        return [found, *[str(a) for a in binary.get("args") or []]] if found else []
    return []


def acp_environment(row: dict[str, Any] | None) -> dict[str, str]:
    """What the launch row says to set in the agent's environment, if anything."""
    launch = row.get("acp") if isinstance(row, dict) else None
    npx = launch.get("npx") if isinstance(launch, dict) else None
    return {str(k): str(v) for k, v in ((npx or {}).get("env") or {}).items()} if isinstance(npx, dict) else {}


def proven() -> tuple[list[str], dict[str, Any], str] | None:
    """The default: the harness print mode would run, over the protocol, where its registry row's launch is
    marked proven and this machine can make it. Nothing otherwise, and print mode runs as it did."""
    try:
        row, _said = harness.choose()
    except harness.NoHarness:
        return None
    launch = row.get("acp") if isinstance(row, dict) else None
    argv = acp_launch(row) if isinstance(launch, dict) and launch.get("proven") is True else []
    return (argv, row, f"agent: {row['name']}, over the Agent Client Protocol") if argv else None


def protocol() -> tuple[list[str], dict[str, Any] | None, str] | None:
    """Where this run takes the protocol: (the launch, the harness row or `None` for a named command, what was
    chosen) — or `None` where every session runs headless."""
    named = os.environ.get(VARIABLE, "").strip()
    chosen = setting()
    if not named and chosen == "protocol":
        named = "1"
    if not named:
        return proven() if chosen != "print" else None
    if named.lower() not in ON:
        # A Windows path is backslashes, which POSIX splitting reads as escapes and drops: kept as written.
        words = shlex.split(named.replace("\\", "\\\\") if os.name == "nt" else named)
        return words, None, f"{VARIABLE}: {named}, over the Agent Client Protocol"
    rows = harness.registry()
    for key in harness.installed_keys():
        argv = acp_launch(rows.get(key))
        if argv:
            return argv, rows[key], f"agent: {rows[key]['name']}, over the Agent Client Protocol"
    raise harness.NoHarness(f"sessions over the protocol were asked for ({VARIABLE}, or `sessions: protocol` in "
                            f".specify/cruise.json), and no initialised harness has a launch row this machine can "
                            f"make (scripts/agents/registry.json, `acp`)")


def reviewing(record: Path) -> bool:
    """Whether the newest stage `benchmark.py` bracketed in this slice's record is one that reads the slice
    fresh — open, or the last thing to have run."""
    try:
        stages = json.loads(Path(record).read_text(encoding="utf-8")).get("stages") or []
    except (OSError, ValueError, AttributeError):
        return False
    newest = stages[-1] if stages and isinstance(stages[-1], dict) else {}
    return str(newest.get("stage", "")) in REVIEWS


def ruling(ask: dict[str, Any]) -> dict[str, Any]:
    """What is said to something the agent asks mid-turn that the policy did not settle: `{"allow": bool,
    "why"}` for a permission, `{"action", "why"}` for a question. Nobody is in the berth, so a permission
    outside it is refused and a question declined. One function, so the captain's answer can take its place."""
    if ask.get("what") == "permission":
        return {"allow": False, "why": "outside the berth, and nobody is here to allow it"}
    return {"action": "decline", "why": "nobody is here; what a person must decide is a `question` line in the "
                                        "deck log"}


def say(line: str, err: bool = False) -> None:
    print(line, file=sys.stderr if err else sys.stdout, flush=True)


def message_prompt(message: dict[str, Any]) -> str:
    """What a delivered message is to the agent: who says it, and that it is a message, not the next stage."""
    who = str(message.get("from") or "person")
    who = "a person" if who == "person" else who
    return (f"A message for this slice from {who}:\n\n{message.get('text', '')}\n\nAnswer it in a few sentences. "
            f"Where it asks for a change to this slice's work, make the change in this berth as the ladder says; "
            f"otherwise carry on from where you were.")


class Drive:
    """One slice's session over the protocol, started on its own thread, watched like a process."""

    def __init__(self, argv: list[str], cwd: Path | str, env: dict[str, str], prompt: str,
                 model: str | None = None, kept: Path | None = None, conversation: Path | None = None,
                 activity: Path | None = None, fresh: bool = False, harness_key: str = "") -> None:
        import acp  # noqa: PLC0415 — carried beside this; imported here so a project without it fails at the drive, not the captain
        self.acp = acp
        self.cwd, self.model, self.env = Path(cwd), model, env
        self.home = Path(conversation) if conversation is not None else None
        self.activity, self.fresh, self.harness_key = activity, fresh, harness_key
        self.session = acp.Session(argv, self.cwd, self.update, acp.policy(self.cwd, self.refuse), self.decline,
                                   env=env, kept=Path(kept) if kept is not None else logs.run_dir(self.cwd) / "acp")
        self.held = ""  # the message chunk not yet ended by a newline
        self.text = ""  # everything the agent said this turn: a refusal's words, a reply
        self.code: int | None = None  # the captain's turn as a process's exit: published once nothing waits on it
        self.outcome: int | None = None  # the same, before any message that waited on the turn was delivered
        self.refusal: harness.Refusal | None = None
        self.prompts: deque[str] = deque([prompt])
        self.cond = threading.Condition()
        self.turning = False
        self.interrupting = False  # an interrupt asked the turn under way to cancel
        self.interrupted = False  # the captain's last turn was cancelled for a message, which costs it no attempt
        self.pausing: tuple[str, str] | None = None
        self.halted: tuple[str, str, str] | None = None  # ("paused" | "stopped", by, why)
        self.closing = False
        self.closed = False
        self.replaying = False
        self.talking = False  # a message's turn is under way: not silence, whatever the deck log says
        self.calls: dict[str, dict[str, Any]] = {}
        self.asks = 0
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()
        if self.home is not None:
            threading.Thread(target=self.look, daemon=True).start()

    # -- a process's face --------------------------------------------------------------------------------

    @property
    def pid(self) -> int:
        child = self.session.child
        return child.pid if child is not None else 0

    @property
    def returncode(self) -> int | None:
        return self.code

    @property
    def alive(self) -> bool:
        return self.thread.is_alive() and not self.closing

    def poll(self) -> int | None:
        return self.code

    def wait(self, timeout: float | None = None) -> int | None:
        with self.cond:
            self.cond.wait_for(lambda: self.code is not None, timeout)
        if self.code is None:
            raise subprocess.TimeoutExpired(self.session.argv, timeout or 0)
        return self.code

    def prompt(self, text: str) -> None:
        """The captain's next prompt into the same session, run once whatever is under way has ended."""
        with self.cond:
            self.code = self.outcome = None
            self.refusal, self.interrupted = None, False
            self.prompts.append(text)
            self.cond.notify_all()

    def terminate(self) -> None:
        self.session.cancel()

    def kill(self) -> None:
        self.session.close()

    def end(self) -> None:
        """The close: a turn under way cancelled, the session's id kept, the agent ended."""
        with self.cond:
            self.closing = True
            self.cond.notify_all()
        if self.turning:
            self.terminate()
        self.thread.join(30)
        if self.thread.is_alive():
            self.kill()
            self.thread.join()

    # -- the session -------------------------------------------------------------------------------------

    def run(self) -> None:
        try:
            self.session.start()
            self.open()
            self.pick()
            while self.next():
                pass
        except Exception as fault:  # noqa: BLE001 — a drive that raised would leave the captain polling for ever
            self.flush()
            say(f"session: {fault}", err=True)
            if self.refusal is None:
                self.refusal = harness.refusal(str(fault))
            self.outcome = 1
            self.undelivered(f"the agent ended before it was delivered: {fault}")
        finally:
            self.closing = True
            if self.session.exited is not None:
                self.undelivered(f"the agent exited ({self.session.exited}) before it was delivered")
            if self.home is not None:
                talk.save_session(self.home, self.session.session_id, self.harness_key)
            self.session.close()
            with self.cond:
                self.closed = True
                self.code = self.code if self.code is not None else (self.outcome if self.outcome is not None else 1)
                self.cond.notify_all()

    def open(self) -> None:
        """Load the session this slice closed with, where the agent can and the stage is not a review; a new
        one otherwise. The thread says which."""
        if self.home is None:
            self.session.new()
            return
        saved = "" if self.fresh else str(talk.saved_session(self.home).get("id") or "")
        loaded, why = False, ("a stage that reviews starts fresh" if self.fresh else "nothing was saved")
        if saved and not self.session.agent.load_session:
            why = "the agent cannot load a session"
        elif saved:
            self.replaying = True  # a load replays the history as updates: none of it is this turn's
            try:
                loaded = self.session.load(saved)
            except self.acp.Fault as fault:
                why = f"the agent would not load it: {fault}"
            finally:
                self.replaying = False
        if not loaded:
            self.session.new()
        talk.note(self.home, "session", id=self.session.session_id, loaded=loaded, why=None if loaded else why)

    def next(self) -> bool:
        """One thing: a message waiting, the captain's prompt, or the close. False once the drive is done."""
        with self.cond:
            while True:
                waiting = talk.queued(self.home) if self.home is not None and not self.pausing else []
                if self.closing or self.session.exited is not None:
                    return False
                if waiting or self.pausing or self.prompts:
                    break
                if self.outcome is not None and self.code is None:
                    self.code = self.outcome  # nothing waits on the captain's turn now: say it ended
                    self.cond.notify_all()
                if self.home is None:
                    return False  # one prompt, and closed
                self.cond.wait(LOOK)
        if self.pausing:
            by, why = self.pausing
            talk.note(self.home, "paused", by=by, why=why or None)
            self.halted = ("paused", by, why)
            return False
        if waiting:
            self.deliver(waiting[0])
        else:
            self.captain_turn(self.prompts.popleft())
        return True

    def turn(self, text: str, about: str) -> str:
        self.text, self.turning = "", True
        if self.home is not None:
            talk.note(self.home, "turn", state="started", about=about)
        try:
            stop = self.session.prompt(text, TURN)
        finally:
            self.turning = False
        self.flush()
        if self.home is not None:
            talk.note(self.home, "turn", state="cancelled" if stop == "cancelled" else "ended", stop=stop)
        last = next((line.strip() for line in reversed(self.text.splitlines()) if line.strip()), "")
        if last:
            self.record("said", last)
        say(f"session: the agent ended its turn: {stop}")
        return stop

    def captain_turn(self, text: str) -> None:
        stop = self.turn(text, "captain")
        if stop == "cancelled" and self.interrupting and self.halted is None:
            # Cancelled for a person's message, which is delivered next: not a run that failed.
            self.interrupting, self.interrupted, self.outcome = False, True, 0
            return
        if stop == "refusal":
            self.refusal = harness.refusal(self.text[-2000:])
        elif stop == "end_turn":
            # A limit said as the agent's last line and followed by an ordinary end of turn: the
            # session did not run, and a captain that read the stop reason spent an attempt on it.
            self.refusal = harness.closing_refusal(self.text[-2000:])
        self.outcome = 0 if stop == "end_turn" and self.refusal is None else 1

    def deliver(self, message: dict[str, Any]) -> None:
        assert self.home is not None
        ident = str(message["id"])
        talk.note(self.home, "delivered", id=ident, mode=str(message.get("mode") or "wait"))
        self.talking = True
        try:
            stop = self.turn(message_prompt(message), ident)
        except Exception:
            talk.note(self.home, "failed", id=ident, why="the agent ended before it answered")
            raise
        finally:
            self.talking = False
        self.interrupting = False
        words = self.text.strip()
        if words:
            talk.note(self.home, "reply", to=ident, text=words[-REPLY:], stop=stop)
        else:
            talk.note(self.home, "unaddressed", id=ident, stop=stop)

    def undelivered(self, why: str) -> None:
        if self.home is None:
            return
        for message in talk.queued(self.home):
            talk.note(self.home, "failed", id=str(message["id"]), why=why)

    # -- the inbox -----------------------------------------------------------------------------------------

    def look(self) -> None:
        """Read every new thing in the inbox while the drive is up, and act on the ones that steer it."""
        assert self.home is not None
        while not self.closed:
            for message in talk.unseen(self.home):
                self.heard(message)
            with self.cond:
                self.cond.wait(LOOK)

    def heard(self, message: dict[str, Any]) -> None:
        assert self.home is not None
        ident, kind = str(message["id"]), str(message.get("kind"))
        by, why = str(message.get("from") or "person"), str(message.get("text") or "")
        talk.note(self.home, "seen", id=ident)
        if kind == "stop":
            talk.note(self.home, "stopped", by=by, why=why or None)
            self.halted = ("stopped", by, why)
            self.end_soon()
        elif kind == "pause":
            self.pausing = (by, why)
        elif kind == "resume":
            if self.pausing is not None or talk.paused(self.home):
                self.pausing = None
                talk.note(self.home, "resumed", by=by)
        elif kind == "withdraw":
            of = str(message.get("of") or "")
            if of not in talk.ids(talk.thread(self.home), "delivered"):
                talk.note(self.home, "withdrawn", id=of)
        elif kind == "say" and message.get("mode") == "interrupt" and self.turning:
            self.interrupting = True
            self.terminate()
        with self.cond:
            self.cond.notify_all()

    def end_soon(self) -> None:
        with self.cond:
            self.closing = True
            self.cond.notify_all()
        if self.turning:
            self.terminate()

    # -- what the agent does ---------------------------------------------------------------------------------

    def pick(self) -> None:
        """The model `cruise.json` names, set where the agent offers it as a config option; the agent's own
        default otherwise, and said."""
        if not self.model:
            return
        for option in self.session.agent.config_options:
            if option.get("category") != "model":
                continue
            for value in option.get("options") or []:
                if self.model in (value.get("value"), value.get("name")):
                    self.session.set_option(str(option.get("id")), value.get("value"))
                    say(f"session: model {self.model}")
                    return
        say(f"session: the agent offers no model named {self.model}; its own default runs")

    def update(self, update: dict[str, Any]) -> None:
        if self.replaying:
            return
        kind = update.get("sessionUpdate")
        if kind == "agent_message_chunk":
            content = update.get("content") or {}
            if content.get("type") == "text":
                chunk = str(content.get("text") or "")
                self.held += chunk
                self.text += chunk
                while "\n" in self.held:
                    line, self.held = self.held.split("\n", 1)
                    say(line)
        elif kind in ("tool_call", "tool_call_update"):
            ident = str(update.get("toolCallId") or "")
            call = self.calls.setdefault(ident, {})
            call.update({key: value for key, value in update.items() if value not in (None, "", [])})
            if kind == "tool_call":
                self.flush()
                say(f"· {update.get('title') or update.get('kind') or 'tool'}")
            if call.get("status") in ("completed", "failed"):
                self.calls.pop(ident, None)
                self.finished(ident, call)
        elif kind == "plan":
            entries = [one for one in update.get("entries") or [] if isinstance(one, dict)]
            done = sum(1 for one in entries if one.get("status") == "completed")
            now = next((str(one.get("content", "")) for one in entries if one.get("status") == "in_progress"), "")
            self.record("plan", f"{done} of {len(entries)} done" + (f": {now}" if now else ""),
                        entries=[{"content": str(one.get("content", "")), "status": str(one.get("status", ""))}
                                 for one in entries])

    def finished(self, ident: str, call: dict[str, Any]) -> None:
        """A tool call that has ended, as the activity log says one: what it touched or what it was."""
        places = [str(one.get("path")) for one in call.get("locations") or [] if isinstance(one, dict) and one.get("path")]
        title = str(call.get("title") or call.get("kind") or "a tool")
        failed = call.get("status") == "failed"
        kind = "failed" if failed else ("edit" if call.get("kind") in EDITS and places else "ran")
        self.record(kind, places[0] if kind == "edit" else title, call=ident, tool=str(call.get("kind") or ""),
                    status=str(call.get("status")))

    def record(self, kind: str, what: str, **fields: Any) -> None:
        """One line in the slice's activity log, in `session.py`'s format; never raised."""
        if self.activity is None or not what.strip():
            return
        line = {"t": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), "fairway": self.env.get("SLIPWAI_FAIRWAY", ""),
                "slice": self.env.get("SLIPWAI_SLICE", ""), "stage": self.env.get("SLIPWAI_STAGE", ""),
                "agent": "session", "kind": kind, "what": " ".join(what.split())[:240],
                **{key: value for key, value in fields.items() if value not in (None, "")}}
        try:
            path = Path(self.activity)
            path.parent.mkdir(parents=True, exist_ok=True)
            with talk.WRITING, path.open("a", encoding="utf-8") as out:
                out.write(json.dumps(line, ensure_ascii=False) + "\n")
            if path.stat().st_size > ACTIVITY_LIMIT:
                kept = path.read_text(encoding="utf-8").splitlines()[-ACTIVITY_KEEP:]
                path.write_text("\n".join(kept) + "\n", encoding="utf-8")
        except OSError:
            return

    def flush(self) -> None:
        if self.held.strip():
            say(self.held)
        self.held = ""

    # -- what the agent asks -----------------------------------------------------------------------------------

    def asked(self, what: str, text: str, options: list[str]) -> tuple[str, dict[str, Any]]:
        self.asks += 1
        ident = f"ask-{self.asks}"
        answer = ruling({"id": ident, "what": what, "text": text, "options": options})
        if self.home is not None:
            talk.note(self.home, "ask", id=ident, what=what, text=text, options=options)
            said = ("allowed" if answer.get("allow") else "refused") if what == "permission" else str(answer.get("action"))
            talk.note(self.home, "answer", to=ident, by="rule", text=f"{said}: {answer.get('why', '')}")
        return ident, answer

    def refuse(self, tool_call: dict[str, Any], options: list[dict[str, Any]]) -> str | None:
        title = str(tool_call.get("title") or "a tool call")
        _, answer = self.asked("permission", title, [str(one.get("kind", "")) for one in options])
        wanted = "allow_once" if answer.get("allow") else "reject_once"
        say(f"session: {'allowed' if answer.get('allow') else 'refused'} {title} — {answer.get('why', '')}")
        return next((str(one["optionId"]) for one in options if one.get("kind") == wanted and "optionId" in one), None)

    def decline(self, params: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
        _, answer = self.asked("question", str(params.get("message") or ""), [])
        say(f"session: declined a question — {params.get('message') or ''} — {answer.get('why', '')}")
        return str(answer.get("action") or "decline"), None

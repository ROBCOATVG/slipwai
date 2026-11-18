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

**Bounded and held.** A message is delivered only while the captain waits on a turn, so its turn is under
the captain's watch and its stage bound; from a merge request to its answer the captain holds them, so no
commit rides to trunk past the gate. A person's message is believed only where the board signed it, and is
fenced off in the prompt. The agent runs in a process group of its own, ended when the captain exits, and
its pid is kept beside the conversation for the next captain to end where this one was killed outright.

The protocol is taken under `sessions: auto` in `.specify/cruise.json` where the harness print mode would
run has a launch the registry marks proven and this machine can make; a project that says nothing stays in
print mode, as it was before `auto` (a project is never switched by migrating); `print` keeps print mode, `protocol` asks for it on any launch row, and `SLIPWAI_ACP` in the environment says first — `1` for the initialised
harness's row, any other value the command that starts an agent (the suite's stand-in).
"""
from __future__ import annotations

import atexit
import contextlib
import json
import os
import secrets
import shlex
import shutil
import signal
import subprocess
import sys
import threading
import time
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
#: Where a held drive records the agent it started and the captain that started it, beside its conversation:
#: a captain killed outright runs no exit handler, and the next one for the stream ends what it left.
AGENT_PID = "agent.pid"
#: Every drive with an agent up in this process, ended when the process exits however it can.
LIVE: set[Drive] = set()


def end_group(pid: int, hard: bool = False) -> None:
    """End an agent and everything it started: it runs in a process group of its own. Windows has no groups,
    and ending the root alone left what it started running, holding its folder: there the tree is ended by
    its root, as `taskkill /T` ends one. Always with `/F`: a console process has no gentler stop to take, and
    `taskkill` without it ends nothing that has no window, which is every agent."""
    if os.name == "nt":  # pragma: no cover - the other platform's branch
        with contextlib.suppress(OSError, subprocess.SubprocessError):
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(pid)], capture_output=True, check=False, timeout=10)
        return
    try:
        os.killpg(pid, signal.SIGKILL if hard else signal.SIGTERM)
    except (OSError, ProcessLookupError):
        pass


@atexit.register
def end_all() -> None:
    """A captain that exits — a stop, a fault, the end of `--once` — takes its agents with it."""
    for held in list(LIVE):
        child = held.session.child
        if child is not None and child.poll() is None:
            end_group(child.pid)


def alive(pid: int) -> bool:
    """Whether that process is still running. Asked, never acted on: on Windows `os.kill(pid, 0)` is not a
    question but a Ctrl-C or `TerminateProcess` (`fleet.alive` says how that was learned), so there the
    process handle is asked instead, exactly as `fleet.alive` asks it."""
    if sys.platform == "win32":  # pragma: no cover - the other platform's branch
        import ctypes  # noqa: PLC0415 - only this branch needs it

        query_limited_information, still_active = 0x1000, 259
        kernel = ctypes.windll.kernel32
        handle = kernel.OpenProcess(query_limited_information, False, pid)
        if not handle:
            return False
        try:
            code = ctypes.c_ulong()
            if not kernel.GetExitCodeProcess(handle, ctypes.byref(code)):
                return False
            return code.value == still_active
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except (OSError, ProcessLookupError):
        return False
    return True


def identity(pid: int) -> str:
    """What says a pid is still the process it was: its start time and its command line, as `ps` gives them
    on macOS and Linux. `''` where it cannot be read — and then nothing is signalled on its strength.

    In the C locale, always: `lstart` is written in the locale's words (`Mo. 16 Nov.` under German), and a
    captain restarted under another locale would otherwise never recognise the agent it is looking for."""
    try:
        done = subprocess.run(["ps", "-o", "lstart=", "-o", "command=", "-p", str(pid)], capture_output=True,
                              text=True, timeout=5, check=False, env={**os.environ, "LC_ALL": "C", "LANG": "C"})
    except (OSError, subprocess.SubprocessError):
        return ""
    return " ".join(done.stdout.split()) if done.returncode == 0 else ""


def reap(conversations: Path) -> list[int]:
    """End every agent a captain that is no longer running left under this stream's conversations: the pids
    a drive recorded, where the captain that recorded them is gone and the process at the pid is still the
    agent — the same start and command line as were recorded beside it. A pid reused after a reboot, or one
    whose process cannot be read, is left alone. What was ended."""
    ended = []
    for path in sorted(Path(conversations).glob(f"*/{AGENT_PID}")):
        held = talk.read_json(path)
        if not isinstance(held, dict) or not all(isinstance(held.get(name), int) and not isinstance(held[name], bool)
                                                 and held[name] > 1 for name in ("pid", "captain")) \
                or not isinstance(held.get("identity"), str):
            continue  # not a record a drive wrote: nothing is signalled on its strength
        pid, captain, was = held["pid"], held["captain"], held["identity"]
        if captain == os.getpid():
            continue
        # The captain is still the captain only where it is the process that was recorded: a pid reused by
        # something else after it died would otherwise keep its agent from ever being ended.
        captain_was = held.get("captain_identity") if isinstance(held.get("captain_identity"), str) else ""
        if alive(captain) and (not captain_was or identity(captain) in (captain_was, "")):
            continue
        if not alive(pid):
            path.unlink(missing_ok=True)
            continue
        now = identity(pid)
        if not was or not now:
            continue  # cannot tell: the record is kept for a captain that can
        if now == was:
            end_group(pid)
            ended.append(pid)
        path.unlink(missing_ok=True)  # ended, or a definite stranger at the pid
    return ended


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


def words(named: str) -> list[str]:
    """A command a person named in the environment, as its words. A Windows path is backslashes, which POSIX
    splitting reads as escapes and drops, so there they are kept as written; elsewhere the split is POSIX's."""
    return shlex.split(named.replace("\\", "\\\\") if os.name == "nt" else named)


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


#: Said once a process: `auto` falling back to print mode, with why.
FELL_BACK: set[str] = set()


def proven() -> tuple[list[str], dict[str, Any], str] | None:
    """`auto`: the harness print mode would run, over the protocol, where its registry row's launch is marked
    proven and this machine can make it. Print mode otherwise, said once with why."""
    try:
        row, _said = harness.choose()
    except harness.NoHarness as none:
        return fell_back(f"no harness can run here ({none})")
    launch = row.get("acp") if isinstance(row, dict) else None
    if not isinstance(launch, dict) or launch.get("proven") is not True:
        return fell_back(f"the registry does not mark {row['name']}'s launch over the protocol proven")
    argv = acp_launch(row)
    if not argv:
        return fell_back(f"this machine cannot make {row['name']}'s launch over the protocol (`npx`, or its "
                         f"command, is not on PATH)")
    return argv, row, f"agent: {row['name']}, over the Agent Client Protocol"


def fell_back(why: str) -> None:
    if why not in FELL_BACK:
        FELL_BACK.add(why)
        say(f"sessions: auto runs in print mode — {why}")
    return None


def protocol() -> tuple[list[str], dict[str, Any] | None, str] | None:
    """Where this run takes the protocol: (the launch, the harness row or `None` for a named command, what was
    chosen) — or `None` where every session runs headless."""
    named = os.environ.get(VARIABLE, "").strip()
    chosen = setting()
    if not named and chosen == "protocol":
        named = "1"
    if not named:
        # `auto`: the protocol where the harness's launch is proven, print mode elsewhere. Nothing said is
        # print mode, exactly as before `auto` was: a project is never switched by migrating.
        return proven() if chosen == "auto" else None
    if named.lower() not in ON:
        return words(named), None, f"{VARIABLE}: {named}, over the Agent Client Protocol"
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
    held = talk.read_json(Path(record))
    stages = held.get("stages") if isinstance(held, dict) else None
    newest = stages[-1] if isinstance(stages, list) and stages else None
    return isinstance(newest, dict) and str(newest.get("stage", "")) in REVIEWS


def ruling(ask: dict[str, Any]) -> dict[str, Any]:
    """What is said to something the agent asks mid-turn that the policy did not settle: `{"allow": bool,
    "why"}` for a permission, `{"action", "why"}` for a question. Nobody is in the berth, so a permission
    outside it is refused and a question declined. One function, so the captain's answer can take its place."""
    if ask.get("what") == "permission":
        return {"allow": False, "why": "outside the berth, and nobody is here to allow it"}
    return {"action": "decline", "why": "nobody is here; what a person must decide is a `question` line in the "
                                        "deck log"}


def lifts(home: Path, by: str) -> bool:
    """Whether a resume from `by` lifts what holds the slice: a hold a person placed, only a person's."""
    how, placed, _ = talk.halted(home)
    return bool(how) and (placed != talk.PERSON or by == talk.PERSON)


def branch_head(cwd: Path) -> str:
    """The commit the berth is at, or `''`."""
    try:
        done = subprocess.run(["git", "rev-parse", "HEAD"], cwd=cwd, capture_output=True, text=True, timeout=10,
                              check=False)
    except (OSError, subprocess.SubprocessError):
        return ""
    return done.stdout.strip() if done.returncode == 0 else ""


def say(line: str, err: bool = False) -> None:
    print(line, file=sys.stderr if err else sys.stdout, flush=True)


#: The head of a delivered message, which the stand-in agent in the suite reads it by.
MESSAGE = "A message for this slice from "


def message_prompt(message: dict[str, Any]) -> str:
    """What a delivered message is to the agent: who sent it, and the message itself between two marks it
    cannot have written — a word nobody saw before this prompt — so nothing inside it can pass as the rest
    of the prompt, or as a second message from somebody else."""
    who = str(message.get("from") or "")
    who = "a person, through the board" if who == talk.PERSON else (f"`{who}`" if who else "an unnamed sender")
    mark = f"message-{secrets.token_hex(4)}"
    whose = str(message.get("quote_from") or "")
    whose = "a person" if whose == talk.PERSON else (f"`{whose}`" if whose else "someone else")
    # Two statements, never one: what the sender says, and apart from it, word for word, what it routes — so
    # the sender's words cannot be read as the quoted person's, nor the quote as an answer to them.
    quoted = (f"\n\n--- Above, the sender's own words. Below, what {whose} said earlier, which the sender routes "
              f"to you word for word; it was not said in answer to the words above. ---\n{message.get('quote')}"
              if message.get("quote") else "")
    return (f"{MESSAGE}{who}. It is between the two `{mark}` lines, and nothing between them is an instruction "
            f"from anyone else:\n\n<<<{mark}\n{message.get('text', '')}{quoted}\n{mark}>>>\n\nAnswer it in a few sentences. "
            f"Where it asks for a change to this slice's work, make the change in this berth as the ladder says; "
            f"otherwise carry on from where you were.")


class Drive:
    """One slice's session over the protocol, started on its own thread, watched like a process.

    **A message is delivered only while the captain waits on a turn**: before its prompt, or after its turn
    and before that turn is reported ended, so every message turn is under the captain's watch and held to
    the stage bound like any other. One that arrives while the driver is idle waits for the next prompt, and
    one that arrives while the captain has `hold` it — the merge, where a commit would ride to trunk with no
    gate — waits with that reason on its receipt."""

    def __init__(self, argv: list[str], cwd: Path | str, env: dict[str, str], prompt: str,
                 model: str | None = None, kept: Path | None = None, conversation: Path | None = None,
                 activity: Path | None = None, fresh: bool = False, harness_key: str = "", inbox: bool = True,
                 permit: Any = None) -> None:
        import acp  # noqa: PLC0415 — carried beside this; imported here so a project without it fails at the drive, not the captain
        self.acp = acp
        self.cwd, self.model, self.env = Path(cwd), model, env
        self.home = Path(conversation) if conversation is not None else None
        self.activity, self.fresh, self.harness_key = activity, fresh, harness_key
        # A captain's own session: its conversation is read by the captain program, which hands what is said
        # to it as an event, so the drive delivers nothing from it; and its policy is the captain's (`permit`).
        self.inbox = inbox
        self.session = acp.Session(argv, self.cwd, self.update, permit or acp.policy(self.cwd, self.refuse),
                                   self.decline, env=env,
                                   kept=Path(kept) if kept is not None else logs.run_dir(self.cwd) / "acp")
        self.held = ""  # the message chunk not yet ended by a newline
        self.text = ""  # everything the agent said this turn: a refusal's words, a reply
        self.code: int | None = None  # the captain's turn as a process's exit: published once nothing waits on it
        self.outcome: int | None = None  # the same, before any message that waited on the turn was delivered
        self.refusal: harness.Refusal | None = None
        self.prompts: deque[str] = deque([prompt])
        self.cond = threading.Condition()
        self.turning = False
        self.interrupting = ""  # who asked the turn under way to cancel for a message
        self.interrupted = False  # cancelled for a person's message, which costs the slice no attempt
        self.pausing: tuple[str, str, str] | None = None  # (id, by, why)
        self.halted: tuple[str, str, str] | None = None  # ("paused" | "stopped", by, why)
        self.halted_by = ""  # the id of the message that halted it
        self.holding = ""  # why messages are kept back now, where the captain said so
        self.silent = ""  # why the captain ended a turn that had gone quiet
        self.message_since: float | None = None  # when the message under way was delivered, by the clock
        self.message_commits = False  # a message's turn moved the branch: the gate is read again
        self.message_commits_person = False  # and the message whose turn moved it was a person's
        self.unlaunched = ""  # the agent could not be started at all, and why
        self.closing = False
        self.closed = False
        self.replaying = False
        self.calls: dict[str, dict[str, Any]] = {}
        self.asks = 0
        self.kept_back: set[str] = set()
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()
        if self.home is not None and self.inbox:
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
        """The captain's next prompt into the same session, run once whatever is under way has ended. Whatever
        was held for the merge is delivered ahead of it."""
        with self.cond:
            self.code = self.outcome = None
            self.refusal, self.interrupted, self.holding = None, False, ""
            self.prompts.append(text)
            self.cond.notify_all()

    def hold(self, why: str) -> None:
        """Keep messages back, saying why on each one's receipt, until the next prompt."""
        with self.cond:
            self.holding = why
            self.cond.notify_all()

    def silenced(self, why: str) -> None:
        """The captain's watch found the turn silent past its bound: a message under way fails with this."""
        self.silent = why
        self.end()

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
            try:
                self.session.start()
            except Exception as fault:
                self.unlaunched = str(fault)
                raise
            self.recorded()
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
            if self.home is not None and self.halted is not None and self.halted[0] == "stopped":
                talk.forget_session(self.home)  # a stop ends the session for good; a resume starts fresh
            elif self.home is not None:
                talk.save_session(self.home, self.session.session_id, self.harness_key)
            self.session.close()
            LIVE.discard(self)
            if self.home is not None:
                (self.home / AGENT_PID).unlink(missing_ok=True)
            with self.cond:
                self.closed = True
                self.code = self.code if self.code is not None else (self.outcome if self.outcome is not None else 1)
                self.cond.notify_all()

    def recorded(self) -> None:
        """The agent's pid and this captain's, where the next captain for the stream looks for what was left."""
        LIVE.add(self)
        child = self.session.child
        if self.home is not None and child is not None:
            self.home.mkdir(parents=True, exist_ok=True)
            said = json.dumps({"pid": child.pid, "captain": os.getpid(), "identity": identity(child.pid),
                               "captain_identity": identity(os.getpid())}) + "\n"
            (self.home / AGENT_PID).write_text(said, encoding="utf-8")

    def open(self) -> None:
        """Load the session this slice closed with, where the agent can, the stage is not a review and it was
        the same harness; a new one otherwise. The thread says which."""
        if self.home is None:
            self.session.new()
            return
        saved = {} if self.fresh else talk.saved_session(self.home)
        ident = str(saved.get("id") or "")
        loaded, why = False, ("a stage that reviews starts fresh" if self.fresh else "nothing was saved")
        if ident and str(saved.get("harness") or "") != self.harness_key:
            why = f"it was saved under another harness ({saved.get('harness') or 'none named'})"
        elif ident and not self.session.agent.load_session:
            why = "the agent cannot load a session"
        elif ident:
            self.replaying = True  # a load replays the history as updates: none of it is this turn's
            try:
                loaded = self.session.load(ident)
            except self.acp.Fault as fault:
                why = f"the agent would not load it: {fault}"
            finally:
                self.replaying = False
        if not loaded:
            self.session.new()
        talk.note(self.home, "session", id=self.session.session_id, loaded=loaded, why=None if loaded else why)

    def waiting(self) -> list[dict[str, Any]]:
        """The messages to deliver now: none while the captain is not waiting on a turn or has held them."""
        if self.home is None or self.pausing or not self.inbox:
            return []
        messages = talk.queued(self.home)
        if self.holding:
            for message in messages:
                if str(message["id"]) not in self.kept_back:
                    self.kept_back.add(str(message["id"]))
                    talk.note(self.home, "held", id=str(message["id"]), why=self.holding)
            return []
        captain_waits = bool(self.prompts) or (self.outcome is not None and self.code is None)
        return messages if captain_waits else []

    def next(self) -> bool:
        """One thing: a message waiting, the captain's prompt, or the close. False once the drive is done."""
        with self.cond:
            while True:
                if self.closing or self.session.exited is not None:
                    return False
                messages = self.waiting()
                if messages or self.pausing or self.prompts:
                    break
                if self.outcome is not None and self.code is None:
                    self.code = self.outcome  # nothing waits on the captain's turn now: say it ended
                    self.cond.notify_all()
                if self.home is None:
                    return False  # one prompt, and closed
                self.cond.wait(LOOK)
            if self.pausing:
                self.paused_now()
                return False
        if messages:
            self.deliver(messages[0])
        else:
            self.captain_turn(self.prompts.popleft())
        return True

    def paused_now(self) -> None:
        """A pause heard and not yet in force is in force now: at the end of the turn it waited for, or however
        else that turn ended — a bound that cancelled it among them, after which the captain reads the hold
        here (`captain.halted`) before it would run the slice again."""
        with self.cond:
            if self.pausing is None or self.home is None:
                return
            ident, by, why = self.pausing
            self.pausing = None
            talk.note(self.home, "paused", by=by, why=why or None)
            self.halted, self.halted_by = ("paused", by, why), ident

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
        if stop == "cancelled" and self.interrupting and self.halted is None and not self.silent:
            # Cancelled for a message, which is delivered next. A person's costs the slice no attempt; anyone
            # else's is a run that did not finish, so nothing but a person can keep a slice going round.
            self.interrupted = self.interrupting == talk.PERSON
            self.interrupting, self.outcome = "", 0 if self.interrupted else 1
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
        before, self.message_since = branch_head(self.cwd), time.monotonic()
        # Only a message delivered after the captain's turn ended can move the head under a gate already read:
        # one delivered ahead of the captain's prompt is before the ladder's turn, which reads the head after it.
        after_turn = self.outcome is not None
        try:
            stop = self.turn(message_prompt(message), ident)
        except Exception:
            talk.note(self.home, "failed", id=ident, why=self.silent or "the agent ended before it answered")
            talk.settle(self.home, ident)
            raise
        finally:
            self.message_since = None
            moved = after_turn and branch_head(self.cwd) != before
            self.message_commits = self.message_commits or moved
            # Only a person's message earns the gate's re-read at no attempt's cost; anyone else's is a run.
            self.message_commits_person = self.message_commits_person or (moved and message.get("from") == talk.PERSON)
        self.interrupting = ""
        words = self.text.strip()
        if self.silent:
            talk.note(self.home, "failed", id=ident, why=self.silent)
        elif words:
            talk.note(self.home, "reply", to=ident, text=words[-REPLY:], stop=stop)
        else:
            talk.note(self.home, "unaddressed", id=ident, stop=stop)
        talk.settle(self.home, ident)

    def undelivered(self, why: str) -> None:
        if self.home is None:
            return
        for message in talk.queued(self.home):
            talk.note(self.home, "failed", id=str(message["id"]), why=why)
            talk.settle(self.home, str(message["id"]))

    # -- the inbox -----------------------------------------------------------------------------------------

    def look(self) -> None:
        """Read every new thing in the inbox while the drive is up, and act on the ones that steer it."""
        assert self.home is not None
        while not self.closed:
            for path, why in talk.refused(self.home):
                talk.reject(self.home, path, why)
            for message in talk.unseen(self.home):
                self.heard(message)
            with self.cond:
                self.cond.wait(LOOK)

    def heard(self, message: dict[str, Any]) -> None:
        assert self.home is not None
        ident, kind = str(message["id"]), str(message.get("kind"))
        by, why = str(message.get("from") or ""), str(message.get("text") or "")
        talk.note(self.home, "seen", id=ident)
        if not talk.genuine(self.home, message):
            talk.note(self.home, "failed", id=ident, why="it says it is from a person and is not signed by the board")
            talk.settle(self.home, ident)
            return
        person_pausing = self.pausing is not None and self.pausing[1] == talk.PERSON
        if kind in ("stop", "pause") and person_pausing and by != talk.PERSON:
            # A person's pause stands from the moment it is heard: nobody else's stop or pause replaces it.
            talk.note(self.home, "failed", id=ident, why="a person's pause is waiting for this turn to end, and stands")
        elif kind == "stop":
            talk.note(self.home, "stopped", by=by, why=why or None)
            self.halted, self.halted_by = ("stopped", by, why), ident
            self.end_soon()
        elif kind == "pause":
            self.pausing = (ident, by, why)
            talk.note(self.home, "pausing", by=by, why=why or None)
        elif kind == "resume":
            pending_pause = self.pausing is not None and (self.pausing[1] != talk.PERSON or by == talk.PERSON)
            if pending_pause or lifts(self.home, by):
                self.pausing = None
                talk.note(self.home, "resumed", by=by)
            elif self.pausing is not None or talk.halted(self.home)[0]:
                talk.note(self.home, "failed", id=ident, why="only a person lifts a hold a person placed")
            # With nothing held a resume has nothing to lift: it is done, harmlessly, like any control read.
        elif kind == "withdraw":
            of = str(message.get("of") or "")
            if of not in talk.handed(talk.thread(self.home)):
                talk.note(self.home, "withdrawn", id=of)
                talk.settle(self.home, of)
        elif kind == "say" and message.get("mode") == "interrupt" and self.turning and not self.holding:
            self.interrupting = by
            self.terminate()
        if kind != "say":
            talk.settle(self.home, ident)
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
            got = talk.read_bytes(path, ACTIVITY_LIMIT, -ACTIVITY_LIMIT)
            if got is not None and got[1] > ACTIVITY_LIMIT:
                kept = got[0].decode("utf-8", errors="replace").splitlines()[1:][-ACTIVITY_KEEP:]
                path.write_text("\n".join(kept) + "\n", encoding="utf-8")
        except OSError:
            return

    def flush(self) -> None:
        if self.held.strip():
            say(self.held)
        self.held = ""

    # -- what the agent asks -----------------------------------------------------------------------------------

    def asked(self, what: str, text: str, options: list[str],
              tool: dict[str, Any] | None = None) -> tuple[str, dict[str, Any]]:
        self.asks += 1
        ident = f"ask-{self.asks}"
        # Which slice asked, and what it would touch: what a captain answering in the rule's place needs.
        answer = ruling({"id": ident, "what": what, "text": text, "options": options, "tool": tool,
                         "slice": self.env.get("SLIPWAI_SLICE", ""), "fairway": self.env.get("SLIPWAI_FAIRWAY", ""),
                         "root": str(self.cwd)})
        if self.home is not None:
            talk.note(self.home, "ask", id=ident, what=what, text=text, options=options)
            said = ("allowed" if answer.get("allow") else "refused") if what == "permission" else str(answer.get("action"))
            talk.note(self.home, "answer", to=ident, by=str(answer.get("by") or "rule"),
                      text=f"{said}: {answer.get('why', '')}")
        return ident, answer

    def refuse(self, tool_call: dict[str, Any], options: list[dict[str, Any]]) -> str | None:
        title = str(tool_call.get("title") or "a tool call")
        places = [str(one.get("path")) for one in tool_call.get("locations") or [] if isinstance(one, dict) and one.get("path")]
        _, answer = self.asked("permission", title, [str(one.get("kind", "")) for one in options],
                               {"title": title, "kind": str(tool_call.get("kind") or ""), "locations": places})
        wanted = "allow_once" if answer.get("allow") else "reject_once"
        say(f"session: {'allowed' if answer.get('allow') else 'refused'} {title} — {answer.get('why', '')}")
        return next((str(one["optionId"]) for one in options if one.get("kind") == wanted and "optionId" in one), None)

    def decline(self, params: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
        _, answer = self.asked("question", str(params.get("message") or ""), [])
        action = str(answer.get("action") or "decline")
        say(f"session: {'answered' if action == 'accept' else 'declined'} a question — {params.get('message') or ''} "
            f"— {answer.get('why', '')}")
        return action, answer.get("content") if action == "accept" else None

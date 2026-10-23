"""The console: a conversation with the harbourmaster, held on the board and read off the same logs it reads.

The harbourmaster is a process, not a person to talk to: it answers requests and writes lines, and has no
inbox for a sentence. What a person wants to ask it is nearly always a question about those lines — why is
this fairway parked, what is the fleet waiting on, what happened in the last hour — and a session that has
read them can answer. So the console is one headless session of the project's coding agent, briefed as the
harbourmaster (`agents/harbour-harbourmaster.md`, the same brief the role is run from) and given nothing to
act with.

**It can read and it cannot do.** The session's tools are `Read`, `Grep` and `Glob`, and no more: no shell,
no editor, no web. The harbourmaster holds this machine's push and merge credentials, and a conversation that
could be talked into using them would turn the one thing here with a way out into a chat box. When the
answer is "do this", the console says which control on the board does it, and a person presses it — the
same way a `request` line is answered by a person today.

**Lines, not a stream.** The page polls with `?since=<n>`, as it does for a build in progress, and the
console answers with the turns after the one the asker already has. A turn is one thing said: a person's
question, the agent's words, or the file it read to say them. The lock is around the list because the
server's thread reads it while this one's writes it.

**A session per project, and it outlives the page.** The conversation is kept by the agent's own session id,
which the first turn mints and every later one resumes, so a reload shows the whole exchange again and the
agent still knows what was said. `reset` starts another.

**What it does not do.** It writes no line into any log: a conversation is not an event in a run, and the
rule that a thing which wrote no line did not happen is about the run.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
import uuid
from collections.abc import Sequence
from pathlib import Path

from .fleet import board
from .shell_environment import login_environment

#: The tools the session is given, and the only ones. A list rather than a deny-list: a tool added to the
#: agent next year is then not a power this console quietly acquired.
TOOLS = "Read,Grep,Glob"
#: The agent's brief, in the places a project keeps it: the canonical `agents/` and the harness's own copy.
BRIEFS = ("agents/harbour-harbourmaster.md", ".claude/agents/harbour-harbourmaster.md")
#: How long one answer may take before it is stopped. An answer is a handful of file reads.
LIMIT = 300
#: How much of the board's fold goes with a question. The fold is small on a quiet project and long on a busy
#: one; what is cut off the end is the oldest of the feed, which the logs themselves still have.
FOLD = 8000
#: Turns kept. A conversation older than this has been scrolled past, and the board holds no archive.
KEPT = 400

ROLE = """You are answering a person at the bridge of this project's board, in a console. You are the
harbourmaster, speaking in the first person and in plain words — say `waiting on you`, not `parked`, unless the
person used the word first.

You can read and search files and nothing else. You cannot change anything, run anything, grant a request or
clear a park, and you must not offer to. Everything you know is in this project: the logs under `.slipwai/logs/`
(the harbour log and each fairway's deck log), `harbour.json`, `.slipwai/`, `specs/` and `docs/`. Read them
before answering a question about what happened; if the logs do not say, say they do not, and do not guess.

When the answer is for the person to do, name the control on the board that does it — the answer box under a
waiting item, the telegraph dial, a need's tick — rather than describing a command. Be short. A list of three
things is better than a page."""


def snapshot(root: Path) -> str:
    """The board as it stands, folded from the logs the way the page folds it, for the agent to read first.

    The agent can read the logs but not run the fold, and some of what the board shows — the counts, who is
    working, how many slots are lit — is the fold's and not any one file's. A console that answered from the
    files alone could say something the page next to it contradicts.
    """
    try:
        return json.dumps(board(root), ensure_ascii=False, default=str)[:FOLD]
    except (OSError, ValueError, KeyError) as fault:
        return f"unavailable: {fault}"


def brief(root: Path) -> str:
    """The harbourmaster's own brief with its front matter taken off, or nothing where the project has none."""
    for name in BRIEFS:
        path = root / name
        if path.is_file():
            text = path.read_text(encoding="utf-8")
            if text.startswith("---\n") and "\n---\n" in text[4:]:
                text = text[4:].split("\n---\n", 1)[1]
            return text.strip()
    return ""


class Console:
    """One conversation: what has been said, whether an answer is being written, and the session behind it."""

    def __init__(self, root: Path, command: Sequence[str] | None = None) -> None:
        self.root = root
        # A seam rather than a mock: a test hands in a command that prints the agent's stream, and the
        # real run builds its own. Whatever it is, the question is its last argument.
        self.command = list(command) if command else None
        self.turns: list[dict] = []
        self.dropped = 0  # turns said and since let go of, so `since` keeps meaning the same thing
        self.session = ""
        self.begun = False
        self.busy = False
        self.child: subprocess.Popen[str] | None = None
        self.login: dict[str, str] | None = None
        self.lock = threading.Lock()

    def environment(self) -> dict[str, str]:
        """The login shell's environment, asked once a conversation: a shell is started to answer it."""
        if self.login is None:
            self.login = login_environment(os.environ)
        return self.login

    def argv(self, message: str) -> list[str] | None:
        """The command for one question, or nothing where this machine has no agent to ask."""
        if self.command:
            return [*self.command, message]
        # On the login shell's `PATH`, not the board's: started at login, the board has `launchd`'s, which holds
        # nothing a person installed, so `claude` was "not on this machine" on a machine that had it.
        found = shutil.which("claude", path=self.environment().get("PATH"))
        if not found:
            return None
        system = f"{brief(self.root)}\n\n{ROLE}".strip()
        resume = ["--resume", self.session] if self.begun else ["--session-id", self.session]
        asked = f"{message}\n\n---\nThe board as it stands now, folded from the logs:\n{snapshot(self.root)}"
        return [found, "-p", asked, "--output-format", "stream-json", "--verbose", "--tools", TOOLS,
                "--allowedTools", TOOLS, "--append-system-prompt", system, *resume]

    def say(self, role: str, text: str, kind: str = "text") -> None:
        with self.lock:
            self.turns.append({"role": role, "kind": kind, "text": text})
            if len(self.turns) > KEPT:
                cut = len(self.turns) - KEPT
                del self.turns[:cut]
                self.dropped += cut

    def said(self, since: int = 0) -> dict:
        """The turns after the `since`th this conversation has said, and whether it is still writing one."""
        with self.lock:
            held = max(since - self.dropped, 0)
            return {"turns": self.turns[held:], "at": self.dropped + len(self.turns), "busy": self.busy}

    def ask(self, message: str) -> str:
        """Put a question to the harbourmaster, or say why it cannot be: it is empty, or one is under way."""
        message = message.strip()
        if not message:
            raise ValueError("ask the harbourmaster something")
        with self.lock:
            if self.busy:
                raise ValueError("the harbourmaster is still answering the last question")
            self.busy = True
            if not self.session:
                self.session = str(uuid.uuid4())
        self.say("person", message)
        argv = self.argv(message)
        if argv is None:
            self.say("harbourmaster", "There is no `claude` on this machine's path, and the console is a session of "
                     "it. Install Claude Code, or start the board from a shell that has it.", "error")
            with self.lock:
                self.busy = False
            return "no agent"
        threading.Thread(target=self.run, args=(argv,), daemon=True).start()
        return "asked"

    def run(self, argv: list[str]) -> None:
        """Run the session to its end, turning what it prints into turns. Never raises: the last thing this
        thread does is say it is no longer busy, because a console stuck on `busy` is one nobody can type in."""
        try:
            self.child = subprocess.Popen(argv, cwd=self.root, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                          stderr=subprocess.STDOUT, text=True, env=self.environment(),
                                          start_new_session=True)
            timer = threading.Timer(LIMIT, self.child.kill)
            timer.start()
            try:
                answered = False
                for line in self.child.stdout or []:
                    answered = self.take(line) or answered
                self.child.wait()
            finally:
                timer.cancel()
            if self.child.returncode and not answered:
                self.say("harbourmaster", f"The session ended with status {self.child.returncode} and said nothing.",
                         "error")
            self.begun = self.begun or answered
        except OSError as fault:
            self.say("harbourmaster", f"The session could not be started: {fault}", "error")
        finally:
            with self.lock:
                self.busy = False
                self.child = None

    def take(self, line: str) -> bool:
        """One line of the agent's stream. True where it carried words for the person."""
        try:
            event = json.loads(line)
        except ValueError:
            return False  # a warning or a banner printed ahead of the stream: not part of the conversation
        if not isinstance(event, dict):
            return False
        if event.get("type") == "assistant":
            spoke = False
            for part in (event.get("message") or {}).get("content") or []:
                if part.get("type") == "text" and str(part.get("text", "")).strip():
                    self.say("harbourmaster", str(part["text"]).strip())
                    spoke = True
                elif part.get("type") == "tool_use":
                    self.say("harbourmaster", reading(part), "read")
            return spoke
        if event.get("type") == "result" and event.get("is_error"):
            self.say("harbourmaster", str(event.get("result") or "The session reported an error."), "error")
        return False

    def reset(self) -> str:
        """End the conversation, and the answer being written if there is one, and start another."""
        with self.lock:
            child = self.child
        if child is not None:
            child.kill()
        with self.lock:
            self.turns, self.dropped, self.session, self.begun = [], self.dropped + len(self.turns), "", False
        return "cleared"


def reading(part: dict) -> str:
    """One tool call as a short line — the file a session opened to answer, so the answer can be checked."""
    given = part.get("input") or {}
    target = given.get("file_path") or given.get("pattern") or given.get("path") or ""
    return f"{part.get('name', 'tool')} {target}".strip()


#: One console per project the board is looking at. The board has one conversation per tree for the reason it
#: has one `./init` per tree: the thing being asked about is the project's, not the window's.
CONSOLES: dict[Path, Console] = {}
_HELD = threading.Lock()


def for_root(root: Path) -> Console:
    with _HELD:
        return CONSOLES.setdefault(root.resolve(), Console(root.resolve()))

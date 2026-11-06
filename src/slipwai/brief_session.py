"""The conversation that writes a brief: one session of the coding agent, with a person, before a project exists.

The console (`console.py`) is the shape, kept on purpose: turns behind a lock, a poll with `since`, one session
id minted by the first turn and resumed by every later one, a stand-in command as the test seam. Three things
differ, and each is the point.

**It has a workspace of its own and can write in it.** `~/.slipwai/sketches/<slug>/` holds `brief/`, the
folder of `docs/reference/the-brief.md` that the start page takes, and `prototype/` beside it, the thing with
taps the person plays. Beside and not inside, because everything in the brief travels as design material and
a prototype's code must not. The tools are the five that read and write files; a print session of the agent
confines them to its working directory, and the system prompt names the two folders and nothing else.

**Its system prompt is the eight steps** of the prototyping plan's section 4, `assets/brief/sketch.md`, with
the folder's shape folded in; `tests/test_brief_session.py` holds that copy to the reference page's, so the
two cannot drift. The three design skills a session needs — the drawing, the states, the gaps — are projected
from the toolkit into the workspace before the first turn, the way `./init` projects them into a project.

**After each answer it reads the brief back** with `brief_check.report`, the same reading the start page
will take, so the page shows the brief counting itself up without a second route and without a second
opinion.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import threading
import uuid
from collections.abc import Sequence
from pathlib import Path

from .assets import SLIPWAI, TOOLKIT_ROOT
from .board_agent import BoardAgent
from .board_settings import Launch, chosen, read
from .brief_check import report
from .console import reading
from .errors import GenerationError
from .harness import acp_environment, row_of
from .shell_environment import login_environment

#: Where this machine keeps its sketches: not a project's, so not under one.
SKETCHES = SLIPWAI / "sketches"
BRIEF, PROTOTYPE = "brief", "prototype"
#: The tools the session is given, and the only ones: it reads and writes files in its workspace.
TOOLS = "Read,Write,Edit,Glob,Grep"
#: The skills the eight steps name, projected from the toolkit into the workspace.
SKILLS = ("frontend-design", "storyboard", "find-gaps")
PROMPT = TOOLKIT_ROOT.parent / "brief" / "sketch.md"
#: A slug: what a product's name becomes as a folder, and the only shape the address accepts.
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
#: What the page says for a person who brought a document, so the session's step 0 begins without them
#: having to say anything: the document is the first thing they said.
BROUGHT = "Here is the document I already have, in brief/prd.md. Read it first."
#: The two lines the prompt asks the session to print, so the page can follow it.
STEP = re.compile(r"^step:\s*([1-4])\s*$", re.MULTILINE)
READY = "The brief is ready to hand over."
#: How long one answer may take: a drawing is longer than a handful of file reads.
LIMIT = 900
KEPT = 400


def slug_of(name: str) -> str:
    """A product's name as a folder: lower case, words joined by one hyphen, nothing else."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")[:64]
    if not SLUG.match(slug):
        raise ValueError("name the product: a word or two, letters and digits")
    return slug


def workspace(slug: str) -> Path:
    """The sketch's folder, for a slug the address may carry. A slug that is not one is refused, which is
    what keeps `..` out of a path built from the address."""
    if not SLUG.match(slug):
        raise ValueError(f"{slug!r} is not a sketch's name")
    return SKETCHES / slug


def prepared(home: Path, skills: str | None = None) -> Path:
    """The workspace with its two folders and the three skills in place, made where it was not. The skills
    land where the agent reads them — its registry row's `skillsDir` — and under `.claude/skills` by default."""
    for name in (BRIEF, PROTOTYPE):
        (home / name).mkdir(parents=True, exist_ok=True)
    for skill in SKILLS:
        landed = home / (skills or ".claude/skills") / skill
        if not landed.is_dir():
            shutil.copytree(TOOLKIT_ROOT / "skills" / skill, landed)
    return home


def started(slug: str, document: str = "") -> Path:
    """A sketch begun from a name, and from a document where the person brought one: it lands as the
    brief's own `prd.md` before the first turn, so the session's step 0 reads it as a reviewer would. A
    sketch that already has a document keeps it; a second one is a refusal, not an overwrite."""
    home = prepared(workspace(slug))
    if document.strip():
        landed = home / BRIEF / "prd.md"
        if landed.is_file():
            raise ValueError(f"{slug} already has a document; start a new sketch under another name")
        landed.write_text(document.strip() + "\n", encoding="utf-8")
        with _HELD:
            if slug in SKETCHED:
                SKETCHED[slug].check = checked(home)
    return home


def role(home: Path) -> str:
    """The eight steps, with this sketch's two folders named by their full paths."""
    return (PROMPT.read_text(encoding="utf-8").strip()
            + f"\n\nThis sketch's folders are `{home / BRIEF}` and `{home / PROTOTYPE}`.")


def checked(home: Path) -> list[str]:
    """The brief read back, as the start page will read it: the five lines, the refusal, or nothing yet."""
    folder = home / BRIEF
    if not folder.is_dir() or not any(folder.rglob("*")):
        return []
    try:
        return report(folder)
    except GenerationError as refused:
        return [str(refused)]


class Sketch:
    """One conversation: what has been said, which step it is at, what the brief says so far, and the session."""

    def __init__(self, slug: str, command: Sequence[str] | None = None, launch: Launch | None = None) -> None:
        self.slug = slug
        self.home = workspace(slug)
        self.command = list(command) if command else None
        self.launch = launch  # the agent to run over the protocol; a test hands one in, the board reads its settings
        self.agent: BoardAgent | None = None
        self.on = ""  # the agent's name, for the page
        self.turns: list[dict] = []
        self.dropped = 0
        self.session = ""
        self.begun = False
        self.busy = False
        self.step = 1
        self.ready = False
        self.check: list[str] = checked(self.home)
        self.child: subprocess.Popen[str] | None = None
        self.login: dict[str, str] | None = None
        self.lock = threading.Lock()

    def environment(self) -> dict[str, str]:
        if self.login is None:
            self.login = login_environment()
        return self.login

    def argv(self, message: str) -> list[str] | None:
        """The command for one turn, or nothing where this machine has no agent to run it."""
        if self.command:
            return [*self.command, message]
        found = shutil.which("claude", path=self.environment().get("PATH"))
        if not found:
            return None
        resume = ["--resume", self.session] if self.begun else ["--session-id", self.session]
        # No MCP servers: a print session otherwise loads the person's own — a browser, a code index — and
        # the first live run spent its turns trying to open the prototype in one. The page shows it.
        return [found, "-p", message, "--output-format", "stream-json", "--verbose", "--tools", TOOLS,
                "--allowedTools", TOOLS, "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
                "--append-system-prompt", role(self.home), *resume]

    def say(self, who: str, text: str, kind: str = "text", more: dict | None = None) -> None:
        with self.lock:
            self.turns.append({"role": who, "kind": kind, "text": text, **(more or {})})
            if len(self.turns) > KEPT:
                cut = len(self.turns) - KEPT
                del self.turns[:cut]
                self.dropped += cut

    def said(self, since: int = 0) -> dict:
        """The turns after the `since`th, whether an answer is being written, the step, and the brief so far."""
        with self.lock:
            held = max(since - self.dropped, 0)
            return {"turns": self.turns[held:], "at": self.dropped + len(self.turns), "busy": self.busy,
                    "step": self.step, "ready": self.ready, "check": list(self.check), "slug": self.slug,
                    "agent": self.on, "thinking": bool(self.agent is not None and self.agent.thinking),
                    "model": self.agent.model if self.agent is not None else ""}

    def ask(self, message: str) -> str:
        """Say something to the session, or say why it cannot be said: nothing, or an answer under way."""
        message = message.strip()
        if not message:
            raise ValueError("say what the product is, or answer the question")
        with self.lock:
            if self.busy:
                raise ValueError("the last answer is still being written")
            self.busy = True
            if not self.session:
                self.session = str(uuid.uuid4())
        self.say("person", message)
        launch = None if self.command else self.launch or chosen(read(), path=self.environment().get("PATH"))
        if launch is not None and launch.able:
            prepared(self.home, row_of(launch.key).get("skillsDir"))
            threading.Thread(target=self.drive, args=(launch, message), daemon=True).start()
            return "asked"
        prepared(self.home)
        argv = self.argv(message)
        if argv is None:
            self.say("sketch", "There is no agent this board can run: nothing on the Settings tab can be launched, "
                     "and `claude` is not on this machine's path. Install one, or start the board from a shell "
                     "that has it.", "error")
            with self.lock:
                self.busy = False
            return "no agent"
        threading.Thread(target=self.run, args=(argv,), daemon=True).start()
        return "asked"

    def drive(self, launch: Launch, message: str) -> None:
        """One turn over the protocol: the role at the head of the first prompt, the agent's updates as turns
        as they arrive, and the brief read back after. Never raises."""
        try:
            if self.agent is None:
                self.agent = BoardAgent(launch, self.home, "sketch", self.heard,
                                        env={**self.environment(), **acp_environment(launch.key)})
                self.on = launch.name
            loaded = self.agent.session is not None or self.agent.begin()
            self.on = self.agent.named
            opened = self.begun or loaded
            stop = self.agent.turn(message if opened else f"{role(self.home)}\n\n---\n\n{message}", LIMIT)
            self.begun = self.begun or stop != "fault"
        except Exception as fault:  # noqa: BLE001 — a conversation stuck on busy is one nobody can type in
            self.say("sketch", f"The session could not be started: {fault}", "error")
            self.agent = None
        finally:
            lines = checked(self.home)
            with self.lock:
                self.check = lines
                self.busy = False

    def heard(self, role: str, kind: str, text: str, more: dict | None) -> None:
        """A turn from the agent, with the step and ready lines read off its words."""
        self.say(role, self.followed(text) if kind == "text" and role == "sketch" else text, kind, more)

    def answer(self, number: str, answer: str | None) -> bool:
        """The person's answer to a card the agent put up."""
        return self.agent is not None and self.agent.answer(number, answer)

    def cancel(self) -> str:
        """Stop the turn under way, the protocol's way; the session stays."""
        if self.agent is not None:
            self.agent.cancel()
            return "stopped"
        with self.lock:
            child = self.child
        if child is not None:
            child.kill()
        return "stopped"

    def run(self, argv: list[str]) -> None:
        """The session to its end, its stream turned into turns, and the brief read back after. Never raises."""
        try:
            self.child = subprocess.Popen(argv, cwd=self.home, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
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
                self.say("sketch", f"The session ended with status {self.child.returncode} and said nothing.", "error")
            self.begun = self.begun or answered
        except OSError as fault:
            self.say("sketch", f"The session could not be started: {fault}", "error")
        finally:
            lines = checked(self.home)
            with self.lock:
                self.check = lines
                self.busy = False
                self.child = None

    def take(self, line: str) -> bool:
        """One line of the agent's stream. True where it carried words for the person."""
        try:
            event = json.loads(line)
        except ValueError:
            return False
        if not isinstance(event, dict):
            return False
        if event.get("type") == "assistant":
            spoke = False
            for part in (event.get("message") or {}).get("content") or []:
                if part.get("type") == "text" and str(part.get("text", "")).strip():
                    self.say("sketch", self.followed(str(part["text"])))
                    spoke = True
                elif part.get("type") == "tool_use":
                    kind = "wrote" if part.get("name") in ("Write", "Edit") else "read"
                    self.say("sketch", reading(part), kind)
            return spoke
        if event.get("type") == "result" and event.get("is_error"):
            self.say("sketch", str(event.get("result") or "The session reported an error."), "error")
        return False

    def followed(self, text: str) -> str:
        """The step and the ready line read off what was said, and the step line taken out of it."""
        for found in STEP.findall(text):
            self.step = int(found)
        if READY in text:
            self.ready = True
        return STEP.sub("", text).strip()

    def reset(self) -> str:
        """End the conversation and start another over the same workspace; the files stay."""
        with self.lock:
            child = self.child
        if child is not None:
            child.kill()
        if self.agent is not None:
            self.agent.cancel()
            self.agent.forget()
            self.agent = None
        with self.lock:
            self.turns, self.dropped, self.session, self.begun = [], self.dropped + len(self.turns), "", False
            self.step, self.ready = 1, False
        return "cleared"


SKETCHED: dict[str, Sketch] = {}
_HELD = threading.Lock()


def for_slug(slug: str) -> Sketch:
    """One conversation per sketch, kept for as long as the board runs, as the console keeps one per project."""
    with _HELD:
        return SKETCHED.setdefault(slug, Sketch(slug))


def sketches() -> list[str]:
    """Every sketch this machine has, by slug."""
    return sorted(one.name for one in SKETCHES.iterdir() if one.is_dir()) if SKETCHES.is_dir() else []

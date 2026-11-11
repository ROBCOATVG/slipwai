"""A turn's child heard to its end, and every way it can end said.

The sketch and the console each run one turn of the coding agent as a child and read its stream. A turn that
ended badly said so only where the child had said nothing at all, so a child stopped at the time limit after
it had spoken, one that crashed half way through an answer, and one whose reader failed in the board itself
each ended in silence: the page showed a conversation that had simply stopped, and the person asked it why.
This module is the one place a child is heard, so the two cannot differ in what they leave unsaid.
"""
from __future__ import annotations

import json
import re
import subprocess
import threading
from collections.abc import Callable, Sequence


def ending(status: int, answered: bool, late: bool, limit: int, aside: Sequence[str]) -> str | None:
    """Why a turn's child ended, in a sentence, or None where it ended well. Every other ending is said. A
    child stopped at the limit after it had spoken, one that crashed half way through an answer, and one that
    left with nothing at all each ended in silence: the page showed a conversation that had simply stopped.
    `aside` is the last of what it printed that was not its stream — where an agent says what went wrong."""
    printed = f" The last it printed: {' / '.join(aside)}" if aside else ""
    if late:
        return f"This answer was stopped after {limit // 60} minutes, before it was finished."
    if status:
        return (f"The session ended with status {status} "
                + ("before the answer was finished." if answered else "and said nothing.") + printed)
    return None if answered else "The session ended without an answer." + printed


def unheard(fault: BaseException) -> str:
    """What is said where the board itself failed while hearing a session, which it then stopped."""
    return ("The board stopped hearing the session, and stopped it rather than leave it running unseen: "
            f"{type(fault).__name__}: {fault}")


def to_its_end(child: subprocess.Popen[str], take: Callable[[str], bool], limit: int) -> tuple[bool, str | None]:
    """A turn's child heard to its end: whether it had words for the person, and why it ended where it did
    not end well (`ending`). A child the board can no longer hear is stopped before the failure is raised:
    the first one outlived its reader by ten minutes, editing files with nobody listening."""
    late = threading.Event()

    def stopped() -> None:
        late.set()
        child.kill()

    timer = threading.Timer(limit, stopped)
    timer.start()
    answered = False
    aside: list[str] = []
    try:
        for line in child.stdout or []:
            answered = take(line) or answered
            if line.strip() and not line.lstrip().startswith("{"):
                aside = [*aside, line.strip()[:200]][-3:]
        child.wait()
    except BaseException:
        child.kill()
        raise
    finally:
        timer.cancel()
    return answered, ending(child.returncode, answered, late.is_set(), limit, aside)


#: What a tool is doing while the agent is still typing its input, by the tool's name.
VERBS = {"Write": "Writing", "Edit": "Editing", "Read": "Reading", "Glob": "Looking for files", "Grep": "Searching"}
PATH = re.compile(r'"file_path"\s*:\s*"((?:[^"\\]|\\.)*)"')


class Doing:
    """What the child is doing now, read off a reply's pieces as they arrive (`--include-partial-messages`).

    A reply is handed over one whole block at a time, and a block can be ten minutes of thinking or a whole
    prototype typed as one file: the page showed *Working…* and nothing else for all of it, and a person
    asked why it had stopped. `now` is the line the page shows instead — *Thinking…*, or *Writing
    prototype/index.html, 48 KB so far* — and it is empty between blocks, when the page's own word stands."""

    def __init__(self) -> None:
        self.now = ""
        self.tool = ""
        self.typed = ""  # the head of the tool's input, which is where its file's name is
        self.size = 0

    def take(self, event: dict) -> None:
        if event.get("type") != "stream_event":
            if event.get("type") in ("assistant", "user", "result"):
                self.now = ""  # the block is whole and has been said as a turn, or its tool is running
            return
        piece = event.get("event") or {}
        kind = piece.get("type")
        if kind == "content_block_start":
            block = piece.get("content_block") or {}
            self.tool, self.typed, self.size = "", "", 0
            if block.get("type") == "tool_use":
                self.tool = str(block.get("name") or "")
                self.now = VERBS.get(self.tool, "Working") + "…"
            else:
                self.now = "Thinking…" if "thinking" in str(block.get("type")) else "Writing its answer…"
        elif kind == "content_block_delta" and self.tool:
            typed = str((piece.get("delta") or {}).get("partial_json") or "")
            self.size += len(typed)
            self.typed = (self.typed + typed)[:2000]
            named = PATH.search(self.typed)
            if named is None:
                return
            try:
                file = "/".join(str(json.loads(f'"{named.group(1)}"')).replace("\\", "/").split("/")[-2:])
            except ValueError:
                return
            so_far = f", {self.size // 1024} KB so far" if self.tool == "Write" and self.size >= 2048 else ""
            self.now = f"{VERBS.get(self.tool, 'Working on')} {file}{so_far}"
        elif kind in ("content_block_stop", "message_stop"):
            self.now = ""

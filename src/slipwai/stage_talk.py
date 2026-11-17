"""What a person says to a stage, kept: the conversation's turns, the messages waiting for its turn to end,
and the hold a person's word puts on the board moving on by itself.

A stage's session is kept under the run folder (`stage_session.KEPT`), and so is what was said to it, beside
it. The run that held those turns in memory is replaced the moment the next stage starts, and gone with the
board when it is restarted: a question asked of the drawing and answered while the model was being started
was a question whose answer nobody could find. So every turn of a conversation with a stage is a line in
`talk.jsonl`, written as it is said, and the page reads it back from there whatever is running now.

**A person's word is a hold.** `upstream: advance` presses the next step's button when a step ends well,
and a reply to something a person said once read as one of those: asking a question approved the storyboard.
Whatever a person says to a stage writes `held` beside the conversation, and the board does not move on
while one stands — until the person says to carry on, or gives the verdict the step was waiting for.
"""
from __future__ import annotations

import contextlib
import json
import os
import re
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any

from .logs import run_dir
from .talk import read_bytes

#: Where the project keeps a stage's session, its conversation and its hold: one folder per command.
KEPT = "stages"
TALK = "talk.jsonl"
HELD = "held"
#: Turns read back for the page; a conversation about one stage says less than this.
SHOWN = 400
#: The turns that are worth keeping: what was said, what was done, what was asked and answered. A thought is
#: the agent's own, and is not one.
KINDS = frozenset({"text", "error", "tool", "tool_update", "plan", "permission", "question", "answered"})


#: What a stage's command looks like — `mockups`, `model`, `draft` — and so the only names a folder here is made
#: from: a name off an address is never joined into a path.
STAGE = re.compile(r"[a-z][a-z-]{0,31}")
#: How much of a conversation is read back: the tail, which is what a page shows.
TAIL = 2 * 1024 * 1024


def known(command: str) -> bool:
    return bool(STAGE.fullmatch(command))


def home(root: Path, command: str) -> Path:
    if not known(command):
        raise ValueError(f"{command!r} is not a stage of this board")
    return run_dir(root) / KEPT / command


#: Per project: whether git ignores the run folder, asked of git once.
_IGNORED: dict[Path, bool] = {}


def ignored(root: Path) -> bool:
    """Whether what is written under the run folder stays out of the project's commits. A project still on
    the 2.0 layout keeps its run state in `.slipwai/`, which nothing may say is ignored; a person's words
    written there would go out with the next commit. Not a repository is nothing to commit into."""
    key = Path(root).resolve()
    if key not in _IGNORED:
        probe = run_dir(root) / KEPT / "talk.jsonl"
        try:
            asked = subprocess.run(["git", "check-ignore", "-q", "--no-index", str(probe)], cwd=root,
                                   capture_output=True, timeout=10, check=False)
            inside = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=root, capture_output=True,
                                    timeout=10, check=False).returncode == 0
            _IGNORED[key] = asked.returncode == 0 or not inside
        except (OSError, subprocess.TimeoutExpired):
            _IGNORED[key] = True
    return _IGNORED[key]


def unignored(root: Path) -> str:
    """The refusal a conversation gets where what it says would be committed; empty where it would not."""
    return "" if ignored(root) else (
        f"this project keeps its run state in {run_dir(root).name}/, which git does not ignore yet, so what you "
        "say to a stage would go out with the next commit: run `slipwai migrate` in the project, then say it")


def add(root: Path, command: str, turn: dict[str, Any]) -> None:
    """One turn, at the end of the stage's conversation file, as a whole line: a file whose last line was
    torn is given the newline it lacks first, so the torn line is lost and this one is not. A turn that cannot
    be written is let go of rather than raised: it was said on the page already, and a stage that stopped for
    a full disk would be the conversation lost twice."""
    if turn.get("kind") not in KINDS and turn.get("kind") != "delivered":
        return
    if not ignored(root):
        return
    with contextlib.suppress(OSError):
        folder = home(root, command)
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / TALK
        torn = False
        if path.is_file() and path.stat().st_size:
            with path.open("rb") as last:
                last.seek(-1, os.SEEK_END)
                torn = last.read(1) != b"\n"
        with path.open("a", encoding="utf-8") as out:
            out.write(("\n" if torn else "") + json.dumps({**turn, "t": round(time.time(), 1)}) + "\n")


def said(root: Path, command: str, words: str, queued: bool = False) -> dict[str, Any]:
    """What the person said, kept as their turn — queued where the stage was still going — and the hold it
    puts on the board."""
    turn = {"role": "person", "kind": "text", "text": words, "id": uuid.uuid4().hex[:12], **({"queued": True}
                                                                                          if queued else {})}
    add(root, command, turn)
    hold(root, command)
    return turn


def turns(root: Path, command: str) -> list[dict[str, Any]]:
    """The whole conversation, oldest first — a page asks for the turns after the count it has, so the count
    never stops growing — with a queued message shown queued until the turn that delivered it."""
    read = read_bytes(home(root, command) / TALK, TAIL, -TAIL)  # the tail, once, a plain file only
    if read is None:
        return []
    lines = read[0].decode("utf-8", "replace").splitlines()
    if read[1] > TAIL:
        lines = lines[1:]  # the first line of a tail is part of one
    found: list[dict[str, Any]] = []
    for line in lines:
        try:
            turn = json.loads(line)
        except ValueError:
            continue
        if not isinstance(turn, dict):
            continue
        if turn.get("kind") == "delivered":
            ids = set(turn.get("ids") or [])
            for one in found:
                if one.get("id") in ids:
                    one.pop("queued", None)
            continue
        found.append(turn)
    return found


def undelivered(root: Path, command: str) -> list[dict[str, Any]]:
    """What a person said while the stage ran that no turn has carried to it yet."""
    return [one for one in turns(root, command) if one.get("queued")]


def hold(root: Path, command: str) -> None:
    with contextlib.suppress(OSError):
        folder = home(root, command)
        folder.mkdir(parents=True, exist_ok=True)
        (folder / HELD).write_text(f"{time.time():.0f}\n", encoding="utf-8")


def release(root: Path, command: str = "") -> list[str]:
    """The person's word to carry on, for one stage or every one: the holds let go of, by command."""
    let = []
    for one in [command] if command else held(root):
        path = home(root, one) / HELD
        if path.is_file():
            with contextlib.suppress(OSError):
                path.unlink()
                let.append(one)
    return let


def held(root: Path) -> list[str]:
    """The stages a person has said something to and not yet said to carry on from, by command."""
    try:
        return sorted(one.name for one in (run_dir(root) / KEPT).iterdir()
                      if known(one.name) and (one / HELD).is_file())
    except OSError:
        return []


def kept(root: Path, command: str) -> bool:
    """Whether this project kept a session for the stage, which is what a conversation with it resumes."""
    return (home(root, command) / "session").is_file()

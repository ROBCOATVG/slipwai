"""Which file a running board was started from, so a newly installed app can tell the board predates it.

The board outlives the app that started it: it is a login service, and a person who drags a new
`Slipwai.app` over the old one leaves the board running the old file from the Trash. Opening the new app
found a board answering, opened it, and the person used yesterday's board while sure they had installed
today's — game-club-manager-new was made by a board that predated the fix it was installed to get.

So every answer the board gives names the file it was started from, as it was then: the path, and that
file's identity on disk. The app compares that with its own executable. The same path holding a different
file is a board this install replaced; a different path is someone's own `slipwai`, and is left alone.
"""
from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from email.message import Message
from pathlib import Path
from urllib.parse import quote, unquote

#: The headers every answer of the board carries.
EXECUTABLE = "X-Slipwai-Executable"
BUILD = "X-Slipwai-Build"
PID = "X-Slipwai-Pid"


@dataclass(frozen=True)
class Build:
    """A board's executable, the identity of the file there when it started, and its process."""

    executable: str
    build: str
    pid: int = 0

    def same_path(self, other: Path) -> bool:
        return os.path.normcase(self.executable) == os.path.normcase(str(other))


def build_of(path: Path) -> str:
    """The identity of the file at `path` now: a replaced file is a new inode, and a rewritten one a new
    size or time. `""` where there is nothing there."""
    try:
        held = path.stat()
    except OSError:
        return ""
    return f"{held.st_ino}-{held.st_size}-{held.st_mtime_ns}"


def executable() -> Path:
    return Path(sys.executable).resolve()


#: This process's, taken once at import: by the time anyone asks, the file at the path may be another one.
STARTED = Build(str(executable()), build_of(executable()))


def headers() -> list[tuple[str, str]]:
    """What the board says about itself on every answer. Quoted, because a header is Latin-1 and a path
    need not be."""
    return [(EXECUTABLE, quote(STARTED.executable)), (BUILD, STARTED.build), (PID, str(os.getpid()))]


def read(said: Message | Mapping[str, str]) -> Build | None:
    """The build a board's answer names, from its headers; `None` from a board too old to say."""
    where = said.get(EXECUTABLE)
    if not where:
        return None
    pid = str(said.get(PID) or "")
    return Build(unquote(str(where)), str(said.get(BUILD) or ""), int(pid) if pid.isdigit() else 0)


def replaced(board: Build | None, here: Path | None = None) -> bool:
    """Whether the board answering is one an install of this copy replaced: started from this copy's path,
    from a file that is no longer the one there. A board too old to say is asked about by the caller."""
    here = executable() if here is None else here
    return board is not None and board.same_path(here) and board.build != build_of(here)

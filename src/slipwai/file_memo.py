"""What a file was read as, kept until the file changes: the board reads the same files on every request.

manda's Voyage window took thirteen seconds to draw on its own and thirty-eight beside its polls: every
request parsed every decision record in every checkout — about five hundred files, in a dozen checkouts,
6,407 parses — and read every slice's benchmark record three times, some 24,000 opens. Almost none of them had
changed since the request before. So a file's reading is kept against its path, its size and the instant it
was last written, and a file is read again only when one of those moved.
"""
from __future__ import annotations

import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

_KEPT: dict[tuple[str, str], tuple[int, int, Any]] = {}
_LOCK = threading.Lock()
#: Enough for every record of a large project in every checkout, and a bound on what a long-lived board holds.
LARGEST = 50_000


def read(path: Path, reading: Callable[[str], Any], name: str) -> Any:
    """`reading` of the file's text, from the last time it was read where the file has not changed since.
    `name` says which reading, so two readers of one file keep theirs apart. OSError and UnicodeDecodeError
    are raised as reading the file would raise them, and nothing is kept for a file that could not be read."""
    stat = path.stat()
    key = (name, str(path))
    with _LOCK:
        held = _KEPT.get(key)
    if held and held[0] == stat.st_mtime_ns and held[1] == stat.st_size:
        return held[2]
    found = reading(path.read_text(encoding="utf-8"))
    with _LOCK:
        if len(_KEPT) >= LARGEST:
            _KEPT.clear()
        _KEPT[key] = (stat.st_mtime_ns, stat.st_size, found)
    return found

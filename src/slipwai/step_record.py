"""How each step the board ran ended, written down when it ends: what `upstream: advance` presses past.

A board advancing by itself once read "nothing is running" as "the last step ended well". Restarted in the
middle of a drawing, it found pages, a research note begun, nothing running, and approved the half-drawn
storyboard on its first poll. So the board now writes, in the run folder, which step ended, about which
feature, with what outcome and when — and advances only past a step it holds such a record for. A pid file
whose process is gone with no record after it is a step interrupted; no record at all is a step the board did
not see end (run before this build, by hand, or in another window), and it waits for a person rather than
guessing.

And what it last pressed, with what the project looked like then: the board never presses the same step for
the same feature twice in a row while nothing has changed — a drawing that drew nothing is not drawn again on
every poll.

Neither is written where git does not ignore the run folder (a project still on the 2.0 layout): a record a
commit would carry is worse than none, and none is the safe side — the board waits for a person.
"""
from __future__ import annotations

import contextlib
import hashlib
import json
import time
from pathlib import Path
from typing import Any

from .logs import run_dir
from .stage_talk import ignored
from .talk import read_json

ENDED = "steps-ended.json"
PRESSED = "upstream-pressed.json"


def ended(root: Path, step: str, feature: str, code: int) -> None:
    """A step's own run ended: written down, by step, replacing what the step's last run left."""
    if not step or not ignored(root):  # never a file a commit of the project would carry
        return
    path = run_dir(root) / ENDED
    held = read_json(path) if path.is_file() else None
    held = held if isinstance(held, dict) else {}
    held[step] = {"feature": feature, "code": int(code), "t": round(time.time(), 1)}
    with contextlib.suppress(OSError):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(held, indent=1), encoding="utf-8")


def record(root: Path, step: str) -> dict[str, Any] | None:
    """How `step` last ended, as the board saw it, or None where it has no record of it ending."""
    path = run_dir(root) / ENDED
    held = read_json(path) if path.is_file() else None
    one = held.get(step) if isinstance(held, dict) else None
    return one if isinstance(one, dict) and isinstance(one.get("t"), (int, float)) else None


def signature(root: Path) -> str:
    """What the project's upstream files look like now, in one digest: the specifications, the mock-ups and
    their verdicts, by name, size and time. Changed by anything a person or a step does to them."""
    specs = root / "specs"
    seen = []
    for path in sorted([*specs.glob("*/spec.md"), *specs.glob("*/mockups/*")]) if specs.is_dir() else []:
        with contextlib.suppress(OSError):
            stat = path.stat()
            seen.append(f"{path.relative_to(root).as_posix()}:{stat.st_size}:{stat.st_mtime_ns}")
    return hashlib.sha1("\n".join(seen).encode("utf-8")).hexdigest()[:16]


def pressed(root: Path, step: str, feature: str) -> None:
    """The board pressed `step` for `feature` by itself: written down with what the project looked like."""
    if not ignored(root):
        return
    with contextlib.suppress(OSError):
        path = run_dir(root) / PRESSED
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"step": step, "feature": feature, "signature": signature(root)}),
                        encoding="utf-8")


def repeated(root: Path, step: str, feature: str) -> bool:
    """Whether pressing `step` for `feature` now would be the same press again with nothing changed since."""
    path = run_dir(root) / PRESSED
    held = read_json(path) if path.is_file() else None
    return (isinstance(held, dict) and held.get("step") == step and held.get("feature") == feature
            and held.get("signature") == signature(root))

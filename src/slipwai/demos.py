"""Who accepts a whole capability, and what the board reads off the logs because of it.

The owner's question settled it: "do we need accept if we're running skipper. I think it's just an
opportunity to add feedback." So the hand's verdict at a capability's walk is its acceptance unless the
project says otherwise, and the film the hand made is something a person looks at when they have time,
never something the run waits on. `.specify/cruise.json`'s `demos` says which: `hand`, the default, or
`person`, which is the board as it was — a capability due a demo, and Accept or Not yet beside it.

**Read here, and nowhere else in the keel**, because two readers turn on it and must agree: the board's fold
(`fleet.board`), which says what is owed a person, and the card that offers a film to comment on. The
toolkit's `clearance.py` and `capabilities.py` read the same key for themselves, since a generated project
has no slipwai to import.

An `accepted` line names who accepted with `by`. One the hand wrote is the acceptance under `hand`; under
`person` it is the last reading before a person's, and closes nothing. A line with no `by` is a person's, as
every such line was before this setting existed.
"""
from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

from .logs import Entry, Unreadable, deck_path, entry, run_dir
from .shell_environment import login_environment, project_python

CONFIG = ".specify/cruise.json"
#: The setting's two values: the hand's verdict accepts a capability, or a person's does.
HAND = "hand"
PERSON = "person"
#: Who an `accepted` line names when the hand wrote it.
WALKER = "sail-demo-hand"
#: Written beside a capability's film the first time a person opens it, so it stops being listed as
#: something to look at. Under the run folder, with the film, and never committed.
OPENED = "opened"


def setting(root: Path) -> str:
    """`hand` or `person`. Absent, unreadable or unknown is `hand`: a project written before the setting
    existed has nobody waiting on a demo, because nothing ever wrote the line that would have made one due."""
    try:
        held = json.loads((root / CONFIG).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return HAND
    value = held.get("demos") if isinstance(held, dict) else None
    return PERSON if value == PERSON else HAND


def accepts(line: Entry, demos: str) -> bool:
    """Whether this `accepted` line accepts its capability under this setting."""
    return demos != PERSON or str(line.fields.get("by", "")) != WALKER


def acceptance(found: Iterable[tuple[str, list[Entry]]], demos: str) -> tuple[list[str], dict[str, str]]:
    """The capabilities accepted, and each one owed a person's demo against the fairway whose log said so.

    Under `hand` nothing is owed a person: a `demo-due` line, from a run that had the setting the other way
    or written by hand, is not a person being asked anything.
    """
    pairs = [(name, line) for name, entries in found for line in entries]
    accepted = {str(line.fields.get("capability")) for _, line in pairs
                if line.kind == "accepted" and accepts(line, demos)}
    due = {} if demos != PERSON else {
        str(line.fields.get("capability")): name for name, line in pairs
        if line.kind == "demo-due" and str(line.fields.get("capability")) not in accepted}
    return sorted(accepted), due


#: What a feature or a capability name may be, the way the chart and the walks folder spell them.
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,80}")


def report(root: Path) -> dict:
    """The project's own reading of every capability — whole, gated, accepted, and why each may not be
    accepted now — from `scripts/agents/capabilities.py --json`. `{}` where the script is too old or cannot
    run: the board then reads acceptance off the log lines alone, as it did."""
    script = root / "scripts/agents/capabilities.py"
    try:
        if '"refused"' not in script.read_text(encoding="utf-8"):
            return {}
        done = subprocess.run([project_python(root), "-B", str(script), "--json"], capture_output=True,
                              text=True, timeout=15, env=login_environment(root=root), check=False)
        found = json.loads(done.stdout)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return {}
    return found if isinstance(found, dict) and isinstance(found.get("rows"), list) else {}


def recorded(found: dict) -> list[str]:
    """The capabilities the hand accepted before there was a line to say so, read off its record."""
    return [str(row.get("capability")) for row in found.get("rows") or [] if row.get("recorded")]


def release_blockers(found: dict) -> list[dict]:
    """The capabilities whole and gated and built on a stand-in, each with what blocks it: never *Built*.

    Read off the project's own rows (`capabilities.py`'s `blockers`), so an older script that has no such
    field reports none rather than every capability."""
    return [{"capability": str(row.get("capability")), "blockers": [str(one) for one in row["blockers"]]}
            for row in found.get("rows") or []
            if row.get("whole") and row.get("gated") and isinstance(row.get("blockers"), list) and row["blockers"]]


def accept(root: Path, capability: str) -> str:
    """A person's Accept, written as the `accepted` line with `by: person`, or why not.

    Held to the same rule as the hand's command, `capabilities.acceptable`, read through the project's own
    script so there is one rule and not two. The board writes the line itself, as `deck.mark_read` writes a
    `read`: a person's acceptance is not something a session should be able to write for itself, and once
    every slice of a capability has merged there may be no session left to read a message asking it to.
    (A later stream moves the board's deck-log writes behind the stream's captain; this is one of them.)
    """
    found = report(root)
    if not found:
        raise ValueError("this project's scripts/agents/capabilities.py cannot say whether the capability is "
                         "whole and cleared; `slipwai migrate` updates it")
    if found.get("demos") != PERSON:
        raise ValueError("nothing here waits on a person to accept a demo: this project takes the hand's verdict "
                         "as the acceptance. Say what the film showed instead")
    row = next((one for one in found["rows"] if one.get("capability") == capability), None)
    if row is None:
        raise ValueError(f"no slice on the chart names the capability {capability!r}")
    if row.get("refused"):
        raise ValueError(str(row["refused"]))
    fairways = [str(one) for one in row.get("fairways") or []]
    if not fairways or not NAME.fullmatch(str(found.get("feature", ""))):
        raise ValueError(f"nothing says which fairway {capability} is in")
    path = deck_path(root, str(found["feature"]), fairways[-1])
    try:
        line = entry("accepted", fairway=fairways[-1], capability=capability, by="person")
    except Unreadable as fault:
        raise ValueError(str(fault)) from fault
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line.line())
    return f"{capability} accepted"


def on_board(root: Path, found: list[tuple[str, list[Entry]]]) -> tuple[str, list[str], dict[str, str]]:
    """The setting, the capabilities accepted and those owed a person, as the board shows them. Under `hand`
    a capability the hand accepted before the line existed is read off its record (`capabilities.py`'s
    `recorded_by_hand`), so a project that migrated mid-voyage keeps what the hand already accepted."""
    demos = setting(root)
    accepted, due = acceptance(found, demos)
    if demos == HAND:
        accepted = sorted(set(accepted) | set(recorded(report(root))))
    return demos, accepted, due


def walk(root: Path, feature: str, capability: str) -> Path | None:
    """The capability's walk folder, or `None` where either name is not one the walks folder holds."""
    if not (NAME.fullmatch(feature) and NAME.fullmatch(capability)) or ".." in (feature + capability):
        return None
    home = (run_dir(root) / "walks").resolve()
    where = (home / feature / capability).resolve()
    return where if where.parent.parent == home and where.is_dir() else None


def charted(root: Path, feature: str, capability: str) -> bool:
    """Whether the feature's chart names this capability, read as text: the keel reads no YAML."""
    try:
        text = (root / "specs" / feature / "chart.yaml").read_text(encoding="utf-8")
    except OSError:
        return False
    return re.search(rf"capability:\s*['\"]?{re.escape(capability)}['\"]?\s*[,}}\n]", text + "\n") is not None


def opened(root: Path, feature: str, capability: str) -> bool:
    where = walk(root, feature, capability)
    return where is not None and (where / OPENED).is_file()


def mark_opened(root: Path, feature: str, capability: str) -> bool:
    """Say a person has opened this film, and whether it was said. For the route that serves a person's press
    of Play; the page's own load fetches the film's first bytes for its length, which is not anybody watching
    it. Only for a capability the chart names and the walks folder holds, inside that folder, and never a
    raise: a route handed a name it should not have is answered no."""
    where = walk(root, feature, capability)
    if where is None or not charted(root, feature, capability):
        return False
    try:
        if not (where / OPENED).is_file():
            (where / OPENED).write_text(datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ") + "\n", encoding="utf-8")
    except OSError:
        return False
    return True

"""Who is at the wheel at each stop of a run, read off the project and changed from the board.

The glossary makes `/sail` and `/cruise` a pair and says why: somebody is at the wheel, or nobody is. What
it does not say, because it was never a dial, is that the choice is not one switch. `/cruise` runs the same
ladder as `/sail` and differs only at the stops — a product question, a release, an unratified constitution,
a block — and `.specify/cruise.json` already answers each of them separately. `park` on any of them *is*
`/sail` for that stop: the fleet stops and the question lands in the inbox for a person.

**So there is no sail-or-cruise switch here, and there should not be.** A board that offered one would be
offering a thing the run does not have. What a person wants when they say "I want to be asked" is a stop
they want to be asked at, and that is what this reads and what this writes.

**Written by the project's own script, never by this.** `scripts/agents/cruise.py --set <key>=<value>` is
what `/cruise-settings` runs; it validates the value against the same `SETTINGS` this renders from, and
`make check-agents` holds the file's shape. A second writer here would be a second thing to keep in step
with the project's own checker, and the first one to drift. A captain reads the file at its next boundary,
which is what makes this a change you can make mid-run.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from .project.cruise import SETTINGS
from .project.cruise_record import SCRIPT
from .shell_environment import login_environment

#: Where the answers live, relative to the project.
CONFIG = ".specify/cruise.json"
#: How long the project's own script gets. It reads one file, checks one value and writes it back; a
#: second of that is already a machine with something wrong on it, and a board that hung on a button
#: press would be worse than one that says it could not.
PATIENCE = 20.0

#: The stops where the answer decides whether a person is asked, in the order a run meets them, each with
#: what it is in plain words and what each of its values means. `hand`, `model` and `enabled` are not here:
#: they are how a run works rather than who answers it, and the fine tune for those is the command page.
STOPS: tuple[tuple[str, str, dict[str, str]], ...] = (
    ("decide", "A product question",
     {"recommended-first": "the stage's recommendation, or the skipper",
      "skipper-always": "the skipper, every time"}),
    ("constitution", "An unratified constitution",
     {"ratify": "the skipper drafts and ratifies it", "park": "park and ask me"}),
    ("unblock", "A block",
     {"bosun": "the bosun works around it", "park": "park and ask me"}),
    ("release", "A release",
     {"flagged": "continue behind a flag, so every merge is dark", "park": "park and ask me"}),
    # Met first, but last here: it is the board's stop rather than the fleet's, and the four above are what
    # this card has always been read for.
    ("upstream", "The specification, storyboard and model",
     {"park": "stop for me at each", "advance": "advance on their own"}),
)
#: The value that means a person is asked. A stop sitting on this is `/sail`'s answer to it.
ASKS = "park"


def known(name: str) -> tuple[str, ...]:
    """The values that stop takes, from the one list the config, the command and the checker share."""
    for key, values, _, _ in SETTINGS:
        if key == name and isinstance(values, tuple):
            return values
    return ()


def orders(root: Path) -> dict[str, str]:
    """What this project's `.specify/cruise.json` says, or `{}` where it has none.

    `{}` and not a refusal: a project generated before `/cruise` was configurable, an adopted repository
    that has not been given one, and a harbour that is not a project at all all reach this, and none of
    them is a fault — the card simply has nothing to show.
    """
    try:
        held = json.loads((root / CONFIG).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(held, dict):
        return {}
    # A stop added after the file was written reads as its default, which is what the project's own script
    # takes it to be: the card then shows where it stands rather than a dial with nothing on.
    later = {key: str(default) for key, _, default, _ in SETTINGS
             if key not in held and any(key == name for name, _, _ in STOPS)}
    return later | {str(a): str(b) for a, b in held.items() if not str(a).startswith("_")}


def asking(root: Path) -> list[str]:
    """Which stops this run will stop for a person at, in the order they are met."""
    held = orders(root)
    return [title for name, title, _ in STOPS if held.get(name) == ASKS]


def set_stop(root: Path, name: str, value: str) -> str:
    """One stop answered differently, through the project's own script, or why it could not be.

    Checked here first only for what the script cannot be asked: that the project has one to run, and that
    the stop and value are ones this board draws. Everything else — whether the value is legal, what the
    file ends up holding — is the script's, which is the point of running it rather than writing the file.
    """
    if not any(name == key for key, _, _ in STOPS):
        raise ValueError(f"`{name}` is not a stop this board sets")
    if value not in known(name):
        raise ValueError(f"`{value}` is not one of {name}'s answers: {', '.join(known(name))}")
    script = root / SCRIPT
    if not script.is_file():
        raise ValueError(f"{SCRIPT} is not in this project, so there is nothing to write the answer. "
                         f"It arrives with `./init`")
    done = subprocess.run([sys.executable, str(script), "--set", f"{name}={value}"],  # noqa: S603 — the
                          cwd=root, capture_output=True, text=True,                   # project's own script
                          timeout=PATIENCE, env=login_environment(), check=False)
    if done.returncode:
        raise ValueError((done.stderr or done.stdout or f"{SCRIPT} exited {done.returncode}").strip())
    return f"{name} = {value}"

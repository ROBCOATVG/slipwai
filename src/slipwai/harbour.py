"""What `harbour.json` holds here, read once and by everything that needs it.

Three things want the harbour's own settings — the terminal board, the page, and the verb that serves the
page — and until 14.4 the page read them from the terminal board's module. That was fine while nothing else
pointed the other way, and it stopped being fine the moment `slipwai fleet` became a deep link into the
board: `cli_fleet` reaching for the server, and the server reaching back for `cli_fleet`, is the cycle
`check-structure` exists to name. The setting is nobody's verb, so it lives on its own.

**An unreadable file is no settings, not a fault.** The board is drawn from the logs and the harbour's
numbers only decorate it; a run that cannot be looked at because its config has a stray comma is a worse
answer than a board with the defaults on it.
"""
from __future__ import annotations

import json
from pathlib import Path

from .project.harbour import CONFIG


def config(root: Path) -> dict:
    """The harbour's settings here, or nothing where there is no readable file."""
    try:
        held = json.loads((root / CONFIG).read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return {}
    return held if isinstance(held, dict) else {}

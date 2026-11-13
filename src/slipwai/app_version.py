"""Whether this app is the release a project was last updated by, and what to do where it is not.

A project records the newest slipwai that wrote it, `generator.updatedWith` in `project.json`. The app reads
and writes that project's run state, so the two have to agree on where it is: 2.1 moved it under
`.slipwai/run/`, and a 2.0 app opened on a migrated project shows an empty board and writes a person's
answers where no captain reads them. So:

- **The project is newer than the app**: the board says so on every page and refuses every change, because
  what it would write lands where the project no longer looks. Update the app.
- **The project is older than the app**: the board works (it follows the project's layout) and says
  `slipwai migrate` brings the project up to it.
- **The same, or no record**: nothing is said.

The app also tells every script it starts which release it is, `SLIPWAI_APP_VERSION`, so a project's own
`scripts/agents/fleet.py` can refuse an older app from the other side (`fleet.py`, `app_too_old`). An app
older than 2.1 sets nothing; nothing in the project can tell it from a person at the terminal, so that one
case is caught only here, by the next app that opens it.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

from .assets import VERSION
from .versions import key

#: What the app tells a script it starts, so the project's own scripts can hold it to the project's release.
APP_VERSION = "SLIPWAI_APP_VERSION"


def recorded(root: Path) -> str:
    """The release that last wrote this project, or "" where it records none."""
    try:
        document = json.loads((root / "project.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return ""
    generator = document.get("generator") if isinstance(document, dict) else None
    if not isinstance(generator, dict):
        return ""
    return str(generator.get("updatedWith") or generator.get("generatedWith") or "")


def standing(root: Path, app: str = VERSION) -> str:
    """`newer` where the project is ahead of this app, `older` where it is behind, `same` otherwise."""
    project = recorded(root)
    if not project or key(project) == (0,) or key(project) == key(app):
        return "same"
    return "newer" if key(project) > key(app) else "older"


def refusal(root: Path, app: str = VERSION) -> str:
    """Why this app may change nothing in this project, or "" where it may."""
    if standing(root, app) != "newer":
        return ""
    return (f"This project was last updated by slipwai {recorded(root)}, and this app is {app}. What it would "
            f"write here goes where the project no longer reads, so it changes nothing until it matches: "
            f"update the app to {recorded(root)} or later, then open the project again.")


def notice(root: Path, app: str = VERSION) -> str:
    """The line every page carries where the app and the project disagree, as HTML, or ""."""
    held = standing(root, app)
    if held == "newer":
        said = refusal(root, app)
    elif held == "older":
        said = (f"This project was last updated by slipwai {recorded(root)}, and this app is {app}. It works as "
                f"it is; `slipwai migrate` in the project brings it up to {app}, with the fleet stopped.")
    else:
        return ""
    tone = "refused" if held == "newer" else "behind"
    return (f'<div class="card app-version {tone}" role="status" style="border-left:4px solid '
            f'{"#c0392b" if held == "newer" else "#d4a017"}"><p>{html.escape(said)}</p></div>')


def with_notice(body: str, root: Path, app: str = VERSION) -> str:
    """The page with the notice put first in its body, or as it was where there is none to give."""
    said = notice(root, app)
    if not said:
        return body
    at = body.find("<body")
    if at < 0:
        return said + body
    close = body.find(">", at)
    return body[:close + 1] + said + body[close + 1:] if close >= 0 else said + body

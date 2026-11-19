"""What `migrate` says about a guard an elected extension has and nobody agreed to.

A replay brings an extension's new files and what it now declares, so a project can gain a guard on an
upgrade. A guard is agreed to by a person and `migrate` is not one: it writes nothing into
`.slipwai/guards.json`. What it does is say so — in its report and on the catch-up page — with the command
that agrees, so a refusal somebody would have wanted is not left waiting for a question nobody asks (#121).

The sentences are the project's own. `scripts/extensions/guard_offer.py` is what `make agents` runs, and
this runs the same script without `--ask`: one place decides what is owed and how it is put, and a project
whose toolkit predates the script is a page short a section, never a traceback.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from .extension_copies import copies
from .layout import layout_of
from .shell_environment import python3
from .toolkit import EXTENSION_ROOT

#: The script in a project that says what is owed, beside the registry runner it names.
SCRIPT = f"{EXTENSION_ROOT}/guard_offer.py"
HEADING = "Guards nobody has agreed to"
#: Long enough for a cold interpreter on a slow disk; the script reads three small files.
BOUND = 60


def said(root: Path, document: dict | None) -> list[str]:
    """One line per elected extension owed an answer, each ending with its command; none where none is owed."""
    script = (layout_of(document).place(SCRIPT) if document else SCRIPT)
    if not (root / script).is_file():
        return []
    try:
        done = subprocess.run([python3(), script], cwd=root, capture_output=True, text=True, check=False,
                              timeout=BOUND, stdin=subprocess.DEVNULL, encoding="utf-8", errors="replace")
    except (OSError, subprocess.SubprocessError):
        return []
    return [line.strip() for line in done.stdout.splitlines() if line.startswith("guards: ")]


def section(root: Path, document: dict | None) -> list[str]:
    """The catch-up page's section, or no lines at all."""
    try:
        lines = said(root, document)
    except Exception:  # noqa: BLE001 — the merge is made: a page short a section, never a traceback
        return []
    if not lines:
        return []
    rows = []
    for line in lines:
        words, _, command = line.removeprefix("guards: ").rpartition(": ")
        rows.append(f"- {words}: `{command}`")
    return [
        "", f"## {HEADING}", "",
        "A guard lets an extension refuse a tool call, so a person agrees to each one. This migration agreed "
        "to nothing: `.slipwai/guards.json` is as it was. For each line below, run the command to agree, or "
        "leave it and the guard never fires. `make agents` says the same until it is settled.",
        "", *rows,
    ]


def owed(root: Path, document: dict | None) -> list[str]:
    """Everything the catch-up page says about this project's extensions: each copy that is not the installed
    package, then each guard waiting for an answer."""
    return [*copies(root, document), *section(root, document)]

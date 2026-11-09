"""`slipwai` in a terminal the person opened themselves, on a Mac, when they ask for it.

The app links `slipwai` for the board's own children (`first_run.link_command`), and never for the person's
shell: phase 23 promised not to touch a profile. Asked, from the *This machine* card, it adds one marked
block to the login shell's profile putting that link's folder on the **end** of the `PATH`, so a `slipwai`
the person installs later is still the one found. *Remove* takes the block out again, and nothing else in
the file is touched either way.

Only on macOS, where the app is the way in: a person on Linux has the command from installing it, and
Windows has *Open a terminal here* instead. Only zsh and bash, the two shells macOS has shipped as the
default; for another the card says what line to add.
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from .shell_environment import TOOLS, account_shell, login_environment

BEGIN = "# >>> slipwai: the app's command, added from the board's Settings >>>"
END = "# <<< slipwai <<<"
#: The folder `first_run.link_command` writes the link into, as a profile line spells it.
FOLDER = '$HOME/.slipwai/tools/slipwai/bin'
LINE = f'export PATH="$PATH:{FOLDER}"'
#: The profile each shell reads when Terminal opens a login shell.
PROFILES = {"zsh": ".zprofile", "bash": ".bash_profile"}


def profile(home: Path | None = None, shell: str | None = None) -> Path | None:
    """The login profile of this account's shell, or None for a shell this does not write to."""
    name = Path(shell if shell is not None else (os.environ.get("SHELL") or account_shell())).name
    file = PROFILES.get(name)
    return ((Path.home() if home is None else home) / file) if file else None


def block() -> str:
    return f"{BEGIN}\n{LINE}\n{END}\n"


def added(file: Path | None) -> bool:
    try:
        return file is not None and BEGIN in file.read_text(encoding="utf-8")
    except OSError:
        return False


def state(home: Path | None = None, shell: str | None = None, tools: Path | None = None,
          path: str | None = None) -> str:
    """`added`, `theirs` (a `slipwai` of their own is on their shell's `PATH`), `absent` (it can be added),
    `unsupported` (a shell this does not write to) or `none` (no app link to point at, or not macOS)."""
    link = (TOOLS if tools is None else tools) / "slipwai/bin/slipwai"
    if sys.platform != "darwin" or not link.is_file():
        return "none"
    file = profile(home, shell)
    if added(file):
        return "added"
    found = shutil.which("slipwai", path=login_environment().get("PATH", "") if path is None else path)
    if found and Path(found).parent.resolve() != link.parent.resolve():
        return "theirs"
    return "absent" if file is not None else "unsupported"


def add(home: Path | None = None, shell: str | None = None) -> str:
    """The block appended to the profile; a sentence saying what was done."""
    file = profile(home, shell)
    if file is None:
        return f"Your shell is not zsh or bash; add this line to its profile yourself: {LINE}"
    if added(file):
        return f"slipwai is already in {file}."
    held = file.read_text(encoding="utf-8") if file.is_file() else ""
    joined = held + ("" if not held or held.endswith("\n") else "\n") + ("\n" if held else "") + block()
    file.write_text(joined, encoding="utf-8")
    return f"Added to {file}. A terminal opened from now on has slipwai; one already open does not."


def remove(home: Path | None = None, shell: str | None = None) -> str:
    """The block taken out of the profile, and nothing else; a sentence saying what was done."""
    file = profile(home, shell)
    if not added(file):
        return "slipwai was not in your shell's profile."
    assert file is not None
    text = file.read_text(encoding="utf-8")
    start, finish = text.index(BEGIN), text.index(END, text.index(BEGIN)) + len(END)
    before, after = text[:start], text[finish:].removeprefix("\n")
    if before.endswith("\n\n"):
        before = before[:-1]
    file.write_text(before + after, encoding="utf-8")
    return f"Removed from {file}. A terminal opened from now on has no slipwai from the app."

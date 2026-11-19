"""`slipwai extension remove`, where it is run in a project that elected the extension: taken back there first.

Removing a package takes it off this machine. A project that elected it keeps its copy until its next
migration, and keeps for ever whatever the extension wrote outside that copy — `codegraph` writes
`scripts/codegraph` — because nothing recorded that it had and there was no point at which it could take it
back (#119). There is now: the `remove` point, fired by the project's own runner, which also names every path
the election recorded that is still there.

**The project un-elects itself.** Anything a generated project runs is a toolkit script, so this runs the
project's `scripts/extensions/hooks.py --remove <key>` and prints what it said. It reaches no other project:
one command run in one directory does not edit repositories it was not run in, so anywhere else it says the
line to run in each.

**It never blocks the removal.** A hook that crashes is the runner's to report, and the runner exits 0. A
runner that cannot be started, or one from before un-election existed, is said here in one line, and the
package is removed all the same.
"""
from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .assets import this_command
from .extension_copies import elected
from .layout import layout_of
from .shell_environment import python3
from .toolkit import EXTENSION_ROOT

#: The project's own verb, relative to it. Said wherever this could not run it.
VERB = "--remove"
#: How long a project's un-election may take before the removal goes on without it.
BOUND = 120


def taken_back(root: Path, key: str, run: Callable[..., Any] = subprocess.run) -> list[str]:
    """What to print before `key` is removed: the project's un-election where `root` is a project that elected
    it, and otherwise the line that un-elects it in one that did."""
    try:
        document = json.loads((root / "project.json").read_text(encoding="utf-8"))
        place = layout_of(document).place(EXTENSION_ROOT)
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        document, place = None, EXTENSION_ROOT
    command = f"python3 {place}/hooks.py {VERB} {key}"
    if document is None or key not in elected(root):
        return [f"a project that elected {key} still has its election, its copy and whatever it wrote there. In "
                f"each: `{command}`, before its next `{this_command()} migrate` takes the copy away"]
    runner = root / place / "hooks.py"
    try:
        knows = f'"{VERB}"' in runner.read_text(encoding="utf-8")
        done = run([python3(), str(runner), VERB, key], cwd=root, text=True, capture_output=True,
                   timeout=BOUND, check=False) if knows else None
    except (OSError, UnicodeDecodeError, subprocess.SubprocessError) as error:
        return [not_here(key, command, f"its runner could not be run ({type(error).__name__})")]
    if done is None:
        return [not_here(key, command, f"its `{place}/hooks.py` is from before an extension could be un-elected")]
    if done.returncode != 0:
        return [not_here(key, command, f"its runner exited {done.returncode}")]
    return [line for line in (done.stdout + done.stderr).splitlines() if line.strip()]


def not_here(key: str, command: str, why: str) -> str:
    return (f"{key} could not be un-elected here: {why}. The package is removed all the same; "
            f"`{this_command()} migrate` brings this project a runner that can, then `{command}`")

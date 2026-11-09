"""The environment a person's own terminal would have, for a child started from somewhere that lacks it.

The board is started from wherever somebody started it — an app, a launcher, an agent's shell — and a child
of it inherits that environment. One of those had `PATH=/usr/bin:/bin` and no exported tokens, so `generate`
refused a managed target for want of its tools and `gh` on a machine that had every one of them signed in:
every check is `which` and the environment, and that is exactly what such a shell reports. So a child is
given what the login shell has, read once, with this process's own variables kept where both have one.

**The tools the board installed.** Git, Python or Node the board fetched live under `~/.slipwai/tools/`,
where no shell looks. One fetched because the machine had none goes on the end of a child's `PATH`. One
fetched because the machine's copy was too old goes at the front, or the old copy would still be found.
"""
from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Mapping
from pathlib import Path

#: Where the board puts a tool the machine did not have: `<key>/tool.json` names its `bin` directory.
TOOLS = Path.home() / ".slipwai" / "tools"


def account_shell() -> str:
    """The login shell the account record names, or `""` where there is no record to ask (Windows)."""
    try:
        import pwd
        return pwd.getpwuid(os.getuid()).pw_shell or ""
    except (ImportError, KeyError, OSError):
        return ""


def login_environment(current: Mapping[str, str] | None = None, shell: str | None = None) -> dict[str, str]:
    """This process's environment with the login shell's `PATH` and exports under it. A shell that cannot be
    asked — none named, or one that does not answer in time — leaves the environment as it was."""
    held = dict(os.environ if current is None else current)
    # `SHELL` first; then the account's own shell, because a process `launchd` starts — the board at login —
    # is given no `SHELL` at all, and without one it ran with `/usr/bin:/bin` and found nothing a person installs.
    command = shell or held.get("SHELL") or account_shell()
    if not command or os.name == "nt":
        return with_tools(held)
    try:
        done = subprocess.run([command, "-ilc", "env -0"], capture_output=True, text=False, timeout=10,
                              stdin=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired):
        return with_tools(held)
    if done.returncode != 0 or not done.stdout:
        return with_tools(held)
    login: dict[str, str] = {}
    for pair in done.stdout.split(b"\0"):
        name, _, value = pair.decode("utf-8", "replace").partition("=")
        if name and "\n" not in name:
            login[name] = value
    paths = [*login.get("PATH", "").split(os.pathsep), *held.get("PATH", "").split(os.pathsep)]
    merged = {**login, **held}
    merged["PATH"] = os.pathsep.join(dict.fromkeys(part for part in paths if part))
    return with_tools(merged)


def board_tools(home: Path | None = None, first: bool = False) -> list[str]:
    """The `bin` directories of the tools the board installed, where each is still there: those that go
    first (installed over an old copy) where `first`, the rest otherwise."""
    found = []
    for record in sorted((TOOLS if home is None else home).glob("*/tool.json")):
        try:
            held = json.loads(record.read_text(encoding="utf-8"))
            where, ahead = str(held.get("bin") or ""), bool(held.get("first"))
        except (OSError, ValueError, AttributeError):
            continue
        if where and Path(where).is_dir() and ahead == first:
            found.append(where)
    return found


def with_tools(held: dict[str, str], home: Path | None = None) -> dict[str, str]:
    """`held` with the board's own tools on its `PATH`: ahead of everything where they replace an old copy,
    after everything otherwise."""
    ahead, after = board_tools(home, first=True), board_tools(home)
    if not ahead and not after:
        return held
    paths = [*ahead, *held.get("PATH", "").split(os.pathsep), *after]
    return {**held, "PATH": os.pathsep.join(dict.fromkeys(part for part in paths if part))}

"""The environment a person's own terminal would have, for a child started from somewhere that lacks it.

The board is started from wherever somebody started it — an app, a launcher, an agent's shell — and a child
of it inherits that environment. One of those had `PATH=/usr/bin:/bin` and no exported tokens, so `generate`
refused a managed target for want of its tools and `gh` on a machine that had every one of them signed in:
every check is `which` and the environment, and that is exactly what such a shell reports. So a child is
given what the login shell has, read once, with this process's own variables kept where both have one.
"""
from __future__ import annotations

import os
import subprocess
from collections.abc import Mapping


def login_environment(current: Mapping[str, str] | None = None, shell: str | None = None) -> dict[str, str]:
    """This process's environment with the login shell's `PATH` and exports under it. A shell that cannot be
    asked — none named, or one that does not answer in time — leaves the environment as it was."""
    held = dict(os.environ if current is None else current)
    command = shell or held.get("SHELL") or ""
    if not command or os.name == "nt":
        return held
    try:
        done = subprocess.run([command, "-ilc", "env -0"], capture_output=True, text=False, timeout=10,
                              stdin=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired):
        return held
    if done.returncode != 0 or not done.stdout:
        return held
    login: dict[str, str] = {}
    for pair in done.stdout.split(b"\0"):
        name, _, value = pair.decode("utf-8", "replace").partition("=")
        if name and "\n" not in name:
            login[name] = value
    paths = [*login.get("PATH", "").split(os.pathsep), *held.get("PATH", "").split(os.pathsep)]
    merged = {**login, **held}
    merged["PATH"] = os.pathsep.join(dict.fromkeys(part for part in paths if part))
    return merged

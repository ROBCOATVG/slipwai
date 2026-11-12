"""The environment a person's own terminal would have, for a child started from somewhere that lacks it.

The board is started from wherever somebody started it — an app, a launcher, an agent's shell — and a child
of it inherits that environment. One of those had `PATH=/usr/bin:/bin` and no exported tokens, so `generate`
refused a managed target for want of its tools and `gh` on a machine that had every one of them signed in:
every check is `which` and the environment, and that is exactly what such a shell reports. So a child is
given what the login shell has, read once, with this process's own variables kept where both have one.

**The tools the board installed.** Git, Python or Node the board fetched live under `~/.slipwai/tools/`,
where no shell looks. One fetched because the machine had none goes on the end of a child's `PATH`. One
fetched because the machine's copy was too old goes at the front, or the old copy would still be found.

**Git's bash, on Windows.** A project's own scripts run under the bash Git for Windows carries, and the
commands its recipes call — `sed`, `grep`, `find`, `sort` — are the ones beside that bash in Git's
`usr/bin`. That folder goes at the very front of a child's `PATH`, or Windows' own `find` and `sort` in
`System32` would be the ones a recipe found. Nothing changes on macOS or Linux.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from collections.abc import Mapping, MutableMapping
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


def login_environment(current: Mapping[str, str] | None = None, shell: str | None = None,
                      root: Path | None = None) -> dict[str, str]:
    """This process's environment with the login shell's `PATH` and exports under it. A shell that cannot be
    asked — none named, or one that does not answer in time — leaves the environment as it was. Given the
    project a child runs in, that project's own venv goes first (`in_project`)."""
    return in_project(from_login(current, shell), root)


def project_venv(root: Path) -> Path | None:
    """The venv `./init` makes where `python3` refuses pip (PEP 668: Homebrew's, a recent Debian's), and
    installs PyYAML into, or None where it made none."""
    folder = root / ".delivery-tools/venv" / ("Scripts" if os.name == "nt" else "bin")
    return folder if folder.is_dir() else None


def in_project(held: dict[str, str], root: Path | None) -> dict[str, str]:
    """`held` with the project's venv first on its `PATH`. `./init` tells a person to put it there when it
    makes one, and a child of the board has nobody to tell: it found the system `python3`, which has no
    PyYAML and will not take it, and the project's scripts stopped at their first `import yaml`."""
    venv = project_venv(root) if root is not None else None
    if venv is None:
        return held
    return {**held, "PATH": os.pathsep.join([str(venv), *(part for part in held.get("PATH", "").split(os.pathsep)
                                                           if part and part != str(venv))])}


def from_login(current: Mapping[str, str] | None = None, shell: str | None = None) -> dict[str, str]:
    """`login_environment` for no project in particular."""
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


def adopt_tools(environ: MutableMapping[str, str] | None = None, home: Path | None = None) -> None:
    """The tools the board installed, on the end of this process's own `PATH`.

    A child given `login_environment` finds them; a program this process starts by its bare name does not,
    because the name is looked for on *this* process's `PATH`. On a machine whose only Git is the board's,
    the first `git` the board ran itself — is there a remote? — was `[WinError 2] The system cannot find
    the file specified`, said in place of the project that had just been made. On the end only: what the
    machine has of its own is still found first, and nothing of Git's `usr/bin` shadows Windows' here."""
    held = os.environ if environ is None else environ
    parts = [part for part in held.get("PATH", "").split(os.pathsep) if part]
    added = [where for where in (*board_tools(home, first=True), *board_tools(home)) if where not in parts]
    if added:
        held["PATH"] = os.pathsep.join([*parts, *added])


def git_bash(path: str) -> Path | None:
    """The `usr/bin` of the first Git for Windows on `path` that carries bash — the folder Git Bash itself
    puts first — or None where every Git on it is one without (MinGit) or there is none. Git's `git.exe`
    sits in `cmd/`, `bin/` or `mingw64/bin/` under the folder Git was installed or unpacked in."""
    for part in path.split(";"):
        folder = Path(part.strip().strip('"')) if part.strip() else None
        if folder is None or not (folder / "git.exe").is_file():
            continue
        for root in (folder.parent, folder.parent.parent):
            if (root / "usr/bin/bash.exe").is_file():
                return root / "usr/bin"
    return None


def windows_python(path: str) -> str | None:
    """The `python.exe` on a Windows `path`, passing over `WindowsApps`, whose `python3.exe` and
    `python.exe` are the Store's stubs that open the Store."""
    kept = ";".join(part for part in path.split(";") if "windowsapps" not in part.lower())
    return shutil.which("python", path=kept)


def python3(system: str | None = None) -> str:
    """What this process starts a project's Python script with: `python3` on macOS and Linux, as always.
    A Windows program starts only `.exe` files, so there it is the `python.exe` the board's children find —
    the one bash's `python3` shim starts — or, outside a frozen app, this process's own."""
    if (system or sys.platform) != "win32":
        return "python3"
    found = windows_python(with_tools(dict(os.environ)).get("PATH", ""))
    return found or ("python" if getattr(sys, "frozen", False) else sys.executable)


def project_python(root: Path | None = None) -> str:
    """The interpreter the project's own scripts run under: the `python3` the login shell finds, which is the
    one `./init` installed PyYAML into — not this process's, which is the keel's own environment and reads
    no YAML by design. The keel's as a fallback, so a machine with no other python still gets an answer.
    The walk is spelled out rather than borrowed from `shutil.which`, which a suite elsewhere stands in for.
    Never `sys.executable` where frozen: that is the slipwai executable itself, which takes a script's path for a
    verb and refuses it."""
    if sys.platform == "win32":  # the `python3` there is bash's shim, which no Windows program can start
        return python3()
    for directory in (login_environment(root=root).get("PATH") or "").split(os.pathsep):
        candidate = Path(directory) / "python3"
        if directory and candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return python3() if getattr(sys, "frozen", False) else sys.executable


def with_tools(held: dict[str, str], home: Path | None = None, system: str | None = None) -> dict[str, str]:
    """`held` with the board's own tools on its `PATH`: ahead of everything where they replace an old copy,
    after everything otherwise, and on Windows Git's `usr/bin` ahead of them all."""
    ahead, after = board_tools(home, first=True), board_tools(home)
    if not ahead and not after and (system or sys.platform) != "win32":
        return held
    paths = [*ahead, *held.get("PATH", "").split(os.pathsep), *after]
    if (system or sys.platform) == "win32" and (bash := git_bash(";".join(paths))) is not None:
        paths.insert(0, str(bash))
    return {**held, "PATH": os.pathsep.join(dict.fromkeys(part for part in paths if part))}

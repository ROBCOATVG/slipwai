"""The harness's own command, installed by the board where the machine has none.

The board talks to an agent over the Agent Client Protocol, and an agent fetched by `npx` is an adapter or
a package in npm's cache: nothing puts the harness's own command — `claude`, `codex`, `gemini` — on any
path. Two things run that command by name. Spec Kit looks for it before it installs an integration, and a
captain runs it headless for every slice. On a machine with nothing but the board and the tools it
installed, `./init --integration claude` therefore ended *claude not found*, the project was left without
Spec Kit's commands, and the draft went on without them.

The registry's `cli` column names the npm package that installs the command, and the command. Where the
machine has no such command and has `npm`, the board installs the package under
`~/.slipwai/tools/<key>-cli/` as the step before `./init`, and records it as it records any tool it
installed (`tool.json`), so every child the board starts finds it and a person's terminal is not touched.
A machine that has the command already is left exactly as it is. A harness the registry names no package
for is left to say so itself, as before.
"""
from __future__ import annotations

import json
import shutil
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from .harness import name_of, row_of
from .shell_environment import TOOLS, adopt_tools, login_environment

#: What a step is made of: the command, the line said before it, and the line said after it for its status.
Part = tuple[list[str], str, Callable[[int], str]]


def row(key: str) -> dict | None:
    """The harness's `cli` row — the package and the command — or `None` where the registry has none."""
    held = row_of(key).get("cli")
    return held if isinstance(held, dict) and held.get("npm") and held.get("cmd") else None


def home(key: str, tools: Path | None = None) -> Path:
    return (TOOLS if tools is None else tools) / f"{key}-cli"


def install_argv(key: str, path: str | None = None, tools: Path | None = None) -> list[str]:
    """The `npm install` that puts the harness's command under the board's tools, or nothing: no row, the
    command already on `path`, or no `npm` to install it with."""
    held = row(key)
    path = login_environment().get("PATH", "") if path is None else path
    if held is None or shutil.which(str(held["cmd"]), path=path) or not shutil.which("npm", path=path):
        return []
    return ["npm", "install", "--prefix", str(home(key, tools)), "--no-fund", "--no-audit", "--loglevel", "error",
            str(held["npm"])]


def announced(key: str) -> str:
    held = row(key) or {}
    return (f"Installing {name_of(key)}'s own command — `{held.get('cmd')}`, from npm's {held.get('npm')} — under "
            f"~/.slipwai/tools: this machine has none, and Spec Kit and the fleet run it by name.")


def installed(key: str, code: int, tools: Path | None = None) -> str:
    """The install recorded as a tool of the board's, where it left the command; the line saying how it ended."""
    held = row(key) or {}
    folder = home(key, tools)
    where = folder / "node_modules" / ".bin"
    if code != 0 or not any(where.glob(f"{held.get('cmd')}*")):
        return (f"`{held.get('cmd')}` could not be installed (npm ended {code}); its lines above say why. `./init` "
                f"is tried all the same, and says what it finds.")
    try:
        package = folder / "node_modules" / str(held["npm"]) / "package.json"
        version = json.loads(package.read_text("utf-8"))["version"]
    except (OSError, ValueError, KeyError):
        version = ""
    record = {"bin": str(where), "version": str(version), "at": datetime.now(UTC).strftime("%Y-%m-%d"), "first": False}
    (folder / "tool.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    adopt_tools(home=folder.parent)
    return f"Installed `{held.get('cmd')}` {version} in {where}.".replace("  ", " ")


def parts(key: str | None, path: str | None = None, tools: Path | None = None) -> list[Part]:
    """The step that installs the harness's command, as what a step is made of; none where nothing is to do."""
    argv = install_argv(key, path, tools) if key else []
    return [(argv, announced(str(key)), lambda code: installed(str(key), code, tools))] if argv else []

"""What a route on the board needs on this machine, and whether the machine has it.

A person who chose a route — an idea, a PRD, a codebase — should learn what it needs before they start, not
from a log ten minutes in. So the tools a route reaches for are one table here, each row saying in plain
words why it is needed, and the board reads the table twice: the *This machine* card on Settings, and a line at the
top of a start page where the route it begins needs something the machine lacks.

**Found means usable, not present.** A tool is looked for on the `PATH` the board's children get
(`login_environment`, which carries what the board installed on its end) and then asked its version. On
macOS `/usr/bin/git` is there on every machine and is a shim that opens Apple's installer when run without
the developer tools, so it is not run at all until `xcode-select -p` says the tools are there.

**A copy too old is reported, not replaced.** The board installs only where the machine has no copy
(`tool_install`); an old one is named with the version needed and left alone.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import dataclass

from .shell_environment import login_environment

#: The Python a project's scripts need, which is the keel's own floor (`pyproject.toml`).
PYTHON_FLOOR = (3, 11)
#: The oldest Node line still maintained. Not the project's `.nvmrc` pin: that is what a project builds with
#: in CI, and a person's Node one line behind it runs the model check and the `npx` agents alike.
NODE_FLOOR = (22,)


@dataclass(frozen=True)
class Tool:
    """One thing a route needs on the machine, why, and where a person gets it themselves."""

    key: str
    name: str
    command: str
    #: The oldest version that does what the route needs, or `()` where any does.
    minimum: tuple[int, ...]
    why: str
    page: str
    #: How it is asked its version: `--version` for most, `go version` and `java -version` for those two.
    asks: tuple[str, ...] = ("--version",)


#: The tools, in the order the card lists them, each `why` in the card's plain words. The code behind each
#: row is in the audit, section 7 of `docs/double-click-plan.md`.
TOOLS = (
    Tool("git", "Git", "git", (), "every project keeps its history in Git, and the agents work on branches of it",
         "https://git-scm.com/downloads"),
    Tool("make", "Make", "make", (), "every check a project runs, and every step the board starts, is run by Make",
         "https://www.gnu.org/software/make/"),
    Tool("python3", "Python", "python3", PYTHON_FLOOR, "a project's own scripts are written in Python, and need "
         "3.11 or newer", "https://www.python.org/downloads/"),
    Tool("node", "Node", "node", NODE_FLOOR, "the event model is checked with it, TypeScript and JavaScript "
         "projects are built with it, and many coding agents are started with it", "https://nodejs.org/en/download"),
    Tool("uv", "uv", "uv", (), "a Python service is built and tested with it",
         "https://docs.astral.sh/uv/getting-started/installation/"),
    Tool("go", "Go", "go", (), "a Go service is built and tested with it", "https://go.dev/dl/", ("version",)),
    Tool("java", "Java", "java", (), "a Java service is built with it", "https://adoptium.net/", ("-version",)),
)
BY_KEY = {one.key: one for one in TOOLS}

#: What each start page's route needs whatever is chosen on it. A language's own needs, and the default
#: profile's Node, are added by `needs`, because the route does not know them until the person has chosen.
ROUTES: dict[str, tuple[str, ...]] = {"/brief": (), "/generate": ("git", "make", "python3"),
                                      "/adopt": ("git", "make", "python3")}
#: The languages that need a tool of their own on the machine.
LANGUAGES: dict[str, tuple[str, ...]] = {"typescript": ("node",), "javascript": ("node",), "python": ("uv",),
                                         "go": ("go",), "java": ("java",), "java-quarkus": ("java",),
                                         "java-spring": ("java",)}
#: The profile whose gate checks the event model with Node, and the one a project gets unasked.
NODE_PROFILE = "event-modelling"
#: On macOS these are shims in `/usr/bin` that open Apple's installer when run without the developer tools.
APPLE_SHIMS = frozenset({"git", "make", "python3"})


@dataclass(frozen=True)
class Found:
    """What the machine has of one tool: `found`, `old` or `missing`, where, and which version."""

    tool: Tool
    state: str
    where: str = ""
    version: str = ""


def version_of(text: str) -> tuple[int, ...]:
    """The first dotted number in a `--version` line: `git version 2.39.5` is `(2, 39, 5)`."""
    hit = re.search(r"(\d+(?:\.\d+)*)", text)
    return tuple(int(part) for part in hit.group(1).split(".")) if hit else ()


def developer_tools() -> bool:
    """Whether macOS's command line developer tools are installed, asked without opening their installer."""
    try:
        return subprocess.run(["xcode-select", "-p"], capture_output=True, timeout=10, check=False).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def found(tool: Tool, path: str | None = None) -> Found:
    """Whether the machine has a usable copy of `tool` on the board's children's `PATH`, and which."""
    path = login_environment().get("PATH", "") if path is None else path
    where = shutil.which(tool.command, path=path)
    if not where:
        return Found(tool, "missing")
    if (sys.platform == "darwin" and tool.command in APPLE_SHIMS and where == f"/usr/bin/{tool.command}"
            and not developer_tools()):
        return Found(tool, "missing")
    try:
        done = subprocess.run([where, *tool.asks], capture_output=True, text=True, timeout=20, check=False)
    except (OSError, subprocess.SubprocessError):
        return Found(tool, "missing", where)
    if done.returncode != 0:
        return Found(tool, "missing", where)
    version = version_of(done.stdout or done.stderr)
    said = ".".join(str(part) for part in version)
    return Found(tool, "old" if tool.minimum and version < tool.minimum else "found", where, said)


def needs(route: str, answers: Mapping[str, str] | None = None) -> list[str]:
    """The tools `route` needs for these answers: the route's own, the language's, and Node where the PRD
    route's profile is the event-modelling one — which it is until somebody picks another."""
    answers = answers or {}
    language = str(answers.get("language") or answers.get("backend") or "").strip().lower()
    keys = [*ROUTES.get(route, ()), *LANGUAGES.get(language, ())]
    if route == "/generate" and (answers.get("profile") or NODE_PROFILE) == NODE_PROFILE:
        keys.append("node")
    return list(dict.fromkeys(keys))


def everything(path: str | None = None) -> list[Found]:
    """Every tool, looked for on one reading of the login `PATH` rather than one per tool."""
    path = login_environment().get("PATH", "") if path is None else path
    return [found(tool, path) for tool in TOOLS]


def lacking(route: str, answers: Mapping[str, str] | None = None, look=None) -> list[Found]:
    """What `route` needs that this machine lacks or has too old: nothing, where it has everything."""
    keys = needs(route, answers)
    if not keys:
        return []
    if look is None:
        path = login_environment().get("PATH", "")
        rows = [found(BY_KEY[key], path) for key in keys]
    else:
        rows = [look(BY_KEY[key]) for key in keys]
    return [one for one in rows if one.state != "found"]

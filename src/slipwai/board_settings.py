"""What runs behind the board: the agent its conversations are sessions of, and what the board remembers
about it.

One file, `~/.slipwai/board.json`, read when a session starts. *Runs on* is a registry key or `auto`, which
is the first agent this machine can launch. A model is remembered per agent, and only ever one the agent
itself offered: the board names no model of its own, it keeps what `session/new` answered under
`configOptions` of category `model` the last time a session began, so the settings page can show it.

A project's own answer outranks the board's. `.specify/integration.json` is what the person told `./init`,
and a console on that project is a session of that agent where this machine can launch it; the first page,
with no project, has only the board's answer. Nothing here is required: no file, no agent that can be
launched, and the board's sessions run as they did before this — on `claude` by name — and say so.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from .assets import SLIPWAI
from .harness import acp_keys, acp_launch, from_spec_kit, name_of
from .shell_environment import login_environment

SETTINGS = SLIPWAI / "board.json"
#: The first agent this machine can launch, in the registry's order. What a board with no file runs on.
AUTO = "auto"


@dataclass
class Settings:
    runs_on: str = AUTO
    models: dict[str, str] = field(default_factory=dict)  # agent key -> the model value it offered and was set
    offered: dict[str, list[dict]] = field(default_factory=dict)  # agent key -> its model options, last seen

    def record(self) -> dict:
        return {"runs_on": self.runs_on, "models": self.models, "offered": self.offered}


def read(path: Path | None = None) -> Settings:
    path = SETTINGS if path is None else path  # looked up now, not when the module loaded, so a test can move it
    try:
        held = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return Settings()
    if not isinstance(held, dict):
        return Settings()
    return Settings(runs_on=str(held.get("runs_on") or AUTO),
                    models={str(k): str(v) for k, v in (held.get("models") or {}).items()},
                    offered={str(k): list(v) for k, v in (held.get("offered") or {}).items() if isinstance(v, list)})


def write(settings: Settings, path: Path | None = None) -> None:
    path = SETTINGS if path is None else path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings.record(), indent=2) + "\n", encoding="utf-8")


@lru_cache(maxsize=1)
def shell_path() -> str:
    """The login shell's PATH, asked once a process. The board started at login has `launchd`'s, which
    holds nothing a person installed, so an agent on this machine was "not on PATH" on a machine that had it."""
    return login_environment(os.environ).get("PATH", os.environ.get("PATH", ""))


@dataclass(frozen=True)
class Launch:
    """One agent as this machine sees it: its key and name, the command, or the sentence saying what is missing."""

    key: str
    name: str
    argv: tuple[str, ...]
    said: str

    @property
    def able(self) -> bool:
        return bool(self.argv)


def launches(path: str | None = None) -> list[Launch]:
    """Every agent the registry can launch, as this machine can or cannot: the settings page's list."""
    found = shell_path() if path is None else path
    return [Launch(key, name_of(key), tuple(argv), said) for key in acp_keys()
            for argv, said in [acp_launch(key, found)]]


def chosen(settings: Settings, root: Path | None = None, path: str | None = None) -> Launch | None:
    """The agent a session on this board runs through, or `None` with nothing this machine can launch.

    A project's recorded harness first, where it has a launch this machine can make; then the board's
    *Runs on*; then, on `auto`, the first agent found. A choice that cannot be launched is not quietly
    replaced by one that can: it is returned as it is, unable, so the page can say what is missing.
    """
    found = shell_path() if path is None else path
    if root is not None:
        recorded = from_spec_kit(root)
        if recorded is not None and recorded.harness in acp_keys():
            argv, said = acp_launch(recorded.harness, found)
            if argv:
                return Launch(recorded.harness, name_of(recorded.harness), tuple(argv), said)
    if settings.runs_on != AUTO:
        argv, said = acp_launch(settings.runs_on, found)
        return Launch(settings.runs_on, name_of(settings.runs_on), tuple(argv), said)
    return next((one for one in launches(found) if one.able), None)


def model_options(options: list[dict]) -> list[dict]:
    """The config options of category `model` an agent offered at `session/new`, flattened to what the
    settings page shows: `{"id", "name", "current", "values": [{"name", "value"}]}`."""
    shown = []
    for one in options:
        if one.get("category") != "model" or one.get("type") != "select":
            continue
        values: list[dict] = []
        for row in one.get("options") or []:
            if "options" in row:  # a group: its name over its rows
                values.extend({"name": f"{row.get('name')}: {inner.get('name')}", "value": inner.get("value")}
                              for inner in row.get("options") or [])
            else:
                values.append({"name": row.get("name"), "value": row.get("value")})
        shown.append({"id": one.get("id"), "name": one.get("name"), "current": one.get("currentValue"),
                      "values": values})
    return shown


def offered(settings: Settings, key: str, options: list[dict], path: Path | None = None) -> None:
    """What an agent offered when a session began, kept so the page can show it next time."""
    settings.offered[key] = model_options(options)
    write(settings, path)

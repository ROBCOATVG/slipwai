"""Which coding agent the delivery material is projected into, and how a run can tell without asking.

`./init` installs Spec Kit and projects the canonical `skills/`, `commands/` and `agents/` into one harness's
native locations; `assets/toolkit/scripts/agents/registry.json` is where the thirty-six it knows are declared,
each with the directories it reads them from. That answer has always been `./init`'s question, asked after
`adopt` had already finished — which is one step too late to be any use to an adoption, because the questions
worth handing to a coding agent are asked before there is one.

It is also a question that mostly need not be asked. A run of `slipwai` started from inside a harness is told
so by its environment, and a repository that already has a team's agent in it says which one in the tree. So
this detects, and records the answer the way every other adopted fact is recorded — with where it came from.
What it cannot tell, it leaves `unrecorded` rather than guessing: `./init` still has its own question, and a
thirty-six-row list is a question a terminal has no good way to ask.

Nothing here decides anything. `adopt` records what this returns, and a person's `--integration` outranks it.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .assets import TOOLKIT_ROOT

REGISTRY = TOOLKIT_ROOT / "scripts/agents/registry.json"
# A context file every harness with `contextMode: canonical` shares, so its presence names none of them.
SHARED_CONTEXT = "AGENTS.md"
# Variables a harness sets in the environment of what it runs, where that has been verified from the harness
# itself (read 2026-09-21). A harness with no row here is not one that cannot be detected — it is one nobody
# has checked, which is why an absent row falls through to the tree and then to `./init`'s own question
# rather than to a guess. Adding a row is one line and a date.
ENVIRONMENT: dict[str, tuple[str, ...]] = {
    "claude": ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT"),
    "cursor-agent": ("CURSOR_AGENT", "CURSOR_TRACE_ID"),
}


@dataclass(frozen=True)
class Agent:
    """Which harness gets the material, and how that was established.

    `harness` is None where nobody has said and nothing showed: `provenance` is then `unrecorded`, which is
    the written form of an open question and not a default. `candidates` carries what the tree suggested when
    it suggested more than one, so the report can say why it is not recording any of them.
    """

    harness: str | None = None
    evidence: str | None = None
    provenance: str = "unrecorded"
    candidates: tuple[str, ...] = ()

    def record(self) -> dict:
        if self.harness is None and not self.candidates:
            return {"provenance": "unrecorded"}
        return {
            **({"harness": self.harness} if self.harness else {}),
            **({"evidence": self.evidence} if self.evidence else {}),
            "provenance": self.provenance,
        }


@lru_cache(maxsize=1)
def registry() -> list[dict]:
    document = json.loads(REGISTRY.read_text())
    return [row for row in document.get("harnesses", []) if isinstance(row, dict) and row.get("key")]


def keys() -> tuple[str, ...]:
    return tuple(row["key"] for row in registry())


def name_of(key: str) -> str:
    return next((row["name"] for row in registry() if row["key"] == key), key)


@lru_cache(maxsize=1)
def marks() -> dict[str, str]:
    """Each path in the tree that names exactly one harness, to the harness it names.

    A directory two harnesses read — `.agents/skills`, which Codex, Zed and Antigravity all use — names
    neither, so it is not a mark. Nor is the shared `AGENTS.md`: every canonical harness writes it.
    """
    claimed: dict[str, set[str]] = {}
    for row in registry():
        for field in ("skillsDir", "commandsDir", "contextFile"):
            path = row.get(field)
            if isinstance(path, str) and path and path != SHARED_CONTEXT:
                claimed.setdefault(path, set()).add(row["key"])
    return {path: next(iter(owners)) for path, owners in claimed.items() if len(owners) == 1}


def from_environment(environ: dict[str, str] | None = None) -> Agent | None:
    """The harness this run was started from, where it says so in the environment."""
    found = os.environ if environ is None else environ
    for key, variables in ENVIRONMENT.items():
        named = next((variable for variable in variables if found.get(variable)), None)
        if named:
            return Agent(key, f"{name_of(key)} set {named} in the environment this ran in", "detected")
    return None


def from_tree(root: Path) -> Agent | None:
    """The harness the repository already uses, where exactly one left something only it reads."""
    seen: dict[str, list[str]] = {}
    for path, key in sorted(marks().items()):
        if (root / path).exists():
            seen.setdefault(key, []).append(path)
    if len(seen) == 1:
        key, paths = next(iter(seen.items()))
        return Agent(key, f"`{'`, `'.join(paths)}` in the tree, which only {name_of(key)} reads", "detected")
    if seen:
        return Agent(None, None, "unrecorded", tuple(sorted(seen)))
    return None


def detect(root: Path, environ: dict[str, str] | None = None) -> Agent:
    """Which harness this adoption is for: the one that started it, else the one already here, else nobody's
    word. The environment outranks the tree — a person running from inside an agent is using that one now,
    whatever the repository was set up for once."""
    return from_environment(environ) or from_tree(root) or Agent()


def chosen(key: str) -> Agent:
    """A harness a person named, which outranks anything detected."""
    return Agent(key, "named with --integration", "overridden")

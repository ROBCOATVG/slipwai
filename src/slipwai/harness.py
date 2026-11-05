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

from .assets import SLIPWAI, TOOLKIT_ROOT

REGISTRY = TOOLKIT_ROOT / "scripts/agents/registry.json"
#: Where the board installs an agent from its archive (`agent_install.py`): `<key>/launch.json` says what to run.
INSTALLED = SLIPWAI / "agents"
# Where Spec Kit records the integration `./init` installed. Written by `specify init` and by nothing this
# factory generates, so its `integration` is not a reading of the tree but a person's answer to `./init`'s
# own question — the strongest evidence there is, and the one that closes the gap where `adopt` could not
# tell and handed the question on.
SPEC_KIT = ".specify/integration.json"
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
    document = json.loads(REGISTRY.read_text(encoding="utf-8"))
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


def from_spec_kit(root: Path) -> Agent | None:
    """The harness `./init` installed, as Spec Kit recorded it when it asked.

    A person answered that question, so this is `confirmed` rather than `detected` — the one source here
    that is somebody's word rather than a reading. It is why a repository whose tree reads for three
    harnesses stops being a question once `./init` has run.
    """
    recorded = root / SPEC_KIT
    if not recorded.is_file():
        return None
    try:
        document = json.loads(recorded.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    key = document.get("integration") if isinstance(document, dict) else None
    if not isinstance(key, str) or key not in keys():
        return None
    return Agent(key, f"`{SPEC_KIT}` records it: `./init` asked, and this was the answer", "confirmed")


def detect(root: Path, environ: dict[str, str] | None = None) -> Agent:
    """Which harness this adoption is for: the one somebody answered `./init` with, else the one this run
    started from, else the one already here, else nobody's word.

    Spec Kit's record outranks both because it is an answer and they are readings. The environment then
    outranks the tree — a person running from inside an agent is using that one now, whatever the repository
    was set up for once."""
    return from_spec_kit(root) or from_environment(environ) or from_tree(root) or Agent()


def chosen(key: str) -> Agent:
    """A harness a person named, which outranks anything detected."""
    return Agent(key, "named with --integration", "overridden")


def row_of(key: str) -> dict:
    """One harness's row, or an empty one for a key the registry has not got."""
    return next((row for row in registry() if row.get("key") == key), {})


def proven(key: str) -> bool:
    """Whether a captain has run a feature end to end on this harness.

    False for every row today, and said rather than left out. A harness's row records what its documentation
    says about running it headless and about its hooks; what it does not record is whether any of that was
    true when a run depended on it. Those are different claims, and a factory that printed the first as
    though it were the second would be making a promise from somebody else's README.
    """
    return bool(row_of(key).get("proven"))


def unproven_line(key: str) -> str:
    """What a verb says about an unproven harness, or `''` for one a captain has driven.

    Not a refusal. Every harness is unproven until somebody is the first to run one, and a factory that
    refused them all would never get a first. It is a sentence, once, saying what is and is not known — and
    the captain's own controls do not depend on any harness hook, which is the half of it that matters.
    """
    if not key or proven(key):
        return ""
    row = row_of(key)
    why = str(row.get("provenWhy") or "no feature has been run end to end on it by a captain")
    return (f"{name_of(key)} is unproven: {why}. Its row is read from its documentation, which is a "
            f"different claim from having worked. The captain's controls depend on no harness hook — it "
            f"reads the last line itself, diffs the controlled files and owns the waits — so what is at "
            f"risk is a second belt, not the run")


# -- the Agent Client Protocol ---------------------------------------------------------------------------
# A harness's `acp` row says how it is launched as an agent over stdio: an `npx` package with its arguments,
# which needs only Node on PATH, or a `binary` already installed. Copied from the protocol's own registry
# on the date the row says. The board's sessions (`acp.py`) are built from what this returns, so the keel
# names no agent of its own.

def acp_row(key: str) -> dict | None:
    """The harness's launch row, or `None` where the registry records none (and an `acpReason` says why)."""
    row = row_of(key).get("acp")
    return row if isinstance(row, dict) else None


def acp_keys() -> tuple[str, ...]:
    """Every harness with a launch row, in the registry's order."""
    return tuple(row["key"] for row in registry() if isinstance(row.get("acp"), dict))


def acp_launch(key: str, path: str | None = None) -> tuple[list[str], str]:
    """The argv that starts this harness as an agent on this machine, and a sentence saying where it came
    from — or an empty argv and a sentence saying what is missing. `path` is the PATH to look on; the
    board passes its login shell's, because its own is `launchd`'s and holds nothing a person installed."""
    import shutil  # noqa: PLC0415 — only this one function looks on PATH, and only the board calls it

    row = acp_row(key)
    if row is None:
        why = str(row_of(key).get("acpReason") or "the registry records no way to launch it as an agent")
        return [], f"{name_of(key)}: {why}"
    env = row.get("npx", {}).get("env") if isinstance(row.get("npx"), dict) else None
    if isinstance(row.get("npx"), dict):
        found = shutil.which("npx", path=path)
        if not found:
            package = row["npx"]["package"]
            return [], f"{name_of(key)} is launched with `npx {package}`, and there is no `npx` on PATH: install Node"
        argv = [found, "--yes", str(row["npx"]["package"]), *[str(a) for a in row["npx"].get("args") or []]]
        return argv, f"{name_of(key)} over `npx` at {found}" + (f", with {', '.join(env)} set" if env else "")
    binary = row["binary"] if isinstance(row.get("binary"), dict) else {}
    command = str(binary.get("cmd") or "")
    found = shutil.which(command, path=path) if command else None
    if found:
        return [found, *[str(a) for a in binary.get("args") or []]], f"{name_of(key)} at {found}"
    put = installed_launch(key)
    if put:
        return put, f"{name_of(key)} installed by the board, at {put[0]}"
    return [], f"{name_of(key)} is launched as `{command}`, which is not on PATH"


def installed_launch(key: str) -> list[str]:
    """The argv of an agent the board installed from its archive, or nothing where it did not."""
    try:
        held = json.loads((INSTALLED / key / "launch.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    command = str(held.get("cmd") or "") if isinstance(held, dict) else ""
    if not command or not Path(command).is_file():
        return []
    return [command, *[str(a) for a in held.get("args") or []]]


def acp_environment(key: str) -> dict[str, str]:
    """What the launch row says to set in the agent's environment, if anything."""
    row = acp_row(key) or {}
    npx = row["npx"] if isinstance(row.get("npx"), dict) else {}
    return {str(k): str(v) for k, v in (npx.get("env") or {}).items()}

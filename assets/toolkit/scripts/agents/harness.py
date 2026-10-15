#!/usr/bin/env python3
"""Which coding agent a headless session runs through, and the command that starts one.

Two things in this directory need to start a fresh harness session and ask it one thing: `cruise.py`, which
asks `/cruise` once an iteration, and `captain.py`, which asks `/sail` once a slice. They had one copy
between them and it was `cruise.py`'s — so the captain, which is the thing that will outlive the runner,
fell back to `scripts/agents/sail.py`. That script is the *settings reader* for `/sail`: handed a slice
and a fairway it prints its table and exits 0. A whole real run was reported through on the strength of it.

So the knowledge is here, and both callers read it:

**Which harness.** The first harness `.specify/integration.json` records as installed that has a verified
`headless` row in `registry.json` and whose binary is on PATH. Not the first one on PATH: a harness `./init`
never initialised here has no projected commands, no delegate types and no hook files, so the command being
asked for is unknown to it and the session ends having done nothing. One that is on PATH but uninitialised
is *named in the refusal*, with the `./init` that would add it, rather than driven.

**What to ask it.** A harness whose row says its print mode resolves this project's slash commands
(`prompt: "slash"`) is asked `/<command>`; every other is asked to read the command file and follow it,
which needs nothing of a harness beyond reading a file and is the same words whatever the harness.

**What the session must not inherit.** A harness session started from inside another's reads the parent's
identity out of the environment and either takes the parent's transcript for its own or refuses to start as
a nested copy. Every harness's session variable comes out, and the row's own `env` goes in.

Nothing here decides anything about a run. It answers *how to start a session*, and the caller says what the
session is for. Standalone and dependency-free, like everything under `scripts/`.
"""
from __future__ import annotations

import json
import os
import shlex
import shutil
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REGISTRY = HERE / "registry.json"


def project_root(script: Path, depth: int) -> Path:
    for candidate in script.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return script.parents[depth]


ROOT = project_root(Path(__file__).resolve(), 2)
INTEGRATION = ROOT / ".specify/integration.json"
#: What `scripts/extensions/hooks.py --elect` wrote: the extensions this project elected, and the tool names
#: they need a session allowed to call. Read here rather than carried in `registry.json` because the tool
#: belongs to whoever brings it — the registry is the keel's catalogue of coding agents, and a tool name in
#: it is handed to every project whether it elected that extension or not (6.1c).
ELECTED = ROOT / ".slipwai/hooks.json"
#: The environment a harness session started from inside another's must not inherit: the parent's own
#: identity, or the child reads the parent's transcript as its own and refuses to start as a nested copy.
PARENT_SESSION_VARIABLES = ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT")


class NoHarness(RuntimeError):
    """No harness here can be asked anything, said as the one line a person reads and acts on."""


def registry() -> dict[str, dict[str, Any]]:
    return {row["key"]: row for row in json.loads(REGISTRY.read_text(encoding="utf-8"))["harnesses"]}


def installed_keys() -> list[str]:
    """The harnesses Spec Kit recorded as installed here, in the order it recorded them; none where it never ran."""
    if not INTEGRATION.is_file():
        return []
    try:
        state = json.loads(INTEGRATION.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return []
    keys = state.get("installed_integrations") or [state.get("default_integration")]
    return [key for key in keys if isinstance(key, str)]


def headless_row(harness: dict[str, Any] | None) -> dict[str, Any] | None:
    row = harness.get("headless") if harness is not None else None
    return row if isinstance(row, dict) else None


def binary_of(harness: dict[str, Any]) -> str:
    """The executable a harness's headless command starts with: what is looked for on PATH."""
    row = headless_row(harness)
    assert row is not None
    return shlex.split(str(row["command"]))[0]


def choose() -> tuple[dict[str, Any], str]:
    """The harness a session runs through, and a sentence saying why that one, or `NoHarness` saying why none.

    The refusal is the whole value of this function. "No harness" has three different causes and three
    different things a person does about them — one is installed and its binary is missing, one is installed
    and the registry records no way to run it headless, or one is on PATH and was never initialised here —
    and a run that said only "no harness" would send them to read source to tell which.
    """
    rows = registry()
    installed = [key for key in installed_keys() if key in rows]
    for key in installed:
        harness = rows[key]
        if headless_row(harness) is not None and shutil.which(binary_of(harness)):
            return harness, f"harness: {harness['name']}"
    on_path = [harness for key, harness in rows.items()
               if key not in installed and headless_row(harness) is not None and shutil.which(binary_of(harness))]
    able = ", ".join(f"{harness['name']} (`{binary_of(harness)}`)" for harness in rows.values()
                     if headless_row(harness) is not None)
    named = ", ".join(rows[key]["name"] for key in installed) or "no harness is initialised here"
    words = " is installed" if len(installed) == 1 else " are installed" if installed else ""
    if installed and headless_row(rows[installed[0]]) is None:
        words += ", and the registry records no way to run it headless"
    elif installed:
        words += f", and `{binary_of(rows[installed[0]])}` is not on PATH"
    if on_path:
        found = ", ".join(f"{harness['name']} (`./init --integration {harness['key']}`)" for harness in on_path)
        raise NoHarness(f"no initialised harness a session can run through is on PATH: {named}{words}. On "
                        f"PATH but never initialised here, so its commands, delegate types and hooks are "
                        f"not projected: {found} — that init adds it beside what is installed; then run "
                        f"again")
    raise NoHarness(f"no harness a session can run through is on PATH: {named}{words}, and none of the "
                    f"harnesses the registry records a headless command for is on PATH — {able} "
                    f"(scripts/agents/registry.json, `headless`)")


def elected_tools(separator: str = ",") -> str:
    """The tool names this project's elected extensions declared, as one allow-list fragment.

    Empty — not the separator, not a stray comma — where nothing was elected or the election has not been
    run, which is the common case and the one a plain generated project is in. The leading separator is
    part of the fragment so that a row can write `'Bash,Skill{tools}'` and read correctly either way.
    """
    try:
        record = json.loads(ELECTED.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return ""
    names = [name for name in record.get("tools", []) if isinstance(name, str) and name.strip()]
    return "".join(f"{separator}{name.strip()}" for name in names)


def template(harness: dict[str, Any], sandbox: bool = False) -> tuple[str, str]:
    """The shell template a session runs, and the sentence saying which permissions it runs under."""
    headless = headless_row(harness)
    assert headless is not None
    permissions = str(headless.get("sandboxPermissions" if sandbox else "permissions", ""))
    # `{tools}` is where an elected extension's tool names join this harness's allow-list, in the spelling
    # the row around it already uses. A row with no placeholder gets nothing added: a harness whose allow
    # list this project has not been taught to extend is left exactly as the registry records it, rather
    # than handed a flag nobody checked it accepts.
    permissions = permissions.replace("{tools}", elected_tools())
    why = ("--sandbox: every permission check is bypassed, which is only for a container with nothing to lose"
           if sandbox else
           "edits are accepted and every other permission is the harness's own to grant or refuse; pass "
           "--sandbox inside a disposable container to bypass them all")
    said = str(headless["command"]).replace("{permissions}", permissions)
    # A headless session in a checkout nobody has trusted ignores the project's own MCP file on some
    # harnesses, so the row's `headlessFlags` make it honoured — passed only when the file exists, since a
    # flag naming a missing file refuses to start, and `{root}` is this checkout for a harness that trusts
    # by path.
    project = harness.get("projectMcp")
    if isinstance(project, dict) and project.get("headlessFlags") and (ROOT / str(project["file"])).is_file():
        said = f"{said} {str(project['headlessFlags']).replace('{root}', str(ROOT))}"
    # The ladder's concurrent slices work in worktrees beside the checkout, which a print session under
    # `acceptEdits` is refused every edit in; the row's `worktreeFlags` name the directory the checkout sits
    # in as a second working directory, so a delegate's first edit is not its last.
    worktrees = headless.get("worktreeFlags")
    if worktrees:
        said = f"{said} {str(worktrees).replace('{parent}', shlex.quote(str(ROOT.parent)))}"
    return said, why


def model_flags(harness: dict[str, Any] | None, model: str | None) -> str:
    """What puts a session on a named model: the row's `modelFlag` with the identifier in it. Nothing where
    no model is named or where the row records no flag — the caller says which, because "the harness's own
    default ran" is a thing a reader has to be told rather than infer from a transcript."""
    headless = headless_row(harness)
    flag = headless.get("modelFlag") if headless is not None else None
    if not model or not flag:
        return ""
    return " " + str(flag).replace("{model}", shlex.quote(model))


def prompt_for(harness: dict[str, Any] | None, command: str, file: Path, argument: str | None = None) -> str:
    """What a session is asked: the slash command, or the words that make any harness read the file."""
    headless = headless_row(harness)
    if headless is not None and headless.get("prompt") == "slash":
        return f"/{command} {argument}" if argument else f"/{command}"
    where = file.relative_to(ROOT).as_posix() if file.is_relative_to(ROOT) else str(file)
    tail = f", with `{argument}` as its argument" if argument else "; it is given no argument"
    return f"Run the /{command} command: read {where} and follow it exactly as written{tail}."


def child_environment(harness: dict[str, Any] | None) -> dict[str, str]:
    """What a session runs under: this environment, plus what the row's `headless.env` sets — Claude Code's
    wait ceiling, which otherwise ends a print session while its delegates still run — and minus every
    harness's own session variables."""
    environment = dict(os.environ)
    for variable in PARENT_SESSION_VARIABLES:
        environment.pop(variable, None)
    for row in registry().values():
        session_variable = (row.get("usage") or {}).get("env")
        if session_variable:
            environment.pop(str(session_variable), None)
    headless = headless_row(harness)
    if headless is not None and isinstance(headless.get("env"), dict):
        environment.update({str(key): str(value) for key, value in headless["env"].items()})
    return environment


#: Where the project declares its delegate types, which every harness's own directory is projected from.
TYPES = ROOT / "agents"


def current_key() -> str:
    """Which harness this session is running inside, from its own session variable, or `""`.

    Asked of the environment rather than of `.specify/integration.json`, because what is *installed* and
    what is *running right now* are different questions and only the second decides whether this session
    can delegate. Two rows declare the variable; where none is set the caller falls back to what is
    installed and says that it did, because a guess reported as a reading is the expensive kind.
    """
    for key, row in registry().items():
        variable = (row.get("usage") or {}).get("env")
        if variable and os.environ.get(str(variable)):
            return key
    return ""


def declared_types() -> list[str]:
    """The delegate types this project declares: one `agents/<name>.md` each, at the root and committed."""
    return sorted(path.stem for path in TYPES.glob("*.md")) if TYPES.is_dir() else []


def projected_types(harness: dict[str, Any]) -> tuple[str, list[str]]:
    """Where this harness reads its delegate types, and which of them are actually in this checkout."""
    row = harness.get("agentFile")
    if not isinstance(row, dict) or not row.get("dir"):
        return "", []
    where = str(row["dir"])
    extension = str(row.get("extension") or ".md")
    place = ROOT / where
    found = sorted(path.name[: -len(extension)] for path in place.glob(f"*{extension}")) if place.is_dir() else []
    return where, found


def delegation(key: str) -> dict[str, Any]:
    """Whether a session in this harness may delegate here, and the sentence that says why not.

    Three different noes, and a run told only *cannot delegate* would have to read source to tell which:
    the harness has no sub-agents at all, the types are declared and this checkout has none of them
    projected, or some are missing.

    The middle one is what this exists for. A cloud checkout has `agents/` from git and nothing under
    `.claude/agents/`, because the projections are derived and git ignores them — so a session there reads
    a method built on delegates and has none to call. That was the sentence nothing was in a position to
    write, and writing it is the whole of this.
    """
    harness = registry().get(key)
    if harness is None:
        return {"harness": key, "name": key, "able": False, "where": "", "declared": [], "projected": [],
                "why": f"no harness row is recorded for {key or 'this session'}, so nothing says whether "
                       f"it delegates"}
    name = str(harness.get("name") or key)
    declared = declared_types()
    where, found = projected_types(harness)
    answer = {"harness": key, "name": name, "where": where, "declared": declared, "projected": found}
    if not where:
        return {**answer, "able": False,
                "why": f"{name} has no delegate types: the registry records no directory it reads them "
                       f"from, so every slice a session here takes runs in that session"}
    if not declared:
        return {**answer, "able": False,
                "why": f"this project declares no delegate types in agents/, so there is nothing for "
                       f"{name} to delegate to"}
    missing = [one for one in declared if one not in found]
    if not found:
        return {**answer, "able": False,
                "why": f"{where}/ holds none of this project's {len(declared)} delegate types. They are "
                       f"derived from agents/ and git ignores them, so a fresh clone — a cloud runner, a "
                       f"new machine — has none. Run `make agents`, then start a new session: a harness "
                       f"reads its delegate types once, at session start"}
    if missing:
        return {**answer, "able": False,
                "why": f"{where}/ is missing {len(missing)} of {len(declared)} delegate types "
                       f"({', '.join(missing[:3])}{'…' if len(missing) > 3 else ''}). Run `make agents`, "
                       f"then start a new session"}
    return {**answer, "able": True,
            "why": f"{name} reads {len(found)} delegate type(s) from {where}/, so the ready set may fan out"}


def can_delegate() -> dict[str, Any]:
    """The answer for this session: its own harness where it says which, else what is installed here.

    How it was decided travels with the answer. *This session's own variable* and *the first of three
    installed* are different grades of evidence, and a ledger that recorded only the verdict would lose
    which one it rests on.
    """
    key = current_key()
    if key:
        return {**delegation(key), "how": "this session's own harness variable"}
    installed = [one for one in installed_keys() if one in registry()]
    if len(installed) == 1:
        return {**delegation(installed[0]), "how": "the one harness installed here; no session variable was set"}
    for one in installed:
        answer = delegation(one)
        if answer["able"]:
            return {**answer, "how": "an installed harness that can; no session variable said which is running"}
    if installed:
        return {**delegation(installed[0]),
                "how": "the first installed harness; no session variable said which is running"}
    return {"harness": "", "name": "", "able": False, "where": "", "declared": declared_types(),
            "projected": [], "how": "nothing is installed here",
            "why": "no harness is initialised in this checkout, so nothing projects delegate types and "
                   "there is nothing to delegate to. Run `./init`"}


def main(argv: list[str]) -> int:
    """`--can-delegate`: whether this session may fan out, as a sentence or as a record.

    Exit 1 where it may not, so a run that takes one slice at a time has a recorded reason rather than a
    judgement. `commands/sail.md` carries the prose; this carries the answer it was asserting.
    """
    if "--can-delegate" not in argv:
        print("harness: run `python3 scripts/agents/harness.py --can-delegate [--json]`", file=sys.stderr)
        return 2
    answer = can_delegate()
    if "--json" in argv:
        print(json.dumps({"v": 1, **answer}))
    else:
        print(f"harness: {'can delegate' if answer['able'] else 'cannot delegate'} — {answer['why']}")
        print(f"  decided by {answer['how']}")
    return 0 if answer["able"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

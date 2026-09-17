#!/usr/bin/env python3
"""Which model runs each stage of `/drive`'s ladder, for the harness this project is initialised for.

`.specify/models.json` holds the choice — a role per stage, and per harness what each role maps to — and
`scripts/agents/registry.json` says whether the harness can act on it at all. This reads both and prints the
one line `/drive` needs before a stage: the model to delegate to, or why the stage runs on the host model.
Nothing is guessed: a role with no identifier mapped, a harness the registry records no mechanism for, and a
project with no table at all are each said in words, so a stage that did not switch is a stage that says so.

    python3 scripts/agents/models.py              # the whole table, per installed harness
    python3 scripts/agents/models.py implement    # one stage, keyed by the command it runs
    python3 scripts/agents/models.py --check      # the table is well-formed; `make check-agents` runs this
    python3 scripts/agents/models.py --set implement=strong claude.fast=haiku   # change it, checked, any time

A change — by hand or with `--set` — takes effect at the next stage `/drive` runs: the table is read before every
stage and cached nowhere. `slipwai migrate` merges a newer factory's table over an edited one rather than
replacing it, so a mapped identifier survives the way every edit to a generated file does.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def project_root(script: Path, depth: int) -> Path:
    """The repository root: the nearest directory above this script holding `project.json`.

    This script's own tree is `<root>/scripts` in a generated project and `<root>/<layout.delivery>/scripts`
    where the method was installed beside an existing codebase (`project.json`'s `layout.delivery`), so how
    far below the root it sits is not something to count; `depth` is only the fallback for a tree with no
    manifest at all.
    """
    for candidate in script.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return script.parents[depth]


ROOT = project_root(Path(__file__).resolve(), 2)
REGISTRY = Path(__file__).with_name("registry.json")
PROJECT = Path(__file__).with_name("project.py")
MODELS = ROOT / ".specify/models.json"
INTEGRATION = ROOT / ".specify/integration.json"
# Every stage the table may name, keyed by the command the stage runs. The factory writes the same list into
# `.specify/models.json`; a key outside it is a typo the check reports rather than a row `/drive` never reads.
KNOWN_STAGES = (
    "principles", "specify", "event-model", "split", "example-map", "gaps", "release-constraint", "plan", "tasks",
    "implement", "converge", "demo", "adversary", "mutation",
)
# A role mapped to this runs on the model running `/drive` itself: no delegation, said in as many words.
HOST = "host"
ABSENT = f"no {MODELS.relative_to(ROOT)}: every stage runs on the host model; `slipwai migrate` writes the table"


def installed() -> list[str]:
    """The harness keys Spec Kit recorded as installed; none before `./init`."""
    if not INTEGRATION.is_file():
        return []
    state = json.loads(INTEGRATION.read_text())
    keys = state.get("installed_integrations")
    if isinstance(keys, list) and keys:
        return list(dict.fromkeys(key for key in keys if isinstance(key, str)))
    default = state.get("default_integration")
    return [default] if isinstance(default, str) else []


def role_of(stage: str, table: dict[str, Any]) -> tuple[str, str]:
    """The role a stage runs under, and a note when it fell to the `default` row."""
    stages = table["stages"]
    if stage in stages:
        return str(stages[stage]), ""
    return str(stages["default"]), f"no `{stage}` row; the `default` row applies"


def resolve(stage: str, table: dict[str, Any], harness: dict[str, Any]) -> tuple[str, str | None, str]:
    """(role, model or None, why) for one stage on one harness. None is the host model, and `why` says which
    of the three reasons made it so — or, with a model, how this harness switches to it."""
    role, fell = role_of(stage, table)
    name = harness["name"]
    mechanism = harness.get("subagentModel")
    if not isinstance(mechanism, dict):
        return role, None, f"the registry records no way for {name} to choose a model for a sub-task"
    roles = table.get("roles", {}).get(harness["key"])
    if not isinstance(roles, dict):
        return role, None, f"no roles mapped for `{harness['key']}` in .specify/models.json"
    value = roles.get(role)
    if value is None:
        return role, None, f"no identifier mapped for `{role}` under `{harness['key']}` in .specify/models.json"
    if value == HOST:
        return role, None, f"`{role}` maps to the host model"
    how = f"{name}: {mechanism.get('how', 'see the registry')}"
    return role, str(value), f"{how}; {fell}" if fell else how


def line(stage: str, table: dict[str, Any], harness: dict[str, Any]) -> str:
    role, model, why = resolve(stage, table, harness)
    target = model if model is not None else "host model"
    return f"{stage}: {role} → {target} — {why}"


def switching(harness: dict[str, Any]) -> str:
    """How this harness gives a sub-task its model, in the spelling its identifiers take — or that it cannot."""
    mechanism = harness.get("subagentModel")
    if not isinstance(mechanism, dict):
        return f"cannot switch: the registry records no way for {harness['name']} to choose a model for a sub-task"
    return f"can switch: {mechanism.get('how')}; identifiers: {mechanism.get('identifiers')}"


def check(table: object, registry: dict[str, dict[str, Any]]) -> list[str]:
    """Everything a hand edit can break, each as one finding."""
    findings: list[str] = []
    if not isinstance(table, dict):
        return ["the table is not a JSON object"]
    stages = table.get("stages")
    if not isinstance(stages, dict) or "default" not in stages:
        return ["`stages` must be an object with a `default` row"]
    allowed = set(KNOWN_STAGES) | {"default"}
    for key, value in stages.items():
        if key not in allowed:
            findings.append(f"`stages.{key}` is not a stage of the ladder; known: {', '.join(KNOWN_STAGES)}")
        if not isinstance(value, str) or not value:
            findings.append(f"`stages.{key}` must name a role")
    named = {value for value in stages.values() if isinstance(value, str)}
    roles = table.get("roles")
    if not isinstance(roles, dict):
        return findings + ["`roles` must be an object keyed by harness"]
    for key, mapping in roles.items():
        if key not in registry:
            findings.append(f"`roles.{key}` is not a harness the registry knows")
        if not isinstance(mapping, dict):
            findings.append(f"`roles.{key}` must map each role to an identifier, `{HOST}`, or null")
            continue
        for role in sorted(named - set(mapping)):
            findings.append(f"`roles.{key}` does not say what `{role}` maps to — an identifier, `{HOST}`, or null")
        for role, value in mapping.items():
            if value is not None and (not isinstance(value, str) or not value):
                findings.append(f"`roles.{key}.{role}` must be an identifier, `{HOST}`, or null")
    return findings


def assign(table: dict[str, Any], registry: dict[str, dict[str, Any]], assignment: str) -> str:
    """Apply one `stage=role` or `harness.role=identifier` to the table in place, and say what changed.

    A role a stage newly names is added as `null` under every harness so the table stays whole and the line
    before the stage says "no identifier mapped" until somebody maps it. A harness the registry records no
    mechanism for is refused: a role mapped for it would never be read, and a setting that does nothing is
    worse than a refusal that says why (docs/agent-harnesses.md).
    """
    key, separator, value = assignment.partition("=")
    if not separator or not key or not value:
        raise RuntimeError(f"--set takes stage=role or harness.role=identifier, not {assignment!r}")
    if "." in key:
        harness, role = key.split(".", 1)
        entry = registry.get(harness)
        if entry is None:
            raise RuntimeError(f"`{harness}` is not a harness the registry knows; `make agents-list` names them")
        if not isinstance(entry.get("subagentModel"), dict):
            raise RuntimeError(f"the registry records no way for {entry['name']} to choose a model for a sub-task, "
                               "so a role mapped for it would never be read")
        table.setdefault("roles", {}).setdefault(harness, {})[role] = None if value == "null" else value
        return f"roles.{harness}.{role} = {value}"
    if key not in KNOWN_STAGES and key != "default":
        raise RuntimeError(f"`{key}` is not a stage of the ladder; known: default, {', '.join(KNOWN_STAGES)}")
    table.setdefault("stages", {})[key] = value
    unmapped = [harness for harness, mapping in table.get("roles", {}).items() if value not in mapping]
    for harness in unmapped:
        table["roles"][harness][value] = None
    added = f" — `{value}` added as null under {', '.join(unmapped)}; map it with --set <harness>.{value}=<id>" \
        if unmapped else ""
    return f"stages.{key} = {value}{added}"


def reproject() -> None:
    """Rewrite the projections, because the agent files carry the model this table just changed.

    A harness that names a sub-task's model in a file (`registry.json`, `agentFile`) has that model written
    into `<dir>/drive-<stage>.md` by `scripts/agents/project.py`. Leaving them behind would mean a change made
    here takes effect at the next stage on Claude Code and never on Codex, and `make check-agents` reporting
    drift for a file nobody edited. Absent an installed integration there is nothing to write, and a failure
    here is reported rather than raised: the table is already written, and `make agents` is the retry.
    """
    if not INTEGRATION.is_file():
        return
    done = subprocess.run(["python3", str(PROJECT)], cwd=ROOT, text=True, capture_output=True)
    if done.returncode != 0:
        print(f"the projections still carry the old model — run `make agents`: {done.stderr.strip()}",
              file=sys.stderr)
        return
    print("Projections rewritten: the agent types carry the model this table names.")


def main() -> None:
    arguments = sys.argv[1:]
    registry = {entry["key"]: entry for entry in json.loads(REGISTRY.read_text())["harnesses"]}
    if not MODELS.is_file():
        print(ABSENT)
        return
    table = json.loads(MODELS.read_text())
    if "--set" in arguments:
        assignments = arguments[arguments.index("--set") + 1:]
        if not assignments:
            raise RuntimeError("--set takes stage=role or harness.role=identifier")
        changed = [assign(table, registry, assignment) for assignment in assignments]
        findings = check(table, registry)
        if findings:
            listed = "\n  - ".join(findings)
            raise RuntimeError(f"not written — the change would leave the table malformed:\n  - {listed}")
        MODELS.write_text(json.dumps(table, indent=2, ensure_ascii=False) + "\n")
        for line_ in changed:
            print(line_)
        print(f"{MODELS.relative_to(ROOT)} written; it takes effect at the next stage /drive runs. Commit it: the "
              "choice is versioned with the project.")
        reproject()
        return
    findings = check(table, registry)
    if "--check" in arguments:
        if findings:
            raise RuntimeError(f"{MODELS.relative_to(ROOT)}:\n  - " + "\n  - ".join(findings))
        print(f"check-models: {MODELS.relative_to(ROOT)} names {len(table['stages']) - 1} stage(s) and "
              f"{len(table['roles'])} harness(es)")
        return
    if findings:
        raise RuntimeError(f"{MODELS.relative_to(ROOT)} is malformed; `make check-agents` lists why")
    harnesses = [registry[key] for key in installed() if key in registry]
    stages = [argument for argument in arguments if not argument.startswith("--")]
    if not harnesses:
        print("no harness installed yet (`./init --integration <agent>` records one): every stage runs on the host "
              "model. The table, by role:")
        for stage in KNOWN_STAGES:
            print(f"  {line(stage, table, {'key': '', 'name': 'an uninitialised project', 'subagentModel': None})}"
                  .split(" — ")[0])
        return
    for harness in harnesses:
        if len(harnesses) > 1 or not stages:
            print(f"{harness['name']} ({harness['key']}):")
            print(f"  {switching(harness)}")
        for stage in stages or KNOWN_STAGES:
            print(f"  {line(stage, table, harness)}" if len(harnesses) > 1 or not stages
                  else line(stage, table, harness))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, KeyError) as error:
        print(f"models: {error}", file=sys.stderr)
        raise SystemExit(1) from None

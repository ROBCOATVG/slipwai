#!/usr/bin/env python3
"""Which capabilities are whole, which have been accepted, and which are owed a demo.

A **capability** is the chunk of work a person's demo is of: usually several slices, named on the chart, and
the smallest thing that means anything on its own to whoever is being shown it. Version 1 stopped a person
at the end of every slice and showed them a fraction of a capability to assemble in their head.

So a whole capability is first owed its **gates** — converge over its diff, gaps over it, the design review
from screenshots, one adversary pass, mutation, and the hand's walk of every example, because a test that passes and a path
that works are different claims and only one of them is machine-checked — and **nobody is stopped for
them**. They are recorded in `specs/<feature>/capabilities/<capability>/gates.md`, whose `Cleared:` line says
they are done. The stop a person attends runs after that.

**A capability built on a stand-in is not done, whatever its gates say.** A `Stand-in: <port> · <adapter> · <the
missing piece>` line in the record — a no-transport mailer, a drop directory, an empty source, a fake where the
real thing does not exist yet — and an `Unreached: <screen> · <why>` line, where the hand's walk could not reach a
screen from seeded state, are each a **release blocker**: the capability is listed as built on a stand-in, it is
not owed a demo and may not be accepted, and the board says so above *Built*. So is a slice of it whose
`try-it.json` is empty, since then no walk reaches its screens. A blocker ends when the stand-in is replaced and
its line removed, or when a person records that the stand-in is the intended behaviour, on the same line:
`· Accepted-by: <who> <date>`. A session never writes that, and one naming an agent is not read as accepted.
The email that was never sent is the reason: the capability cleared on its safe half, and nothing tracked the
cloud half to completion.

**This is not a release gate.** Accepting a demo says the capability is right. Hoisting a flag says the
business wants it live, which may be another quarter or never, and stays a person's act on their own timing.
A capability may sit accepted and dark for as long as the business wants, so the two are reported here as
separate columns and neither is ever derived from the other. A capability under the `open` release mode has
no flag at all and still has a demo.

**Who accepts it is `.specify/cruise.json`'s `demos`.** Under `hand`, the default, the hand's verdict at the
walk is the acceptance, written as the demo stop says, and the film is there for a person to comment on;
nobody is asked. Under `person` a person accepts it, and an `accepted`
line the hand wrote is the last reading before theirs, not the acceptance.

    python3 scripts/agents/capabilities.py          # every capability, with what it is waiting for
    python3 scripts/agents/capabilities.py --gates  # only the ones owed their gates now (`--json` for the board)
    python3 scripts/agents/capabilities.py --due    # only the ones owed a demo now
    python3 scripts/agents/capabilities.py --blocked  # whole and gated, and built on a stand-in
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


def project_root(script: Path) -> Path:
    for candidate in script.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return script.parents[2]


ROOT = project_root(Path(__file__).resolve())
SPECS = ROOT / "specs"
sys.path.insert(0, str(Path(__file__).resolve().parent))
import clearance  # noqa: E402 — which feature holds a slice's own files
import logs  # noqa: E402 — carried beside this script; it owns where the run's state lives
LOGS = logs.logs_dir(ROOT)
V = 1
#: What a gate record's last word says once every gate has run with nothing above the bar left open.
CLEARED = re.compile(r"^Cleared:\s*\S", re.MULTILINE)
#: A release blocker in a gate record: a stand-in on the actor's path, or a screen the walk could not reach.
BLOCKER = re.compile(r"^(Stand-in|Unreached):[ \t]*(.*)$", re.MULTILINE)
#: What a person writes on a blocker's own line to say it is the intended behaviour.
ACCEPTED_BY = re.compile(r"·\s*Accepted-by:\s*(\S+)")
#: Who may not accept a stand-in: every agent the ladder sends, by its type or its role.
AGENTS = re.compile(r"^(sail-|harbour-|drive-)|^(hand|skipper|bosun|captain|harbourmaster|agent|claude)$",
                    re.IGNORECASE)
#: `.specify/cruise.json`'s `demos`, and who an `accepted` line names when the hand's verdict wrote it.
HAND, PERSON, WALKER = "hand", "person", "sail-demo-hand"


def load_yaml(text: str) -> object:
    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError:  # pragma: no cover - exercised on a machine without PyYAML
        subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "PyYAML"], check=True)
        import yaml  # type: ignore[import-not-found]
    return yaml.safe_load(text)


def chart() -> tuple[dict, str]:
    for path in sorted(SPECS.glob("*/chart.yaml")) if SPECS.is_dir() else []:
        loaded = load_yaml(path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            return loaded, path.parent.name
    return {}, ""


def lines(feature: str) -> list[dict]:
    """Every deck log's lines, in no particular order across streams. A stream's are read from every file
    that holds them: one of its name under a further feature has lines a session wrote there, as its own."""
    paths = [*(LOGS / feature).glob("*.jsonl")] if (LOGS / feature).is_dir() else []
    found: list[dict] = []
    held = logs.streams(ROOT)
    for path in sorted(paths):
        beside = [one for one in held.get(path.stem, []) if one.parent != path.parent]
        for number, text in enumerate(logs.stream_lines([path, *beside]), start=1):
            if not text.strip():
                continue
            try:
                line = json.loads(text)
            except ValueError:
                raise SystemExit(f"capabilities: {path.name}:{number} is not JSON. Reading past it would "
                                 f"report a capability whole that is not.") from None
            if isinstance(line, dict) and line.get("v") != V:
                raise SystemExit(f"capabilities: {path.name}:{number} says v{line.get('v')} and this reader "
                                 f"knows v{V}. Run `slipwai upgrade`.")
            if isinstance(line, dict):
                found.append(line)
    return found


def slices_by_capability(charted: dict) -> dict[str, list[str]]:
    """Each capability against its slices, in the chart's order, which is split order."""
    grouped: dict[str, list[str]] = {}
    for slice_id, entry in (charted.get("slices") or {}).items():
        if isinstance(entry, dict) and entry.get("capability"):
            grouped.setdefault(str(entry["capability"]), []).append(str(slice_id))
    return grouped


def feature_of(charted: dict | None, feature: str, capability: str) -> str:
    """The feature a capability's records are under: its slices', which on a chart several features share is
    not always the chart's. `feature`, the chart's, where no row says otherwise or no chart was given."""
    members = slices_by_capability(charted or {}).get(capability)
    return clearance.feature_of_slice(members[0], charted, feature) if members else feature


def cleared(feature: str, capabilities: list[str], charted: dict | None = None) -> set[str]:
    """The capabilities whose gate record carries its `Cleared:` line."""
    found = set()
    for capability in capabilities:
        record = SPECS / feature_of(charted, feature, capability) / "capabilities" / capability / "gates.md"
        if record.is_file() and CLEARED.search(record.read_text(encoding="utf-8")):
            found.add(capability)
    return found


def record_blockers(text: str) -> list[str]:
    """The release blockers a gate record names that no person has accepted, each as a sentence."""
    found = []
    for kind, said in BLOCKER.findall(text):
        who = ACCEPTED_BY.search(said)
        if who and not AGENTS.search(who.group(1)):
            continue
        parts = [part.strip() for part in ACCEPTED_BY.split(said)[0].split("·") if part.strip()]
        if kind == "Stand-in":
            shape = "" if len(parts) >= 3 else " (it names no port, adapter and missing piece: write all three)"
            found.append(f"built on a stand-in: {' · '.join(parts) or 'unnamed'}{shape}")
        else:
            found.append(f"the walk cannot reach {' · '.join(parts) or 'a screen'} from seeded state")
        if who:
            found[-1] += f" — `Accepted-by: {who.group(1)}` names an agent, and only a person accepts a stand-in"
    return found


def empty_story(path: Path) -> bool:
    """A `try-it.json` that seeds nothing and opens nothing, so no walk reaches the slice's screens."""
    try:
        story = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False  # check-try refuses an unreadable story; this reader does not report it twice
    return not isinstance(story, dict) or not any(story.get(key) for key in ("open", "steps", "given"))


def blockers(feature: str, capabilities: list[str], charted: dict | None = None) -> dict[str, list[str]]:
    """Each capability's release blockers: its record's stand-ins and unreached screens no person accepted,
    and each of its slices whose story is empty. A capability with none is not in the answer."""
    grouped = slices_by_capability(charted or {})
    found: dict[str, list[str]] = {}
    for capability in capabilities:
        record = SPECS / feature_of(charted, feature, capability) / "capabilities" / capability / "gates.md"
        said = record_blockers(record.read_text(encoding="utf-8")) if record.is_file() else []
        for member in grouped.get(capability, []):
            story = SPECS / clearance.feature_of_slice(member, charted, feature) / "slices" / member / "try-it.json"
            if story.is_file() and empty_story(story):
                said.append(f"{member}'s try-it.json is empty, so no walk reaches its screens from seeded state")
        if said:
            found[capability] = said
    return found


def demos_setting() -> str:
    """`hand` or `person`: who accepts a whole capability. Absent or unreadable is `hand`."""
    try:
        held = json.loads((ROOT / ".specify" / "cruise.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return HAND
    return PERSON if isinstance(held, dict) and held.get("demos") == PERSON else HAND


def recorded_by_hand(feature: str, grouped: dict[str, list[str]], charted: dict | None = None) -> set[str]:
    """The capabilities whose hand's acceptance is recorded where a voyage recorded it before the line existed.

    A project mid-voyage has the hand's verdicts on paper and no `accepted` line, because nothing wrote one:
    the capability's `demo-log.md`, whose last section is the hand's `accepted`, or a register row naming
    `accepted-by: sail-demo-hand` for every one of its slices. Read as the hand's acceptance where no line
    says so, so a project that migrates does not lose every capability the hand had already accepted.
    """
    rows: dict[str, str] = {}
    # Each feature keeps its own register, so every feature a capability here belongs to is read.
    for home in dict.fromkeys([feature, *(feature_of(charted, feature, one) for one in grouped)]):
        register = SPECS / home / "slices" / "README.md"
        if not register.is_file():
            continue
        for text in register.read_text(encoding="utf-8").splitlines():
            cells = text.strip().strip("|").split("|")
            if text.strip().startswith("|") and cells:
                rows[cells[0].strip().strip("`").split(" ")[0]] = text
    found = set()
    for capability, members in grouped.items():
        log = SPECS / feature_of(charted, feature, capability) / "capabilities" / capability / "demo-log.md"
        heads = [line for line in log.read_text(encoding="utf-8").splitlines()
                 if line.startswith("## ")] if log.is_file() else []
        if heads and " accepted " in f" {heads[-1]} " and WALKER in heads[-1]:
            found.add(capability)
        elif members and all("accepted-by" in rows.get(one, "") and WALKER in rows.get(one, "") for one in members):
            found.add(capability)
    return found


def state(charted: dict, written: list[dict], gated: set[str] | frozenset[str] = frozenset(),
          demos: str = "", recorded: set[str] | frozenset[str] = frozenset(),
          blocked: dict[str, list[str]] | None = None) -> list[dict]:
    """One row per capability: its slices, how many have merged, and whether it is whole, gated or accepted.

    `accepted` and `hoisted` are kept apart on purpose. A capability the business is deliberately holding
    back is not a late one, and a board that derived one from the other could not tell them apart. Under
    `person` an `accepted` line by the hand accepts nothing; under `hand` the hand's acceptance `recorded`
    before there was a line (`recorded_by_hand`) counts once the capability is whole and gated. `demos` is
    read from the project where not given. `blocked` is each capability's release blockers (`blockers`).
    """
    person = (demos or demos_setting()) == PERSON
    merged = {str(line["slice"]) for line in written if line.get("kind") == "merged" and line.get("slice")}
    accepted = {str(line["capability"]) for line in written
                if line.get("kind") == "accepted" and line.get("capability")
                and not (person and line.get("by") == WALKER)}
    hoisted = {str(line["flag"]) for line in written if line.get("kind") == "flag-hoisted" and line.get("flag")}
    fairway_of = {str(name): str(entry.get("fairway", "")) for name, entry in (charted.get("slices") or {}).items()
                  if isinstance(entry, dict)}
    rows = []
    for capability, members in slices_by_capability(charted).items():
        done = [slice_id for slice_id in members if slice_id in merged]
        whole, cleared_now = len(done) == len(members), capability in gated
        by_record = not person and whole and cleared_now and capability in recorded and capability not in accepted
        rows.append({
            "capability": capability,
            "slices": members,
            # Every fairway its slices sit in, in split order. Its `accepted` and `demo-due` lines go to the
            # last; every reader folds every fairway's log of the feature, so one is enough.
            "fairways": list(dict.fromkeys(fairway_of.get(one, "") for one in members if fairway_of.get(one))),
            "merged": len(done),
            "whole": whole,
            "gated": cleared_now,
            "accepted": capability in accepted or by_record,
            "recorded": by_record,
            "hoisted": capability in hoisted,
            "waiting": [slice_id for slice_id in members if slice_id not in merged],
            "blockers": list((blocked or {}).get(capability, [])),
        })
    return rows


def acceptable(row: dict) -> str:
    """Why this capability may not be accepted now, or `""`: the one rule every writer of `accepted` and
    `demo-due` is held to — the hand's command and the board's Accept alike. Whole, every slice merged, and
    its gates record carrying `Cleared:`; an acceptance before either is a verdict on something unfinished."""
    if row["accepted"]:
        return f"{row['capability']} is accepted already"
    if not row["whole"]:
        return f"{row['capability']} is not whole: {', '.join(row['waiting'])} not merged"
    if not row["gated"]:
        return f"{row['capability']}'s gates have not cleared: its gates.md has no `Cleared:` line"
    if row.get("blockers"):
        return (f"{row['capability']} is a release blocker, not done: {'; '.join(row['blockers'])}. Replace the "
                f"stand-in and remove its line, or have a person add `· Accepted-by: <who> <date>` to it")
    return ""


def gates_due(rows: list[dict]) -> list[dict]:
    """Whole and its gates not yet cleared: converge, gaps, design review, adversary, mutation and the walk."""
    return [row for row in rows if row["whole"] and not row["gated"] and not row["accepted"]]


def due(rows: list[dict]) -> list[dict]:
    """Whole, gated and not yet accepted. That is the whole trigger, and nothing about a flag is in it. Under
    `hand` these are owed the hand's `accepted` line, never a person."""
    return [row for row in rows if row["whole"] and row["gated"] and not row["accepted"] and not row.get("blockers")]


def blocked(rows: list[dict]) -> list[dict]:
    """Whole and gated, and built on a stand-in: release blockers, which the board shows above *Built*."""
    return [row for row in rows if row["whole"] and row["gated"] and row.get("blockers")]


def rows_of(feature: str, charted: dict) -> list[dict]:
    grouped = slices_by_capability(charted)
    return state(charted, lines(feature), cleared(feature, list(grouped), charted),
                 recorded=recorded_by_hand(feature, grouped, charted),
                 blocked=blockers(feature, list(grouped), charted))


def main(argv: list[str]) -> int:
    charted, feature = chart()
    if not charted:
        print("capabilities: no chart yet, so no capability is owed a demo")
        return 0
    rows = rows_of(feature, charted)
    if "--gates" in argv:
        owed = gates_due(rows)
        if "--json" in argv:
            # The board's port: which capabilities are whole and ungated, so it never says *Built* over them.
            print(json.dumps({"v": V, "feature": feature, "owed": [row["capability"] for row in owed],
                              "blocked": [{"capability": row["capability"], "blockers": row["blockers"]}
                                          for row in blocked(rows)]}))
            return 0
        print(f"capabilities: {len(owed)} owed their gates")
        for row in owed:
            print(f"  {row['capability']} — {', '.join(row['slices'])}")
        return 0
    if "--blocked" in argv:
        held = blocked(rows)
        print(f"capabilities: {len(held)} built on a stand-in — release blockers, not done")
        for row in held:
            print(f"  {row['capability']}: {'; '.join(row['blockers'])}")
        return 0
    if "--json" in argv:
        # The board's other port: every row, with why each may not be accepted now, under the project's setting.
        print(json.dumps({"v": V, "feature": feature, "demos": demos_setting(),
                          "rows": [{**row, "refused": acceptable(row)} for row in rows]}))
        return 0
    if "--due" in argv:
        owed = due(rows)
        if demos_setting() == PERSON:
            print(f"capabilities: {len(owed)} owed a demo")
        else:
            print(f"capabilities: nothing is owed a person — `demos` is `hand`, so the hand's verdict accepts each. "
                  f"{len(owed)} whole and gated with no `accepted` line yet: the demo stop writes it")
        for row in owed:
            print(f"  {row['capability']} — {', '.join(row['slices'])}")
        return 0
    print(f"capabilities: {len(rows)} in {feature}")
    for row in rows:
        if row["accepted"]:
            where = "accepted" + (" (the hand's, from its record)" if row["recorded"] else "") + (
                ", hoisted" if row["hoisted"] else ", not hoisted")
        elif row["whole"] and row["gated"] and row["blockers"]:
            where = f"whole and gated, and a release blocker — {'; '.join(row['blockers'])}"
        elif row["whole"] and row["gated"]:
            where = ("whole and gated — a demo is due" if demos_setting() == PERSON
                     else "whole and gated — the hand's `accepted` line is owed")
        elif row["whole"]:
            where = "whole — gates due"
        else:
            where = f"{row['merged']} of {len(row['slices'])} merged, waiting on {', '.join(row['waiting'])}"
        print(f"  {row['capability']}: {where}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

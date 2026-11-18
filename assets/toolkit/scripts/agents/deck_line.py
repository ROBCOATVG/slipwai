#!/usr/bin/env python3
"""The deck lines a session owes for a slice and for a whole capability, written by a command and not by hand.

A captain holds a slice to three lines: a `mark-set` for every mark the chart says it sets, a `demo` with
its verdict, and — where it has a story — `seeded`. `seeded` always had a writer, `try_it.py seed --slice`.
The other two had none: a session wrote them by appending JSON to the fairway's log itself, and a harness
that judges each action read a session editing the record it is judged by as exactly that, and refused.
game-club-manager's TB1 was built, proven and accepted, and was dispatched about once a minute for two hours
because it could not write the line that says so; eighty-four notes under *Waiting on you* said the same
thing, and a person was asked to append two lines of JSON.

So the lines have a door, and the door checks what a hand could not be held to: the slice is on the chart,
the mark is one the chart says this slice sets, the verdict is one of the three a demo can have.

    python3 scripts/agents/deck_line.py mark-set --slice TB1 --mark ClubWeekSet
    python3 scripts/agents/deck_line.py demo --slice TB1 --verdict accepted --by sail-demo-hand \\
        --log specs/<feature>/slices/TB1/demo-log.md

A whole capability's two lines had no door either, and nothing wrote them: `accepted`, and `demo-due` where
a person accepts demos. Who accepts is `.specify/cruise.json`'s `demos` — the hand, by default, whose
verdict at the walk is the acceptance; or a person, whose demo is then due:

    python3 scripts/agents/deck_line.py accepted --capability place-an-order --by sail-demo-hand
    python3 scripts/agents/deck_line.py demo-due --capability place-an-order

Both are refused unless the capability is whole and its gates record says `Cleared:` (`capabilities.py`'s
`acceptable`), `accepted` under `person` and `demo-due` under `hand`. This door takes only the hand's
acceptance: a person's is written by the board when they press Accept, so no session can accept as them.

None is a claim the captain takes on trust: a merge is still the harbourmaster's, after the full gate.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import capabilities  # noqa: E402
import clearance  # noqa: E402
import logs  # noqa: E402


def project_root(script: Path) -> Path:
    for candidate in script.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return script.parents[2]


ROOT = project_root(Path(__file__).resolve())


class Refused(Exception):
    """The line was not written, and why."""


def charted(slice_id: str, feature: str = "") -> tuple[str, dict]:
    """The feature whose chart holds this slice, and the slice's own entry in it."""
    found, name = clearance.chart(feature)
    body = (found.get("slices") or {}).get(slice_id)
    if not name:
        raise Refused("no feature under specs/ has a chart.yaml, so nothing says which slices there are")
    if not isinstance(body, dict):
        raise Refused(f"{slice_id} is not a slice on specs/{name}/chart.yaml")
    return name, body


def fairway_of(body: dict) -> str:
    """The fairway whose log the line belongs in: the captain's word for a session it dispatched, the
    chart's for one run by hand — as `try_it.py` reads it for `seeded`."""
    return os.environ.get("SLIPWAI_FAIRWAY", "") or str(body.get("fairway", ""))


def line(kind: str, slice_id: str, feature: str = "", mark: str = "", verdict: str = "",
         by: str = "", log: str = "") -> logs.Entry:
    """The entry, or a refusal that names what the chart or the vocabulary says instead."""
    name, body = charted(slice_id, feature)
    fairway = fairway_of(body)
    if not fairway:
        raise Refused(f"nothing says which fairway {slice_id} is in — set SLIPWAI_FAIRWAY or give the slice "
                      f"a `fairway` on specs/{name}/chart.yaml")
    if kind == "mark-set":
        sets = [str(one) for one in (body.get("sets") or [])]
        if mark not in sets:
            raise Refused(f"the chart says {slice_id} sets {', '.join(sets) or 'no mark'}, not {mark!r}. A "
                          f"mark another slice sets is that slice's line to write")
        return logs.entry("mark-set", fairway=fairway, slice=slice_id, mark=mark)
    said = {name: value for name, value in (("by", by), ("log", log)) if value}
    try:
        return logs.entry("demo", fairway=fairway, slice=slice_id, verdict=verdict, **said)
    except logs.Unreadable as fault:
        raise Refused(str(fault)) from fault


#: The lines about a whole capability rather than a slice, and the one accepter this door writes for.
CAPABILITY_KINDS = ("accepted", "demo-due")
HAND = "sail-demo-hand"


def capability_line(kind: str, capability: str, feature: str = "", by: str = "") -> tuple[str, logs.Entry]:
    """The feature and the entry for a capability's line, or a refusal saying why not.

    Held to `capabilities.acceptable` — whole and cleared — and to the setting: `accepted` is the hand's
    under `hand`, `demo-due` a person's under `person`. A capability spanning fairways logs to the last of
    them in split order, where its last slice merged; every reader folds every fairway's log of the feature
    (`capabilities.lines`, `clearance.lines`, the board's fold), so the line is seen from all of them."""
    found, name = clearance.chart(feature)
    if not name:
        raise Refused("no feature under specs/ has a chart.yaml, so nothing says which capabilities there are")
    row = next((one for one in capabilities.rows_of(name, found) if one["capability"] == capability), None)
    if row is None:
        raise Refused(f"no slice on specs/{name}/chart.yaml names the capability {capability!r}")
    if not row["fairways"]:
        raise Refused(f"nothing says which fairway {capability} is in — give its slices a `fairway` on "
                      f"specs/{name}/chart.yaml")
    person = capabilities.demos_setting() == capabilities.PERSON
    if kind == "demo-due" and not person:
        raise Refused("`demos` is `hand` in .specify/cruise.json, so no person is owed a demo: the hand's verdict "
                      "accepts it — write `accepted --by sail-demo-hand` instead")
    if kind == "accepted" and by != HAND:
        raise Refused(f"this command writes only the hand's acceptance (`--by {HAND}`); a person's is written "
                      f"by the board when they press Accept")
    if kind == "accepted" and person:
        raise Refused("`demos` is `person` in .specify/cruise.json, so the hand's verdict is not the acceptance: "
                      "write `demo-due` and a person accepts it on the board")
    refused = capabilities.acceptable(row)
    if refused:
        raise Refused(refused)
    fairway = row["fairways"][-1]
    if kind == "demo-due":
        return name, logs.entry("demo-due", fairway=fairway, capability=capability)
    return name, logs.entry("accepted", fairway=fairway, capability=capability, by=by)


def write(entry: logs.Entry, feature: str) -> Path:
    path = logs.deck_path(ROOT, feature, str(entry.fields["fairway"]))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(entry.line())
    return path


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="deck_line", description=__doc__.splitlines()[0])
    parser.add_argument("kind", choices=("mark-set", "demo", *CAPABILITY_KINDS))
    parser.add_argument("--slice", default="", dest="slice_id", metavar="ID")
    parser.add_argument("--capability", default="", help="for `accepted` and `demo-due`: as the chart names it")
    parser.add_argument("--mark", default="", help="for `mark-set`: the mark, as the chart names it")
    parser.add_argument("--verdict", default="", help=f"for `demo`: one of {', '.join(logs.VERDICTS)}")
    parser.add_argument("--by", default="", help="for `demo`: who walked it, as `sail-demo-hand`; for "
                                                 "`accepted`: `sail-demo-hand`, the only one it takes")
    parser.add_argument("--log", default="", help="for `demo`: the demo log the verdict is recorded in")
    parser.add_argument("--feature", default="", help="the feature, where more than one has a chart")
    parsed = parser.parse_args(argv)
    if parsed.kind in CAPABILITY_KINDS:
        if not parsed.capability:
            parser.error(f"{parsed.kind} needs --capability")
        try:
            feature, entry = capability_line(parsed.kind, parsed.capability, parsed.feature, parsed.by)
            path = write(entry, feature)
        except (Refused, logs.Unreadable) as refused:
            print(f"deck_line: no `{parsed.kind}` line for {parsed.capability}: {refused}", file=sys.stderr)
            return 1
        print(f"{parsed.kind}: {parsed.capability}; the line is in {path.relative_to(ROOT).as_posix()}")
        return 0
    if not parsed.slice_id:
        parser.error(f"{parsed.kind} needs --slice")
    if parsed.kind == "mark-set" and not parsed.mark:
        parser.error("mark-set needs --mark")
    if parsed.kind == "demo" and not parsed.verdict:
        parser.error("demo needs --verdict")
    try:
        feature, _ = charted(parsed.slice_id, parsed.feature)
        entry = line(parsed.kind, parsed.slice_id, parsed.feature, parsed.mark, parsed.verdict,
                     parsed.by, parsed.log)
        path = write(entry, feature)
    except Refused as refused:
        print(f"deck_line: no `{parsed.kind}` line for {parsed.slice_id}: {refused}", file=sys.stderr)
        return 1
    said = parsed.mark if parsed.kind == "mark-set" else parsed.verdict
    print(f"{parsed.kind}: {parsed.slice_id} — {said}; the line is in {path.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

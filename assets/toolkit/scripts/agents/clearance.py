#!/usr/bin/env python3
"""What may start now: the chart's marks against the deck logs' `mark-set` lines.

Version 1's rule was "its own contract is settled", which a slice could only answer about itself. That
serialised a fresh fairway, because nothing said what a slice was waiting *for*. Issue #32 asked for this
one: a slice has clearance when every mark it steers by has been set, and a mark is set when some slice
wrote a `mark-set` line for it at its own first stage, in its own worktree.

So a sibling unblocks this slice by having **planned**, not by having merged. That is the whole of the
parallelism version 2 promises. If a merge were the signal, every fairway would wait on every other one.

**State comes from the log and never from a status field.** In the first attempt `model.yaml` said `planned`
for eight slices that were built and merged, because the field was written at plan time and never
reconciled. A log line is written by the thing that did the work at the moment it did it.

This lives in the toolkit rather than in the keel because the things that ask it — a `/sail` session, and
the captain — run inside a generated project, which has no slipwai to import. That is the same reason
`check-chart` and `check-slice-scope` are scripts. The first version of this was a keel module, and it was
unreachable from everything that needed it.

    python3 scripts/agents/clearance.py            # every slice that may start now
    python3 scripts/agents/clearance.py BIL-01     # whether that one may, and what it waits on
"""
from __future__ import annotations

import json
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
LOGS = ROOT / ".slipwai/logs"
#: Where each machine's harbourmaster writes its own log. A directory of files rather than one file since
#: 11.3, and never a feature's — a `feature` directory and this one are both under `.slipwai/logs`.
HARBOUR_LOGS = LOGS / "harbour"
#: The log format this reader knows. A newer line is refused rather than guessed at.
V = 1
MARK_SET = "mark-set"
#: Offline machine-readable query supported by this script, checked before a board invokes it.
QUERY_VERSION = 1


def load_yaml(text: str) -> object:
    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError:  # pragma: no cover - exercised on a machine without PyYAML
        subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "PyYAML"], check=True)
        import yaml  # type: ignore[import-not-found]
    return yaml.safe_load(text)


def chart(feature: str = "") -> tuple[dict, str]:
    """The first feature with a chart, and its name. One feature is in flight at a time."""
    for path in sorted(SPECS.glob("*/chart.yaml")) if SPECS.is_dir() else []:
        if feature and path.parent.name != feature:
            continue
        loaded = load_yaml(path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            return loaded, path.parent.name
    return {}, ""


def marks_set(feature: str) -> set[str]:
    """Every mark some slice has set, from every fairway's deck log and from the harbour log.

    A line of a kind this reader does not know is ignored: the logs hold a dozen kinds and will grow, and a
    reader that refused the unfamiliar would break every time one was added. A line in a *newer format* is a
    different matter and stops the read, because guessing which fields moved is how a reader reports a run
    that did not happen.
    """
    found: set[str] = set()
    paths = [*(LOGS / feature).glob("*.jsonl")] if (LOGS / feature).is_dir() else []
    # Every machine's harbour log, since there is one per machine: a mark another machine's harbourmaster
    # carried is what clears a slice here, and reading only one of them would make clearance depend on
    # which machine happened to carry it.
    paths += [*HARBOUR_LOGS.glob("*.jsonl")] if HARBOUR_LOGS.is_dir() else []
    harbour = LOGS / "harbour.jsonl"
    if harbour.is_file():
        paths.append(harbour)
    for path in sorted(paths):
        for number, text in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not text.strip():
                continue
            try:
                line = json.loads(text)
            except ValueError:
                raise SystemExit(f"clearance: {path.name}:{number} is not JSON. A log with a line nobody "
                                 f"can read is a log that answers wrongly rather than not at all.") from None
            if not isinstance(line, dict):
                continue
            if line.get("v") != V:
                raise SystemExit(f"clearance: {path.name}:{number} says v{line.get('v')} and this reader "
                                 f"knows v{V}. Run `slipwai upgrade`.")
            if line.get("kind") == MARK_SET and line.get("mark"):
                found.add(str(line["mark"]))
    return found


def observed(charted: dict) -> set[str]:
    """Every slice the chart records as `observed`, which is every slice that is not work.

    An `observed` slice says *this is what the code already does*. Nobody builds it, so nobody is offered
    it — and a later slice that steers by what it sets is cleared the moment the chart is drawn, because
    the behaviour it waits on shipped before this model existed.
    """
    return {str(slice_id) for slice_id, entry in (charted.get("slices") or {}).items()
            if isinstance(entry, dict) and entry.get("observed") is True}


def already_set(charted: dict) -> set[str]:
    """The marks an `observed` slice sets, which no deck log will ever carry a `mark-set` line for."""
    return {str(mark) for slice_id in observed(charted)
            for mark in (charted.get("slices") or {}).get(slice_id, {}).get("sets") or []}


def steered_by(charted: dict, slice_id: str) -> list[str]:
    entry = (charted.get("slices") or {}).get(slice_id)
    steers = entry.get("steers_by") if isinstance(entry, dict) else None
    return [str(mark) for mark in steers] if isinstance(steers, list) else []


def setter_of(charted: dict, mark: str) -> str | None:
    for slice_id, entry in (charted.get("slices") or {}).items():
        if isinstance(entry, dict) and mark in [str(name) for name in entry.get("sets") or []]:
            return str(slice_id)
    return None


def cleared(charted: dict, settled: set[str], slice_id: str) -> bool | str:
    """`True`, or the sentence saying what this slice waits on and who owes it.

    Every missing mark, not the first: a fairway told one blocker at a time is a fairway blocked once per
    blocker. A slice the chart does not name is refused rather than cleared, because answering yes for an
    uncharted slice would clear anything anybody asked about.
    """
    if slice_id not in (charted.get("slices") or {}):
        return f"{slice_id} is not on the chart, so nothing says what it steers by"
    waiting = [mark for mark in steered_by(charted, slice_id) if mark not in settled]
    if not waiting:
        return True
    owed = [f"{mark} (set by {setter_of(charted, mark)})" if setter_of(charted, mark)
            else f"{mark} (no slice sets it — the chart is wrong)" for mark in waiting]
    return f"{slice_id} steers by {', '.join(owed)}, and none of those is set yet"


def cleared_slices(charted: dict, settled: set[str]) -> list[str]:
    """Every slice that may start now, in the chart's own order, which is split order.

    An `observed` slice is never among them: it is a record of what the code does, not work somebody takes,
    and a ready set that offered one would send a captain to build what is already built.
    """
    never = observed(charted)
    settled = settled | already_set(charted)
    return [str(slice_id) for slice_id in (charted.get("slices") or {})
            if str(slice_id) not in never
            and all(mark in settled for mark in steered_by(charted, str(slice_id)))]


def main(argv: list[str]) -> int:
    if "--json" in argv:
        # A board's read query never installs a dependency or reaches the network.
        try:
            import yaml  # noqa: F401
        except ImportError:
            print(json.dumps({"v": QUERY_VERSION, "error": "PyYAML is not installed. Run `python3 -m pip install PyYAML` "
                                       "in this project's Python environment"}))
            return 1
    requested = ""
    if "--json" in argv and "--feature" in argv:
        index = argv.index("--feature") + 1
        if index >= len(argv) or argv[index].startswith("--"):
            print(json.dumps({"v": QUERY_VERSION, "error": "give a feature name. Run "
                             "`python3 scripts/agents/clearance.py --json --feature <feature>`"}))
            return 1
        requested = argv[index]
    charted, feature = chart(requested)
    if "--json" in argv:
        if not charted:
            print(json.dumps({"v": QUERY_VERSION, "error": "no readable chart exists. Run `make chart`"}))
            return 1
        settled = marks_set(feature) | already_set(charted)
        ready: dict[str, list[str]] = {}
        for slice_id in cleared_slices(charted, settled):
            fairway = str((charted.get("slices") or {})[slice_id].get("fairway", ""))
            ready.setdefault(fairway, []).append(slice_id)
        print(json.dumps({"v": QUERY_VERSION, "feature": feature, "ready": ready}))
        return 0
    if not charted:
        print("clearance: no chart yet, so nothing is waiting on anything")
        return 0
    settled = marks_set(feature) | already_set(charted)
    if argv:
        answer = cleared(charted, settled, argv[0])
        print(f"clearance: {argv[0]} is cleared" if answer is True else f"clearance: {answer}")
        return 0 if answer is True else 1
    ready = cleared_slices(charted, settled)
    print(f"clearance: {len(ready)} of {len(charted.get('slices') or {})} slices cleared in {feature}")
    for slice_id in ready:
        print(f"  {slice_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

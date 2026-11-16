"""An eval case for the captain, as a file a person reads and edits, and the throwaway project it becomes.

A case is one JSON file under `evals/captain/cases/<decision>/`, one moment of one stream at which the
captain had a choice to make:

- `situation` — two or three sentences a person reads first: what was going on.
- `source` — where the moment was cut from, with nothing personal in it.
- `snapshot` — the stream at that moment: `feature`, `fairway`, `slices` (each slice's state in a few
  words), `deck` and `harbour` (the log lines that matter, as the logs hold them), `activity` (the last
  lines of a slice's activity log, by slice), `gate` (the refusal text, for a failed gate), `said` (what a
  person told the stream: `id`, `text`, `from`), `slots` (free session slots, for choosing what starts),
  `others` (other streams' deck lines, by stream, where the moment turns on them). The captain is given
  the snapshot and nothing else, so a label rests on what is in it: never on `situation`, never on hindsight.
- `synthetic` — true for a moment made up because the recorded runs had none like it; `source` says why.
- `event` — what wakes the captain, in contract 2.2's shape. `facts` may be left out: it is then the
  snapshot, which is the fold the decision needs.
- `label` — `accept` (orders a person would accept), `wrong` (orders that would be plainly wrong), `why`
  (a sentence), `signed_off` (who confirmed the label; empty until a person has), `note` (anything else,
  such as that the label is a draft from what happened next).

The patterns in `accept` and `wrong` are read by `eval_score.matches`.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from eval_score import VERBS

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "evals/captain/cases"
TOOLKIT = ROOT / "assets/toolkit"
#: The four decisions, by the event kind that asks each, with the words the report uses for it.
DECISIONS = {
    "choose-next": "which cleared slice starts next",
    "gate-failed": "after a failed gate: retry or park",
    "message": "which slices a person's message is for",
    "stuck": "what to do about a stuck slice",
}
#: What the program will take for each decision when a case does not say: the `may` of contract 2.2.
MAY = {
    "choose-next": ["start", "none"],
    "gate-failed": ["retry", "park", "say", "ask", "none"],
    "message": ["message", "resume", "say", "ask", "none"],
    "stuck": ["message", "pause", "stop", "park", "say", "ask", "none"],
}
SHAPES = ("slice", "slices", "within", "naming")
ROUTED = ("required", "optional")
#: What the toolkit gives the throwaway project: how a session is started, how an order is written, and the
#: captain's own door for the evals (`captain_agent.py decide`) with what it imports.
CARRIED = ("scripts/agents/harness.py", "scripts/agents/registry.json", "scripts/agents/orders.py",
           "scripts/agents/captain_agent.py", "scripts/agents/drive.py", "scripts/agents/acp.py",
           "scripts/agents/logs.py", "scripts/agents/talk.py")
#: Written at the root of every throwaway project: the one place `captain_agent.py decide` agrees to run.
MARKER = ".slipwai-eval"


def load(path: Path) -> dict[str, Any]:
    case = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(case, dict):
        raise ValueError(f"{path}: a case is a JSON object")
    case.setdefault("id", case_id(path))
    return case


def case_id(path: Path) -> str:
    """`<decision>/<name>`: the folder it is in and its file's name, which is how a run refers to it."""
    return f"{path.parent.name}/{path.stem}"


def every(cases: Path = CASES, decision: str | None = None) -> list[Path]:
    folders = [cases / decision] if decision else sorted(one for one in cases.iterdir() if one.is_dir())
    return sorted(path for folder in folders if folder.is_dir() for path in folder.glob("*.json"))


def pattern_faults(where: str, pattern: object) -> list[str]:
    if not isinstance(pattern, dict):
        return [f"{where}: a pattern is an object with a `verb`"]
    verbs = pattern.get("verb")
    named = [verbs] if isinstance(verbs, str) else verbs if isinstance(verbs, list) else []
    faults = [] if named and all(one in VERBS for one in named) else [
        f"{where}: `verb` is one of {', '.join(sorted(VERBS))}, or a list of them"]
    present = [shape for shape in [*SHAPES, *ROUTED] if shape in pattern]
    # `required` and `optional` are one shape between them: the slices a message must and may go to.
    shapes = [shape for shape in present if shape not in ROUTED]
    shapes += ["required/optional"] if set(present) & set(ROUTED) else []
    if len(shapes) > 1:
        faults.append(f"{where}: one of {', '.join(SHAPES)}, required/optional at most, not {', '.join(shapes)}")
    for shape in present:
        value = pattern[shape]
        single = shape in ("slice", "naming")
        if single and not (isinstance(value, str) and value):
            faults.append(f"{where}: `{shape}` is one slice")
        if not single and not (isinstance(value, list) and all(isinstance(one, str) for one in value)):
            faults.append(f"{where}: `{shape}` is a list of slices")
    unknown = set(pattern) - {"verb", *SHAPES, *ROUTED}
    if unknown:
        faults.append(f"{where}: unknown keys {', '.join(sorted(unknown))}")
    return faults


def faults(case: dict[str, Any], decision: str | None = None) -> list[str]:
    """Everything wrong with a case's shape, one sentence each; none is a case the runner can use."""
    found = [f"`{key}` is missing" for key in ("situation", "source", "snapshot", "event", "label")
             if key not in case]
    snapshot, event, label = case.get("snapshot") or {}, case.get("event") or {}, case.get("label") or {}
    kind = event.get("kind")
    if kind not in DECISIONS:
        found.append(f"event `kind` is one of {', '.join(DECISIONS)}, not {kind!r}")
    elif decision and kind != decision:
        found.append(f"event `kind` is {kind!r} and the case is filed under {decision!r}")
    for key in ("feature", "fairway"):
        if not isinstance(snapshot.get(key), str) or not snapshot.get(key):
            found.append(f"snapshot `{key}` is missing")
    if not isinstance(snapshot.get("slices"), dict):
        found.append("snapshot `slices` is each slice's state, by slice")
    for key in ("deck", "harbour"):
        if not isinstance(snapshot.get(key, []), list):
            found.append(f"snapshot `{key}` is a list of log lines")
    may = event.get("may")
    if may is not None and not (isinstance(may, list) and may and all(one in VERBS for one in may)):
        found.append("event `may` is a list of verbs orders.py takes")
    if not isinstance(event.get("id"), str) or not isinstance(event.get("t"), str):
        found.append("event `id` and `t` are strings")
    accept = label.get("accept")
    if not isinstance(accept, list) or not accept:
        found.append("label `accept` lists at least one order a person would accept")
    for name in ("accept", "wrong"):
        for index, pattern in enumerate(label.get(name) or []):
            found += pattern_faults(f"label `{name}`[{index}]", pattern)
    if not isinstance(label.get("why"), str) or not label.get("why", "").strip():
        found.append("label `why` is a sentence")
    if not isinstance(label.get("signed_off"), str):
        found.append("label `signed_off` is who confirmed it, or \"\" until a person has")
    return found


def event_of(case: dict[str, Any]) -> dict[str, Any]:
    """The event as the captain receives it: `may` and `facts` filled in where the case leaves them out."""
    event = dict(case["event"])
    event.setdefault("v", 1)
    event.setdefault("may", MAY[event["kind"]])
    event.setdefault("slice", "")
    if "facts" not in event:
        event["facts"] = {key: value for key, value in case["snapshot"].items() if key not in ("feature",)}
    return event


def context_of(case: dict[str, Any]) -> tuple[set[str], int | None]:
    """What an answer is checked against beside its label: the slices the stream has, and its free slots."""
    snapshot = case["snapshot"]
    slots = snapshot.get("slots")
    return set(snapshot.get("slices") or {}), slots if isinstance(slots, int) else None


def write_lines(path: Path, lines: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(line) + "\n" for line in lines), encoding="utf-8")


def lay_out(case: dict[str, Any], root: Path, integration: Path | None = None, brief: Path | None = None) -> Path:
    """The case as a project's state under `root`, which is a throwaway directory. The event file's path.

    Everything goes where the program keeps it under `.slipwai/run/` — the deck log, a harbour log, the
    activity logs, what the person said in the captain's inbox, the event — so the captain reads the
    moment the way it would read a real stream, and `orders/<fairway>/` is there, empty, for its answer.
    """
    snapshot, event = case["snapshot"], event_of(case)
    feature, fairway = snapshot["feature"], snapshot["fairway"]
    run = root / ".slipwai/run"
    (root / "project.json").write_text("{}\n", encoding="utf-8")
    (root / MARKER).write_text("laid out by the evals: a throwaway project, never a checkout\n", encoding="utf-8")
    # A case's log lines leave out the `fairway` every line of one stream carries; the log has it back.
    write_lines(run / "logs" / feature / f"{fairway}.jsonl",
                [{"v": 1, "fairway": fairway, **line} for line in snapshot.get("deck", [])])
    write_lines(run / "logs/harbour/eval.jsonl",
                [{"v": 1, "fairway": fairway, **line} for line in snapshot.get("harbour", [])])
    # Other streams' deck logs, where the moment turns on them: a captain reads its neighbours' logs too.
    for other, lines in (snapshot.get("others") or {}).items():
        write_lines(run / "logs" / feature / f"{other}.jsonl", [{"v": 1, "fairway": other, **line} for line in lines])
    for slice_id, lines in (snapshot.get("activity") or {}).items():
        write_lines(run / "activity" / fairway / f"{slice_id}.jsonl", lines)
    said = snapshot.get("said")
    if isinstance(said, dict) and said.get("id"):
        inbox = run / "talk" / fairway / "_captain/inbox" / f"{said['id']}.json"
        inbox.parent.mkdir(parents=True, exist_ok=True)
        message = {"v": 1, "kind": "say", "mode": "wait", "from": "person", **said}
        inbox.write_text(json.dumps(message) + "\n", encoding="utf-8")
    (run / "orders" / fairway).mkdir(parents=True, exist_ok=True)
    events = run / "events" / fairway / f"{event['id']}.json"
    events.parent.mkdir(parents=True, exist_ok=True)
    events.write_text(json.dumps(event, indent=1) + "\n", encoding="utf-8")
    for relative in CARRIED:
        source = TOOLKIT / relative
        if source.is_file():
            (root / relative).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(source, root / relative)
    if brief is not None and brief.is_file():
        (root / "agents").mkdir(exist_ok=True)
        shutil.copy(brief, root / "agents" / brief.name)
    if integration is not None and integration.is_file():
        (root / ".specify").mkdir(exist_ok=True)
        shutil.copy(integration, root / ".specify/integration.json")
    return events

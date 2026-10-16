#!/usr/bin/env python3
"""Lay out the evidence for the seam tests from `docs/event-model/model.yaml`. `make seams` runs this.

It prints candidates, not contexts: the slices that write one stream, the views that fold only that
stream, the views that fold several, and what crosses between groups. The method that reads this is in
`skills/domain-driven-design/resources/bounded-contexts.md`, *The Seam Tests*, and the step that runs it
is `skills/event-modeling/references/nine-steps.md`, *Apply Conway's Law*. A stream is never split, so a
stream written from two contexts is reported as refused. One stream prints one candidate and no seam.

`--json` prints the same as data, for a test or another script.
"""
from __future__ import annotations

import json
import subprocess
import sys
from collections import OrderedDict
from pathlib import Path


def project_root(script: Path) -> Path:
    """Specs and the manifest stay at the repository root when adoption relocates delivery material."""
    for candidate in script.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return script.parents[2]


DELIVERY = Path(__file__).resolve().parents[2]
ROOT = project_root(Path(__file__).resolve())
MODEL = DELIVERY / "docs/event-model/model.yaml"


def load_yaml(text: str) -> object:
    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError:  # pragma: no cover - exercised on a machine without PyYAML
        subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "PyYAML"], check=True)
        import yaml  # type: ignore[import-not-found]
    return yaml.safe_load(text)


def events_of(item: dict) -> list[str]:
    """The events this slice produces: every `evt` frame it is not reading from somewhere else."""
    frames = item.get("frames")
    if not isinstance(frames, list):
        return []
    return [str(frame["name"]) for frame in frames
            if isinstance(frame, dict) and frame.get("type") == "evt"
            and frame.get("external") is not True and frame.get("name")]


def stream_name(item: dict) -> str | None:
    """`listing-{listingId}` is the `listing` stream: the identity with its placeholder cut off, which is
    the same reading the renderer gives a swimlane. A slice guarding with `guard` has no stream name."""
    stream = item.get("stream")
    if not isinstance(stream, str) or not stream:
        return None
    head = stream.split("{", 1)[0].rstrip("-_: ")
    return head or stream


def seams(model: object) -> dict:
    """Group the slices by the stream they write, attach the views and automations by what they fold, and
    say what crosses between groups. Pure, so a test can hand it a model and read the answer."""
    slices = model.get("slices") if isinstance(model, dict) else None
    if not isinstance(slices, list):
        return {"candidates": [], "crossings": [], "across": [], "split_streams": [], "unplaced": []}

    producer: dict[str, str] = {}
    groups: "OrderedDict[str, dict]" = OrderedDict()

    def group(name: str) -> dict:
        return groups.setdefault(name, {
            "stream": name, "slices": [], "writers": [], "actors": [], "contexts": [], "events": [],
            "folds_from": OrderedDict(), "capabilities": []})

    def note(bucket: list, value: object) -> None:
        if value is not None and value != "" and value not in bucket:
            bucket.append(value)

    # First pass: who writes which stream, and which events are theirs.
    for item in slices:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        name = stream_name(item)
        if name is None:
            continue
        found = group(name)
        note(found["slices"], str(item["id"]))
        note(found["writers"], str(item["id"]))
        note(found["actors"], item.get("actor"))
        note(found["contexts"], item.get("context"))
        note(found["capabilities"], item.get("capability"))
        for event in events_of(item):
            note(found["events"], event)
            producer.setdefault(event, name)

    # Second pass: what each slice folds from streams other than its own. A view with no stream is
    # attached to the one stream it folds, or listed as reading across when it folds several.
    across: list[dict] = []
    unplaced: list[str] = []
    for item in slices:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        own = stream_name(item)
        reads = item.get("reads")
        folded = [str(event) for event in reads] if isinstance(reads, list) else []
        by_stream: "OrderedDict[str, list[str]]" = OrderedDict()
        for event in folded:
            source = producer.get(event)
            if source is None or source == own:
                continue
            by_stream.setdefault(source, []).append(event)
        if own is not None:
            for source, events in by_stream.items():
                groups[own]["folds_from"].setdefault(source, [])
                for event in events:
                    note(groups[own]["folds_from"][source], event)
            continue
        if len(by_stream) == 1:
            (source,) = by_stream
            found = group(source)
            note(found["slices"], str(item["id"]))
            note(found["actors"], item.get("actor"))
            note(found["contexts"], item.get("context"))
            note(found["capabilities"], item.get("capability"))
        elif by_stream:
            across.append({"slice": str(item["id"]), "name": item.get("name"), "actor": item.get("actor"),
                           "context": item.get("context"),
                           "folds": {source: events for source, events in by_stream.items()}})
        else:
            unplaced.append(str(item["id"]))

    crossings = [{"from": source, "to": target, "events": events}
                 for target, found in groups.items()
                 for source, events in found["folds_from"].items()]
    split = [found["stream"] for found in groups.values() if len(found["contexts"]) > 1]
    candidates = []
    for found in groups.values():
        record = dict(found)
        record["folds_from"] = {source: events for source, events in found["folds_from"].items()}
        candidates.append(record)
    return {"candidates": candidates, "crossings": crossings, "across": across,
            "split_streams": split, "unplaced": unplaced}


def said(names: list[str]) -> str:
    return ", ".join(names) if names else "—"


def report(found: dict) -> str:
    """The evidence, in the order the proposal is written: candidates, then what crosses, then what is
    left to decide. Every line is something a person can disagree with by pointing at the model."""
    lines: list[str] = []
    candidates = found["candidates"]
    if not candidates:
        return "seams: no slice names a stream yet, so there is nothing to group. Model the writes first."
    contexts = {context for item in candidates for context in item["contexts"]}
    lines.append(f"seams: {len(candidates)} candidate{'s' if len(candidates) != 1 else ''} "
                 f"(the slices that write one stream, with the views that fold only it) "
                 f"in {len(contexts)} context{'s' if len(contexts) != 1 else ''} today")
    lines.append("")
    for item in candidates:
        count = len(item["slices"])
        lines.append(f"  {item['stream']}  —  {count} slice{'s' if count != 1 else ''}, "
                     f"{len(item['writers'])} writing; actors {said(item['actors'])}; "
                     f"context {said(item['contexts'])}")
        lines.append(f"      capabilities: {said(item['capabilities'])}")
        lines.append(f"      events: {said(item['events'])}")
        for source, events in item["folds_from"].items():
            lines.append(f"      folds from {source}: {', '.join(events)}")
    if found["across"]:
        lines.append("")
        lines.append("  reads across several candidates — a view, or a context of its own if its rules "
                     "change for their own reasons:")
        for view in found["across"]:
            parts = "; ".join(f"{source}: {', '.join(events)}" for source, events in view["folds"].items())
            lines.append(f"    {view['slice']} {view['name'] or ''} ({view['actor'] or 'no actor'}) folds {parts}")
    if found["unplaced"]:
        lines.append("")
        lines.append(f"  no stream and reads nothing a stream produces: {said(found['unplaced'])}")
    lines.append("")
    if found["split_streams"]:
        for stream in found["split_streams"]:
            lines.append(f"  REFUSED: stream {stream} is written from more than one context; a stream is never "
                         "split (bounded-contexts.md, The Seam Tests).")
        lines.append("")
    if len(candidates) == 1:
        lines.append("  One stream, so one candidate and no seam to test: one context, with this as the evidence.")
        return "\n".join(lines)
    if found["crossings"]:
        count = len(found["crossings"])
        lines.append(f"  {count} crossing{'s' if count != 1 else ''} between candidates' writes, every one an "
                     "event folded on the far side (contract coupling, cheap):")
        for edge in found["crossings"]:
            lines.append(f"    {edge['to']} folds {edge['from']}: {', '.join(edge['events'])}")
    else:
        lines.append("  No write folds another candidate's events; what traffic there is between them is the "
                     "views above.")
    lines.append("")
    lines.append("  Candidates are not contexts. Test each seam for language, change and flow and write the "
                 "table down: skills/domain-driven-design/resources/bounded-contexts.md, The Seam Tests.")
    return "\n".join(lines)


def main() -> int:
    if not MODEL.is_file():
        print(f"seams: {MODEL.relative_to(DELIVERY)} is missing; model the first workflow before looking for "
              "seams", file=sys.stderr)
        return 1
    found = seams(load_yaml(MODEL.read_text(encoding="utf-8")))
    if "--json" in sys.argv[1:]:
        print(json.dumps(found, indent=2))
    else:
        print(report(found))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"seams failed: {error}", file=sys.stderr)
        raise SystemExit(1)

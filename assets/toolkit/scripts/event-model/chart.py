#!/usr/bin/env python3
"""Render `specs/<feature>/chart.yaml` from `docs/event-model/model.yaml`. `make chart` runs this.

On the event-modelling profile the model already answers every question the chart asks. It names each
slice's context and service, types the events each slice produces, and says what each slice reads. So the
chart is not written here, it is *derived* here, and `check-chart` refuses a committed chart that has
drifted from the model — the way `make check-drawio` holds the committed canvas to the same file.

**An event's mark points at the model, and no schema is generated from it.** The model is already the typed
contract on this profile: a frame's `attributes` carry the names, which of them identify something, and a
loose type where the modeller wrote one. Turning that into JSON Schema would mean inventing a mapping from
the model's type words to JSON Schema's, and that mapping would immediately *be* the contract every other
fairway steers by — a type system invented in a renderer, by nobody, holding up everything downstream. So
the mark names `docs/event-model/model.yaml` with the event as its fragment, which is a contract a reader
can open and a gate can check the existence of. The standard profile writes JSON Schema files because it
has no model; this profile has one, which is the whole difference between them.

The chart compares as data rather than as text, so re-rendering with a different YAML writer, or a
reordered model, is not drift. Drift is a fairway, a mark or a slice that says something different.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODEL = ROOT / "docs/event-model/model.yaml"
MANIFEST = ROOT / "project.json"
SPECS = ROOT / "specs"
#: What an event mark names. The fragment is the event; the file is the model, which is the contract here.
MODEL_PATH = "docs/event-model/model.yaml"


def load_yaml(text: str) -> object:
    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError:  # pragma: no cover - exercised on a machine without PyYAML
        subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "PyYAML"], check=True)
        import yaml  # type: ignore[import-not-found]
    return yaml.safe_load(text)


def services() -> dict[str, dict]:
    """Each deployable's record, by name. An unreadable manifest is an empty mapping, as `check.py` reads it."""
    try:
        document = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    deployables = document.get("deployables") if isinstance(document, dict) else None
    return deployables if isinstance(deployables, dict) else {}


def contexts_of(record: dict) -> list[str]:
    """A service's contexts: its `contexts`, or the one `context` an older manifest named."""
    contexts = record.get("contexts")
    if isinstance(contexts, list) and contexts:
        return [str(name) for name in contexts]
    return [str(record["context"])] if isinstance(record.get("context"), str) else []


def owns(name: str, record: dict, context: str) -> list[str]:
    """The paths this fairway owns. A service holding one context owns all of it; one holding several owns
    the context's own directory, which is where `/sail` puts a context's code and `check-imports` keeps it."""
    path = str(record.get("path") or name).rstrip("/")
    return [f"{path}/**"] if len(contexts_of(record)) <= 1 else [f"{path}/src/{context}/**"]


def events_of(item: dict) -> list[str]:
    """The events this slice produces: every `evt` frame it is not reading from somewhere else."""
    frames = item.get("frames")
    if not isinstance(frames, list):
        return []
    return [str(frame["name"]) for frame in frames
            if isinstance(frame, dict) and frame.get("type") == "evt"
            and frame.get("external") is not True and frame.get("name")]


def unreadable(model: object) -> list[str]:
    """Every slice in the model this renderer cannot read, said by where it is.

    A model with three slices and no `id` on any of them used to render an empty chart and report
    "0 slices" as a success. The checker then refused the chart for a different reason and nobody could
    see that the model was the problem. A renderer that drops what it cannot read is a renderer that makes
    a chart with holes in it, and a chart with holes is what the whole of clearance then believes.
    """
    slices = model.get("slices") if isinstance(model, dict) else None
    if not isinstance(slices, list):
        return []
    return [f"slice {number} of the model has no `id`, so nothing can name it"
            for number, item in enumerate(slices, start=1)
            if not (isinstance(item, dict) and item.get("id"))]


def only_service(deployables: dict[str, dict]) -> str | None:
    """The one deployable a slice's code could land in, or None where there is a choice to be made.

    `kind: service`, not "the only deployable": a project with one service and a web app has two
    deployables and still nothing to decide, and resolving to the web app would put a context's code in
    the browser.
    """
    found = [name for name, record in deployables.items() if record.get("kind") == "service"]
    return found[0] if len(found) == 1 else None


def service_for(item: dict, deployables: dict[str, dict]) -> tuple[str, dict] | None:
    """Which deployable owns this slice: the one it names, or the only service there is.

    `service` is optional on a slice while a project has one service — there is nothing to decide then —
    so resolving only the named one left such a project with no fairways at all, and a chart
    `check-chart` then refused for naming fairways it had not got. The renderer and the checker
    disagreeing about what a chart is is the worst pairing of the two there is.
    """
    named = str(item.get("service") or "")
    if named in deployables:
        return named, deployables[named]
    only = only_service(deployables)
    return (only, deployables[only]) if only else None


def render(model: object, deployables: dict[str, dict]) -> dict:
    """The chart this model means. Sorted throughout, so two renders of one model are one chart."""
    slices = model.get("slices") if isinstance(model, dict) else None
    items = [item for item in slices if isinstance(item, dict) and item.get("id")] if isinstance(slices, list) else []

    service_of: dict[str, tuple[str, dict]] = {}
    for item in items:
        context = str(item.get("context") or "")
        found = service_for(item, deployables)
        if context and found is not None:
            service_of[context] = found

    fairways, marks, charted = {}, {}, {}
    for context, (service, record) in sorted(service_of.items()):
        fairways[context] = {"context": context, "service": str(record.get("path") or service),
                             "owns": owns(service, record, context)}
    for item in sorted(items, key=lambda entry: str(entry["id"])):
        for event in events_of(item):
            marks[event] = {"kind": "event", "schema": f"{MODEL_PATH}#{event}"}
    for item in sorted(items, key=lambda entry: str(entry["id"])):
        reads = item.get("reads")
        charted[str(item["id"])] = {
            "fairway": str(item.get("context") or ""),
            "capability": str(item.get("capability") or ""),
            "sets": sorted(events_of(item)),
            "steers_by": sorted(str(event) for event in reads) if isinstance(reads, list) else [],
            # An `observed` slice records behaviour that is already in the tree (15.10). It stays on the
            # chart because a later slice steers by what it sets — that is the join, and the reason the
            # model is global — but it is not work: its marks are set by the code existing, and `/sail`
            # must never offer it. `clearance.py` reads this.
            **({"observed": True} if item.get("status") == "observed" else {}),
        }
    return {"v": 1, "feature": feature_name(), "fairways": fairways, "marks": marks, "slices": charted}


def feature_name() -> str:
    """The feature in flight: the one directory under `specs/` that has a slice record, else the model's."""
    candidates = sorted(path.name for path in SPECS.glob("*/") if (path / "slices").is_dir()) if SPECS.is_dir() else []
    return candidates[0] if candidates else "model"


def chart_path() -> Path:
    return SPECS / feature_name() / "chart.yaml"


def rendered() -> dict | None:
    """The chart the model means, or None where there is no model to mean one."""
    if not MODEL.is_file():
        return None
    return render(load_yaml(MODEL.read_text(encoding="utf-8")), services())


def main() -> int:
    chart = rendered()
    if chart is None:
        print("chart: no event model here; the chart is written by /chart on this profile")
        return 0
    faults = unreadable(load_yaml(MODEL.read_text(encoding="utf-8")))
    if faults:
        print("chart: the model holds slices this cannot read, so no chart is written", file=sys.stderr)
        for fault in faults:
            print(f"  {fault}", file=sys.stderr)
        print("  Run: npm run -w scripts/event-model check   (which says what each slice is missing)",
              file=sys.stderr)
        return 1
    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError:  # pragma: no cover
        subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "PyYAML"], check=True)
        import yaml  # type: ignore[import-not-found]
    path = chart_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    document = (
        "# Rendered from docs/event-model/model.yaml by `make chart`. Never edit by hand:\n"
        "# `make check-chart` refuses a chart that disagrees with the model.\n"
        + yaml.safe_dump(chart, sort_keys=True, default_flow_style=False, allow_unicode=True)
    )
    path.write_text(document, encoding="utf-8")
    print(f"chart: {path.relative_to(ROOT).as_posix()} written from the model — "
          f"{len(chart['fairways'])} fairways, {len(chart['marks'])} marks, {len(chart['slices'])} slices")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

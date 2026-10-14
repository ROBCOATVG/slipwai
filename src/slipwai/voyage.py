"""The slices of a voyage by where they stand, and the committed model with that standing drawn on it.

Two folds and one rewrite. The slices come from the chart's own clearance reading — the project's script,
through its offline JSON port, which is the one reader of `chart.yaml` the keel allows itself — joined with
the deck logs' claimed, merged and parked lines, so that a column on the board is never a status field.
The model is `docs/event-model/model.drawio` exactly as committed, with each slice's caption cell re-stroked
by the same fold: the renderer gives that cell a deterministic id from the slice's own, so the board finds
it in the XML without parsing the picture. The recoloured copy exists only in the response; the file is
never written, and `make check-drawio` keeps holding it to `model.yaml`.

The viewer that draws it is draw.io's own, one Apache-licensed script of four and a half megabytes. Not
carried in the wheel: fetched once into `~/.slipwai/` on the first request and served from there after,
which is offline from the second time on and says so plainly on a machine that has never reached it.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

from .assets import SLIPWAI
from .fleet import clearance_query, fairways, harbour_log

#: Where the board shows a slice: the four columns, in the order a person reads them.
COLUMNS = ("todo", "working", "waiting", "done")
#: The clearance script's states, folded to the board's four.
CLEARANCE = {"done": "done", "running": "working", "awaiting-demo": "working"}
#: The stroke each state puts on a slice's caption in the drawio — draw.io's own colour space, not the
#: board's tokens, because the picture keeps draw.io's colours in both themes.
STROKES = {"done": ("#0f6b6b", "3", ""), "working": ("#8a6d24", "3", ""),
           "waiting": ("#b4432f", "3", "dashed=1;dashPattern=6 4;"), "todo": ("", "", "")}
MODEL = "docs/event-model/model.yaml"
DRAWIO = "docs/event-model/model.drawio"
#: draw.io's read-only viewer, and where a copy of it is kept once fetched.
VIEWER_URL = "https://viewer.diagrams.net/js/viewer-static.min.js"
VIEWER = SLIPWAI / "drawio-viewer.min.js"


def cell_id(slice_id: str) -> str:
    """The id `scripts/event-model/drawio.ts` gives a slice's caption cell: `c-slice-<id>`, sanitised as it
    sanitises — every character outside `[A-Za-z0-9_-]` an underscore."""
    return "c-" + re.sub(r"[^A-Za-z0-9_-]", "_", f"slice-{slice_id}")


def folded(root: Path, feature: str = "") -> tuple[list[dict[str, str]], str]:
    """Every charted slice with its state, fairway, why, and marks — and a fault where the chart could not be
    read. Empty, and no fault, where there is no chart yet."""
    feature, result, fault = clearance_query(root, feature)
    states = result.get("states") if isinstance(result.get("states"), dict) else {}
    if fault or not states:
        return [], fault
    found, _ = fairways(root, harbour_log(root))
    rows: list[dict[str, str]] = []
    for slice_id, entry in states.items():
        state = CLEARANCE.get(str(entry.get("state", "")), "todo")
        row = {"slice": str(slice_id), "feature": feature, "state": state, "why": str(entry.get("why", "")),
               "fairway": "", "clearance": str(entry.get("state", ""))}
        owner = next((one for one in found if slice_id in one.claimed or slice_id in one.merged), None)
        if owner is not None:
            row["fairway"] = owner.name
            if slice_id in owner.merged:
                row["state"] = "done"
            elif owner.slice_now == slice_id:
                row["state"] = "waiting" if owner.parks else "working"
        rows.append(row)
    return sorted(rows, key=lambda row: (COLUMNS.index(row["state"]), row["slice"])), ""


def counts(rows: list[dict[str, str]]) -> dict[str, int]:
    """How many slices stand in each state — what the passage's slice stage reads."""
    return {state: sum(1 for row in rows if row["state"] == state) for state in COLUMNS if any(
        row["state"] == state for row in rows)}


def restroked(xml: str, states: dict[str, str]) -> str:
    """The committed drawio with each slice's caption stroked by its state. Unknown slices and a file the
    renderer did not write are left exactly as they are; a file that does not parse comes back untouched."""
    try:
        tree = ET.fromstring(xml)
    except ET.ParseError:
        return xml
    wanted = {cell_id(slice_id): state for slice_id, state in states.items()}
    changed = False
    for cell in tree.iter("mxCell"):
        state = wanted.get(str(cell.get("id", "")))
        if not state:
            continue
        colour, width, extra = STROKES.get(state, STROKES["todo"])
        if not colour:
            continue
        style = re.sub(r"(strokeColor|strokeWidth|dashed|dashPattern)=[^;]*;", "", str(cell.get("style", "")))
        cell.set("style", f"{style}strokeColor={colour};strokeWidth={width};{extra}")
        changed = True
    return ET.tostring(tree, encoding="unicode") if changed else xml


def model_xml(root: Path, states: dict[str, str]) -> tuple[str, str]:
    """The drawio to show, re-stroked, and the one line to say about it: nothing where there is none, and a
    note where `model.yaml` is newer than the committed picture."""
    page = root / DRAWIO
    if not page.is_file():
        return "", (f"no {DRAWIO} yet: `make model-drawio` writes it from {MODEL}" if (root / MODEL).is_file()
                    else "this project has no event model")
    note = ""
    source = root / MODEL
    if source.is_file() and source.stat().st_mtime > page.stat().st_mtime:
        note = f"{MODEL} is newer than the picture; `make model-drawio` redraws it"
    try:
        return restroked(page.read_text(encoding="utf-8"), states), note
    except OSError as fault:
        return "", f"{DRAWIO} could not be read: {fault.strerror or fault}"


def viewer_script() -> tuple[bytes, str]:
    """draw.io's viewer, from the copy beside the packages or from the network once. The bytes and, where
    there are none, the line that says why."""
    if VIEWER.is_file():
        return VIEWER.read_bytes(), ""
    try:
        with urllib.request.urlopen(VIEWER_URL, timeout=30) as answer:
            body = answer.read()
    except (urllib.error.URLError, OSError, ValueError) as fault:
        return b"", (f"draw.io's viewer could not be fetched from {VIEWER_URL} ({fault}); the model is shown "
                     f"once this machine has reached it, and {DRAWIO} opens in draw.io meanwhile")
    try:
        VIEWER.parent.mkdir(parents=True, exist_ok=True)
        VIEWER.write_bytes(body)
    except OSError:
        pass  # served this once; kept next time the directory can be written
    return body, ""


def viewer_config(xml: str) -> str:
    """The attribute draw.io's viewer reads: the picture, and the controls a read-only timeline wants."""
    return json.dumps({"xml": xml, "nav": True, "resize": True, "toolbar": "zoom layers lightbox",
                       "lightbox": False, "highlight": "#0f6b6b", "border": 12})


def states_of(rows: list[dict[str, str]]) -> dict[str, str]:
    return {row["slice"]: row["state"] for row in rows}


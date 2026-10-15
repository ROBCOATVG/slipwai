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
import os
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


def titles(root: Path, feature: str) -> dict[str, str]:
    """What each slice is called, read off the split's own table — `| S01 Set up an account | …` — or its
    headings; the chart carries ids and nothing a person would say. Empty where there is no split yet."""
    page = root / "specs" / feature / "story-split.md"
    if not page.is_file():
        return {}
    text = page.read_text(encoding="utf-8", errors="replace")
    found: dict[str, str] = {}
    for slice_id, title in re.findall(r"^\*\*(S\d+)\s+([^*\n]+?)\*\*", text, re.MULTILINE):
        found.setdefault(slice_id, title.strip())
    for slice_id, title in re.findall(r"^\|\s*(S\d+)\s+([^|\n]+?)\s*\|", text, re.MULTILINE):
        found[slice_id] = title.strip()
    return found


def fleet_running(root: Path) -> bool:
    """Whether anything `fleet.py start` started is still alive: its pid files, each checked against the
    process table. No file is nothing started; a file whose pid is gone is a captain that has died."""
    running = root / ".slipwai/running"
    for pid_file in sorted(running.glob("*.pid")) if running.is_dir() else []:
        try:
            os.kill(int(pid_file.read_text(encoding="utf-8").strip()), 0)
            return True
        except (OSError, ValueError):
            continue
    return False


def folded(root: Path, feature: str = "") -> tuple[list[dict[str, str]], str]:
    """Every charted slice with its state, fairway, why, and marks — and a fault where the chart could not be
    read. Empty, and no fault, where there is no chart yet."""
    feature, result, fault = clearance_query(root, feature)
    states = result.get("states") if isinstance(result.get("states"), dict) else {}
    if fault or not states:
        return [], fault
    found, _ = fairways(root, harbour_log(root))
    named = titles(root, feature)
    rows: list[dict[str, str]] = []
    for slice_id, entry in states.items():
        state = CLEARANCE.get(str(entry.get("state", "")), "todo")
        row = {"slice": str(slice_id), "title": named.get(str(slice_id), ""), "feature": feature, "state": state,
               "why": str(entry.get("why", "")), "fairway": "", "clearance": str(entry.get("state", ""))}
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
    # Named, because the host fronts the file with a proxy that answers 403 to Python's default agent —
    # the same refusal a target's bootstrap script met on a self-hosted forge, for the same reason.
    request = urllib.request.Request(VIEWER_URL, headers={"User-Agent": "slipwai-board"})
    try:
        with urllib.request.urlopen(request, timeout=30) as answer:
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
    # Not responsive and not auto-fitted: both scale the picture to the canvas's width with a transform the
    # graph's own zoom knows nothing about, and a timeline fitted to its width is a line nobody can read.
    # The page fits the lanes to the canvas's height itself and hands the rest to the controls.
    return json.dumps({"xml": xml, "nav": True, "resize": False, "responsive": False, "auto-fit": False,
                       "center": False, "toolbar": "", "lightbox": False, "highlight": "#0f6b6b", "border": 12,
                       "zoom": 1})


#: Where the mock-up stage writes, under a feature, and the route the board serves it at.
MOCKUPS = "mockups"
MOCK_ROUTE = "/mockups/"


def mockups(root: Path, seat: str = "") -> list[dict[str, str]]:
    """Every wireframe the mock-up stage has written, by feature: its name, its title and where the board
    serves it. The title is the page's own `<title>`, with the stage's `Mock:` prefix taken off.

    `seat` goes on each address because these are shown in frames, and a frame is the one thing on the
    voyage the browser fetches without a script's help: unseated it would be served out of whatever
    directory the board was started in, which is another window's project inside this one's page.
    """
    specs = root / "specs"
    found: list[dict[str, str]] = []
    for page in sorted(specs.glob(f"*/{MOCKUPS}/*.html")) if specs.is_dir() else []:
        feature = page.parent.parent.name
        try:
            head = page.read_text(encoding="utf-8", errors="replace")[:4000]
        except OSError:
            continue
        match = re.search(r"<title>(.*?)</title>", head, re.IGNORECASE | re.DOTALL)
        title = re.sub(r"^\s*mock(-?up)?:\s*", "", match.group(1).strip(), flags=re.IGNORECASE) if match else page.stem
        found.append({"feature": feature, "name": page.name, "title": title or page.stem,
                      "href": f"{MOCK_ROUTE}{feature}/{page.name}" + (f"?seat={seat}" if seat else "")})
    return found


def mockup_file(root: Path, where: str) -> Path | None:
    """The file a `/mockups/<feature>/<name>` request names, or nothing where it names anything outside a
    feature's mockups directory — a path with `..` in it, a symlink out of the checkout, a sibling that is
    not a mock-up. The route serves a mock-up's own stylesheet and images too, which is why this is a
    directory and not one file."""
    feature, _, name = where.partition("/")
    if not feature or not name or not name.strip("/"):
        return None
    home = (root / "specs" / feature / MOCKUPS).resolve()
    try:
        path = (home / name).resolve()
    except OSError:
        return None
    if not path.is_relative_to(home) or not path.is_file() or not home.is_relative_to(root.resolve()):
        return None
    return path


def states_of(rows: list[dict[str, str]]) -> dict[str, str]:
    return {row["slice"]: row["state"] for row in rows}


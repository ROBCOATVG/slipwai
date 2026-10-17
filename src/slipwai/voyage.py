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

The screens are the design review's photographs, labelled by the same fold as the columns.
"""
# budget: 450 — the fold, the model, the mock-ups and the screenshots one voyage is read from
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import quote, unquote

from .assets import SLIPWAI
from .fleet import clearance_query, fairways, harbour_log
from .process_alive import alive

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
    """What each slice is called. The chart carries ids and nothing a person would say.

    Three places the split writes a name, and the candidates table is the one that matters: `| S10 |
    Appoint a moderator |` under a `Value` heading. The same cell (`| S01 Set up an account |`) and a bold
    heading are the older shapes. The slice graph is `| Slice | depends_on |`, so a second cell is only a
    name while the heading in force says `Value` — otherwise a slice is called after a dash.
    """
    page = root / "specs" / feature / "story-split.md"
    if not page.is_file():
        return {}
    text = page.read_text(encoding="utf-8", errors="replace")
    found: dict[str, str] = {}
    for slice_id, title in re.findall(r"^\*\*(S\d+)\s+([^*\n]+?)\*\*", text, re.MULTILINE):
        found.setdefault(slice_id, title.strip())
    for slice_id, title in re.findall(r"^\|\s*(S\d+)\s+([^|\n]+?)\s*\|", text, re.MULTILINE):
        found[slice_id] = title.strip()
    value = False
    for line in text.splitlines():
        if not line.startswith("|"):
            value = False
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells[:1] == ["Slice"]:
            value = len(cells) > 1 and cells[1] == "Value"
        elif value and len(cells) > 1 and re.fullmatch(r"S\d+", cells[0]) and cells[1] not in ("", "—", "-"):
            found[cells[0]] = cells[1]
    return found


def fleet_running(root: Path) -> bool:
    """Whether anything `fleet.py start` started is still alive: its pid files, each checked against the
    process table. No file is nothing started; a file whose pid is gone is a captain that has died."""
    running = root / ".slipwai/running"
    for pid_file in sorted(running.glob("*.pid")) if running.is_dir() else []:
        try:
            if alive(int(pid_file.read_text(encoding="utf-8").strip())):
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
#: The path segment that carries a window. A query is dropped by every relative address a mock-up then
#: asks for — its stylesheet, its script, the next frame — and a sandboxed frame does not send it back.
SEAT_PATH = "by"
_SEAT = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
#: The specification a feature is built from, and the route the board serves it at. Served at all because
#: Continue the build is a person's word that the specification is good, and a page that asks for that word
#: and gives no way to read the thing is asking somebody to agree to a file they have not opened.
SPEC = "spec.md"
SPEC_ROUTE = "/spec/"
#: Where the design review writes a screen it has looked at, and the route the board serves it at.
SLICES = "slices"
DESIGN = "design"
SCREEN_ROUTE = "/screens/"
#: Raster only. An SVG opened as its own page can carry a script, and a note beside a screenshot is not one.
IMAGES = frozenset({".png", ".jpg", ".jpeg", ".webp", ".gif"})


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
                      "href": mockup_href(feature, page.name, seat)})
    return found


def mockup_href(feature: str, name: str, seat: str = "") -> str:
    """Where the board serves one mock-up. The seat is a path segment, so the page's own files stay on it.

    Under the seat the address is the file's own path in the project, so a link the stage wrote for the file
    where it lies — `../spec.md`, `../../../docs/design/styles.css` — reaches the same file served.
    """
    where = f"specs/{feature}/{MOCKUPS}/{name}"
    if seat and _SEAT.fullmatch(seat):
        return f"{MOCK_ROUTE}{SEAT_PATH}/{quote(seat, safe='')}/{where}"
    return f"{MOCK_ROUTE}{where}"


def mockup_where(where: str) -> tuple[str, str]:
    """The seat a `/mockups/` remainder names, and the `<feature>/<name>` under it.

    An empty seat is the unseated form, which reads the directory the board was started in.
    """
    parts = where.split("/", 3)
    if (len(parts) == 4 and parts[0] == SEAT_PATH and _SEAT.fullmatch(unquote(parts[1]))
            and parts[2] and parts[3]):
        return unquote(parts[1]), f"{parts[2]}/{parts[3]}"
    return "", where


def mockup_file(root: Path, where: str) -> Path | None:
    """The file a `/mockups/<feature>/<name>` request names, or nothing where it names anything outside a
    feature's mockups directory — a path with `..` in it, a symlink out of the checkout, a sibling that is
    not a mock-up. The route serves a mock-up's own stylesheet and images too, which is why this is a
    directory and not one file.

    A remainder that starts `specs/` or `docs/` is a path in the project, which is the form `mockup_href`
    writes; see `design_file` for what that form may reach."""
    if where.partition("/")[0] in ("specs", "docs"):
        return design_file(root, where)
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


def design_file(root: Path, where: str) -> Path | None:
    """The file a project-relative `/mockups/` remainder names, where it is one a storyboard may point at: a
    feature's mock-ups, that feature's specification, or what the project was handed under `docs/design/`.

    The mock-up stage reads `docs/design/` and is told to follow it, so a storyboard links the stylesheet and
    the drawings there rather than copying them; refusing them is a storyboard with no styles and empty
    frames. Anything else in the project — its configuration, a slice's plan, the logs — stays refused, and
    the test is on the resolved path, so neither `..` nor a symlink reaches past it.
    """
    home = root.resolve()
    try:
        path = (home / unquote(where)).resolve()
    except OSError:
        return None
    if not path.is_file() or not path.is_relative_to(home):
        return None
    parts = path.relative_to(home).parts
    handed = len(parts) > 2 and parts[:2] == ("docs", "design")
    drawn = len(parts) > 3 and parts[0] == "specs" and parts[2] == MOCKUPS
    specified = len(parts) == 3 and parts[0] == "specs" and parts[2] == SPEC
    return path if handed or drawn or specified else None


def spec_file(root: Path, feature: str) -> Path | None:
    """The `specs/<feature>/spec.md` a `/spec/<feature>` request names, or nothing where it names anything
    else — a path with `..` in it, a symlink out of the checkout, a feature that has no specification.

    One file and not a directory, which is the difference between this and `mockup_file`: a mock-up is a
    page with its own stylesheet and images beside it, and a specification is a document.
    """
    if not feature or "/" in feature.strip("/"):
        return None
    home = (root / "specs").resolve()
    try:
        path = (home / feature.strip("/") / SPEC).resolve()
    except OSError:
        return None
    if not path.is_relative_to(home) or not path.is_file() or not home.is_relative_to(root.resolve()):
        return None
    return path


def states_of(rows: list[dict[str, str]]) -> dict[str, str]:
    return {row["slice"]: row["state"] for row in rows}


def screen_address(feature: str, slice_id: str, name: str, seat: str, stamp: int) -> str:
    """The address of one screenshot. `v` is the file's time, so a review that replaces it is a new picture
    rather than the one the browser kept."""
    path = "/".join(quote(part, safe="") for part in (feature, slice_id, name))
    query = [f"seat={quote(seat, safe='')}"] if seat else []
    query.append(f"v={stamp}")
    return f"{SCREEN_ROUTE}{path}?{'&'.join(query)}"


def screen_file(root: Path, where: str) -> Path | None:
    """The image a `/screens/<feature>/<slice>/<name>` request names, or nothing where it names anything
    else — a path with `..` in it, a symlink out of the checkout, a note or a drawing beside the picture.

    One directory and not the slice's whole record: the review's photographs live in `design/`, and a route
    that served the rest would be serving the slice's plan."""
    feature, _, rest = unquote(where).partition("/")
    slice_id, _, name = rest.partition("/")
    if not feature or not slice_id or not name or "/" in name or Path(name).suffix.lower() not in IMAGES:
        return None
    home = (root / "specs" / feature / SLICES / slice_id / DESIGN).resolve()
    try:
        path = (home / name).resolve()
    except OSError:
        return None
    if not path.is_relative_to(home) or not path.is_file() or not home.is_relative_to(root.resolve()):
        return None
    return path


def _shot_paths(root: Path) -> list[tuple[Path, str, str, str]]:
    """Every photograph the route would serve: the file, its feature, its slice and its name."""
    specs = root / "specs"
    found: list[tuple[Path, str, str, str]] = []
    if not specs.is_dir():
        return found
    for page in sorted(specs.glob(f"*/{SLICES}/*/{DESIGN}/*")):
        parts = page.relative_to(specs).parts
        if len(parts) != 5 or parts[1] != SLICES or parts[3] != DESIGN or page.suffix.lower() not in IMAGES:
            continue
        feature, slice_id, name = parts[0], parts[2], parts[4]
        if screen_file(root, f"{feature}/{slice_id}/{name}") is None:
            continue
        found.append((page, feature, slice_id, name))
    return found


def screens(root: Path, rows: list[dict[str, str]], seat: str = "") -> list[dict[str, str]]:
    """Every design-review screenshot, with the slice's standing on it.

    The review writes them under `specs/<feature>/slices/<id>/design/`. The standing is the voyage's own
    fold — done, working, waiting, to do — and a slice the chart has not got is to do, which is what a
    picture with no row is. The same slice id in two features is two slices."""
    known = {(str(row.get("feature", "")), str(row.get("slice", ""))): row for row in rows}
    found: list[dict[str, str]] = []
    for page, feature, slice_id, name in _shot_paths(root):
        row = known.get((feature, slice_id), {})
        state = str(row.get("state", "todo"))
        if state not in COLUMNS:
            state = "todo"
        try:
            stamp = page.stat().st_mtime_ns
        except OSError:
            continue
        found.append({"feature": feature, "slice": slice_id, "title": str(row.get("title", "")),
                      "state": state, "name": name,
                      "href": screen_address(feature, slice_id, name, seat, stamp)})
    return found


def shot_names(root: Path) -> list[str]:
    """What the poll's signature needs of the screenshots: each path and the time it was written, so a
    picture landing — or one replaced — is a page built out of different files."""
    named: list[str] = []
    for page, _, _, _ in _shot_paths(root):
        try:
            named.append(f"{page.relative_to(root / 'specs').as_posix()}:{page.stat().st_mtime_ns}")
        except OSError:
            continue
    return named


def running_app(root: Path) -> str:
    """Where the project's browser app is served, when `project.json` records a port for one.

    The gallery links it. It does not embed it: a dev server, a sign-in and a frame that refuses to be
    framed are three different ways an embedded app shows nothing, and a link still opens. Empty where
    there is no browser app, or the value in the port is not one."""
    try:
        document = json.loads((root / "project.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return ""
    deployables = document.get("deployables") if isinstance(document, dict) else None
    if not isinstance(deployables, dict):
        return ""
    for record in deployables.values():
        if not isinstance(record, dict) or record.get("kind") != "web":
            continue
        port = record.get("port")
        if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
            continue
        return f"http://localhost:{port}"
    return ""


def shape(root: Path, rows: list[dict[str, str]], fleet: dict, feature: str, made: bool) -> str:
    """What this page is *made of*, as one short line, so that a poll can tell a changed page from a
    changed strip.

    The strip repaints itself from `/voyage.json`, and for a while that was the whole of keeping this page
    current. It is not: the Open spec button, the storyboard, the screenshots, the model and the work cards
    are all rendered
    once, by the server, out of files that were not there yet. A window opened during the draft watched the
    specification land and showed nothing of it until somebody reloaded, which is the one thing a page that
    polls is supposed to save a person from.

    So the poll carries this as well, the page remembers the one it was drawn with, and a difference is a
    reload. A reload rather than a repaint because what changes here is which cards exist, and that is rare
    — a file appearing — where the strip's states change every few seconds. Every part below is a count, a
    name or an mtime: this is asked for as long as a window is open, so nothing here reads a file.
    """
    specs = root / "specs"
    drawn = sorted(page.relative_to(specs).as_posix()
                   for page in specs.glob(f"*/{MOCKUPS}/*.html")) if specs.is_dir() else []
    photographed = shot_names(root)
    picture = root / DRAWIO
    home = root / "docs/intake"
    intake = []
    if home.is_dir():
        for folder in sorted(path for path in home.iterdir() if path.is_dir() and not path.name.startswith(".")):
            flags = ""
            if (folder / "confirmed").is_file():
                flags += "c"
            if (folder / "specified.json").is_file():
                flags += "s"
            if (root / ".specify/assessments" / folder.name / "decision.md").is_file():
                flags += "d"
            intake.append(f"{folder.name}:{flags}")
    verdicts = sorted(f"{page.parent.parent.name}:{int(page.stat().st_mtime)}"
                      for page in specs.glob(f"*/{MOCKUPS}/mock-states.md")) if specs.is_dir() else []
    berths = [str(one.get("state", "")) for one in (fleet.get("berths") or []) if isinstance(one, dict)]
    return "|".join((feature, "".join(str(row["state"])[:1] for row in rows), ",".join(drawn),
                     ",".join(photographed), ",".join(verdicts),
                     str(int(picture.stat().st_mtime) if picture.is_file() else 0), ",".join(berths),
                     str(len(fleet.get("inbox") or [])), "f" if made else "", ",".join(intake)))

#!/usr/bin/env python3
"""What this project has already drawn or built, listed for the mock-up stage before it draws a feature.

`/mockups` drew each feature alone. The researcher was handed the specification, the domain notes and
`docs/design/`, so a second feature got a second storyboard holding only its own surfaces, in a look made up
for it, beside an app that already had a shell, tokens and thirty screens. And a project that crossed from
version 1 — a built app, and no `specs/<feature>/mockups/` anywhere — had no storyboard of what exists at all.

So the stage is handed a list, the way `surfaces.py` hands a session its budget, rather than told to go looking:

    python3 scripts/agents/existing.py 002-export            # print it
    python3 scripts/agents/existing.py 002-export --write    # and keep it as specs/002-export/mockups/existing.md
    python3 scripts/agents/existing.py 002-export --json     # the same, for a program

**What it reads, in the order the stage is told to read it.** Earlier features' `specs/*/mockups/` — the
surfaces and what `mock-states.md` says of each state. Each browser app `project.json` records (`kind: web`):
its screen previews under `screens/`, one page per state, grouped by surface; the routes its source names; its
own stylesheets under `src/styles/`. The event model's `ui` frames, each with its slice and that slice's
status. The design review's photographs. `docs/design.md`, and what a person handed over under `docs/design/`.

**What it says is evidence, not a verdict.** A preview, a route, a frame whose slice is `implemented`, a
photograph: each is listed as what it is and where, and the stage decides what to frame. It reads and never
changes the project, but for the one page `--write` keeps, which says the same thing for the same project.

**It says what each surface is, from that evidence** (`classified`). `built`: a preview, else a `ui` frame whose
slice is `implemented`, else a design-review photograph, else a route — in that order, and the first that
applies is named, with the page or photograph that shows the surface where one does. `planned`: an earlier
feature's surface with a state somebody approved and no evidence at all that it is built. Names are matched
across the sources by their words — a preview's file names, a frame's name, the component a route renders, a
route's last segment — and each row says what it matched, because a match by name is a reading and not a fact.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


def project_root(script: Path) -> Path:
    for candidate in script.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return script.parents[2]


ROOT = project_root(Path(__file__).resolve())
MOCKUPS = "mockups"
#: The page `--write` keeps, beside the research note it is the first input of.
PAGE = "existing.md"
NOT_A_SURFACE = ("storyboard.html", "index.html")
TITLE = re.compile(r"<title>(.*?)</title>", re.IGNORECASE | re.DOTALL)
SURFACE = re.compile(r"^##\s*Surface:\s*(?P<name>.+?)\s*$", re.MULTILINE)
STATE = re.compile(r"^-\s*(?P<state>.+?)\s*—\s*(?P<verdict>approved|parked|n/a)\b", re.MULTILINE)
#: A route as most routers spell it: `path="/x"` on an element, `path: '/x'` in a table.
ROUTE = re.compile(r"""\bpath\s*[=:]\s*\{?\s*["'`](/[^"'`\s]*)["'`]""")
SOURCE = (".tsx", ".jsx", ".ts", ".js", ".vue", ".svelte")
SHELL = re.compile(r"^(App|Layout|Shell|Root)\b|Layout\.|Shell\.", re.IGNORECASE)
IMAGES = (".png", ".jpg", ".jpeg", ".webp", ".gif")
#: What a storyboard says a surface is, on the frame or link that shows it; `drawn.py` on the board reads the same.
TAG = re.compile(r"<[a-zA-Z][^<>]*>")
KIND = re.compile(r"""\bdata-surface=["'](built|changed|new|planned)["']""", re.IGNORECASE)
#: The two kinds a storyboard frames and nobody is asked about: the project's own, and an earlier feature's.
FRAMED = ("built", "planned")
ELEMENT = re.compile(r"""\b(?:element|component|Component)\s*[=:]\s*\{?\s*<?\s*([A-Z][A-Za-z0-9]*)""")
WORD = re.compile(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|\d+")
#: What a frame or a component is called beside the surface's own name, and the words a title spends on grammar.
SUFFIX = frozenset({"screen", "form", "page", "panel", "control", "dialog", "view", "step", "route"})
SMALL = frozenset({"a", "an", "the", "your", "my", "of", "to", "with", "for", "is", "who", "this"})
TARGET = re.compile(r"""(?:src|href)=["']([^"'#?]+\.html)["']""", re.IGNORECASE)


def kinds(home: Path) -> dict[Path, str]:
    """Each page a feature's storyboard marks `built`, `planned`, `changed` or `new`, by its resolved path."""
    board = home / "storyboard.html"
    found: dict[Path, str] = {}
    if not board.is_file():
        return found
    for tag in TAG.findall(board.read_text(encoding="utf-8", errors="replace")):
        kind, target = KIND.search(tag), TARGET.search(tag)
        if kind and target:
            found.setdefault((home / target.group(1)).resolve(), kind.group(1).lower())
    return found


def title_of(page: Path) -> str:
    try:
        found = TITLE.search(page.read_text(encoding="utf-8", errors="replace")[:8192])
    except OSError:
        return page.stem
    plain = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", found.group(1))).strip() if found else ""
    return re.sub(r"^\s*mock(-?up)?:\s*", "", plain, flags=re.IGNORECASE) or page.stem


def storyboards(feature: str, root: Path) -> list[dict[str, Any]]:
    """Every other feature's mock-ups: its storyboard, each surface page, and each state's verdict."""
    found = []
    for home in sorted((root / "specs").glob(f"*/{MOCKUPS}")):
        pages = sorted(page for page in home.glob("*.html") if page.name not in NOT_A_SURFACE)
        if home.parent.name == feature or not (pages or (home / "storyboard.html").is_file()):
            continue
        states = home / "mock-states.md"
        text = states.read_text(encoding="utf-8", errors="replace") if states.is_file() else ""
        heads = list(SURFACE.finditer(text))
        said = {head.group("name"): [{"state": one.group("state"), "verdict": one.group("verdict")}
                                     for one in STATE.finditer(text[head.end():(heads[at + 1].start()
                                                               if at + 1 < len(heads) else len(text))])]
                for at, head in enumerate(heads)}
        board = home / "storyboard.html"
        found.append({"feature": home.parent.name, "storyboard": rel(board, root) if board.is_file() else "",
                      "stylesheet": rel(home / "mockups.css", root) if (home / "mockups.css").is_file() else "",
                      "surfaces": [{"name": (name := title_of(page).split("—")[-1].strip()),
                                    "page": rel(page, root), "states": said.get(name, [])} for page in pages]})
    return found


def rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def tracked(home: Path, root: Path) -> int | None:
    """How many files under `home` git holds, or `None` where this is not a checkout git can answer for."""
    try:
        done = subprocess.run(["git", "-C", str(root), "ls-files", "--", rel(home, root)],
                              capture_output=True, text=True, check=False, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    return None if done.returncode else sum(line.endswith(".html") for line in done.stdout.splitlines())


def previews(home: Path, root: Path) -> list[dict[str, Any]]:
    """The app's screen previews by surface. A preview is one state of one screen and its title says both —
    `Deal console — deals` — so the pages are grouped by what is before the dash."""
    found: dict[str, list[dict[str, str]]] = {}
    for page in sorted(home.glob("*.html")) if home.is_dir() else []:
        surface, dash, state = title_of(page).partition("—")
        found.setdefault(surface.strip(), []).append({"state": state.strip() if dash else "shown",
                                                      "page": rel(page, root)})
    return [{"name": name, "states": states} for name, states in found.items()]


def sources(app: Path) -> list[Path]:
    src = app / "src"
    return sorted(path for path in src.rglob("*") if path.suffix in SOURCE and path.is_file()
                  and "node_modules" not in path.parts and ".test." not in path.name
                  and ".spec." not in path.name) if src.is_dir() else []


def apps(root: Path) -> list[dict[str, Any]]:
    """Each browser app `project.json` records, with its look, its routes and its previews."""
    try:
        held = json.loads((root / "project.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    records = held.get("deployables") if isinstance(held, dict) else None
    found = []
    for name, record in sorted(records.items()) if isinstance(records, dict) else []:
        if not isinstance(record, dict) or record.get("kind") != "web" or not isinstance(record.get("path"), str):
            continue
        app = root / record["path"]
        files = sources(app)
        routes: list[dict[str, str]] = []
        renders: dict[str, str] = {}
        for path in files:
            text = path.read_text(encoding="utf-8", errors="replace")
            for at in ROUTE.finditer(text):
                route = at.group(1)
                if route not in [one["path"] for one in routes]:
                    routes.append({"path": route, "file": rel(path, root)})
                    # The component is on the route's own tag or row: read up to the next route, no further.
                    after = text[at.end():at.end() + 240]
                    after = after[:nearer.start()] if (nearer := ROUTE.search(after)) else after
                    renders[route] = named.group(1) if (named := ELEMENT.search(after)) else ""
        screens = app / "screens"
        found.append({"name": name, "path": record["path"],
                      "styles": sorted(rel(sheet, root) for sheet in (app / "src/styles").glob("*.css")),
                      "shell": [rel(path, root) for path in files
                                if SHELL.search(path.name) and len(path.relative_to(app).parts) <= 3],
                      "routes": routes, "renders": renders, "screens": rel(screens, root) if screens.is_dir() else "",
                      "committed": tracked(screens, root) if screens.is_dir() else None,
                      "previews": previews(screens, root)})
    return found


def frames(root: Path) -> tuple[list[dict[str, Any]], str]:
    """The event model's `ui` frames, each with its slice and the slice's status — and why not, where the model
    is there and could not be read."""
    model = root / "docs/event-model/model.yaml"
    if not model.is_file():
        return [], ""
    try:
        import yaml  # type: ignore[import-not-found]
        held = yaml.safe_load(model.read_text(encoding="utf-8"))
    except ImportError:
        return [], "PyYAML is not installed here, so its `ui` frames are not listed: read the file"
    except Exception as fault:  # noqa: BLE001 — a model that does not parse is the model gate's to refuse
        return [], f"it could not be read ({type(fault).__name__}), so its `ui` frames are not listed"
    found = []
    for one in held.get("slices", []) if isinstance(held, dict) and isinstance(held.get("slices"), list) else []:
        for frame in one.get("frames", []) if isinstance(one, dict) and isinstance(one.get("frames"), list) else []:
            if isinstance(frame, dict) and frame.get("type") == "ui":
                shown = [{"state": str(mock.get("state", "")), "at": str(mock.get("at", ""))}
                         for mock in frame.get("mockups") or [] if isinstance(mock, dict)]
                found.append({"name": str(frame.get("name", "")), "slice": str(one.get("id", "")),
                              "status": str(one.get("status", "")), "mockups": shown,
                              "code": [str(path) for path in one.get("code") or [] if isinstance(path, str)]})
    return found, ""


def words(name: str) -> tuple[str, ...]:
    """A name as its words, lower-case and singular, however it is spelled: `NewWorkspaceForm`,
    `new-workspace`, `New workspace` and `/workspaces/new` are compared by these."""
    return tuple(word.lower().rstrip("s") or word.lower() for word in WORD.findall(name))


def key(name: str) -> tuple[str, ...]:
    """The words that name the surface: without a title's grammar, and without `Screen` or `Form` at the end."""
    found = [word for word in words(name) if word not in SMALL]
    while len(found) > 1 and found[-1] in SUFFIX:
        found.pop()
    return tuple(found)


def shared(stems: list[tuple[str, ...]]) -> tuple[str, ...]:
    """The words every one of a surface's preview files begins with: `deal-console` of `deal-console-empty`."""
    first = stems[0] if stems else ()
    size = next((at for at in range(len(first)) if any(stem[:at + 1] != first[:at + 1] for stem in stems)), len(first))
    return first[:size]


def matched(named: tuple[str, ...], rows: list[dict[str, Any]], within: bool = False) -> dict[str, Any] | None:
    """The surface a name belongs to, or `None`: the one called exactly that, else the one whose preview files
    begin with it — the most general of those — else, for a route's last segment (`within`), one whose files
    have it somewhere in their name. A name of no words matches nothing."""
    if not named:
        return None
    for row in rows:
        if named in row["keys"]:
            return row
    begins = [row for row in rows if any(stem[:len(named)] == named for stem in row["stems"])]
    if not begins and within:
        begins = [row for row in rows if any(stem[at:at + len(named)] == named for stem in row["stems"]
                                             for at in range(len(stem)))]
    return min(begins, key=lambda row: (len(row["keys"][0]) if row["keys"] else 0, row["name"])) if begins else None


def classified(earlier: list[dict[str, Any]], browser: list[dict[str, Any]], modelled: list[dict[str, Any]],
               photographs: list[str], root: Path) -> list[dict[str, Any]]:
    """Every surface the evidence names, with what it is — `built` or `planned` — the first evidence in the
    order preview, implemented `ui` frame, photograph, route, and its picture: the page or photograph that
    shows it, or `""` where nothing does."""
    rows: list[dict[str, Any]] = []

    def row(name: str, evidence: str, picture: str, names: list[str], stems: list[str], kind: str = "built",
            **more: Any) -> dict[str, Any]:
        rows.append({"name": name, "kind": kind, "evidence": evidence, "picture": picture, "routes": [],
                     "frames": [], "approved": [], **more, "stems": [words(stem) for stem in stems],
                     "keys": [one for one in dict.fromkeys(key(name) for name in names) if one]})
        return rows[-1]

    for app in browser:
        for one in app["previews"]:
            stems = [Path(state["page"]).stem for state in one["states"]]
            made = row(one["name"], "preview", one["states"][0]["page"], [one["name"]], stems,
                       states=len(one["states"]), pages=[state["page"] for state in one["states"]])
            made["keys"].insert(0, shared(made["stems"]))
    previewed = list(rows)

    def shown(path: str, renders: str) -> dict[str, Any] | None:
        """The previewed surface a route shows: by the component it renders, else by its last literal segment."""
        last = [part for part in path.split("/") if part and part[0] not in ":*["][-1:]
        return matched(key(renders), previewed) or matched(words(last[0]) if last else (), previewed, within=True)

    routed = {renders: one for app in browser for path, renders in app.get("renders", {}).items()
              if renders and (one := shown(path, renders)) is not None}
    shot: dict[str, list[str]] = {}
    for path in photographs:  # specs/<feature>/slices/<slice>/design/<photograph>
        shot.setdefault(path.split("/")[3], []).append(path)
    by_name: dict[str, list[dict[str, Any]]] = {}
    for frame in modelled:
        by_name.setdefault(frame["name"], []).append(frame)
    for name, group in by_name.items():
        drawn = [mock["at"] for frame in group for mock in frame["mockups"] if (root / mock["at"]).is_file()]
        seen = [path for frame in group for path in shot.get(frame["slice"], [])]
        implemented = any(frame["status"] == "implemented" for frame in group)
        said = [f"{name} ({', '.join(frame['slice'] + ' ' + (frame['status'] or 'no status') for frame in group)})"]
        found = next((one for one in previewed if {Path(at).stem for frame in group for at in
                                                   (mock["at"] for mock in frame["mockups"])}
                      & {Path(page).stem for page in one["pages"]}), None) or matched(key(name), previewed)
        # Else by the slice's own `code`: the route component it names, and the previews that route shows.
        linked = [found] if found is not None else list({id(one): one for frame in group for path in frame["code"]
                                                         if (one := routed.get(Path(path).stem))}.values())
        for one in linked:
            one["frames"] += said
        if linked:
            continue
        if implemented or seen:  # a frame nobody built and nobody photographed is not evidence of anything
            row(name, "frame" if implemented else "photograph", (drawn or seen or [""])[0], [name], [])["frames"] += said
    for app in browser:
        for route in app["routes"]:
            renders = app.get("renders", {}).get(route["path"], "")
            found = shown(route["path"], renders) or matched(key(renders), rows)
            if found is None:
                found = row(route["path"], "route", "", [renders] if renders else [], [], file=route["file"])
            found["routes"].append(route["path"] + (f" ({renders})" if renders else ""))
    for one in earlier:
        for surface in one["surfaces"]:
            agreed = [state["state"] for state in surface["states"] if state["verdict"] == "approved"]
            found = matched(key(surface["name"]), rows) or matched(words(Path(surface["page"]).stem), rows)
            if found is not None and found["kind"] == "built":
                found["approved"].append(f"{one['feature']}: {surface['page']}")
            elif found is None and agreed:  # approved there, and nothing here says anybody built it
                row(surface["name"], "approved", surface["page"], [surface["name"]], [Path(surface["page"]).stem],
                    kind="planned", feature=one["feature"], states=len(agreed))
    return [{name: value for name, value in one.items() if name not in ("stems", "keys", "pages")} for one in rows]


def counted(surfaces: list[dict[str, Any]]) -> dict[str, int]:
    """How many of each: built, how many of those have no picture, and planned."""
    return {"built": sum(one["kind"] == "built" for one in surfaces),
            "unseen": sum(one["kind"] == "built" and not one["picture"] for one in surfaces),
            "planned": sum(one["kind"] == "planned" for one in surfaces)}


def listing(feature: str, root: Path = ROOT) -> dict[str, Any]:
    """Everything the stage is handed, and the two things it follows from it: whose look, and what the
    storyboard is made from."""
    earlier, browser = storyboards(feature, root), apps(root)
    modelled, unread = frames(root)
    handed = sorted(rel(path, root) for path in (root / "docs/design").rglob("*") if path.is_file()) \
        if (root / "docs/design").is_dir() else []
    photographs = sorted(rel(path, root) for path in (root / "specs").glob("*/slices/*/design/*")
                         if path.suffix.lower() in IMAGES)
    styles = [sheet for app in browser for sheet in app["styles"]]
    kept = [one["stylesheet"] for one in earlier if one["stylesheet"]]
    look = ({"follow": "handed", "files": handed} if handed else {"follow": "app", "files": styles} if styles
            else {"follow": "earlier", "files": kept} if kept else {"follow": "proposed", "files": []})
    built = any(app["previews"] or app["routes"] for app in browser) or bool(photographs) \
        or any(frame["status"] == "implemented" for frame in modelled)
    surfaces = classified(earlier, browser, modelled, photographs, root)
    return {"feature": feature, "storyboards": earlier, "apps": browser, "frames": modelled, "model": unread,
            "surfaces": surfaces, "counts": counted(surfaces),
            "photographs": photographs, "design": "docs/design.md" if (root / "docs/design.md").is_file() else "",
            "handed": handed, "look": look,
            "storyboard": "extend" if earlier else "from-what-exists" if built else "first"}


LOOK = {"handed": "what a person handed over under docs/design/ — follow it",
        "app": "the app's own — every new surface links these stylesheets and sits in the app's shell",
        "earlier": "the look an earlier feature's storyboard set — link its stylesheet; do not propose a second",
        "proposed": "nothing to follow — set a short proposed look, as /mockups says"}
STORYBOARD = {"extend": "this project has a storyboard — frame its surfaces and draw this feature into the flow",
              "from-what-exists": "this project has built surfaces and no storyboard — make one from what exists, "
                                  "with this feature's surfaces in it",
              "first": "nothing is drawn or built yet — this is the project's first storyboard"}


EVIDENCE = {"preview": "a preview", "frame": "an implemented `ui` frame", "photograph": "a design-review photograph",
            "route": "a route alone", "approved": "approved, not built"}


def surfaces_said(surfaces: list[dict[str, Any]]) -> list[str]:
    """What each surface is, one row each: the word, the first evidence for it, and the picture to frame."""
    if not surfaces:
        return []
    counts = counted(surfaces)
    out = ["## What each surface is", "",
           f"{counts['built']} built, {counts['unseen']} of them with no picture; {counts['planned']} planned. "
           "Matched by name across the sources, so each row says what it matched: read it as evidence.", ""]
    for one in surfaces:
        unseen = one["kind"] == "built" and not one["picture"]
        rest = [f"route {route}" for route in one["routes"]] + [f"frame {frame}" for frame in one["frames"]] \
            + [f"approved for {approved}" for approved in one["approved"]]
        if one["kind"] == "planned":
            shows = (f"approved for {one['feature']} ({one['states']} state(s)) and nothing here says it is built: "
                     f"frame {one['picture']}")
        elif unseen:
            shows = f"{EVIDENCE[one['evidence']]}, and nothing shows how it looks"
        else:
            shows = f"{EVIDENCE[one['evidence']]}: {one['picture']}" \
                + (f" ({one['states']} state(s))" if one.get("states") else "")
        out.append(f"- {one['kind']}{', no picture' if unseen else ''} — {one['name']} — {shows}"
                   + (f"; {'; '.join(rest)}" if rest else ""))
    return [*out, ""]


def said(found: dict[str, Any]) -> str:
    """The list as the page the stage reads: every source, where it is, and what it is evidence of."""
    out = [f"# What exists, for {found['feature']}", "",
           "Written by `scripts/agents/existing.py`; `/mockups` reads it before it draws. Evidence, not a verdict.",
           "", f"- **Look:** {LOOK[found['look']['follow']]}"
               + (f": {', '.join(found['look']['files'][:6])}" if found["look"]["files"] else "") + ".",
           f"- **Storyboard:** {STORYBOARD[found['storyboard']]}.",
           '- **Marking:** frame what is listed here where it lies, `data-surface="built"` — or '
           '`data-surface="planned"` where it is approved for an earlier feature and not built; draw what this '
           'feature changes or adds as a page of its own, `data-surface="changed"` or `data-surface="new"`.', ""]
    out += surfaces_said(found.get("surfaces", []))
    for one in found["storyboards"]:
        out += [f"## Earlier feature {one['feature']}", "",
                f"Storyboard: {one['storyboard'] or 'none; its surface pages are below'}", ""]
        out += [f"- {surface['name']} — {surface['page']}"
                + (" — " + ", ".join(f"{state['state']} ({state['verdict']})" for state in surface["states"])
                   if surface["states"] else " — no verdict recorded") for surface in one["surfaces"]] + [""]
    for app in found["apps"]:
        committed = ("" if app["committed"] is None else f", {app['committed']} committed")
        out += [f"## Browser app {app['name']} ({app['path']})", "",
                f"- Stylesheets: {', '.join(app['styles']) or 'none under src/styles/'}",
                f"- Shell: {', '.join(app['shell']) or 'not found by name; read docs/design.md'}",
                f"- Routes: {', '.join(route['path'] for route in app['routes']) or 'none it could read'}",
                f"- Previews: {sum(len(one['states']) for one in app['previews'])} page(s) of "
                f"{len(app['previews'])} surface(s) under {app['screens'] + '/' if app['screens'] else 'no screens/'}"
                f"{committed}", ""]
        out += [f"  - {one['name']} — " + ", ".join(f"{state['state']} ({Path(state['page']).name})"
                                                    for state in one["states"]) for one in app["previews"]] + [""]
    if found["frames"] or found["model"]:
        out += ["## Event model (docs/event-model/model.yaml)", ""] + ([found["model"], ""] if found["model"] else [])
        out += [f"- {frame['name']} — {frame['slice']}, {frame['status'] or 'no status'}"
                + (f" — {len(frame['mockups'])} mock-up(s): " + ", ".join(mock["at"] for mock in frame["mockups"][:3])
                   + (" …" if len(frame["mockups"]) > 3 else "") if frame["mockups"] else "")
                for frame in found["frames"]] + [""]
    out += ["## Design", "", f"- docs/design.md: {'there' if found['design'] else 'none'}",
            f"- docs/design/: {', '.join(found['handed'][:12]) or 'nothing handed over'}",
            f"- Design-review photographs: {len(found['photographs'])}"
            + (f" under {', '.join(sorted({str(Path(one).parent) for one in found['photographs']})[:6])}"
               if found["photographs"] else ""), ""]
    return "\n".join(out)


def write(feature: str, root: Path = ROOT) -> Path:
    """Keep the list beside the research note it is the first input of, and answer where."""
    path = root / "specs" / feature / MOCKUPS / PAGE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(said(listing(feature, root)), encoding="utf-8")
    return path


def main(argv: list[str]) -> int:
    named = [one for one in argv if not one.startswith("--")]
    specs = sorted((ROOT / "specs").glob("*/spec.md"))
    feature = named[0] if named else (specs[0].parent.name if specs else "")
    if not feature or not (ROOT / "specs" / feature / "spec.md").is_file():
        has = ", ".join(path.parent.name for path in specs) or "no specification yet"
        print(f"existing: {feature or 'the feature'} has no specification here; this project has {has}. "
              f"Run: python3 scripts/agents/existing.py <feature>", file=sys.stderr)
        return 2
    if "--json" in argv:
        print(json.dumps(listing(feature), indent=2))
        return 0
    if "--write" in argv:
        print(f"existing: wrote {rel(write(feature), ROOT)}")
    print(said(listing(feature)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

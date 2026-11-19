#!/usr/bin/env python3
"""Hold the split's surfaces to what a person actually approved, in both directions.

The mock-up review draws a feature's surfaces, storyboards them, and stops for a person to approve each
state one at a time into `specs/<feature>/mockups/mock-states.md`. The split then says which of those states
each slice delivers. Neither half is worth much without this gate, because both failures are silent.

**A slice that names a state nobody approved** is a slice built against something that was never agreed —
either a `parked` state, which is a question still open, or one that is in the file nowhere at all, which is
one nobody has seen. In version 1 the first sight of a screen was the demo of the slice that built it, and
this is that failure arriving through the split instead.

**An approved state no slice names** is the other direction, and it is the one nobody would otherwise
notice. A person looked at a drawing, said yes to it, and the split quietly did not carry it. Afterwards an
unbuilt surface looks exactly like a surface nobody asked for: there is no error, no gap in the tests, and
nothing to find until somebody goes looking for a thing they remember agreeing to.

**A feature with no surfaces is a written answer**, not an absence. `mock-states.md` holding `surfaces:
none` says the question was asked — a migration, an integration, a scheduled job — and every slice then
leaves the column empty. A feature with no `mock-states.md` at all has not run the stage, which is the
mock-up review rung's business rather than this gate's, so it passes here and says so.

**A built surface has no verdict, and is owed none.** A further feature's storyboard frames what the project
already has, marked `data-surface="built"`, so a reader sees one flow; the verdict covers what the feature
changes and adds, and `mock-states.md` carries a `<!-- built: … -->` line for each built surface instead of a
block. Nothing here asks after those. A slice that *names* one is still refused, and told why: it was shown,
not put up for a verdict, so nothing about it was approved to build.

**A planned surface is the same, for another reason.** `data-surface="planned"` is a surface an earlier feature
had approved and nobody has built yet, framed here so the flow reads whole; its line is `<!-- planned: … -->`.
Its verdict was given under the earlier feature and the slice that delivers it is that feature's, so a slice of
this feature that names it is refused too, and told which of the two it meant.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path


def project_root(script: Path) -> Path:
    for candidate in script.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return script.parents[1]


ROOT = project_root(Path(__file__).resolve())
SPECS = ROOT / "specs"
#: A surface's heading in `mock-states.md`, and one of its states beneath it.
SURFACE = re.compile(r"^##\s*Surface:\s*(?P<name>.+?)\s*$", re.MULTILINE)
STATE = re.compile(r"^-\s*(?P<state>.+?)\s*—\s*(?P<verdict>approved|parked|n/a)\b", re.MULTILINE)
#: What a slice names in the split's *Surfaces and states* column: `<surface> · <state>`, several per cell
#: separated by `;`. The middle dot is the separator everywhere else in this toolkit's tables.
PAIR = re.compile(r"^(?P<surface>.+?)\s*·\s*(?P<state>.+?)$")
#: A surface the storyboard framed as built, as the board writes it: its page's title, whole, and where it is.
BUILT = re.compile(r"^<!-- built: (?P<title>.+) — (?P<page>\S+) \(", re.MULTILINE)
#: And one it framed as planned: approved for an earlier feature, not built yet, and not this feature's to deliver.
PLANNED = re.compile(r"^<!-- planned: (?P<title>.+) — (?P<page>\S+) \(", re.MULTILINE)
NONE = "surfaces: none"
FIX = "python3 scripts/check-surfaces.py"


def approved(text: str) -> dict[str, set[str]] | None:
    """Each surface against the states a person approved, or `None` where the feature has no surfaces."""
    if NONE in text:
        return None
    found: dict[str, set[str]] = {}
    headings = list(SURFACE.finditer(text))
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        body = text[heading.end():end]
        found[heading.group("name")] = {
            state.group("state") for state in STATE.finditer(body) if state.group("verdict") == "approved"
        }
    return found


def every_state(text: str) -> dict[str, dict[str, str]]:
    """Each surface against every state and its verdict, so a refusal can say *why* one is not approved."""
    found: dict[str, dict[str, str]] = {}
    headings = list(SURFACE.finditer(text))
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        body = text[heading.end():end]
        found[heading.group("name")] = {s.group("state"): s.group("verdict") for s in STATE.finditer(body)}
    return found


def built(text: str, lines: re.Pattern[str] = BUILT) -> dict[str, str]:
    """Every name a built surface answers to — its page's title, and each half of `<surface> — <state>` —
    against the page that shows it. Only ever read to say why a slice may not name one. With `PLANNED`, the
    same of the surfaces framed as planned."""
    found: dict[str, str] = {}
    for line in lines.finditer(text):
        for name in (line.group("title"), *line.group("title").split(" — ")):
            found.setdefault(name.strip(), line.group("page"))
    return found


def delivered(split: str) -> dict[str, list[tuple[str, str]]]:
    """Each slice against the `<surface> · <state>` pairs its row names."""
    rows: dict[str, list[tuple[str, str]]] = {}
    column = None
    for line in split.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if column is None:
            if any(cell.lower().startswith("surfaces and states") for cell in cells):
                column = next(i for i, cell in enumerate(cells) if cell.lower().startswith("surfaces and states"))
            continue
        if len(cells) <= column or set("".join(cells)) <= set("-: "):
            continue
        name = cells[0]
        if not name or name.startswith("...") or name.lower() == "slice":
            continue
        pairs = []
        for part in cells[column].split(";"):
            found = PAIR.match(part.strip())
            if found:
                pairs.append((found.group("surface").strip(), found.group("state").strip()))
        rows[name] = pairs
    return rows


def faults(states: str, split: str, where: str) -> list[str]:
    allowed = approved(states)
    if allowed is None:
        named = {pair for pairs in delivered(split).values() for pair in pairs}
        return [f"{where}: `{NONE}` was written down and the split still names "
                f"{', '.join(f'{s} · {t}' for s, t in sorted(named))}. One of the two is wrong, and it is a "
                f"question for the mock-up review rather than a thing to resolve here"] if named else []
    verdicts = every_state(states)
    standing, coming = built(states), built(states, PLANNED)
    found: list[str] = []
    claimed: dict[tuple[str, str], list[str]] = {}
    for slice_id, pairs in delivered(split).items():
        for surface, state in pairs:
            claimed.setdefault((surface, state), []).append(slice_id)
            if surface not in allowed and surface in standing:
                found.append(f"{where}: {slice_id} delivers `{surface} · {state}` and that surface is shown as "
                             f"built ({standing[surface]}): it was framed for the flow and never put up for a "
                             f"verdict. Where this feature changes it, draw the change as a page of its own, "
                             f'mark it `data-surface="changed"` in the storyboard and get its verdict')
            elif surface not in allowed and surface in coming:
                found.append(f"{where}: {slice_id} delivers `{surface} · {state}` and that surface is shown as "
                             f"planned ({coming[surface]}): an earlier feature had it approved and has not built "
                             f"it, so the slice that delivers it is that feature's. Where this feature changes "
                             f'it, draw the change as a page of its own, mark it `data-surface="changed"` in '
                             f"the storyboard and get its verdict")
            elif surface not in allowed:
                found.append(f"{where}: {slice_id} delivers `{surface} · {state}` and no surface of that "
                             f"name is in mock-states.md. Nobody has seen it")
            elif state not in allowed[surface]:
                verdict = verdicts.get(surface, {}).get(state)
                why = (f"it is `{verdict}` there" if verdict else "it is not in that surface's states at all")
                found.append(f"{where}: {slice_id} delivers `{surface} · {state}` and {why}. A slice builds "
                             f"what a person approved, and a parked state is a question still open")
    for (surface, state), by in sorted(claimed.items()):
        if len(by) > 1:
            found.append(f"{where}: `{surface} · {state}` is delivered by {' and '.join(sorted(by))}. "
                         f"One state is one slice's, or neither slice owns it")
    for surface, states_of in sorted(allowed.items()):
        for state in sorted(states_of):
            if (surface, state) not in claimed:
                found.append(f"{where}: `{surface} · {state}` was approved and no slice delivers it. An "
                             f"unbuilt surface looks exactly like a surface nobody asked for")
    return found


def main() -> int:
    found: list[str] = []
    checked = 0
    for states in sorted(SPECS.glob("*/mockups/mock-states.md")) if SPECS.is_dir() else []:
        feature = states.parent.parent
        split = feature / "story-split.md"
        if not split.is_file():
            continue
        checked += 1
        found.extend(faults(states.read_text(encoding="utf-8"), split.read_text(encoding="utf-8"),
                            split.relative_to(ROOT).as_posix()))
    if found:
        print("check-surfaces: the split and the approved states disagree\n", file=sys.stderr)
        for fault in sorted(set(found)):
            print(f"  {fault}", file=sys.stderr)
        print(f"\nRun: {FIX}", file=sys.stderr)
        return 1
    if not checked:
        print("check-surfaces: no feature has both a mock-states.md and a split yet; nothing to hold")
        return 0
    print(f"check-surfaces: {checked} split(s) deliver every approved state, and only approved states")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

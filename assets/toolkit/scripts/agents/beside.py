#!/usr/bin/env python3
"""Which of a fairway's slices may run beside which: the split's `parallel_ok_with`, worked out and written.

A split stage with nobody present wrote `—` in the `parallel_ok_with` column of every row of a thirty-eight
slice fairway, because the template offered `—` for "none" in the column beside it. `clearance.py` then read
`—` there as *runs beside nothing*, and the fairway ran one slice at a time all night with three boilers lit
and the session the other fairway freed sitting idle. Nothing was written down to say anyone chose it.

`—` now means the same in both columns — nothing declared — and *runs beside nothing* is the word `alone`.
This is the other half: the column filled from evidence rather than left as a placeholder, and the choice
written as a decision a person can review, the way the split's order is.

**What two slices collide on**, read from what is written before any code exists:

- **the same stream** — `stream` on each slice's block in `docs/event-model/model.yaml`. Two slices appending
  to one aggregate's stream decide against one history, and their tests seed the same events;
- **the same screen** — a mockup path under a slice's frames in the model, or a surface in the split's
  *Surfaces and states* column. One screen built by two slices at once is one file edited twice;
- **the same file** — `code` on a slice's block, once a slice has it. A file more than half of a fairway's
  slices name is a seam every slice adds a line to — the composition root, the stylesheet — and is resolved
  in split order at merge, as `check-slice-scope` allows; it is named in the decision and is not a collision.

A slice is listed beside every sibling in its fairway, not yet merged, that it collides with on none of
those; one listed beside none is written `alone`. A merged slice keeps its row as written. Slices in two
fairways are never compared: a fairway's captain checks the graph only against its own slices in flight.

`python3 scripts/agents/beside.py --fill [--feature <f>]` writes it; `--check` prints what `check-chart`
refuses. Standalone, as everything beside it: a generated project has no slipwai to import.
"""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import clearance  # noqa: E402

#: Past this share of a fairway's slices naming one file, the file is a seam everyone adds to, not a collision.
SEAM_SHARE = 0.5
HEADER = "| Slice | depends_on | parallel_ok_with | Notes |\n|---|---|---|---|"
SURFACES = "surfaces and states"


def model_blocks() -> dict[str, dict]:
    """Each slice's block in the event model, by id; empty off the event profile."""
    model = clearance.ROOT / "docs/event-model/model.yaml"
    if not model.is_file():
        return {}
    try:
        loaded = clearance.load_yaml(model.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 - a model that will not parse is `check-model`'s to refuse
        return {}
    items = loaded.get("slices") if isinstance(loaded, dict) else None
    return {str(item.get("id")): item for item in items or [] if isinstance(item, dict) and item.get("id")}


def surfaces(feature: str, known: list[str]) -> dict[str, set[str]]:
    """The surfaces each slice names in the split's *Surfaces and states* column: `<surface> · <state>`, `;`
    between pairs, as `check-surfaces` reads it."""
    split = clearance.SPECS / feature / "story-split.md"
    if not split.is_file():
        return {}
    found: dict[str, set[str]] = {}
    column = -1
    for line in split.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip().startswith("|"):
            column = -1 if not line.strip() or line.startswith("#") else column
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        lowered = [cell.lower() for cell in cells]
        if SURFACES in lowered:
            column = lowered.index(SURFACES)
            continue
        if column < 0 or column >= len(cells) or set(cells[0]) <= set("-: "):
            continue
        named = {pair.split("·")[0].strip().strip("`").lower() for pair in cells[column].split(";")}
        named -= {"", "—", "-", "none", "n/a"}
        for slice_id in clearance.ids_in(cells[0], known, []):
            found.setdefault(slice_id, set()).update(named)
    return found


def touches(charted: dict, feature: str) -> dict[str, set[tuple[str, str]]]:
    """Everything each slice of this feature names that a sibling could collide on, as (kind, name)."""
    known = [str(one) for one in (charted.get("slices") or {})]
    blocks, screens = model_blocks(), surfaces(feature, known)
    found: dict[str, set[tuple[str, str]]] = {}
    for slice_id in known:
        block = blocks.get(slice_id) or {}
        mine: set[tuple[str, str]] = set()
        if block.get("stream"):
            mine.add(("stream", str(block["stream"])))
        for frame in block.get("frames") or []:
            for mockup in (frame.get("mockups") or []) if isinstance(frame, dict) else []:
                if isinstance(mockup, dict) and mockup.get("at"):
                    mine.add(("screen", str(mockup["at"])))
        for path in block.get("code") or []:
            mine.add(("file", str(path)))
        mine.update(("screen", name) for name in screens.get(slice_id, set()))
        found[slice_id] = mine
    return found


def seams(touched: dict[str, set[tuple[str, str]]], mine: list[str]) -> set[tuple[str, str]]:
    """The files more than `SEAM_SHARE` of these slices name: added to by every slice, merged in order."""
    naming = [one for one in mine if any(kind == "file" for kind, _ in touched.get(one, set()))]
    counts: dict[tuple[str, str], int] = {}
    for one in naming:
        for touch in touched.get(one, set()):
            if touch[0] == "file":
                counts[touch] = counts.get(touch, 0) + 1
    return {touch for touch, count in counts.items() if len(naming) > 1 and count > SEAM_SHARE * len(naming)}


def worked_out(charted: dict, feature: str, finished: set[str]) -> tuple[dict[str, set[str] | None],
                                                                        dict[str, dict[str, list[str]]], set]:
    """(each unfinished slice's siblings it may run beside, or None for one already finished; for each slice,
    each sibling kept apart and what they share; the seams set aside as not collisions)."""
    slices = charted.get("slices") or {}
    home = clearance.feature_of(charted)
    own = [str(one) for one in slices if clearance.feature_of_slice(str(one), charted, home) == feature]
    touched = touches(charted, feature)
    beside: dict[str, set[str] | None] = {}
    apart: dict[str, dict[str, list[str]]] = {}
    set_aside: set[tuple[str, str]] = set()
    fairway_of = {str(one): str((body or {}).get("fairway", "")) for one, body in slices.items()}
    for fairway in dict.fromkeys(fairway_of[one] for one in own):
        mine = [one for one in own if fairway_of[one] == fairway]
        seam = seams(touched, mine)
        set_aside |= seam
        open_ = [one for one in mine if one not in finished]
        for one in mine:
            if one in finished:
                beside[one] = None
                continue
            beside[one] = set()
            for other in open_:
                if other == one:
                    continue
                shared = sorted(f"{kind} `{name}`" for kind, name in (touched[one] & touched[other]) - seam)
                if shared:
                    apart.setdefault(one, {})[other] = shared
                else:
                    beside[one].add(other)  # type: ignore[union-attr]
    return beside, apart, set_aside


def rendered(charted: dict, feature: str, beside: dict[str, set[str] | None],
             apart: dict[str, dict[str, list[str]]]) -> list[str]:
    """The table's rows, one slice each, in chart order: its own `depends_on`, the siblings it runs beside or
    `alone`, and its note with what keeps it apart where something does."""
    rows = {one: row for row in clearance.graph_rows(charted) if row.feature == feature for one in row.slices}
    order = [one for one in (str(s) for s in charted.get("slices") or {}) if one in beside]
    lines = []
    for one in order:
        row = rows.get(one)
        deps = ", ".join(dep for dep in (row.depends if row else []) if dep != one) or "—"
        allowed = beside[one]
        if allowed is None:
            cell = row.cells[2] if row and len(row.cells) > 2 else "—"
        else:
            cell = ", ".join(other for other in order if other in allowed) or clearance.ALONE
        note = (row.cells[3] if row and len(row.cells) > 3 else "").strip()
        kept = apart.get(one) or {}
        if kept and allowed is not None:
            why = "; ".join(f"not beside {other} (both touch {', '.join(shared)})" for other, shared in kept.items())
            note = f"{note}; {why}" if note else why
        if allowed is None:
            note = note or "merged"
        lines.append(f"| {one} | {deps} | {cell} | {note.replace('|', '/')} |")
    return lines


def rewrite(text: str, rows: list[str]) -> str:
    """The split with its `## Slice graph` table replaced by `rows`, or the section added before the parking
    lot where there was none. Prose around the table is kept as written."""
    lines = text.splitlines()
    start = next((index for index, line in enumerate(lines)
                  if line.startswith("#") and line.strip().lstrip("#").strip().lower() == "slice graph"), None)
    table = [*HEADER.splitlines(), *rows]
    if start is None:
        before = next((index for index, line in enumerate(lines) if line.strip().lower() == "## parking lot"),
                      len(lines))
        return "\n".join([*lines[:before], "## Slice graph", "", *table, "", *lines[before:]]) + "\n"
    end = next((index for index in range(start + 1, len(lines)) if lines[index].startswith("#")), len(lines))
    body = lines[start + 1:end]
    first = next((index for index, line in enumerate(body) if line.strip().startswith("|")), None)
    if first is None:
        body = [*body[:1], "", *table, *body[1:]] if body else ["", *table, ""]
    else:
        last = first
        while last + 1 < len(body) and body[last + 1].strip().startswith("|"):
            last += 1
        body = [*body[:first], *table, *body[last + 1:]]
    return "\n".join([*lines[:start + 1], *body, *lines[end:]]) + ("\n" if text.endswith("\n") else "")


def next_decision(feature: str) -> str:
    """The next decision number, reserved the way every other writer reserves one where `ids.py` can, else
    one past the highest this feature's log holds."""
    try:
        import ids  # noqa: PLC0415 — beside this script; reaches git, so loaded only when writing

        return ids.reserve(1, "beside")[0]
    except Exception:  # noqa: BLE001 — a number is still owed where the reservation cannot be made
        log = clearance.SPECS / feature / "decisions.md"
        text = log.read_text(encoding="utf-8") if log.is_file() else ""
        numbers = [int(n) for n in re.findall(r"^## D(\d+)\b", text, flags=re.M)]
        return f"D{max(numbers, default=0) + 1}"


def decision(feature: str, number: str, beside: dict[str, set[str] | None], apart: dict[str, dict[str, list[str]]],
             set_aside: set, charted: dict, why_now: str) -> str:
    """The entry that records the column, for a person to confirm or change."""
    slices = charted.get("slices") or {}
    open_ = [one for one, allowed in beside.items() if allowed is not None]
    alone = [one for one in open_ if not beside[one]]
    fairways = sorted({str((slices.get(one) or {}).get("fairway", "")) for one in open_})
    kept = sorted({f"{one}/{other}" for one, others in apart.items() for other in others if one < other})
    seam = ", ".join(f"`{name}`" for _, name in sorted(set_aside)) or "none"
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    together = ("every slice in a stream can run beside every other" if not kept else
                "slices that would change the same screen, history or file wait for each other, and the rest of "
                "each stream runs side by side")
    return "\n".join([
        f"## {number} — Which slices may run beside which (`parallel_ok_with`)?",
        f"- **Stage:** split · **Slice:** chart · **When:** {stamp} · **Stream:** {', '.join(fairways) or '—'}",
        f"- **Question:** {why_now} Which of each fairway's slices not yet merged may run at the same time, "
        f"read off what they would collide on rather than left as a placeholder.",
        "- **Options:** (a) **fill the column from collisions — the same stream, screen or file — and list "
        "every other sibling; recommended**; (b) `alone` on every row, one slice at a time per fairway; (c) "
        "leave every row unrestricted.",
        f"- **Decision:** (a). Kept apart: {', '.join(kept) or 'none'}. Alone: {', '.join(alone) or 'none'}. "
        f"Seams every slice adds to, merged in split order and not counted: {seam}.",
        f"- **In short:** In each stream, {together}.",
        "- **Why:** two slices at once only cost something where they change the same thing; everything else "
        "they share is a contract, which the method makes independent. (b) is the run that cost a night; (c) "
        "runs slices that collide side by side and pays for it in merge conflicts. · **Read against:** "
        "`docs/event-model/model.yaml` (each slice's `stream`, mockups and `code`), the split's *Surfaces and "
        "states*, `commands/sail.md` (*Running ready slices concurrently*); no convention yet",
        "- **Decided by:** host (stage recommendation)",
        "- **Confidence:** medium · **Would reverse if:** two slices listed beside each other turn out to change "
        "a file neither names yet, which a merge conflict between them would show",
        f"- **Written to:** `specs/{feature}/story-split.md`",
        "- **Status:** awaiting human confirmation",
        "",
    ])


def finished(charted: dict, feature: str) -> set[str]:
    """The slices already merged, by the evidence clearance reads: nothing is refilled under one."""
    folded_logs = clearance.with_evidence(charted, clearance.folded(clearance.lines(feature)))
    done = clearance.done_marked(feature)
    return {str(one) for one in charted.get("slices") or {} if clearance.is_done(folded_logs, done, str(one))}


def fill(feature: str = "", why_now: str = "The split's `parallel_ok_with` column was not filled in.") -> str:
    """Fill the column for every unmerged slice of the feature, record the decision, and say what was written."""
    charted, home = clearance.chart(feature)
    if not charted:
        return f"beside: no chart for {feature or 'any feature'}; run `make chart` first"
    feature = feature or home
    split = clearance.SPECS / feature / "story-split.md"
    if not split.is_file():
        return f"beside: specs/{feature}/story-split.md is not there; the split writes it"
    beside, apart, set_aside = worked_out(charted, feature, finished(charted, feature))
    if not beside:
        return f"beside: the chart has no slices of {feature}"
    split.write_text(rewrite(split.read_text(encoding="utf-8"), rendered(charted, feature, beside, apart)),
                     encoding="utf-8")
    number = next_decision(feature)
    log = clearance.SPECS / feature / "decisions.md"
    existing = log.read_text(encoding="utf-8") if log.is_file() else "# Decisions\n"
    log.write_text(existing.rstrip("\n") + "\n\n" + decision(feature, number, beside, apart, set_aside, charted,
                                                               why_now), encoding="utf-8")
    clearance.GRAPHS.clear()
    alone = sorted(one for one, allowed in beside.items() if allowed is not None and not allowed)
    return (f"beside: filled parallel_ok_with for {sum(1 for a in beside.values() if a is not None)} slice(s) of "
            f"{feature}, {len(alone)} alone; recorded {number} in specs/{feature}/decisions.md for a person to "
            f"confirm. Run `make check-chart`.")


def faults(charted: dict) -> list[str]:
    """What `check-chart` refuses: a fairway kept to one slice at a time that no decision accounts for."""
    found = []
    for held in clearance.serialised(charted):
        if any(clearance.beside_decisions(feature.strip()) for feature in held.feature.split(",")):
            continue
        rows = "; ".join(f"`{row}`" for row in held.rows[:4]) + (f" and {len(held.rows) - 4} more"
                                                                   if len(held.rows) > 4 else "")
        said = ("never filled in: every row's `parallel_ok_with` is a placeholder" if held.why == "unfilled"
                else "filled so that no two of its slices may run together")
        found.append(f"specs/{held.feature}/story-split.md: fairway `{held.fairway}` has {len(held.slices)} slices "
                     f"and its slice graph is {said} ({rows}), and no decision in specs/{held.feature}/decisions.md "
                     f"says why. Run `python3 scripts/agents/beside.py --fill --feature {held.feature}`, which "
                     f"works the column out from what the slices would collide on and records it; or, where one "
                     f"at a time is meant, write `alone` and a `## D<n> — Which slices may run beside which "
                     f"(parallel_ok_with)?` entry with the reason")
    return found


def main(argv: list[str]) -> int:
    feature = argv[argv.index("--feature") + 1] if "--feature" in argv and argv.index("--feature") + 1 < len(argv) else ""
    if "--fill" in argv:
        said = fill(feature)
        print(said)
        return 0 if "filled" in said else 1
    charted, _ = clearance.chart(feature)
    found = faults(charted) if charted else []
    for fault in found:
        print(fault, file=sys.stderr)
    if not found:
        print("beside: every fairway of more than one slice may run more than one, or says why not")
    return 1 if found else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

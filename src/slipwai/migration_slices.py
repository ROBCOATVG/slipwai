"""What a crossing takes to be a slice, and which event names it finds already in a log.

Two readings of a version 1 project, both of which the crossing got wrong by reading too much (issue 95).

**A split names its slices in one place.** The whole text used to be searched for anything shaped like an
id, and a split's notes are full of those — `CS-3`, `FR-006`, `V-10` are a scenario, a requirement and a
rule, in the very shape of a slice id. They were listed as slices to place, which nobody could do, so the
crossing's confirmation never succeeded and no fairway could be claimed. And on the event profile the model
is what a slice is: the chart is rendered from it, so a slice only the split holds is named for a person
and never listed as `unplaced`.

**A stored event keeps its name.** `check-model`'s two naming rules arrived with version 2, and a project
with `WorkspaceCreated` already in its log could only satisfy them by renaming it. So the crossing records,
once, the names its built slices hold, and the rules ask nothing of those.
"""
from __future__ import annotations

import json
import re
from collections.abc import Collection, Mapping, Sequence

#: Where a crossing records the event names the project already had in a log, which `check-model`'s two
#: naming rules then ask nothing of: a stored event cannot be renamed. Written once, here, and read by
#: `scripts/event-model/check.py` and `held-names.ts`, which spell the same path.
NAMES_FROM = ".specify/event-names-from.json"
#: The statuses that say a slice's events may already be written: built, or recorded from code that exists.
#: A slice that is only modelled or planned has raised nothing, so its events can still be renamed and the
#: rules hold them — the stricter of the two readings issue 95 left open.
WRITTEN = frozenset({"implemented", "observed"})
#: What a slice's id looks like where a split writes one: `S38`, `ORD-01`, `CL2`. Read only out of the first
#: column of a split's slice table and never out of its prose — a split quotes scenario, requirement and
#: rule ids (`CS-3`, `FR-006`, `V-10`) in the very same shape, and nothing but where it stands says which a
#: token is.
SLICE = re.compile(r"(?<![\w-])[A-Z][A-Z0-9]*-?\d+(?![\w-])")
#: A run of slices in one cell, `S38–S41` or `L02 to L23`: an en dash, an em dash or the word, never a
#: hyphen, which is inside ids like `ORD-01`. The spelling `clearance.py` reads the same table with.
RUN = re.compile(r"(?<![\w-])([A-Z][A-Z0-9]*?-?)(\d+)\s*(?:–|—|\bto\b)\s*\1?(\d+)(?![\w-])")


def named(split: str, known: Collection[str] = ()) -> list[str]:
    """The slices a split names: the first column of its `## Slice graph` table, and nothing else it says.

    The whole text used to be searched for anything shaped like an id, and a split's notes are full of
    those: one project's crossing listed `CS-3`, `FR-006`, `R-11` and `V-10` as slices to place, none of
    which is a slice, so its confirmation could never succeed and nothing could be claimed (issue 95). A
    row's first cell is the one place the split says "this is a slice". It may name one, several, or a run
    (`S38–S41`); `known` are ids already established as slices — the model's — which are recognised however
    they are spelled, since the model admits a lower-case id this shape does not.

    A split written before the slice graph existed has no such table, and falls back to the first column
    of any table headed `Slice` — the split candidates. One with neither names nothing here, and its slices
    are the directories under `slices/`.
    """
    graph: list[str] = []
    headed: list[str] = []
    inside = columns = False
    for line in split.splitlines():
        text = line.strip()
        if text.startswith("#"):
            inside, columns = text.lstrip("#").strip().lower() == "slice graph", False
            continue
        if not text.startswith("|"):
            columns = False
            continue
        cell = text.strip("|").split("|")[0].strip()
        if cell.strip("`* ").lower() == "slice":
            columns = True
        elif not set(cell) <= set("-: "):
            if inside:
                graph.append(cell)
            elif columns:
                headed.append(cell)
    found: list[str] = []
    for cell in graph or headed:
        for prefix, low, high in RUN.findall(cell):
            found += [f"{prefix}{number:0{len(low)}d}" for number in range(int(low), int(high) + 1)]
        found += SLICE.findall(cell)
        found += [slice_id for slice_id in known
                  if re.search(rf"(?<![\w-]){re.escape(slice_id)}(?![\w-])", cell)]
    return sorted(set(found))


def stored_names(slices: list[dict]) -> list[str]:
    """The names of the events these slices may already have written, sorted and once each.

    Read after the statuses are reconciled, so a slice trunk proves shipped counts whatever its field said.
    """
    return sorted({frame["name"] for item in slices if item.get("status") in WRITTEN
                   for frame in item.get("frames") or []
                   if isinstance(frame, dict) and frame.get("type") == "evt"
                   and isinstance(frame.get("name"), str) and frame["name"]})


def names_file(names: Sequence[str]) -> bytes:
    """`NAMES_FROM` as it is written: the names, and a sentence for whoever opens it."""
    held = {"events": list(names),
            "why": "Events the model's implemented slices held when slipwai migrate crossed this project from "
                   "version 1. A stored event cannot be renamed, so scripts/event-model/check.py does not ask "
                   "event-is-not-crud or event-is-not-negative of these names; every event named since is "
                   "held to both. Written once; leave it as it is."}
    return (json.dumps(held, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def modelled_only(found: Sequence[str], held: Collection[str]) -> tuple[list[str], list[str]]:
    """(the slices the model holds, the names it does not), of what a split and its directories name.

    `make chart` renders the chart from the model and `check-chart` refuses one that disagrees. A slice only
    the split holds has no frames, the model's grammar admits none without, and so no chart could ever carry
    it — listing it as `unplaced` asked a person for a placement that cannot be made.
    """
    return ([slice_id for slice_id in found if slice_id in held],
            [slice_id for slice_id in found if slice_id not in held])


def unmodelled_section(unmodelled: Mapping[str, Sequence[str]]) -> str:
    """The catch-up page's account of the names the model does not hold, or nothing where it holds them all."""
    if not unmodelled:
        return ""
    return ("## Slices the model does not hold\n\n"
            "Each of these has a row in a split's slice graph or a directory under `slices/`, and no slice "
            "in the event model. The chart is rendered from the model, so none of them is on it, none is "
            "`unplaced`, and the confirmation above does not wait for them. Where one is work still to do, "
            "model it — a slice needs at least one frame — and `make chart` charts it; where one is not a "
            "slice at all, there is nothing to do.\n\n"
            + "".join(f"- `{feature}`: {', '.join(f'`{slice_id}`' for slice_id in names)}\n"
                      for feature, names in sorted(unmodelled.items())) + "\n")


def kept_section(kept: Sequence[str]) -> str:
    """The catch-up page's list of the names the rules will not ask about: an exemption nobody was told
    of is one nobody can check."""
    if not kept:
        return ""
    return ("## Event names kept\n\n"
            "These events belong to slices that were `implemented` at this crossing, so they may already be "
            "in a log, and a stored event cannot be renamed. `make check-model` does not ask "
            "`event-is-not-crud` or `event-is-not-negative` of them; it holds every event named from here on "
            f"to both. The list is `{NAMES_FROM}`, written once: take a name out of it when the event it "
            "names is retired, and never add one to pass the gate.\n\n"
            + ", ".join(f"`{name}`" for name in kept) + "\n\n")

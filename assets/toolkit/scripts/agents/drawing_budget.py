# Written by scripts/shared-modules.py from src/slipwai/drawing_budget.py. Do not edit: edit the keel's module,
# run `make shared`, and commit both. A generated project has no slipwai to import, and both runtimes need
# this one — so there is one source and this copy, and `make check-shared` refuses a copy that has drifted.
"""How long a drawing of the storyboard may take: one reading, for the board and for the project's script.

The mock-up stage is ended at a ceiling so that a session that has hung, or is polishing what nobody asked
for, does not run for ever. The ceiling was fifteen minutes for a first drawing and ten for a redraw, and that
was a guess from a feature with a handful of surfaces: a further feature with ten stories and twenty surfaces
spent ten of its fifteen minutes on the research alone, was ended while six delegates were still writing
pages, and left twenty screens with no storyboard and no review — a failure the person had to work out how to
restart. A ceiling is there to end a session that is lost, not one that is working, so it is an hour and half
an hour now, and a person who wants another number writes the row in `harbour.json`.

The board read none of this. `surfaces.py` read `harbour.json`; a drawing the board ran over the protocol was
ended at a literal nine hundred seconds whatever the file said, and was never told how long it had. Both ask
here now.

Carried into a generated project as `scripts/agents/drawing_budget.py` (`scripts/shared-modules.py`), so this
imports nothing but the standard library.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

#: Minutes for a first drawing and for a redraw, where `harbour.json` has no `surfaces` or `surfaces-redraw`
#: row. The generated file has none: its `stages` are the slice ladder's, which this stage is not on.
FIRST_MINUTES = 60
REDRAW_MINUTES = 30


def seconds(harbour: Path, redraw: bool) -> float:
    """Seconds a drawing may take: the default scaled by `harbour.json`'s `stage_scale`, or the `surfaces`
    (or `surfaces-redraw`) row a person wrote there.

    A row is read as it stands, as `captain.stage_bound` reads its rows, because ringing the telegraph scales
    every row in `stages` in place and scaling it again here would count the telegraph twice. The default has
    no row to be scaled in, so `stage_scale` is applied to it here. Never under a minute, which is the floor
    the telegraph's own scaling keeps: a budget of nothing would read as a drawing that failed.
    """
    try:
        held = json.loads(harbour.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        held = {}
    held = held if isinstance(held, dict) else {}
    found = held.get("stages")
    stages = found if isinstance(found, dict) else {}
    row = stages.get("surfaces-redraw" if redraw else "surfaces")
    minutes = row.get("minutes") if isinstance(row, dict) else None
    if isinstance(minutes, int | float) and not isinstance(minutes, bool) and minutes > 0:
        return max(1.0, float(minutes)) * 60.0
    scale = held.get("stage_scale")
    scale = float(scale) if isinstance(scale, int | float) and not isinstance(scale, bool) else 1.0
    return max(1.0, (REDRAW_MINUTES if redraw else FIRST_MINUTES) * scale) * 60.0


def told(allowed: float, started: float | None = None) -> dict[str, str]:
    """What a drawing's session is told of its budget, as the environment `commands/mockups.md` reads: the
    minutes it has, and the clock time they run out."""
    began = time.time() if started is None else started
    return {"SLIPWAI_BUDGET_MINUTES": f"{allowed / 60:g}",
            "SLIPWAI_BUDGET_ENDS": time.strftime("%H:%M", time.localtime(began + allowed))}

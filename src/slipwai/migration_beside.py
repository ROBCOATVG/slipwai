"""The catch-up page's section for a split whose `parallel_ok_with` was never filled in.

Before 2.1.0 the split template offered `—` for "none" in `depends_on`, and `clearance.py` read the same
`—` in `parallel_ok_with` as *runs beside nothing*. A split stage with nobody present wrote `—` on every
row of a thirty-eight slice fairway, which then ran one slice at a time all night. The toolkit now reads
`—` as "nothing declared" in both columns, so such a fairway is no longer held to one — but the column is
still a placeholder, and slices that do collide on a stream or a screen are now unrestricted. The split
stage's rule fills it; this section is how a project already past its split learns it owes the same.

It reads the project's own `beside.py` — the copy the merge just brought in — rather than a second
definition of the rule, so what `migrate` reports, what `/catch-up` runs and what `check-chart` refuses are
one rule. It never writes anything into the split or the decision log: it only says what is owed.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

from .layout import layout_of

#: The modules `beside.py` loads by bare name from beside itself. Popped before and after, so a project's
#: copies are never served from another project's or the keel's.
CARRIED = ("beside", "clearance", "logs", "ids")


def loaded(root: Path, document: dict | None) -> ModuleType | None:
    """The project's own `beside.py`, loaded from where its layout puts the toolkit; None where it has none."""
    place = layout_of(document).place("scripts/agents/beside.py") if document else "scripts/agents/beside.py"
    script = root / place
    if not script.is_file():
        return None
    for name in CARRIED:
        sys.modules.pop(name, None)
    sys.path.insert(0, str(script.parent))
    try:
        spec = importlib.util.spec_from_file_location("beside", script)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        sys.modules["beside"] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(script.parent))


def unfilled(root: Path, document: dict | None) -> list[tuple[str, str, int]]:
    """(feature, fairway, slices) for each fairway whose split left every `parallel_ok_with` row a placeholder
    and whose decision log says nothing about it."""
    beside = loaded(root, document)
    if beside is None:
        return []
    try:
        clearance = beside.clearance
        found = []
        for chart in sorted((clearance.SPECS).glob("*/chart.yaml")):
            charted = clearance.load_yaml(chart.read_text(encoding="utf-8"))
            if not isinstance(charted, dict):
                continue
            for held in clearance.serialised(charted):
                if held.why == "unfilled" and not any(clearance.beside_decisions(one.strip())
                                                      for one in held.feature.split(",")):
                    found.append((held.feature, held.fairway, len(held.slices)))
        return found
    finally:
        for name in CARRIED:
            sys.modules.pop(name, None)


def section(root: Path, document: dict | None) -> list[str]:
    """The lines the catch-up page carries for every such fairway; none where there is none."""
    try:
        found = unfilled(root, document)
    except Exception:  # noqa: BLE001 — the merge is made: a page short a section, never a traceback
        return []
    if not found:
        return []
    lines = ["", "## A split whose `parallel_ok_with` was never filled in", "",
             "Before this version the split template offered `—` for *none* and the fleet read `—` in "
             "`parallel_ok_with` as *runs beside nothing*, so a fairway whose split wrote it on every row ran one "
             "slice at a time. The fleet now reads `—` as *nothing declared*, as it does in `depends_on` — so these "
             "fairways are no longer held to one, and slices that do share a stream or a screen are no longer kept "
             "apart either. Fill the column from what the slices would collide on:", ""]
    lines += [f"- `{fairway}` in `specs/{feature}/story-split.md`: {count} slices, every row `—`." for feature, fairway,
              count in found]
    lines += ["", "For each feature named:", ""]
    for feature in dict.fromkeys(feature for feature, _, _ in found):
        lines += [f"1. `python3 scripts/agents/beside.py --fill --feature {feature}`. It fills the column for "
                  f"every slice not yet merged — beside every sibling it shares no stream, screen or file with, "
                  f"`alone` where that is none — and records the choice as a decision awaiting confirmation in "
                  f"`specs/{feature}/decisions.md`.",
                  "2. `make check-chart`, which refuses a fairway kept to one slice at a time with no decision.",
                  "3. Commit both files and land them on trunk the way any change lands. A fleet that is running "
                  "reads the refilled graph at its next boundary, with no restart, and the harbourmaster hands the "
                  "fairway the spare sessions."]
    return lines

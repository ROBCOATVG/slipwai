#!/usr/bin/env python3
"""What the logs say happened to each slice, written where the model's renderers can colour it.

The browsable model already badges every slice with `model.yaml`'s `status` — `proposed`, `modelled`,
`planned`, `implemented`. That field is written by a person at plan time, and it is the field that failed:
MANDA's `model.yaml` said `planned` for eight slices that were built and merged, because nobody went back.

**So the page shows two bands, and this is the second one.** What the model *intends* stays where it is,
written by a person. What *happened* is folded from the deck logs by this, written by nobody. Showing the
two side by side makes the drift visible — a slice badged `implemented` whose log holds nothing is that
same failure, drawn on the page where somebody would see it.

**It writes nowhere near `model.yaml`.** The moment a fold writes back into the field it is folding
against, there is one band again and it is the one that lies. It writes `.slipwai/run-state.json`, which
is ignored by git, and it never touches `model.drawio` either: that file is committed and
`make check-drawio` holds it current, so a heartbeat would dirty the tree on every pass.

**The page works without it.** No run, no file, and the renderers draw exactly what they draw today. This
is an overlay, and an overlay that was required would make the model unrenderable on a fresh checkout.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import logs  # noqa: E402


def project_root() -> Path:
    for candidate in HERE.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return HERE.parents[1]


ROOT = project_root()
OUT = ROOT / ".slipwai/run-state.json"
#: What the logs can say about a slice, slowest-moving first. The order is the order a slice walks them in,
#: which is what lets a renderer treat it as a scale rather than a set of unrelated words.
STATES = ("not started", "claimed", "marks set", "demoed", "merged", "parked")


def deck_logs() -> list[Path]:
    return logs.deck_logs(ROOT)


def entries() -> tuple[list[logs.Entry], list[str]]:
    """Every deck-log entry, and a line for each log that could not be read.

    One unreadable log does not stop the others: this is an overlay on a picture, and a picture missing
    one stream's colour is better than no picture — which is the opposite of the fold a board does, where
    a hole makes the whole thing confidently wrong.
    """
    found: list[logs.Entry] = []
    faults: list[str] = []
    for path in deck_logs():
        try:
            found += logs.fold(path.read_text(encoding="utf-8").splitlines())
        except (OSError, UnicodeDecodeError, logs.Unreadable) as fault:
            faults.append(f"{path.name}: {fault}")
    return found, faults


def parked_fairways(found: list[logs.Entry]) -> dict[str, str]:
    """Each fairway that is parked, and why. A park is per fairway; a slice inherits it."""
    parked: dict[str, str] = {}
    for entry in found:
        fairway = str(entry.fields.get("fairway", ""))
        if entry.kind == "parked":
            parked[fairway] = str(entry.fields.get("why", ""))
        elif entry.kind == "claimed" and fairway in parked:
            parked.pop(fairway)  # it started something, so whatever parked it was dealt with
    return parked


def per_slice(found: list[logs.Entry]) -> dict[str, dict]:
    """Each slice the logs mention, with what happened to it and when it last did anything."""
    state: dict[str, dict] = {}
    parked = parked_fairways(found)
    for entry in found:
        slice_id = str(entry.fields.get("slice", ""))
        if not slice_id:
            continue
        row = state.setdefault(slice_id, {"state": "not started", "marks": [], "fairway": "", "at": ""})
        row["fairway"] = str(entry.fields.get("fairway", "")) or row["fairway"]
        row["at"] = entry.t or row["at"]
        if entry.kind == "claimed":
            row["state"] = "claimed"
        elif entry.kind == "mark-set":
            row["marks"] = sorted({*row["marks"], str(entry.fields.get("mark", ""))})
            row["state"] = "marks set"
        elif entry.kind == "demo":
            row["state"] = "demoed"
            row["verdict"] = str(entry.fields.get("verdict", ""))
        elif entry.kind == "merged":
            row["state"] = "merged"
            row["commit"] = str(entry.fields.get("commit", ""))
    for slice_id, row in state.items():
        if row["fairway"] in parked and row["state"] != "merged":
            row["state"], row["why"] = "parked", parked[row["fairway"]]
    return state


def marks_set(found: list[logs.Entry]) -> list[str]:
    """Every mark some slice has set. What makes the arrows on the model mean something: a mark that is
    set is what clears the slices steering by it, and that is the thing a picture can show and a row
    cannot."""
    return sorted({str(e.fields.get("mark", "")) for e in found if e.kind == "mark-set"})


def state() -> dict:
    """The whole overlay. `v` so a renderer meeting a newer one can say so rather than guess."""
    found, faults = entries()
    return {"v": 1, "states": list(STATES), "slices": per_slice(found),
            "marks": marks_set(found), "unreadable": faults}


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="run-state", description="What the logs say happened, for the model's renderers to colour")
    parser.add_argument("--out", default=str(OUT), help=f"where to write it (default: {OUT})")
    parser.add_argument("--print", action="store_true", help="to stdout instead, and write nothing")
    parsed = parser.parse_args(argv)
    whole = state()
    if parsed.print:
        print(json.dumps(whole, indent=2, ensure_ascii=False))
        return 0
    path = Path(parsed.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(whole, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    counted = len(whole["slices"])
    print(f"run-state: {path.relative_to(ROOT).as_posix()} — {counted} slice(s) the logs mention, "
          f"{len(whole['marks'])} mark(s) set")
    for fault in whole["unreadable"]:
        print(f"  {fault} — that stream has no colour on the model", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

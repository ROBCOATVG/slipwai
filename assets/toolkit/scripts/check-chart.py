#!/usr/bin/env python3
"""Hold `specs/<feature>/chart.yaml` — the contracts, written before the split, that every fairway steers by.

The chart is the one file a captain and a gate both read on either profile. It names the fairways, what
each slice publishes, what each slice steers by, the paths a fairway owns, and the capability each slice is
part of. On the event-modelling profile `make chart` renders it from `model.yaml`; on the standard profile a
`/chart` stage writes it. Either way this is what holds it, because a chart nobody checks is a comment.

Seven rules, and each one exists because its absence fails quietly rather than loudly:

1. **Every mark is typed and its file is there.** A mark is a contract, and a contract another fairway
   steers by has to be something they can read: a JSON Schema, an OpenAPI operation, a port's two schemas.
   A mark naming a file nobody wrote is a promise that is discovered at the far end, by the fairway that
   believed it.
2. **Every mark steered by is set by some slice.** Otherwise a slice waits on a mark no one is building,
   and clearance (slice 5.5) never comes. The fairway looks blocked and nothing says on what.
3. **No mark is set by two slices.** Two setters is two schemas for one name, resolved by whichever merged
   last, which is the one failure that cannot be found by reading either slice on its own.
4. **No mark is deleted from a frozen chart.** The chart is frozen before any slice is claimed. A mark that
   disappears is a contract withdrawn from under whoever steered by it; an amendment is additive and goes
   in `fairways/<name>/chart.d/`, folded on `main` by the harbourmaster.
5. **Every slice names the capability it is part of.** A capability is what a person's demo is for. A slice
   naming none would never complete one, so no demo would ever come due and nothing would say why — the
   loop would run to the end of a feature having stopped nobody, which reads exactly like a loop with
   nothing to show.
6. **Once the split has run, every slice says `sets` and `steers_by` out loud.** An empty list is an answer;
   an absent key is refused. This is new with slice 7.8, and it is what makes the captain's gate readable:
   a slice is through its gate when the log holds a `mark-set` for every mark its `sets` names, so `sets: []`
   has to be a positive statement that this slice publishes nothing. On the event profile the renderer
   always writes both keys, so it was one already; on the standard profile the split authors them and this
   read them with `body.get("sets") or []`, under which a slice that simply forgot the key took a
   demo-only gate by omission — the quietest way there is to pass a gate.

7. **The fairways were derived from a recorded context decision.** `specs/<feature>/decisions.md` holds an
   entry asking which bounded contexts the feature touches — its heading or `Question` says *bounded
   context* — carrying the seam table its answer was read off. One fairway is an answer too, and the one
   that most needs saying: it puts every slice behind one captain. A headless run once wrote "one context,
   so one fairway" into the split with no seam test, no table and no entry, and thirty-one slices queued
   behind the first; nothing refused it because nothing looked. (One context was right there, for a reason
   nobody wrote down — two cross-group invariants — which is the point: the gate holds the reason, not the
   answer.) And **a fairway over `CROWDED` slices owes a `Why not split:` line** in that entry citing the
   invariant that spans its groups, because past a dozen serial slices the reason costs a run enough to be
   written. The count asks for a reason, never for a split.

On the event-modelling profile there is an eighth, and it is about where the chart came from rather than
what it says: the committed chart must be what `make chart` would render from `model.yaml`. The model is
the source of truth on that profile, so a chart edited by hand is a second answer to a question that
already had one, and the two diverge silently because nothing else reads both. This holds it the way
`make check-drawio` holds the committed canvas. It compares the two as data rather than as text, so a
different YAML writer is not drift; a fairway, a mark or a slice that says something different is — **and
so is the same slices in another order**, which is slice 18.1. The order of the `slices` block is the order
every captain takes them in, so two orders are two answers to what runs first, and a chart reordered by
hand is the decision taken away from the split that took it.

Before the rules, the shape: the keys that have to be there, the four mark kinds, and a slice naming a
fairway that exists. A malformed chart is reported as a shape fault and the rules are not run over it,
because every one of them would then report the same damage again in its own words.

Exit 0 and say so where there is no chart yet: a project with no feature in flight has nothing to hold, and
`make verify` runs this everywhere.
"""
from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from pathlib import Path

def project_root(script: Path, depth: int) -> Path:
    """The repository root, which is not always one above `scripts/`.

    A brownfield adoption puts the method's material under `project.json`'s `layout.delivery`, so this
    script sits at `<repo>/<delivery>/scripts/`, while `specs/` stays at the repository root either way.
    Hard-coding one level up found `<repo>/<delivery>/specs`, which does not exist, so the gate reported
    `no chart yet` and exited 0 on every adopted project — a gate that is green because it is looking in
    the wrong place. `check-slice-scope` has always resolved it this way; this one did not until it was
    caught.
    """
    for candidate in script.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return script.parents[depth]


ROOT = project_root(Path(__file__).resolve(), 1)
SPECS = ROOT / "specs"
KINDS = {"event", "schema", "route", "port"}
# What each kind names, and what the gate opens to prove the contract is really there.
BODIES = {"event": ("schema",), "schema": ("schema",), "route": ("operation",), "port": ("inputs", "outputs")}
FIX = "python3 scripts/check-chart.py"
#: How many slices one fairway may hold before its context decision owes a `Why not split:` line. A fairway
#: is one captain merging in order, so its slices are serial; a feature's split is usually five to ten
#: slices, and past twelve one context is the decision that takes a run's parallelism away, which a person
#: should see argued rather than inherited.
CROWDED = 12
#: What marks the context decision among a feature's entries: its heading or `Question` names it.
CONTEXT_QUESTION = re.compile(r"bounded[ -]contexts?", re.IGNORECASE)
TABLE_ROW = re.compile(r"^\s*\|.*\|.*\|")
WHY_NOT_SPLIT = re.compile(r"\*\*Why not split:\*\*\s*\S")
WRITE_IT = ("Run pass one's seam tests (commands/chart.md; on the event profile, nine-steps.md Step 9, "
            "*Interrogate every stream* and *Apply Conway's Law*) and record the answer as `## D<n> — Which bounded contexts does {feature} touch?` in "
            "specs/{feature}/decisions.md, with the seam table — candidate, entities, evidence, what crosses, "
            "confidence")


def load_yaml(text: str) -> object:
    """The parser the other gates use, installed beside them where the environment has not got it."""
    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError:  # pragma: no cover - exercised on a machine without PyYAML
        subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "PyYAML"], check=True)
        import yaml  # type: ignore[import-not-found]
    return yaml.safe_load(text)


def charts() -> list[Path]:
    """Every feature's chart. A feature with none has not reached its chart stage yet."""
    return sorted(SPECS.glob("*/chart.yaml")) if SPECS.is_dir() else []


def shape_faults(chart: object, path: Path) -> list[str]:
    """The keys, the kinds, and a slice's fairway. Everything the five rules assume is already true."""
    where = path.relative_to(ROOT).as_posix()
    if not isinstance(chart, dict):
        return [f"{where}: not a mapping"]
    faults = [f"{where}: no `{key}` block" for key in ("v", "feature", "fairways", "marks", "slices")
              if key not in chart]
    if faults:
        return faults
    for block in ("fairways", "marks", "slices"):
        if not isinstance(chart[block], dict):
            faults.append(f"{where}: `{block}` is not a mapping of name to body")
    if faults:
        return faults
    for name, body in chart["marks"].items():
        if not isinstance(body, dict) or body.get("kind") not in KINDS:
            faults.append(f"{where}: mark `{name}` has no kind, or one that is not {', '.join(sorted(KINDS))}")
            continue
        for key in BODIES[body["kind"]]:
            if not body.get(key):
                faults.append(f"{where}: {body['kind']} mark `{name}` names no `{key}`")
    for name, body in chart["fairways"].items():
        owns = body.get("owns") if isinstance(body, dict) else None
        if not isinstance(owns, list) or not owns:
            faults.append(f"{where}: fairway `{name}` names no `owns`. On either profile that list is the "
                          f"whole of the boundary `check-slice-scope` holds, so a fairway without one is a "
                          f"fairway no gate protects")
    for name, body in chart["slices"].items():
        if not isinstance(body, dict):
            faults.append(f"{where}: slice `{name}` is not a mapping")
        elif body.get("fairway") not in chart["fairways"]:
            faults.append(f"{where}: slice `{name}` names fairway `{body.get('fairway')}`, which the chart has not got")
    return faults


def frozen(path: Path) -> dict | None:
    """The chart as trunk has it, for the deletion rule. `None` where git cannot answer, which is not a fault."""
    relative = path.relative_to(ROOT).as_posix()
    for revision in ("origin/main", "main"):
        shown = subprocess.run(["git", "show", f"{revision}:{relative}"],
                               cwd=ROOT, capture_output=True, text=True, check=False)
        if shown.returncode == 0:
            was = load_yaml(shown.stdout)
            return was if isinstance(was, dict) else None
    return None


def rule_faults(chart: dict, path: Path) -> list[str]:
    """The five. Each refusal names the thing, the file, and what to do instead."""
    where = path.relative_to(ROOT).as_posix()
    faults: list[str] = []
    marks, slices = chart["marks"], chart["slices"]

    for name, body in marks.items():
        for key in BODIES[body["kind"]]:
            named = str(body[key]).split("#")[0]
            if not (ROOT / named).is_file():
                faults.append(f"{where}: mark `{name}` names {named}, which is not in the tree. "
                              f"Write the contract before the chart promises it")

    setters: dict[str, list[str]] = {}
    for slice_id, body in slices.items():
        for mark in body.get("sets") or []:
            setters.setdefault(str(mark), []).append(slice_id)
    for mark, by in sorted(setters.items()):
        if len(by) > 1:
            faults.append(f"{where}: mark `{mark}` is set by {' and '.join(sorted(by))}. "
                          f"One mark has one setter; the others steer by it")
        if mark not in marks:
            faults.append(f"{where}: slice {by[0]} sets `{mark}`, which the `marks` block does not declare")

    for slice_id, body in slices.items():
        for mark in body.get("steers_by") or []:
            if str(mark) not in setters:
                faults.append(f"{where}: slice {slice_id} steers by `{mark}`, which no slice sets. "
                              f"It will never be cleared, and nothing else will say why")

    was = frozen(path)
    if isinstance(was, dict) and isinstance(was.get("marks"), dict):
        for gone in sorted(set(was["marks"]) - set(marks)):
            faults.append(f"{where}: mark `{gone}` was on the frozen chart and is not here now. "
                          f"A mark is set once and never moved; amend in fairways/<name>/chart.d/ instead")

    if (SPECS / str(chart.get("feature", "")) / "story-split.md").is_file():
        # The split has run, so the chart's second pass is owed. Before that it is not, which is why this
        # is conditional rather than a rule about every chart: `/chart` writes pass one and `make verify`
        # runs this in between, and a gate that refused the state it tells you to be in is a gate people
        # learn to skip.
        if not slices:
            faults.append(f"{where}: the split has run and the chart names no slices. The split writes the "
                          f"`slices` block — fairway, capability, sets, steers_by — and nothing is claimed "
                          f"until it has")
        charted = set(marks)
        spoken_for = {str(mark) for body in slices.values()
                      for key in ("sets", "steers_by") for mark in (body.get(key) or [])}
        for forgotten in sorted(charted - spoken_for):
            faults.append(f"{where}: mark `{forgotten}` is declared and no slice sets or steers by it. "
                          f"Either a slice publishes it, or it was a promise pass one made and the split "
                          f"dropped")

        for slice_id, body in slices.items():
            for key in ("sets", "steers_by"):
                if key not in body:
                    faults.append(f"{where}: slice {slice_id} does not say `{key}`. Write `{key}: []` where "
                                  f"the answer is none — a captain holds a slice to the marks its `sets` "
                                  f"names, so an absent key is a gate taken by omission rather than an "
                                  f"answer")
                elif body[key] is not None and not isinstance(body[key], list):
                    faults.append(f"{where}: slice {slice_id}'s `{key}` is not a list")

    for slice_id, body in slices.items():
        if not body.get("capability"):
            faults.append(f"{where}: slice {slice_id} names no `capability`. "
                          f"A person's demo is per capability, so a slice without one is never demoed")
    return faults


def context_decisions(feature: str) -> list[str]:
    """The text of each entry in this feature's decision log that answers which bounded contexts it touches."""
    log = SPECS / feature / "decisions.md"
    if not log.is_file():
        return []
    entries = re.split(r"^(?=## )", log.read_text(encoding="utf-8"), flags=re.M)
    found = []
    for entry in entries:
        heading = entry.split("\n", 1)[0]
        question = next((line for line in entry.splitlines() if line.startswith("- **Question:**")), "")
        if entry.startswith("## ") and CONTEXT_QUESTION.search(heading + question):
            found.append(entry)
    return found


def context_faults(chart: dict, path: Path) -> list[str]:
    """Rule seven: fairways drawn from a context decision somebody can read, argued where they are crowded."""
    fairways = chart["fairways"]
    if not fairways:
        return []
    where = path.relative_to(ROOT).as_posix()
    feature = str(chart.get("feature", ""))
    write_it = WRITE_IT.format(feature=feature)
    decided = context_decisions(feature)
    if not decided:
        if len(fairways) == 1:
            return [f"{where}: one fairway, `{next(iter(fairways))}`, and no recorded decision says why this "
                    f"feature is one bounded context. One fairway is one captain taking every slice in turn, "
                    f"so it is the answer that most needs its evidence. {write_it}"]
        return [f"{where}: {len(fairways)} fairways and no recorded decision says which bounded contexts they "
                f"are or why. {write_it}"]
    if not any(TABLE_ROW.search(line) for entry in decided for line in entry.splitlines()):
        return [f"{where}: the bounded-context decision in specs/{feature}/decisions.md carries no seam table, "
                f"so nothing says what it was read off. {write_it}"]
    held: dict[str, int] = {}
    for body in chart["slices"].values():
        held[str(body.get("fairway"))] = held.get(str(body.get("fairway")), 0) + 1
    crowded = sorted(name for name, count in held.items() if count > CROWDED)
    if crowded and not any(WHY_NOT_SPLIT.search(entry) for entry in decided):
        named = ", ".join(f"`{name}` ({held[name]} slices)" for name in crowded)
        return [f"{where}: {named} holds more than {CROWDED} slices, all serial behind one captain, and the "
                f"bounded-context decision in specs/{feature}/decisions.md has no `- **Why not split:**` line. "
                f"Cite, by requirement, the invariant that spans its groups and keeps them on one stream — a "
                f"decision reading several groups' state at once, or a closure one sets and all must check. "
                f"The count asks for the reason to be written, not for a split"]
    return []


def model_drift(path: Path) -> list[str]:
    """On the event profile, what the model means against what is committed. Empty where there is no model."""
    delivery = Path(__file__).resolve().parents[1]
    renderer = delivery / "scripts/event-model/chart.py"
    if not renderer.is_file() or not (delivery / "docs/event-model/model.yaml").is_file():
        return []
    spec = importlib.util.spec_from_file_location("chart_renderer", renderer)
    if spec is None or spec.loader is None:  # pragma: no cover - a renderer that will not load
        return []
    module = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode = True
    spec.loader.exec_module(module)
    meant = module.rendered()
    if meant is None or module.chart_path() != path:
        return []
    committed = load_yaml(path.read_text(encoding="utf-8"))
    where = path.relative_to(ROOT).as_posix()
    out_of_order = order_drift(committed, meant)
    if committed == meant and not out_of_order:
        return []
    differing = sorted(block for block in ("fairways", "marks", "slices")
                       if not isinstance(committed, dict) or committed.get(block) != meant[block])
    said = ", ".join(differing + out_of_order) or "the chart"
    return [f"{where}: {said} disagree(s) with docs/event-model/model.yaml. "
            f"The model is the source of truth here; run `make chart` rather than editing the chart"]


def order_drift(committed: object, meant: dict) -> list[str]:
    """The blocks whose rows are the same and in another order, each naming the first row that differs.

    Equality is not enough for these two, which is the whole of slice 18.1: a dict holding the same rows in
    another order is equal to it, and the order of `slices` is the order every captain takes them in. So a
    chart with two slices swapped compares equal to the one the model means and tells every captain to do
    something else, and before this the gate said it was fine.
    """
    if not isinstance(committed, dict):
        return []
    found: list[str] = []
    for block in ("fairways", "slices"):
        here, there = committed.get(block), meant.get(block)
        if not isinstance(here, dict) or not isinstance(there, dict) or set(here) != set(there):
            continue  # A row added or dropped is a difference the equality above reports better.
        differing = [(name, expected) for name, expected in zip(here, there) if name != expected]
        if differing:
            name, expected = differing[0]
            found.append(f"the order of `{block}` (`{name}` is where the model has `{expected}`)")
    return found


def main() -> int:
    found = charts()
    if not found:
        print("check-chart: no chart yet; nothing to hold")
        return 0
    faults: list[str] = []
    for path in found:
        chart = load_yaml(path.read_text(encoding="utf-8"))
        shape = shape_faults(chart, path)
        # A malformed chart would make every rule report the same damage in its own words.
        faults.extend(shape if shape else rule_faults(chart, path) + context_faults(chart, path)  # type: ignore[arg-type]
                      + model_drift(path))
    if faults:
        print("check-chart: the chart does not hold\n", file=sys.stderr)
        for fault in sorted(set(faults)):
            print(f"  {fault}", file=sys.stderr)
        print(f"\nRun: {FIX}", file=sys.stderr)
        return 1
    marks = sum(len(load_yaml(path.read_text(encoding="utf-8"))["marks"]) for path in found)  # type: ignore[index]
    print(f"check-chart: {len(found)} chart(s), {marks} marks, one setter each, every slice in a capability")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

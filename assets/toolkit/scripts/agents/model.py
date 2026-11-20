#!/usr/bin/env python3
"""The step after an approved storyboard on an event-modelling project: the model, and then a stop.

The chart is drawn from the model, so this does not chart, split or cast off. One headless session, told
`SLIPWAI_STAGE=model`, reading the specification and the states a person has just approved.

    python3 scripts/agents/model.py
    python3 scripts/agents/model.py --prompt    # say the prompt and stop: the board runs it over the protocol
"""
from __future__ import annotations

import json
import os
import shlex
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import harness  # noqa: E402

ROOT = harness.ROOT
import feature_stages  # noqa: E402 — carried beside this script; the board asks the same of it
import logs  # noqa: E402 — carried beside this script; it owns where the run's state lives

SPECS = ROOT / "specs"
MODEL = ROOT / "docs/event-model/model.yaml"
PID = logs.run_dir(ROOT) / "model-next.pid"
#: The streams and contexts are named here, and the chart is only rendered from them afterwards — so this is
#: where the feature's shape is decided, by a session with nobody to ask. It was once told only to write the
#: model, named one stream from the spec's noun ("one record per leaver"), ran no seam test, and the chart
#: rendered one fairway of thirty-one serial slices. So it is told Step 9 by name, and how to stand in for
#: the person the context question is for.
PROMPT = (
    "The storyboard is approved. Model this product and stop before the chart. Read "
    "skills/event-modeling/SKILL.md, each specs/<feature>/spec.md, and the approved states in "
    "specs/<feature>/mockups/mock-states.md. Write docs/event-model/model.yaml from those drawings. "
    "Run Step 9 of skills/event-modeling/references/nine-steps.md in full: interrogate every stream before "
    "naming it, give each its invariant under `streams`, then `make seams` and the three seam tests. Record "
    "the context answer, one context included, as the next entry of specs/<feature>/decisions.md with the "
    "seam table (and a Why not split line for a context over twelve slices), Decided by: host (stage "
    "recommendation), Status: awaiting human confirmation, and post its question to the board as a "
    "`question` line, as commands/chart.md 'Record the context answer, every time' says. Proceed on your "
    "best-evidenced proposal; nobody is here to ask. Do not chart, split or implement. Give every slice you "
    "write `feature: <the directory under specs/ it belongs to>`."
)
#: A further feature: the model is global and already holds an earlier feature's slices, so this one's are
#: added to it. Said separately, because "write the model from those drawings" over a model that is somebody's
#: built product is an instruction to rewrite it.
FURTHER = (
    "The storyboard of specs/{feature} is approved, and docs/event-model/model.yaml already holds the slices "
    "of what was built before it. Add this feature to that model and stop before the chart. Read "
    "skills/event-modeling/SKILL.md, specs/{feature}/spec.md, and the approved states in "
    "specs/{feature}/mockups/mock-states.md. Add this feature's slices to docs/event-model/model.yaml, each "
    "with `feature: {feature}` and an id no slice has; never renumber, reorder, rename or rewrite a slice that "
    "is there, and where this feature changes what one does, model the change as a new slice and say which "
    "slice it changes in the decision entry. Run Step 9 of skills/event-modeling/references/nine-steps.md "
    "for the slices you add: interrogate every stream they touch before naming or extending it, then `make "
    "seams` and the three seam tests over the whole model. Record the context answer, one context included, "
    "as the next entry of specs/{feature}/decisions.md with the seam table, Decided by: host (stage "
    "recommendation), Status: awaiting human confirmation, and post its question to the board as a "
    "`question` line, as commands/chart.md 'Record the context answer, every time' says. Proceed on your "
    "best-evidenced proposal; nobody is here to ask. Do not chart, split or implement."
)


def profile() -> str:
    try:
        return str(json.loads((ROOT / "project.json").read_text(encoding="utf-8")).get("profile") or "")
    except (OSError, json.JSONDecodeError, AttributeError):
        return ""


def feature() -> str:
    """The feature being modelled: the one `.specify/feature.json` names, else the only one it could be."""
    return feature_stages.name_in_hand(ROOT)


def further() -> bool:
    """Whether the model already holds slices and none of them is the feature in hand's."""
    named = feature()
    return bool(named) and MODEL.is_file() and slices_named(MODEL.read_text(encoding="utf-8", errors="replace")) \
        and not feature_stages.modelled_for(ROOT, named)


def prompt() -> str:
    return FURTHER.format(feature=feature()) if further() else PROMPT


def modelled() -> bool:
    """Whether the model holds the feature in hand; whether it names a slice at all where nothing says which."""
    if not MODEL.is_file():
        return False
    named = feature()
    if named:
        return feature_stages.modelled_for(ROOT, named)
    return slices_named(MODEL.read_text(encoding="utf-8", errors="replace"))


def approved() -> bool:
    """Whether a person has approved the storyboard of the feature in hand and left nothing parked; of any
    feature, where nothing says which is in hand."""
    if feature():
        return feature_stages.approved_for(ROOT, feature())
    if not SPECS.is_dir():
        return False
    marked = list(SPECS.glob("*/mockups/mock-states.md"))
    if not marked:
        return False
    texts = [path.read_text(encoding="utf-8", errors="replace") for path in marked]
    return any("\u2014 approved" in text or "surfaces: none" in text for text in texts) and not any(
        "\u2014 parked" in text for text in texts)


def slices_named(text: str) -> bool:
    lines = [line for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")]
    for index, line in enumerate(lines):
        if line.startswith("slices:"):
            rest = line.partition(":")[2].strip()
            if rest:
                return rest not in ("[]", "{}", "null", "~")
            return index + 1 < len(lines) and lines[index + 1].startswith((" ", "-"))
    return False


def main(argv: list[str]) -> int:
    if argv == ["--prompt"]:
        print(prompt())
        return 0
    if profile() != "event-modelling":
        print("model: this project is not event-modelling; the chart is the next step, and approving the "
              "storyboard starts it", file=sys.stderr)
        return 2
    if not approved():
        print("model: no approved storyboard under specs/; approve it on the voyage first", file=sys.stderr)
        return 2
    if modelled():
        print(f"model: docs/event-model/model.yaml already holds {feature() or 'a slice'}; nothing to start",
              flush=True)
        return 0
    asked = prompt()
    try:
        chosen, said = harness.choose()
    except harness.NoHarness as refusal:
        print(f"model: {refusal}", file=sys.stderr)
        return 2
    template, why = harness.template(chosen)
    line = template.replace("{prompt}", shlex.quote(asked))
    print(f"{said}; {why}", flush=True)
    print(f"+ {line}", flush=True)
    environment = {**harness.child_environment(chosen), "SLIPWAI_STAGE": "model"}
    PID.parent.mkdir(parents=True, exist_ok=True)
    PID.write_text(f"{os.getpid()}\n", encoding="utf-8")
    try:
        exited = harness.run_session(shlex.split(line), ROOT, environment)
    finally:
        if PID.is_file() and PID.read_text(encoding="utf-8").strip() == str(os.getpid()):
            PID.unlink()
    if exited:
        print(f"model: the session exited {exited}; whatever it wrote is under docs/event-model/, "
              f"uncommitted or committed as it said", file=sys.stderr)
        return exited
    if not modelled():
        print(f"model: the session ended without a slice{' of ' + feature() if feature() else ''} in "
              "docs/event-model/model.yaml; read its last lines "
              "above", file=sys.stderr)
        return 1
    print(f"modelled: docs/event-model/model.yaml holds {feature() or 'a slice'}. Continue the build charts it.",
          flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

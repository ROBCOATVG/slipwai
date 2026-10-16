#!/usr/bin/env python3
"""The step after an approved storyboard on an event-modelling project: the model, and then a stop.

The chart is drawn from the model, so this does not chart, split or cast off. One headless session, told
`SLIPWAI_STAGE=model`, reading the specification and the states a person has just approved.

    python3 scripts/agents/model.py
"""
from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import harness  # noqa: E402

ROOT = harness.ROOT
SPECS = ROOT / "specs"
MODEL = ROOT / "docs/event-model/model.yaml"
PID = ROOT / ".slipwai" / "model-next.pid"
PROMPT = (
    "The storyboard is approved. Model this product and stop before the chart. Read "
    "skills/event-modeling/SKILL.md, each specs/<feature>/spec.md, and the approved states in "
    "specs/<feature>/mockups/mock-states.md. Write docs/event-model/model.yaml from those drawings. "
    "Do not chart, split or implement."
)


def profile() -> str:
    try:
        return str(json.loads((ROOT / "project.json").read_text(encoding="utf-8")).get("profile") or "")
    except (OSError, json.JSONDecodeError, AttributeError):
        return ""


def approved() -> bool:
    """Whether a person has approved a storyboard and left nothing parked."""
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
    del argv
    if profile() != "event-modelling":
        print("model: this project is not event-modelling; the chart is the next step, and approving the "
              "storyboard starts it", file=sys.stderr)
        return 2
    if not approved():
        print("model: no approved storyboard under specs/; approve it on the voyage first", file=sys.stderr)
        return 2
    if MODEL.is_file() and slices_named(MODEL.read_text(encoding="utf-8", errors="replace")):
        print("model: docs/event-model/model.yaml already names a slice; nothing to start", flush=True)
        return 0
    try:
        chosen, said = harness.choose()
    except harness.NoHarness as refusal:
        print(f"model: {refusal}", file=sys.stderr)
        return 2
    template, why = harness.template(chosen)
    line = template.replace("{prompt}", shlex.quote(PROMPT))
    print(f"{said}; {why}", flush=True)
    print(f"+ {line}", flush=True)
    environment = {**harness.child_environment(chosen), "SLIPWAI_STAGE": "model"}
    PID.parent.mkdir(parents=True, exist_ok=True)
    PID.write_text(f"{os.getpid()}\n", encoding="utf-8")
    try:
        done = subprocess.run(shlex.split(line), cwd=ROOT, env=environment, check=False)
    finally:
        if PID.is_file() and PID.read_text(encoding="utf-8").strip() == str(os.getpid()):
            PID.unlink()
    if done.returncode:
        print(f"model: the session exited {done.returncode}; whatever it wrote is under docs/event-model/, "
              f"uncommitted or committed as it said", file=sys.stderr)
        return done.returncode
    if not MODEL.is_file() or not slices_named(MODEL.read_text(encoding="utf-8", errors="replace")):
        print("model: the session ended without a slice in docs/event-model/model.yaml; read its last lines "
              "above", file=sys.stderr)
        return 1
    print("modelled: docs/event-model/model.yaml names a slice. Continue the build charts it.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

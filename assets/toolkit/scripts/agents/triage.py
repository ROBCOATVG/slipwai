#!/usr/bin/env python3
"""`/triage`: where each piece of feedback the board captured should go, proposed and never acted on.

A person says what using the built app showed them, on the board, and the board writes it under
`docs/feedback/`. This starts the one session that reads those records beside the specification, the
examples and the chart, and writes a proposal into each: a defect, a change, new scope, something already
planned, or a note. It refuses to start with nothing to read, and it checks afterwards that every record it
was given came back proposed, because a person is about to be asked to confirm what is in them.
"""
from __future__ import annotations

import re
import shlex
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import harness  # noqa: E402

ROOT = harness.ROOT
COMMAND = ROOT / "commands/triage.md"
PLACE = ROOT / "docs/feedback"
ROUTES = ("defect", "change", "scope", "planned", "note")
NAME = re.compile(r"^(\d{4})-[a-z0-9-]+\.md$")


def front(path: Path) -> dict[str, str]:
    """A record's front matter, as `slipwai.feedback.parse` reads it."""
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---\n"):
        return {}
    head = text[4:].partition("\n---\n")[0]
    return {key.strip(): value.strip() for key, colon, value in (line.partition(":") for line in head.splitlines())
            if colon and key.strip()}


def waiting() -> list[Path]:
    """Every record nobody has proposed a route for, dropped or confirmed."""
    if not PLACE.is_dir():
        return []
    found = []
    for path in sorted(PLACE.glob("*.md")):
        held = front(path) if NAME.match(path.name) else {}
        if held and not any(held.get(key) for key in ("proposed", "dropped", "confirmed")):
            found.append(path)
    return found


def main(argv: list[str]) -> int:
    given = waiting()
    if argv:
        given = [path for path in given if path.name[:4] in {one.zfill(4) for one in argv}]
    if not given:
        print("triage: nothing waiting under docs/feedback")
        return 0
    numbers = ",".join(path.name[:4] for path in given)
    try:
        chosen, said = harness.choose()
    except harness.NoHarness as refusal:
        print(f"triage: {refusal}", file=sys.stderr)
        return 2
    template, why = harness.template(chosen)
    prompt = harness.prompt_for(chosen, "triage", COMMAND, numbers)
    line = template.replace("{prompt}", shlex.quote(prompt))
    print(f"{said}; {why}", flush=True)
    print(f"+ {line}", flush=True)
    environment = {**harness.child_environment(chosen), "SLIPWAI_STAGE": "triage"}
    exited = harness.run_session(shlex.split(line), ROOT, environment)
    if exited:
        print(f"triage: the session exited {exited}; whatever it wrote is under docs/feedback", file=sys.stderr)
        return exited
    left = [path.name for path in given if not path.is_file() or front(path).get("route") not in ROUTES
            or not front(path).get("proposed")]
    if left:
        print(f"triage: the session ended with {', '.join(left)} not proposed; `make triage` tries again",
              file=sys.stderr)
        return 1
    print(f"triaged: {numbers}; confirm each on the board")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

#!/usr/bin/env python3
"""`/draft`: the constitution and the first specification, drafted from a product requirements document.

One headless session of the installed harness, asked for `/draft <document>` with `commands/draft.md` as its
rules, run in the foreground so that whoever started it — a person at a terminal, or the board after `./init`
— reads what it says as it says it. Nothing is written here: the session writes, and this starts it and says
how it ended. The session is told which stage it is (`SLIPWAI_STAGE=draft`) the way a captain tells a `/sail`
session, because the page it reads has two faces and the environment is how it tells them apart.

    python3 scripts/agents/draft.py              # docs/prd.md
    python3 scripts/agents/draft.py <document>   # a PRD somewhere else
"""
from __future__ import annotations

import shlex
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import harness  # noqa: E402

ROOT = harness.ROOT
COMMAND = ROOT / "commands/draft.md"
DEFAULT = "docs/prd.md"
SPECS = ROOT / "specs"


def specifications() -> list[Path]:
    """Every feature with a specification, which is what the session is expected to leave one of."""
    return sorted(SPECS.glob("*/spec.md")) if SPECS.is_dir() else []


def main(argv: list[str]) -> int:
    named = argv[0] if argv else DEFAULT
    document = Path(named) if Path(named).is_absolute() else ROOT / named
    if not document.is_file():
        print(f"draft: {named} is not a file; a product requirements document is the one thing this reads",
              file=sys.stderr)
        return 2
    try:
        chosen, said = harness.choose()
    except harness.NoHarness as refusal:
        print(f"draft: {refusal}", file=sys.stderr)
        return 2
    template, why = harness.template(chosen)
    where = document.relative_to(ROOT).as_posix() if document.is_relative_to(ROOT) else str(document)
    prompt = harness.prompt_for(chosen, "draft", COMMAND, where)
    line = template.replace("{prompt}", shlex.quote(prompt))
    before = set(specifications())
    print(f"{said}; {why}", flush=True)
    print(f"+ {line}", flush=True)
    environment = {**harness.child_environment(chosen), "SLIPWAI_STAGE": "draft"}
    exited = harness.run_session(shlex.split(line), ROOT, environment)
    if exited:
        print(f"draft: the session exited {exited}; whatever it wrote is on the current branch, "
              f"uncommitted or committed as it said", file=sys.stderr)
        return exited
    written = [path for path in specifications() if path not in before]
    if not written:
        print("draft: the session ended without writing a specs/<feature>/spec.md, so there is nothing to "
              "launch; read its last lines above", file=sys.stderr)
        return 1
    print(f"drafted: {', '.join(path.parent.relative_to(ROOT).as_posix() for path in written)} — read the "
          f"specification, then /launch (the board's Continue the build) charts and splits it and casts off")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

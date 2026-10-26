#!/usr/bin/env python3
"""One adoption step only the agent can take, handed to a headless session: the build floor, `smoke`, the parity
list, the module map, the risk register.

The board shows the adoption's sequence read off the tree, and takes the steps that are a command or a record
itself. These are neither: each is reading the old code and writing down what was proven, which is the agent's.
Without this the board's voyage stopped at the first of them with nothing to press. The session is given the step
as `next_steps` words it, told to read the decided strategy's playbook, and told to stop when the step is done;
the board reads the tree again when it ends, and the step is done when the tree says so — not when the session
says it is.

    python3 scripts/agents/step.py "<the step>" "<why, and what done looks like>"
"""
from __future__ import annotations

import shlex
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import harness  # noqa: E402

ROOT = harness.ROOT
#: The method's own folder: `layout.delivery` of an adopted repository.
DELIVERY = HERE.parent.parent


def prompt(action: str, why: str) -> str:
    where = DELIVERY.relative_to(ROOT).as_posix() if DELIVERY != ROOT else "."
    return (f"Take one step of this repository's adoption, and only that step: {action} — {why}.\n\n"
            f"The decided change strategy is the accepted ADR under `{where}/docs/adr/` and the `strategy` record in "
            f"`project.json`; its playbook is `{where}/docs/strategies/<strategy>.md`, and the build floor's is "
            f"`{where}/docs/strategies/build-floor.md`. Do what the playbook says for this step under that strategy, "
            "and nothing the strategy forbids: under a rewrite or a strangler fig the old code is pinned and "
            "characterised, never modernised. Record facts only once they are proven by running them. Leave no "
            "tracked file changed by a build: build output a build rewrites is untracked (`.gitignore`, "
            "`git rm -r --cached`) as part of the step. Commit what you wrote, with a message saying which step it "
            "is; a commit that changes the code that was here carries a `Legacy-change: build` trailer for the build "
            "floor, `Legacy-change: characterise` for `smoke` and the parity list — the gate refuses one without it "
            f"once a strangler fig or a rewrite is decided. Then stop: `slipwai adopt --next` (or `{where}/docs/adoption.md`) names the next step, and it is "
            "not yours to take.")


def main(argv: list[str]) -> int:
    if not argv:
        print("step: name the step to take", file=sys.stderr)
        return 2
    try:
        chosen, said = harness.choose()
    except harness.NoHarness as refusal:
        print(f"step: {refusal}", file=sys.stderr)
        return 2
    template, why = harness.template(chosen)
    line = template.replace("{prompt}", shlex.quote(prompt(argv[0], argv[1] if len(argv) > 1 else "")))
    print(f"{said}; {why}", flush=True)
    print(f"+ {line}", flush=True)
    environment = {**harness.child_environment(chosen), "SLIPWAI_STAGE": "adopt-step"}
    exited = harness.run_session(shlex.split(line), ROOT, environment)
    if exited:
        print(f"step: the session exited {exited}; whatever it wrote is on the current branch", file=sys.stderr)
    return exited


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

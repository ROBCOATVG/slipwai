"""`slipwai release-state`: where the product is, and how dark a merge is because of it.

`slipwai release-state` says the state, the mode, what a merge means and which declared flags the mode does
not need. `slipwai release-state <state> --why '<reason>'` moves the product: it records the state in
`project.json` and writes the ADR, and commits neither, because moving the product is a person's decision
and the commit is where they sign it. The project carries the same module as
`scripts/agents/release_state.py`, so a session in it needs no slipwai to read or move the state.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from .assets import this_command
from .errors import GenerationError, refuse
from .release_state import STATES, WHEN, Refused, move, said


def release_state_main(argv: list[str], root: Path | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog=f"{this_command()} release-state",
        description="Where the product is, and how dark a merge is because of it. With a state, move the "
                    "product there: " + "; ".join(f"{name}: {WHEN[name]}" for name in STATES) + ".",
    )
    parser.add_argument("state", nargs="?", choices=STATES, help="move the product to this state")
    parser.add_argument("--why", default="", help="what changed about who uses the product (required with a state)")
    arguments = parser.parse_args(argv)
    here = root or Path.cwd()
    prog = f"{this_command()} release-state"
    if not (here / "project.json").is_file():
        refuse(prog, GenerationError(f"{here} has no project.json; run this inside a project `slipwai generate` made"))
    if arguments.state is None:
        print(said(here))
        return
    try:
        written = move(here, arguments.state, arguments.why)
    except Refused as refused:
        refuse(prog, str(refused))
    print(f"release-state: the product is {arguments.state}. Wrote "
          + " and ".join(str(path.relative_to(here)) for path in written)
          + "; commit them together, and the next slice merges under the new mode.")

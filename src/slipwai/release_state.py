"""Where the product is, and how dark a merge is because of it: read, said, and moved.

A flag is how merging and releasing become two decisions. That is right for a product people use, and pure
drag for one nobody uses yet: a reader to call, two test paths, a key to hoist before every demo, and a
slice parked because its flag could be declared nowhere. lean-coffee-club opened a flag on its first
capability, and both of its first two slices stalled on flags no actor needed.

So the mode is not a setting to weigh per slice. **It follows from one fact about the product**, recorded as
`state` in `project.json`, and a person moves it:

    pre-launch   no production, or one only the team sees    → open      a merge is visible at once
    pilot        a production with known pilot users         → keystone  dark by omission
    live         real users use what trunk deploys            → flagged   dark behind a key seeded off

`promoted` is a fourth mode no state implies: production takes a promoted build rather than every push, a
fact about how a team deploys. A project declares it as `release` in `project.json` and keeps it.

**A project with no state recorded merges flagged**, as every project did before the state existed. Reading a
missing state as pre-launch would have turned a product with users into one whose merges go straight to
them, silently, on the next migration. So the absence is said, and a person records the state once.

Moving the state is a person's decision and an ADR, because it changes what every later merge means; a run
never moves it. `python3 scripts/agents/release_state.py --set <state> --why '<reason>'` writes both.

Standard library only: `make shared` carries this module into every generated project, which has no slipwai
to import, and both the keel and the project's own gates read it.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

#: Where a product is, in the order it moves.
STATES = ("pre-launch", "pilot", "live")
#: Where a newly generated product starts: nobody uses it yet. An adopted repository records none, because
#: the code it already had may well have users, and only a person knows.
NEW_STATE = STATES[0]
#: Version 2's first spellings, read as the state they meant and never written again.
EARLIER = {"slipway": "pre-launch", "sea-trials": "pilot", "in-service": "live"}
#: How dark a merge is.
MODES = ("open", "keystone", "flagged", "promoted")
MODE_OF_STATE = {"pre-launch": "open", "pilot": "keystone", "live": "flagged"}
#: The mode of a project that has recorded no state: today's behaviour, never a silent change to it.
UNRECORDED_MODE = "flagged"
WHAT_A_MERGE_MEANS = {
    "open": "visible at once: trunk is the demo, and no slice opens a flag",
    "keystone": "dark by omission: every slice of a capability lands except its entry point, which is the "
                "capability's last slice",
    "flagged": "dark behind a key seeded off, which only a person hoists",
    "promoted": "visible on trunk and in preview; production takes only what passes the promotion gate",
}
WHEN = {
    "pre-launch": "no production yet, or one only the team sees",
    "pilot": "known pilot users use what trunk deploys",
    "live": "real users use what trunk deploys, and must not be surprised",
}
#: A declared flag in `infra/service/flags.auto.tfvars`: the key and its value.
DECLARED = re.compile(r'^\s*(?P<key>[A-Za-z_][A-Za-z0-9_-]*)\s*=\s*"(?P<value>[^"]*)"', re.MULTILINE)
FLAGS = "infra/service/flags.auto.tfvars"


class Refused(ValueError):
    """A state that is not one, or a move that is not allowed, said as the one line a person reads."""


def spelled(state: object) -> str | None:
    """The state a recorded value means, or None where nothing is recorded or it is not one."""
    if not isinstance(state, str):
        return None
    state = EARLIER.get(state, state)
    return state if state in STATES else None


def state_of(document: dict) -> str | None:
    """The product's state from a `project.json` document, or None where none is recorded."""
    return spelled(document.get("state"))


def mode_of(document: dict) -> str:
    """The mode this product merges under: `promoted` where declared, else what its state implies."""
    if document.get("release") == "promoted":
        return "promoted"
    state = state_of(document)
    return MODE_OF_STATE[state] if state is not None else UNRECORDED_MODE


def read(root: Path) -> dict:
    """The project's `project.json`, or an empty document where it cannot be read."""
    try:
        document = json.loads((root / "project.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return {}
    return document if isinstance(document, dict) else {}


def declared_flags(root: Path) -> dict[str, str]:
    """Every flag the project declares, with its seed value."""
    try:
        text = (root / FLAGS).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return {}
    return {match["key"]: match["value"] for match in DECLARED.finditer(text)}


def said(root: Path) -> str:
    """What `release_state.py` prints: the state, the mode, what a merge means, and what to do about it."""
    document = read(root)
    state, mode = state_of(document), mode_of(document)
    lines = []
    if state is None:
        lines.append(f"state: unrecorded · mode: {mode} — a merge is {WHAT_A_MERGE_MEANS[mode]}.")
        lines.append("No state is recorded in project.json, so this project merges flagged, as it always has. "
                     "A person records it once: python3 scripts/agents/release_state.py --set <state> --why "
                     "'<reason>' (" + "; ".join(f"{name}: {WHEN[name]}" for name in STATES) + ").")
    else:
        lines.append(f"state: {state} · mode: {mode} — a merge is {WHAT_A_MERGE_MEANS[mode]}.")
    flags = declared_flags(root)
    if mode in ("open", "keystone") and flags:
        held = ", ".join(f"{key} = {value}" for key, value in sorted(flags.items()))
        lines.append(f"{len(flags)} flag(s) declared that this mode does not need: {held}. Each can be struck "
                     "with the reads and the off-path tests that hold it, in a change of its own.")
    return "\n".join(lines)


def adr_number(root: Path) -> int:
    """The next ADR number under `docs/adr/`."""
    numbers = [int(match.group(1)) for path in (root / "docs/adr").glob("*.md")
               if (match := re.match(r"^(\d{4})-", path.name))]
    return max(numbers, default=0) + 1


def adr(number: int, before: str | None, after: str, why: str, today: date) -> str:
    """The ADR that records the move: what the state was, what it is, why, and what a merge now means."""
    was = before or "unrecorded"
    mode = MODE_OF_STATE[after]
    return f"""# {number:04d}. The product is {after}

Date: {today.isoformat()}

## Status

Accepted

## Context

The product's state was **{was}**. It is a fact about the product, recorded as `state` in `project.json`,
and the release mode follows from it: how dark a merge is. A person moves it, because it changes what every
later merge means; a run never does.

{why.strip()}

## Decision

The product is **{after}**: {WHEN[after]}. It merges **{mode}**: a merge is {WHAT_A_MERGE_MEANS[mode]}.

## Consequences

- `/sail`'s release stage reads this mode once per slice, from `python3 scripts/agents/release_state.py`.
""" + {
        "open": "- No slice opens a flag. A flag already declared can be struck with the code and the tests that "
                "hold it.\n",
        "keystone": "- Each capability's entry point — the route, menu item or command that exposes it — lands "
                    "with its last slice; the slices before it land unreachable.\n",
        "flagged": "- Each releasable capability is held behind a flag seeded `off` until a person hoists it.\n",
    }[mode] + "- Moving the state again is another ADR like this one.\n"


def move(root: Path, to: str, why: str, today: date | None = None) -> list[Path]:
    """Record the state in `project.json` and write the ADR; the paths written. Nothing is committed."""
    after = spelled(to)
    if after is None or to not in STATES:
        raise Refused(f"{to!r} is not a product state; one of: {', '.join(STATES)}")
    if not why.strip():
        raise Refused("--why needs the reason: what changed about who uses the product")
    path = root / "project.json"
    try:
        text = path.read_text(encoding="utf-8")
        document = json.loads(text)
    except (OSError, ValueError, UnicodeDecodeError) as error:
        raise Refused(f"project.json cannot be read: {error}") from error
    before = state_of(document)
    if before == after:
        raise Refused(f"the product is already {after}")
    ordered: dict = {}
    # Where `metadata` writes it — after `shape`, or after `target` where there is no shape — so the next
    # migration's replay puts it on the same line. Anywhere else, git merged the two and the key was there twice.
    beside = "shape" if "shape" in document else "target"
    for key, value in document.items():
        if key == "state":
            continue
        ordered[key] = value
        if key == beside:
            ordered["state"] = after
    ordered.setdefault("state", after)
    path.write_text(json.dumps(ordered, indent=2) + "\n", encoding="utf-8")
    number = adr_number(root)
    record = root / "docs/adr" / f"{number:04d}-the-product-is-{after}.md"
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(adr(number, before, after, why, today or date.today()), encoding="utf-8")
    return [path, record]


def main(argv: list[str] | None = None, root: Path | None = None) -> int:
    parser = argparse.ArgumentParser(description="Where the product is, and how dark a merge is because of it.")
    parser.add_argument("--set", dest="to", choices=STATES, help="move the product to this state (a person's)")
    parser.add_argument("--why", default="", help="with --set: what changed about who uses the product")
    parser.add_argument("--mode", action="store_true", help="print the mode alone")
    arguments = parser.parse_args(argv)
    here = root or Path.cwd()
    if arguments.to:
        try:
            written = move(here, arguments.to, arguments.why)
        except Refused as refused:
            print(f"release-state: {refused}", file=sys.stderr)
            return 2
        print(f"release-state: the product is {arguments.to}; wrote " + ", ".join(
            str(path.relative_to(here)) for path in written) + ". Commit both together.")
        return 0
    print(mode_of(read(here)) if arguments.mode else said(here))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

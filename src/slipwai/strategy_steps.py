"""The steps a decided strategy adds to an adoption, between the decision and the first specification.

The sequence used to go from "an accepted ADR" straight to the constitution and the first spec, whatever the ADR
said — so a rewrite's first feature was specified for the old stack, because nothing had made the new one, and a
strangler fig's slices landed in the old app, because nothing said a new home had to exist first. Each playbook
(`docs/strategies/`) names what has to hold before the first feature; this reads the decided strategy and its lines
off the record and puts those steps in the sequence, each read off the tree like the rest:

- **the build floor** first, whatever the strategy — pinned as it is or brought up to date, as its `Build:` line says;
- **`smoke`** for every application that was here, before anything is pinned against it;
- **the new home** where a strangler fig grows it `beside` or a rewrite builds it — generated, on the stack the ADR
  records — or, `inside`, **the modules declared** with their violations frozen;
- **the behaviour to keep**, `docs/parity.md`, where everything moves: a rewrite, or a strangler fig with `End: all`;
- **the risk register**, where the system is left as it is.

A strategy whose ADR is missing a line it needs adds none of these: the decision step is still the one to take.
"""
from __future__ import annotations

import re
from pathlib import Path

from .layout import Layout
from .origin import Adoption
from .services import App, wrapped_of

PARITY = "docs/parity.md"
MODULE_MAP = "docs/module-map.md"
RISK_REGISTER = "risk-register.md"
#: The last step here when a rewrite is built in a new repository: the rest of the voyage is that project's.
CONTINUE = "continue in the new system at"
STACK = re.compile(r"(backend|frontend|persistence)\s+([\w.-]+)")


def stack_of(lines: dict[str, str]) -> dict[str, str]:
    """`backend <b> · frontend <f> · persistence <p>`, as its three answers."""
    said = lines.get("Stack") or lines.get("New home stack") or ""
    return {key: value for key, value in STACK.findall(said)}


def home_of(strategy: str, lines: dict[str, str]) -> tuple[str, str]:
    """Where the new home lives and its path: `inside`, `beside` or `new-repo`, then what follows the word."""
    said = (lines.get("New home") if strategy == "strangler-fig" else lines.get("Home")) or ""
    place, _, where = said.partition(" ")
    return place.lower(), where.strip()


def name_of(where: str, fallback: str) -> str:
    """The new home's service name: the last part of its path."""
    return (Path(where).name if where else "") or fallback


def new_system(root: Path, adoption: Adoption) -> Path | None:
    """The new repository a rewrite is built in, once it exists; None for anything else."""
    record = adoption.strategy or {}
    if record.get("decided") != "rewrite" or record.get("missing"):
        return None
    place, where = home_of("rewrite", record.get("lines") or {})
    home = (root / where).resolve() if place == "new-repo" and where else None
    return home if home and (home / "project.json").is_file() else None


def everything_moves(strategy: str, lines: dict[str, str]) -> bool:
    return strategy == "rewrite" or str(lines.get("End", "")).lower().startswith("all")


def steps(root: Path, layout: Layout, adoption: Adoption, apps: list[App],
          name: str = "next") -> list[tuple[str, str, bool]]:
    """`(action, why, done)` for each step the decided strategy adds, in order; none while its ADR is incomplete."""
    record = adoption.strategy or {}
    strategy, lines = record.get("decided"), record.get("lines") or {}
    if not strategy or record.get("missing"):
        return []
    found: list[tuple[str, str, bool]] = []
    build_open = any(step.get("kind") == "build" for step in record.get("programme") or [] if isinstance(step, dict))
    found.append((
        "the build floor, in the agent",
        f"each application builds from a clean clone through one declared build, every dependency and tool version "
        f"written down — `{lines.get('Build') or 'as the strategy says'}`. `docs/strategies/build-floor.md` has the "
        "eight criteria; it is first whatever the strategy, because nothing can be pinned, upgraded or replaced "
        "against a build that only works on one machine",
        not build_open,
    ))
    unproven = [app.name for app in wrapped_of(apps) if not (app.commands or {}).get("smoke")]
    found.append((
        "prove each application starts (`smoke`), in the agent",
        (f"{', '.join(unproven)} — " if unproven else "") + "run it once the way the README or CI says, write what "
        f"was proven in `{layout.under('survey/running.md')}`, and record the command as `smoke`: before anything is "
        "characterised against it",
        not unproven,
    ))
    if strategy in ("strangler-fig", "rewrite"):
        place, where = home_of(strategy, lines)
        stack = stack_of(lines)
        on = " · ".join(f"{key} {value}" for key, value in stack.items()) or "the stack the ADR records"
        if place == "inside":
            found.append((
                "declare the modules and freeze their violations, in the agent",
                f"the new home is modules inside the old deployable: the module map in `{layout.under(MODULE_MAP)}` "
                "and every existing violation frozen as a ratcheted baseline before the first feature, so the first "
                "feature lands in a module (`docs/strategies/target-shape.md`)",
                (root / layout.under(MODULE_MAP)).is_file(),
            ))
        elif place == "new-repo":
            home = (root / where).resolve() if where else None
            found.append((
                "generate the new system",
                f"a new project at `{where}` on {on}: the rewrite is built there, and this repository's voyage "
                "hands over to it",
                bool(home and (home / "project.json").is_file()),
            ))
        else:
            found.append((
                "generate the new home",
                f"`add-service {name_of(where, name)}` beside the old code, on {on} — current from day one, and "
                "where every new feature is built",
                any(app.generated for app in apps),
            ))
    if strategy in ("strangler-fig", "rewrite") and everything_moves(strategy, lines):
        found.append((
            "the behaviour to keep, `docs/parity.md`, in the agent",
            f"everything moves, so every behaviour of the old system is listed in `{layout.under(PARITY)}` and "
            "marked preserve, preserve-quirk, fix or drop from how it is used — port the behaviour, not the bugs",
            (root / layout.under(PARITY)).is_file(),
        ))
    if strategy == "leave-it":
        found.append((
            "the risk register, in the agent",
            f"each accepted risk in `{layout.under(RISK_REGISTER)}` with its compensating control and its owner, "
            f"reviewed by `{lines.get('Review', 'the review date')}` (`docs/strategies/leave-it.md`)",
            (root / layout.under(RISK_REGISTER)).is_file(),
        ))
    return found

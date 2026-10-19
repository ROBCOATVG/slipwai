"""`slipwai telegraph`: ringing the harbour's one lever, and setting a single number under it.

Three shapes, and the third is the one that matters. `slipwai telegraph` shows where it is. `slipwai
telegraph <position>` rings it, which sets every number together. `slipwai telegraph --set boilers=2`
changes one and leaves the rest, and the board then says `half-ahead, adjusted` — because a board reporting
a position the numbers do not match is a board that is lying.

`delegate` and `cycle` belong to `/sail` and are mirrored here, so a person sets every width in one place;
`--set` writes them back to `.specify/sail.json`, where `/sail` reads them. The telegraph never rings them,
because they are not the harbour's to decide.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .assets import this_command
from .errors import GenerationError, refuse
from .project.harbour import CONFIG
from .telegraph import LISTS, MEANS, MIRRORED, POSITIONS, WIDTHS, Refused, applied, described, parse_setting, scaled

SAIL = ".specify/sail.json"


def read(path: Path) -> dict:
    """The file, or a refusal. Never a fresh default: these numbers are what a person decided, and quietly
    starting again from the generated ones is how a run goes fast on a day somebody slowed it down."""
    if not path.is_file():
        raise GenerationError(f"{path} is not here. Run this inside a project `slipwai generate` made, or "
                              f"`slipwai migrate` to bring a older one up to a keel that has a telegraph")
    try:
        held = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError) as error:
        raise GenerationError(f"{path} cannot be read ({error}), and it is what this run is held to") from None
    if not isinstance(held, dict):
        raise GenerationError(f"{path} is not an object, so there is nothing in it to set")
    return held


def write(path: Path, held: dict) -> None:
    path.write_text(json.dumps(held, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def shown(held: dict) -> list[str]:
    """Where the telegraph is, and every number under it."""
    at = str(held.get("position", "full-ahead"))
    lines = [f"telegraph: {described(at, held)}"]
    width = max(len(name) for name in {**MEANS, **WIDTHS})
    for name, said in {**MEANS, **WIDTHS}.items():
        lines.append(f"  {name:<{width}}  {held.get(name, 'unset')!s:<8}  {said}")
    return lines


def sail_settings(root: Path) -> dict:
    path = root / SAIL
    try:
        held = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return {}
    return held if isinstance(held, dict) else {}


def ring(root: Path, name: str) -> list[str]:
    """Ring a position: every number together, and the stage budgets scaled with them."""
    path = root / CONFIG
    held = read(path)
    whole = applied(name, held)
    if isinstance(held.get("stages"), dict):
        whole["stages"] = scaled(held["stages"], float(whole["stage_scale"]))
    write(path, whole)
    return [f"telegraph: rung to {name}", *shown(whole)[1:]]


def not_on_the_chart(known: list[str], wanted: list[str]) -> list[str]:
    """The names in `wanted` the chart has not got — slice 18.2, and only while a person is here.

    Two moments and two answers, deliberately. **Here** somebody has just typed the name, so a typo that
    quietly did nothing is the worst outcome there is and it is refused. **At read time** `fleet.py` and
    `clearance.py` ignore a name they do not know, because the chart moves under a setting that outlives
    it — a fairway renamed by a later split would otherwise park the whole run from a file nobody looked at.

    An empty `known` refuses nothing: before the chart stage there is nothing to check against, and a
    priority set then is a person saying which stream they want first rather than a mistake.
    """
    return [name for name in wanted if name not in known] if known else []


def charted_fairways(root: Path) -> list[str]:
    """The fairways this project has, asked of its own clearance script through the offline JSON port.

    The one reader of `chart.yaml` the keel allows itself, so the names checked here are the same ones the
    fleet will light rather than a second parse of the file that could disagree with it. Anything that goes
    wrong reads as "cannot say", which refuses nothing.
    """
    from .fleet import clearance_query
    try:
        _, found, fault = clearance_query(root)
    except Exception:  # pragma: no cover - a project whose clearance will not run refuses nothing
        return []
    if fault or not isinstance(found, dict):
        return []
    named = found.get("fairways")
    return [str(name) for name in named] if isinstance(named, list) else []


def set_one(root: Path, pairs: list[str]) -> list[str]:
    """Set named numbers one at a time, each where it belongs: the harbour's here, `/sail`'s in its own file."""
    harbour_path, sail_path = root / CONFIG, root / SAIL
    held = read(harbour_path)
    settings = sail_settings(root)
    said: list[str] = []
    for pair in pairs:
        name, value = parse_setting(pair)
        if name in LISTS:
            wanted = [str(one) for one in value] if isinstance(value, list) else []
            missing = not_on_the_chart(charted_fairways(root), wanted) if wanted else []
            if missing:
                raise Refused(f"the chart has no fairway called {missing[0]!r}. `{name}` names the "
                              f"fairways the chart has, in the order you want them lit")
            held[name] = wanted
            names = ", ".join(wanted) if wanted else "the chart's own order"
            said.append(f"  {name} = {names}")
            continue
        if name in MIRRORED:
            settings[name] = value
            said.append(f"  {name} = {value}  (in {SAIL}, which is where `/sail` reads it)")
        else:
            held[name] = value
            said.append(f"  {name} = {value}")
    write(harbour_path, held)
    if settings:
        sail_path.parent.mkdir(parents=True, exist_ok=True)
        write(sail_path, settings)
    at = str(held.get("position", "full-ahead"))
    return [f"telegraph: {described(at, held)}", *said,
            f"`{this_command()} telegraph {at}` puts every number back to what that position means"]


def telegraph_main(argv: list[str]) -> None:
    prog = f"{this_command()} telegraph"
    parser = argparse.ArgumentParser(
        prog=prog, description="Where this harbour's lever is set, and what every number under it is",
        epilog="Ringing a position sets every number together and resets any that were adjusted. "
               "`--set` changes one and leaves the rest, and the board then says the position with "
               "`adjusted` after it. Fastest first: " + ", ".join(POSITIONS) + ".")
    parser.add_argument("position", nargs="?", choices=POSITIONS, help="the position to ring")
    parser.add_argument("--set", dest="pairs", nargs="+", metavar="<name>=<value>", default=None,
                        help="set one number and leave the others")
    parser.add_argument("--root", default=".", metavar="<directory>", help="the harbour (default: here)")
    parsed = parser.parse_args(argv)
    root = Path(parsed.root).expanduser()
    try:
        if parsed.position and parsed.pairs:
            raise GenerationError("ring a position or set a number, not both in one command: ringing resets "
                                  "every number, so the two together would not mean what either does alone")
        if parsed.pairs:
            print("\n".join(set_one(root, parsed.pairs)))
        elif parsed.position:
            print("\n".join(ring(root, parsed.position)))
        else:
            print("\n".join(shown(read(root / CONFIG))))
    except (GenerationError, Refused) as error:
        refuse(prog, error)

"""The target checks that need the package imported, run in an interpreter of their own.

`python -m slipwai.conformance.target_probe <package> <report>` imports the package's module, reads
`TARGET`, and writes `{"findings": {check: [line, …]}, "not_run": {check: reason}}` to `<report>`. It exits
0 whatever it found: a finding is the package's, and only a crash of the suite itself exits otherwise.

In a child and not in the caller, for the reason the language suite forks: importing a package runs its
code, and a suite that ran it in its own process would be one whose verdict a package could change. Nothing
it prints is the report, so nothing a package prints is.
"""
from __future__ import annotations

import importlib
import json
import signal
import sys
from pathlib import Path
from typing import Any

from ..target_protocol import DEPLOYMENT_SHAPES, SCRIPTS, SHAPES, Target, faults

#: Why `shapes` was not read: the package did not import, so there is no `TARGET` to ask.
UNLOADED = "the package did not load, so nothing it answers can be read"


def module_of(name: str) -> str:
    """The module a target package's `TARGET` is imported from, derived from its name as a language's is."""
    return f"slipwai_target_{name.replace('-', '_')}"


def imported(package: Path, name: str) -> tuple[Target | None, list[str]]:
    """The package's `TARGET`, or the one line saying why it could not be read."""
    module = module_of(name)
    sys.path.insert(0, str(package))
    try:
        found = importlib.import_module(module)
    except BaseException as error:  # whatever a package's import raises is a finding, never a traceback
        return None, [f"{module} could not be imported: {type(error).__name__}: {error}"]
    target = getattr(found, "TARGET", None)
    if target is None:
        return None, [f"{module} has no TARGET. A target package exports one, as a language package "
                      f"exports its LANGUAGE"]
    if not isinstance(target, Target):
        return None, [f"{module}'s TARGET is a {type(target).__name__}, not a Target. Import it from "
                      f"`slipwai.target_protocol`, which is the one the keel reads"]
    if target.name != name:
        return None, [f"{module}'s TARGET is called {target.name} and its target.json names {name}. The two "
                      f"are one thing: `--target {name}` has to find the answers filed under that name"]
    return target, []


def shape_findings(package: Path, target: Target) -> list[str]:
    """Every file the stacks and the scripts name that the package does not ship.

    The one check that needs the answers *and* the directory at once, which is why it is here rather than
    in the parent: a stack made of files nobody ships applies nothing, and the first anyone would know is
    an apply that failed in somebody's account.
    """
    named: list[tuple[str, str]] = []
    shapes: Any = target.answers.get(SHAPES, {})
    if isinstance(shapes, dict):
        named += [(f"the {shape} stack", str(path)) for shape, paths in shapes.items()
                  if isinstance(paths, (list, tuple)) for path in paths]
    choices = target.answers.get(DEPLOYMENT_SHAPES, {})
    if isinstance(choices, dict):
        for shape, row in choices.items():
            if not isinstance(row, dict):
                continue
            for phase, files in row.get("stacks", {}).items():
                if isinstance(files, dict):
                    named += [(f"{shape} {phase}/{where}", str(source)) for where, source in files.items()]
            named += [(f"{shape} {where}", str(source)) for where, source in row.get("scripts", {}).items()]
    scripts: Any = target.answers.get(SCRIPTS, {})
    if isinstance(scripts, dict):
        named += [(f"{where}", str(source)) for where, source in scripts.items()]
    return [f"{what} names {path}, which this package does not ship" for what, path in named
            if not (package / path).is_file()]


def probe(package: Path, name: str, managed: bool) -> dict[str, dict]:
    """The two checks that need the package imported: what its `TARGET` answers, and what it ships."""
    target, refused = imported(package, name)
    if target is None:
        return {"findings": {"protocol": refused}, "not_run": {"shapes": UNLOADED}}
    return {"findings": {"protocol": faults(target, managed), "shapes": shape_findings(package, target)},
            "not_run": {}}


def main(argv: list[str]) -> int:
    signal.signal(signal.SIGTERM, lambda _number, _frame: sys.exit(128 + signal.SIGTERM))
    package, name, managed, destination = Path(argv[0]), argv[1], argv[2] == "managed", Path(argv[3])
    destination.write_text(json.dumps(probe(package.absolute(), name, managed)), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

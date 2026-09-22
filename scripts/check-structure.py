#!/usr/bin/env python3
"""Fail when the factory's own source stops having the shape it claims.

The generated projects get `scripts/check-imports.py`, which fails a build when domain code names an outer
layer. This is the same idea turned on the factory: the rules below are the architecture, written where they
can be enforced rather than only described, so a module cannot quietly start depending on the command line
or grow back into a second `generate.py`.

Three rules, each with a failure it exists to prevent:

1. **Direction.** Imports point inward, toward the tiers that know less. A part of the generated repository
   may read the selection; the selection may not read a part. Without this, `selection` gains an import of
   `project.makefile` "just to reuse a string" and the thing every module depends on starts depending on
   everything.
2. **No cycles.** Python enforces this at import time, but only for the paths that actually get imported —
   and it reports it as an ImportError from whichever module happened to be first. Checked here, a cycle is
   a named pair before anyone pays for it.
3. **Size.** A module over the budget is the state this package was split out of: a file nobody reads
   end to end, whose contents are found by grep and edited in the dark.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src/slipwai"

# Each tier may import from earlier tiers and from nothing later. `project.*` is one tier rather than a
# stack of sub-tiers on purpose: within it the order is enforced by rule 2, which needs no maintenance, and
# a hand-kept sub-tier list would be a second place to update every time a part is added.
TIERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    # Where the factory's own material is, how a refusal is raised, how a version string reads, what the
    # entry for the release in flight is made of, what a project's name becomes in each ecosystem's
    # namespace, and which half-built shape a run has opted into.
    ("foundation", ("assets", "errors", "versions", "changelog", "naming", "experimental")),
    # What a caller may ask for, what an option declares about the feature it owns, what an optional
    # dev-tooling hook is, where a project goes to production, what a snippet resolves to, what differs
    # per backend language and where each backend answers its two probes — and what a build ecosystem's
    # files say, for a repository the factory did not make.
    ("contract", ("catalog", "axes", "features", "extensions", "targets", "examples", "backends", "images",
                  "ecosystems", "probes")),
    # One validated answer per axis, which applications a project has, what they add up to being able to do,
    # how a written manifest reads back into that list, how a canonical toolkit file reaches a project, where
    # the delivery material lives — and the build wrapper a wrapped Java application runs through, written
    # where its repository has none.
    ("answers", ("selection", "services", "capabilities", "manifest", "tooling", "toolkit", "layout", "survey",
                 "delivery_facts", "origin", "wrappers", "convergence", "structure", "platform", "strategy",
                 "quick_wins", "programme")),
    # One module per part of the repository being generated.
    ("parts", ("project",)),
    # The whole of a project, assembled and written — one more service added to one that exists — and the
    # whole of it again, from a newer factory, as a commit the existing one can merge, that merge made, what
    # the merge could not do said out loud, and where an adoption stands in the sequence it was given.
    ("assembly", ("scaffold", "add_service", "replay", "migrate", "catch_up", "adopt", "adopt_report", "resurvey",
                  "converge", "next_steps")),
    # The command line, and the entry point the executable is built from.
    ("edge", ("cli", "cli_add", "cli_adopt", "cli_interview", "cli_prompts", "preflight", "upgrade", "__main__")),
    # The package's own `__init__`: last, so it may name anything and nothing may name it.
    ("package", ("__init__",)),
)

# A module over this is the file this package was split out of. Tests get the same budget: a suite nobody
# reads is a suite whose duplicate coverage nobody notices.
MODULE_BUDGET = 350
# A package facade dispatches; anything longer is behaviour hiding somewhere no one looks for it.
FACADE_BUDGET = 40


def tier_of(module: str) -> tuple[int, str]:
    """Which tier a dotted module name belongs to, by its first matching prefix."""
    for index, (name, prefixes) in enumerate(TIERS):
        for prefix in prefixes:
            if module == prefix or module.startswith(f"{prefix}."):
                return index, name
    raise SystemExit(f"check-structure: {module} belongs to no declared tier — add it to TIERS")


def module_name(path: Path) -> str:
    relative = path.relative_to(PACKAGE).with_suffix("")
    parts = [part for part in relative.parts if part != "__init__"]
    return ".".join(parts) if parts else "__init__"


def imported_modules(path: Path, text: str) -> list[tuple[int, str]]:
    """Every sibling module this one imports, as (line, dotted name). Absolute imports are not ours."""
    here = path.relative_to(PACKAGE).parent.parts
    found: list[tuple[int, str]] = []
    for node in ast.walk(ast.parse(text)):
        if not isinstance(node, ast.ImportFrom) or not node.level:
            continue
        # `from .x import y` is level 1 and relative to this module's own package; each extra dot climbs one.
        base = list(here[: len(here) - (node.level - 1)])
        if node.module is None:
            # `from . import x, y` names submodules of the package, not members of a module.
            found += [(node.lineno, ".".join([*base, alias.name])) for alias in node.names]
            continue
        target = ".".join([*base, node.module])
        if target:
            found.append((node.lineno, target))
    return found


def main() -> int:
    violations: list[str] = []
    modules = sorted(path for path in PACKAGE.rglob("*.py"))
    graph: dict[str, set[str]] = {}

    for path in modules:
        relative = path.relative_to(ROOT).as_posix()
        text = path.read_text()
        name = module_name(path)
        length = len(text.splitlines())
        budget = FACADE_BUDGET if path.name == "__init__.py" else MODULE_BUDGET
        if length > budget:
            what = "package facade" if path.name == "__init__.py" else "module"
            violations.append(f"{relative}: {length} lines in one {what}, over the {budget}-line budget")
        if ast.get_docstring(ast.parse(text)) is None:
            violations.append(f"{relative}: no module docstring saying what part this is")

        index, tier = tier_of(name)
        graph[name] = set()
        for line, target in imported_modules(path, text):
            target_index, target_tier = tier_of(target)
            graph[name].add(target)
            if target_index > index:
                violations.append(
                    f"{relative}:{line}: {tier} imports {target_tier}: {name} -> {target}. "
                    "Imports point inward; move what is shared into a tier both may read."
                )

    # Rule 2: a cycle anywhere, reported as the pair that closes it rather than as an ImportError later.
    for name in sorted(graph):
        seen: set[str] = set()
        stack = [(name, [name])]
        while stack:
            current, route = stack.pop()
            for target in sorted(graph.get(current, ())):
                if target == name:
                    violations.append(f"import cycle: {' -> '.join([*route, target])}")
                    stack.clear()
                    break
                if target not in seen:
                    seen.add(target)
                    stack.append((target, [*route, target]))

    for path in sorted((ROOT / "tests").glob("*.py")):
        length = len(path.read_text().splitlines())
        if length > MODULE_BUDGET:
            relative = path.relative_to(ROOT).as_posix()
            violations.append(f"{relative}: {length} lines in one suite, over the {MODULE_BUDGET}-line budget")

    if violations:
        print("check-structure: the source does not have the shape it claims\n", file=sys.stderr)
        for violation in sorted(set(violations)):
            print(f"  {violation}", file=sys.stderr)
        return 1
    print(f"check-structure: {len(modules)} modules, {len(TIERS)} tiers, no upward imports and no cycles")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

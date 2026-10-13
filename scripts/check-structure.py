#!/usr/bin/env python3
"""Fail when the keel's own source stops having the shape it claims.

The generated projects get `scripts/check-imports.py`, which fails a build when domain code names an outer
layer. This is the same idea turned on the keel: the rules below are the architecture, written where they
can be enforced rather than only described, so a module cannot quietly start depending on the command line
or grow back into a second `generate.py`.

Four rules, each with a failure it exists to prevent:

1. **Direction.** Imports point inward, toward the tiers that know less. A part of the generated repository
   may read the selection; the selection may not read a part. Without this, `selection` gains an import of
   `project.makefile` "just to reuse a string" and the thing every module depends on starts depending on
   everything.
2. **No cycles.** Python enforces this at import time, but only for the paths that actually get imported —
   and it reports it as an ImportError from whichever module happened to be first. Checked here, a cycle is
   a named pair before anyone pays for it.
3. **Size.** A module over the budget is the state this package was split out of: a file nobody reads
   end to end, whose contents are found by grep and edited in the dark.
4. **The import surface.** A package may import only the keel modules `import-surface.txt` lists *for its
   kind*, and that file may list only modules the keel has. Without it, a package leans on a module nobody
   promised it, and a rename inside the keel breaks a language built somewhere this repository cannot see.
   The file is a section per kind — `[language]`, `[target]` — because the two are promised different
   things and the ceiling is on how far into the keel any one kind may reach, not a budget shared between
   them.

The keel knows no package in the other direction either: an absolute import of a `slipwai_language_*` or a
`slipwai_target_*` module anywhere in `src/` is a violation, whichever package it names. A target is on that
list for the reason a language is — the keel names no product, and the keel naming a cloud is precisely what
the clouds were made packages to stop. Written as a rule rather than left as a habit, because the whole of
phase 10 is undone by one `import slipwai_target_aws` that nothing refuses.

Every module the keel has must be named in TIERS. That is deliberate friction. A module arrives with the
slice that brings it back, and the slice says out loud which tier it belongs to.
"""

from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KEEL = ROOT / "src/slipwai"

# Each tier may import from earlier tiers and from nothing later. `project.*` is one tier rather than a
# stack of sub-tiers on purpose: within it the order is enforced by rule 2, which needs no maintenance, and
# a hand-kept sub-tier list would be a second place to update every time a part is added.
#
# The tiers are the architecture and they are all declared here from the first slice. Their members are
# not: a tier is empty until the phase that brings its modules back fills it, one slice at a time.
TIERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    # Where the keel's own material is, how a refusal is raised, how a version string reads, what the entry
    # for the release in flight is made of, and what a project's name becomes in each ecosystem's namespace.
    # `ed25519` is here and imports nothing: it is arithmetic over one curve, the standard library's own
    # SHA-512 and no opinion about packages — which is what makes it testable against the RFC's vectors
    # alone (slice 6.5b).
    ("foundation", ("assets", "errors", "versions", "changelog", "whats_new", "naming", "logs",
                    "brand", "ed25519")),
    # What a caller may ask for, what an option declares about the feature it owns, what an optional
    # dev-tooling hook is, where a project goes to production, what differs per package and where each
    # backend answers its probes. The registry and the loader land here in phase 2.
    ("contract", ("registry", "family_only", "renamed", "language_shape", "language_directory", "extension_directory",
                  "features", "extensions", "extension_shape", "extension_tools", "hooks", "guards",
                  "telegraph", "targets", "target_shape", "target_protocol", "target_directory",
                  "axes", "catalog", "rungs",
                  "catalog_checks", "catalog_merge",
                  # A named set of answers — which languages, which axes, which extensions — read as a
                  # document and nothing more, which is why it sits with the other shapes the chandlery
                  # asks about rather than with the answers it resolves to.
                  "quickstart",
                  "catalog_options", "loaded", "loaded_targets", "backends", "probes", "ecosystems", "npm_workspace",
                  "examples", "harness",
                  "images")),
    # One validated answer per axis, which applications a project has, and what they add up to being able
    # to do.
    ("answers", ("selection", "origin", "layout", "services", "tooling", "capabilities", "berths", "fleet", "deck",
                 "toolkit", "platform", "convergence", "delivery_facts", "programme", "quick_wins",
                 "uncommitted", "wrappers", "strategy", "survey", "structure", "big_picture", "deployment_shapes",
                 "big_picture_guards", "manifest")),
    # One module per part of the repository being generated.
    ("parts", ("project",)),
    # The whole of a project, assembled and written, and the whole of it again from a newer keel — and the
    # same material assembled for a harness to install with no project at all, which is this tier for the
    # same reason the rest of it is: it reads every part.
    ("assembly", ("plugin", "native", "unlabel", "next_steps", "scaffold", "adopt_report", "add_service", "adopt",
                  "migration_legacy", "migration_flight", "migration_settings", "migration_claims",
                  "migration_crossing", "migration_result", "migration_merge", "migration_renames",
                  "replay", "catch_up", "migrate", "resurvey", "confirm", "converge", "shape_converge")),
    # The command line, and the entry point the executable is built from.
    ("edge", ("cli", "__main__", "preflight", "upgrade", "cli_confirm", "cli_init",
              # The `./init` a new project is handed over to, in a terminal and in the background.
              "init_run",
              "cli_prompts", "cli_interview", "cli_offered", "cli_language", "cli_search", "cli_add", "cli_adopt",
              # The interview `generate` runs when it is given nothing, and the quickstart it offers first.
              "cli_generate", "cli_quickstart", "quickstart_install", "cli_migrate",
              # The chandlery client: the index, a release file, an install as one
              # transaction, the plan a verb shows first, and upkeep after a keel moves.
              "index_schema", "language_index", "language_release", "language_install", "language_plan",
              "language_upkeep", "browser_app",
              # The other kind of package: its install, its scaffold, and the two verbs over them.
              "extension_install", "target_install", "cli_target",
              "package_new", "package_templates", "target_templates", "package_release",
              "package_version", "package_sources", "cli_extension", "cli_package",
              "trust", "cli_trust", "channel", "channel_new", "channel_page", "cli_channel",
              "cli_telegraph", "harbour", "cli_fleet",
              # The read side served to whatever is doing the work: the tools and the stdio session.
              "mcp", "cli_mcp",
              # The board, as a page a person answers from: the render, the server and the verb — and
              # what bare `slipwai` does, which is open that same board.
              "page_shell", "bridge", "bridge_page", "cli_bridge", "cli_start", "interview_page", "adopt_page",
              # The chandlery as a tab of it: `search` and the install verbs, rendered.
              "chandlery_page",
              # The conformance suite a package runs against itself, and its generated-variant
              # matrix: entry points the keel exports rather than modules it reads.
              "conformance", "matrix")),
    # The package's own `__init__`: last, so it may name anything and nothing may name it.
    ("package", ("__init__",)),
)

# A module over this is the file this package was split out of. Tests get the same budget: a suite nobody
# reads is a suite whose duplicate coverage nobody notices.
#
# **What it measures, re-examined at 16.8 now that it is not being spent on paragraphs.** Phase 16 took
# `src/slipwai/project/` from 48% of its lines inside non-docstring string literals to 32%, and the modules
# at the limit from ten to four. The number stays at 350 and it still counts *every* line, which are two
# decisions and not one.
#
# The number stays because it is now binding on code without being moved: the largest modules in the tree
# are 95 to 100% code — `ecosystems.py` at 349 of 349, `test_services.py` at 350 of 350 — and several sit
# exactly here, which is the budget doing the job it was written for rather than catching English.
#
# It counts every line because counting code only would stop it binding at all: measured that way the
# largest module in the repository is exactly 350, so nothing would be over and the rule would be a no-op
# the day it changed. And it would make prose free to keep in Python, which is the incentive phase 16 spent
# eight slices removing. A reader's working set is the file in front of them, whatever its lines hold.
#
# **An asset's own size is deliberately not budgeted.** The largest is `assets/toolkit/commands/sail.md` at
# 355 lines. A page is read top to bottom, has headings to navigate by, and is as long as its subject —
# none of which is true of a module, which is why a module has a budget. What holds an asset instead is
# `tests/test_generated_prose.py`: every token it names must be provided, every value provided must be
# named, and nothing it renders may still carry a marker. That is the drift a page can actually suffer.
MODULE_BUDGET = 350
# A package facade dispatches; anything longer is behaviour hiding somewhere no one looks for it.
FACADE_BUDGET = 40

# The kinds of package whose Python the keel imports, each in a directory of its own, loaded by name at run
# time. Extensions are not here: an extension's executable half is the `init.py` that runs inside a
# generated project, where the keel is not installed and nothing of it can be imported.
PACKAGE_PREFIXES = {"language": "slipwai_language_", "target": "slipwai_target_"}
PACKAGES = ROOT / "packages"
SURFACE = ROOT / "import-surface.txt"
# How many keel modules any one kind of package may be promised. The plan's number, read off what the six
# language packages actually import; past it a package is reaching into the keel rather than being answered
# by it, and that is the same question whichever kind is asking.
CEILING = 20
# A section header in the surface: `[language]`, `[target]`. Lines before the first one are the language's,
# which is what the whole file was before there was a second kind to promise anything to.
SECTION = "language"


def tier_of(module: str) -> tuple[int, str]:
    """Which tier a dotted module name belongs to, by its first matching prefix."""
    for index, (name, prefixes) in enumerate(TIERS):
        for prefix in prefixes:
            if module == prefix or module.startswith(f"{prefix}."):
                return index, name
    raise SystemExit(f"check-structure: {module} belongs to no declared tier — add it to TIERS")


def module_name(path: Path) -> str:
    relative = path.relative_to(KEEL).with_suffix("")
    parts = [part for part in relative.parts if part != "__init__"]
    return ".".join(parts) if parts else "__init__"


def imported_modules(path: Path, text: str) -> list[tuple[int, str]]:
    """Every sibling module this one imports, as (line, dotted name). Absolute imports are not ours."""
    here = path.relative_to(KEEL).parent.parts
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


def package_imports(text: str) -> list[tuple[int, str, str]]:
    """Every absolute import of a package in a module, as (line, kind, top-level module), anywhere in it.

    Every kind the gate walks, from the one table that names them, so a kind the keel may not know is
    refused the day it is declared rather than the day somebody remembers to add a branch here. `ast.walk`
    rather than the module's body, because a deferred import inside a function is still the keel knowing a
    cloud, and it is the shape somebody reaches for when the top of the file is being watched.
    """
    found: list[tuple[int, str, str]] = []
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
            names = [node.module]
        else:
            continue
        for top in (name.split(".")[0] for name in names):
            found += [(node.lineno, kind, top) for kind, prefix in PACKAGE_PREFIXES.items()
                      if top.startswith(prefix)]
    return found


def import_surface(listing: str, kind: str | None = None) -> set[str]:
    """The modules `import-surface.txt` lists: one dotted name per line, blanks and `#` comments ignored.

    One section per kind of package, headed `[language]` or `[target]`, because the two are promised
    different things and the ceiling is on what any one kind may reach for. `kind` is one section; without
    it, every section at once — which is what holds the file's other direction, since a line naming a module
    the keel has not got is a promise nobody can keep whichever section somebody wrote it in.

    Lines before the first header are the language's. The file was one flat list of what a language may
    import before there was a second kind to promise anything to, and that is what such a list still means.
    """
    found: dict[str, set[str]] = {name: set() for name in PACKAGE_PREFIXES}
    section = SECTION
    for raw in listing.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].strip()
            found.setdefault(section, set())
            continue
        found[section].add(line)
    if kind is None:
        return {module for modules in found.values() for module in modules}
    return set(found.get(kind, ()))


def keel_modules() -> set[str]:
    """Every module the keel has, by the dotted name a package imports it by (`slipwai.registry`)."""
    return {"slipwai" if name == "__init__" else f"slipwai.{name}" for name in map(module_name, KEEL.rglob("*.py"))}


def keel_imports(text: str, modules: set[str]) -> list[tuple[int, str]]:
    """Every keel module a package module imports, as (line, dotted name), the way Python resolves it:
    `from slipwai import registry` names `slipwai.registry`, a module the keel has, and `from slipwai import x`
    the package `slipwai` where `x` is a name in it rather than a module of its own."""
    found: list[tuple[int, str]] = []
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, ast.Import):
            found += [(node.lineno, alias.name) for alias in node.names if alias.name.split(".")[0] == "slipwai"]
        elif isinstance(node, ast.ImportFrom) and not node.level and (node.module or "").split(".")[0] == "slipwai":
            for alias in node.names:
                named = f"{node.module}.{alias.name}"
                found.append((node.lineno, named if named in modules else str(node.module)))
    return found


def read_module(path: Path) -> tuple[str, str | None]:
    """A module's text, decoded as Python decodes it (UTF-8, or the encoding it declares), and the one line naming it
    when it cannot be decoded or parsed, so the gate reports that rather than a traceback."""
    relative = path.relative_to(ROOT).as_posix()
    try:
        text = importlib.util.decode_source(path.read_bytes())
        ast.parse(text)
    except (SyntaxError, UnicodeDecodeError, ValueError) as error:
        message = error.msg if isinstance(error, SyntaxError) else str(error)
        line = f" (line {error.lineno})" if isinstance(error, SyntaxError) and error.lineno else ""
        return "", f"{relative}: does not parse: {message}{line}"
    return text, None


def surface_violations(modules: set[str]) -> tuple[int, list[str]]:
    """How many packages were read, and each package module's import of a keel module the surface omits.

    The surface is held whether or not a package exists to break it: a line naming a module the keel does
    not have is a promise nobody can keep, and the empty list of phase 1 is checked the same way.
    """
    listing = SURFACE.read_text(encoding="utf-8") if SURFACE.is_file() else ""
    violations = [
        f"{SURFACE.name}: the import surface lists {module}, which the keel does not have"
        for module in sorted(import_surface(listing) - modules)
    ]
    if not PACKAGES.is_dir():
        return 0, violations
    # An empty package directory is a clone that skipped a submodule: nothing in it can be checked. The
    # keel pins no first-party package — one toy fixture is all its own gate reads — but a contributor's
    # checkout may hold their package here, and an empty directory is as wrong there as anywhere.
    violations += [
        f"packages/{entry.name} is not checked out: git submodule update --init packages/{entry.name}"
        for entry in sorted(PACKAGES.iterdir())
        if entry.is_dir() and not entry.name.startswith(".") and not any(entry.iterdir())
    ]
    packages = sorted((kind, directory)
                      for kind, prefix in PACKAGE_PREFIXES.items()
                      for directory in PACKAGES.glob(f"*/{prefix}*/"))
    for kind, directory in packages:
        surface = import_surface(listing, kind)
        name = directory.parent.name
        for path in sorted(directory.rglob("*")):
            relative = path.relative_to(ROOT).as_posix()
            if path.is_symlink():
                violations.append(f"{relative}: a symlink inside {kind} {name}'s source, whose target this gate "
                                  "does not read; a package holds its own files")
                continue
            if "__pycache__" not in path.parts and path.suffix in (".pyc", ".so", ".pyd"):
                violations.append(f"{relative}: a compiled module in {kind} {name}'s source, which this gate "
                                  "cannot read; ship the .py")
            if path.suffix != ".py" or not path.is_file():
                continue
            text, fault = read_module(path)
            if fault:
                violations.append(fault)
                continue
            violations += [
                f"{relative}:{line}: {kind} {name} imports {module}, which is not on the import surface "
                f"listed in {SURFACE.name} for a {kind}"
                for line, module in sorted(set(keel_imports(text, modules))) if module not in surface
            ]
    return len(packages), violations


def main() -> int:
    modules = sorted(path for path in KEEL.rglob("*.py"))
    packages, violations = surface_violations(keel_modules())
    graph: dict[str, set[str]] = {}

    for path in modules:
        relative = path.relative_to(ROOT).as_posix()
        text, fault = read_module(path)
        if fault:
            violations.append(fault)
            continue
        name = module_name(path)
        length = len(text.splitlines())
        budget = FACADE_BUDGET if path.name == "__init__.py" else MODULE_BUDGET
        if length > budget:
            what = "package facade" if path.name == "__init__.py" else "module"
            violations.append(f"{relative}: {length} lines in one {what}, over the {budget}-line budget")
        if ast.get_docstring(ast.parse(text)) is None:
            violations.append(f"{relative}: no module docstring saying what part this is")

        violations += [
            f"{relative}:{line}: the keel imports a {kind} package: {package}"
            for line, kind, package in package_imports(text)
        ]
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
        text, fault = read_module(path)
        if fault:
            violations.append(fault)
            continue
        length = len(text.splitlines())
        if length > MODULE_BUDGET:
            relative = path.relative_to(ROOT).as_posix()
            violations.append(f"{relative}: {length} lines in one suite, over the {MODULE_BUDGET}-line budget")

    if violations:
        print("check-structure: the source does not have the shape it claims\n", file=sys.stderr)
        for violation in sorted(set(violations)):
            print(f"  {violation}", file=sys.stderr)
        return 1
    listing = SURFACE.read_text(encoding="utf-8") if SURFACE.is_file() else ""
    promised = ", ".join(f"{len(import_surface(listing, kind))} for a {kind}" for kind in sorted(PACKAGE_PREFIXES))
    print(f"check-structure: {len(modules)} modules, {len(TIERS)} tiers, no upward imports and no cycles; "
          f"{packages} package(s) import only what the surface promises — {promised}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

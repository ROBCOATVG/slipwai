"""`slipwai extension list|install|upgrade|remove|check` and `slipwai hooks`: the optional dev tooling, and its points.

An extension is not a product-architecture choice, so it is not asked at `slipwai generate` and has no verb
under it. It is installed into the package directory beside the languages, offered by `./init`'s menu in every
project generated after that, and elected there or later with `./init --extension <key>`.

`hooks` is the other half of the same question and the one a person actually asks when something did not run:
which moments the keel fires, what each is given, and which installed extension attaches to it. It prints the
closed set whether or not anything is installed, because "there is no such point" and "nothing is attached to
it" are different answers and a list that showed only the attached ones could not tell them apart.
"""
from __future__ import annotations

import argparse

from .assets import this_command
from .catalog import REFUSALS
from .errors import GenerationError, refuse
from .extension_directory import MANIFEST, absent
from .extension_given import split
from .extension_install import catalogue, install, remove
from .extension_shape import OBLIGATIONS
from .guards import GUARDS
from .guards import declared as declared_guards
from .hooks import POINTS, declared
from .language_directory import directory

VERBS = ("list", "install", "upgrade", "remove", "check")


def rows() -> list[str]:
    """The installed extensions, each with what the catalogue shows and the points it attaches to."""
    found = catalogue(directory())
    if not found:
        return [f"  none installed; `{this_command()} extension install <path-or-url>` adds one"]
    lines: list[str] = []
    for key, manifest in found:
        name = manifest.get("name", key)
        lines.append(f"  {key}  {name}")
        description = manifest.get("description")
        if isinstance(description, str) and description:
            lines.append(f"      {description}")
        try:
            missing = {(kind, point): path for kind, point, path in absent(directory() / key, manifest)}
            points = attached(declared(manifest), "hook", missing)
        except (ValueError, KeyError) as error:  # a manifest the loader already refused, said once more here
            missing, points = {}, f"unreadable ({error})"
        lines.append(f"      hooks: {points or 'none'}")
        try:
            may_refuse = attached(declared_guards(manifest), "guard", missing)
        except (ValueError, KeyError) as error:
            may_refuse = f"unreadable ({error})"
        lines.append(f"      guards: {may_refuse or 'none'}")
        if missing:
            lines.append(f"      this package is not whole; install a release that is: "
                         f"`{this_command()} extension install {key}`")
    return lines


def attached(found: dict[str, dict], kind: str, missing: dict[tuple[str, str], str]) -> str:
    """The points one extension declares, each one whose script is not in the package saying so.

    Listed bare, a hook whose file is missing reads as a hook that is there — which is what `codegraph` 1.0.0's
    `after-stage` did for the life of that version while it ran in no project (#117).
    """
    return ", ".join(f"{name} ({missing[kind, name]} is not in the package, so it never runs)"
                     if (kind, name) in missing else name for name in sorted(found))


def list_extensions() -> None:
    print("extensions")
    for line in rows():
        print(line)
    for line in REFUSALS:
        if line.startswith("extension "):
            print(f"  {line}")


def attached_to(reader) -> dict[str, list[str]]:
    """Which installed extension declares what, by name, for one of the two sets."""
    found: dict[str, list[str]] = {}
    for key, manifest in catalogue(directory()):
        try:
            for name in reader(manifest):
                found.setdefault(name, []).append(key)
        except (ValueError, KeyError):
            continue
    return found


def hooks_listing() -> list[str]:
    """Every point, what fires it, what it is given, and which installed extension attaches to it — each one whose
    script is not in its package saying so, in the words `extension list` uses (#126)."""
    attached = attached_to(declared)
    missing: dict[tuple[str, str], str] = {}
    for key, manifest in catalogue(directory()):
        try:
            missing.update({(key, name): path for kind, name, path in absent(directory() / key, manifest)
                            if kind == "hook"})
        except (ValueError, KeyError):  # a manifest the loader already refused attaches to nothing above
            continue
    lines: list[str] = []
    for point in POINTS:
        who = ", ".join(f"{key} ({missing[key, point.name]} is not in the package, so it never runs)"
                        if (key, point.name) in missing else key
                        for key in sorted(attached.get(point.name, []))) or "nothing attached"
        lines.append(f"  {point.name}")
        lines.append(f"      fires {point.when}")
        lines.append(f"      given {', '.join(point.given)}")
        lines.append(f"      {who}")
    return lines


def guards_listing() -> list[str]:
    """Every guard, what fires it, what it is given, what refusing does, and who may."""
    attached = attached_to(declared_guards)
    lines: list[str] = []
    for one in GUARDS:
        who = ", ".join(sorted(attached.get(one.name, []))) or "nothing attached"
        lines.append(f"  {one.name}")
        lines.append(f"      fires {one.when}")
        lines.append(f"      given {', '.join(one.given)}")
        lines.append(f"      refusing it: {one.refusing}")
        lines.append(f"      {who}")
    return lines


def hooks_main(argv: list[str]) -> None:
    """`slipwai hooks`: the closed set of points, and what is on each."""
    argparse.ArgumentParser(prog=f"{this_command()} hooks",
                            description="The moments an extension may attach to, and what is attached").parse_args(argv)
    print("hook points — a hook is reported and never fatal to the rung it runs around")
    for line in hooks_listing():
        print(line)
    print()
    print("guards — a guard may refuse one tool call by exiting 2, and the rung still completes")
    for line in guards_listing():
        print(line)
    print()
    print("  a hook is run where an extension is elected; a guard is also agreed to, because it refuses")
    print("  things a person asked for. An extension declaring a guard nobody agreed to fires none")


def check_main(path: str) -> None:
    """`slipwai extension check <dir>`: what a package would install as, and the six obligations it is held to.

    The manifest half is checked here; the obligations are checked by the conformance suite, which runs the
    entry point against a generated project. This prints them so that a publisher reading one refusal is not
    left guessing what the other five are.
    """
    from pathlib import Path

    from .catalog import CORE
    from .extension_directory import fault_in
    root = Path(path).expanduser()
    manifest, fault = fault_in(root.name, root, CORE["schemaVersion"])
    if manifest is None:
        raise GenerationError(f"{root}: {fault}")
    print(f"{root}: a readable {MANIFEST}")
    print(f"  key          {manifest['key']}  — `./init --extension {manifest['key']}`")
    print(f"  shown as     {manifest['name']}")
    print(f"  core         {manifest['core']}")
    missing = {(kind, point): script for kind, point, script in absent(root, manifest)}
    print(f"  hooks        {attached(declared(manifest), 'hook', missing) or 'none'}")
    print(f"  guards       {attached(declared_guards(manifest), 'guard', missing) or 'none'}  — these may "
          f"refuse a tool call, and are agreed to at election")
    kept, back = split(root, manifest)
    held = f"; not {', '.join(path.as_posix() for path in back)}" if back else ""
    print(f"  a project    is given {len(kept)} file(s) under scripts/extensions/{manifest['key']}/{held}")
    print("  obligations, which `slipwai conformance --extension` runs:")
    for name, said in OBLIGATIONS:
        print(f"    {name:<10} {said}")


def extension_main(argv: list[str]) -> None:
    """Dispatch `slipwai extension <verb>`."""
    parser = argparse.ArgumentParser(prog=f"{this_command()} extension",
                                     description="The optional dev tooling a project may elect at `./init`")
    parser.add_argument("verb", choices=VERBS)
    parser.add_argument("arguments", nargs="*", metavar="<name-or-path>")
    parser.add_argument("--accept-publisher", action="store_true",
                        help="accept this package's publisher without being asked, and remember it")
    parser.add_argument("--pre", action="store_true", help="with upgrade: count snapshots in the index")
    parsed = parser.parse_args(argv)
    try:
        if parsed.verb == "upgrade":
            from .extension_upkeep import upgrade
            from .language_index import snapshots
            print("\n".join(upgrade(parsed.arguments, directory(), prerelease=snapshots(parsed.pre))))
        elif parsed.verb == "list":
            list_extensions()
        elif parsed.verb == "install":
            for line in install(parsed.arguments, directory(), parsed.accept_publisher):
                print(line)
            print(f"`./init --extension <key>` elects one in a project; a project generated before this "
                  f"install does not offer it until `{this_command()} migrate` is run in it")
        elif parsed.verb == "remove":
            from pathlib import Path

            from .extension_removal import taken_back
            for name in parsed.arguments:
                # Taken back in this project first, while the package that says how is still here (#119).
                if (directory() / name / MANIFEST).is_file():
                    print("\n".join(taken_back(Path.cwd(), name)))
                print("\n".join(remove([name], directory())))
        else:
            if len(parsed.arguments) != 1:
                raise GenerationError(f"`{this_command()} extension check <directory>` takes one directory")
            check_main(parsed.arguments[0])
    except GenerationError as error:
        refuse(f"{this_command()} extension", error)

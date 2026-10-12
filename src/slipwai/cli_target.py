"""`slipwai target list|install|remove|check`: the clouds a project can be deployed to.

The third kind's verb. A target is not optional dev tooling and it is not a language, so it gets its own
word rather than a flag on either: `--target <name>` is a question `generate` asks, and the answers it can
offer are exactly what is installed here.

`list` prints what is installed and the row each contributes, including the ones the loader refused — what
is installed is the directory's to say, and a refused target that could not be listed is one nobody can
remove. `check` is what a publisher runs on a directory before releasing it: the manifest read, the `TARGET`
imported, and every member the protocol asks of a managed target, so one refusal does not leave the other
five to be found one run at a time.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from .assets import this_command
from .catalog import REFUSALS
from .errors import GenerationError, refuse
from .language_directory import Refused, directory
from .target_directory import MANIFEST, TargetPackage, fault_in, import_package
from .target_install import catalogue, install, remove
from .target_protocol import PROTOCOL, required
from .target_shape import catalogue_entry

VERBS = ("list", "install", "remove", "check")


def rows() -> list[str]:
    """The installed targets, each with what the prompt would show and what it does to the menus."""
    found = catalogue(directory())
    if not found:
        return [f"  none installed; `{this_command()} target install <name-or-path>` adds one. Without one, "
                f"a project is local only or deploys somewhere the keel does not own"]
    lines: list[str] = []
    for name, manifest in found:
        lines.append(f"  {name}  {manifest.get('label', 'unreadable target.json')}")
        if manifest.get("managed"):
            lines.append("      managed: the keel provisions and deploys this — its stacks, images, pipeline")
        if required_axes := manifest.get("requires"):
            lines.append(f"      requires: {', '.join(required_axes)}")
        brought = sorted(option for options in manifest.get("axes", {}).values() for option in options)
        lines.append(f"      brings: {', '.join(brought) or 'no answer of its own'}")
    return lines


def list_targets() -> None:
    print("targets")
    for line in rows():
        print(line)
    for line in REFUSALS:
        if line.startswith("target "):
            print(f"  {line}")


def check_main(path: str) -> None:
    """`slipwai target check <dir>`: what a package would install as, and everything the protocol asks.

    Both halves and all of them at once. A publisher told one fault per run is a publisher running this six
    times to find out what their package owes.
    """
    root = Path(path).expanduser()
    manifest, fault = fault_in(root.name if root.name else path, root, "9.0")
    if manifest is None:
        raise GenerationError(f"{root}: {fault}")
    name = manifest["name"]
    print(f"{root}: a readable {MANIFEST}")
    print(f"  name         {name}  — `--target {name}`")
    print(f"  shown as     {manifest['label']}")
    print(f"  core         {manifest['core']}")
    provisions = ("yes — its stacks, its images, its pipeline" if manifest.get("managed")
                  else "no — a project deploys where the keel does not own the infrastructure")
    print(f"  managed      {provisions}")
    print(f"  row          {catalogue_entry(manifest)}")
    try:
        import_package(TargetPackage(name, root, manifest))
    except Refused as error:
        raise GenerationError(str(error)) from None
    owed = required() if manifest.get("managed") else ()
    print(f"  TARGET       answers {len(owed)} required member(s), and is accepted")
    print("  the protocol, which `slipwai conformance --target` runs against a generated project:")
    for member in PROTOCOL:
        owes = "required of a managed target" if member.required else "optional"
        print(f"    {member.name:<16} {member.shape} ({owes})")


def target_main(argv: list[str]) -> None:
    """Dispatch `slipwai target <verb>`."""
    parser = argparse.ArgumentParser(prog=f"{this_command()} target",
                                     description="Where a generated project is deployed to")
    parser.add_argument("verb", choices=VERBS)
    parser.add_argument("arguments", nargs="*", metavar="<name-or-path>")
    parser.add_argument("--accept-publisher", action="store_true",
                        help="accept this package's publisher without being asked, and remember it")
    parsed = parser.parse_args(argv)
    try:
        if parsed.verb == "list":
            list_targets()
        elif parsed.verb == "install":
            for line in install(parsed.arguments, directory(), parsed.accept_publisher):
                print(line)
            print(f"`{this_command()} generate --target <name>` writes a project that deploys there; a "
                  f"project generated before this install does not offer it until `{this_command()} "
                  f"migrate` is run in it")
        elif parsed.verb == "remove":
            for line in remove(parsed.arguments, directory()):
                print(line)
        else:
            if len(parsed.arguments) != 1:
                raise GenerationError(f"`{this_command()} target check <directory>` takes one directory")
            check_main(parsed.arguments[0])
    except GenerationError as error:
        refuse(f"{this_command()} target", error)

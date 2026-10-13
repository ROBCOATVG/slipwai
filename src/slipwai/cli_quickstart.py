"""`slipwai quickstart install|save|show|list|remove`, and what `generate --quickstart` does with one.

No verb that *runs* one, because that verb is `generate`: a quickstart is not a thing to run, it is a set
of answers to give. `install` fetches somebody else's out of the chandlery. `save` writes what this project
actually has, so the decision somebody already made is recorded rather than described from memory. `show`
says in plain words what it would do **before it does any of it**, which is the only way a person who does
not know what an extension is can agree to electing one. `list` is what is saved here, and `remove` takes
one out again.

**Installing a quickstart installs no packages**, and the distinction matters at exactly one moment. The
catalogue is read once, when this process starts, so a language fetched halfway through could not answer a
single question asked after it. A quickstart that names a package this machine has not got is therefore
refused — by `generate`, with every missing name in one line and the one command that fetches them all.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import quickstart, quickstart_install
from .assets import this_command
from .catalog import CATALOG, CORE, families
from .errors import GenerationError, refuse
from .guards import REGISTRY as GUARD_REGISTRY
from .language_directory import directory as package_directory
from .package_new import core_range
from .quickstart import Quickstart
from .versions import parse

#: The election record `./init` and an extension's own `init.py` keep, read here to say what this project
#: elected. Not the hook registry: that says what is attached, and an extension with no hooks is elected
#: all the same.
ELECTED = ".slipwai/extensions.json"
MANIFEST = "project.json"
#: The verbs, in the order a person meets them: one that fetches somebody else's, three over their own.
VERBS = ("install", "save", "show", "list", "remove")


def read_json(path: Path) -> dict:
    """One of a project's own records, or `{}` where it is absent or unreadable — every one of them is
    written by a run rather than by a person, and a project that has not run `./init` simply has none."""
    try:
        held = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return {}
    return held if isinstance(held, dict) else {}


def agreed_in(root: Path) -> dict[str, list[str]]:
    """Which guards each extension in this project was agreed to fire, read off `.slipwai/guards.json`."""
    agreed: dict[str, list[str]] = {}
    for name, bodies in (read_json(root / GUARD_REGISTRY).get("guards") or {}).items():
        for body in bodies if isinstance(bodies, list) else []:
            key = body.get("extension") if isinstance(body, Mapping) else None
            if isinstance(key, str):
                agreed.setdefault(key, []).append(str(name))
    return agreed


def elected_in(root: Path) -> dict[str, tuple[str, ...]]:
    """Every extension this project elected, each with the guards it was agreed to fire.

    Elected and agreed are two answers and stay two here: an extension is elected by being installed and
    agreed to by somebody answering a question, so one that was elected and refused its guards is saved as
    elected with no guards — which is what the next project should ask, and does (13.4).
    """
    recorded = read_json(root / ELECTED).get("extensions")
    agreed = agreed_in(root)
    keys = [key for key in recorded if isinstance(key, str)] if isinstance(recorded, list) else []
    return {key: tuple(sorted(agreed.get(key, []))) for key in sorted(set(keys) | set(agreed))}


def range_for(version: str) -> str:
    """The range a saved package is named by: at least what is installed, below its next major.

    Never the version itself. A quickstart that pinned the snapshot it was written from would hold a team
    to the afternoon somebody saved it, and the first thing anybody would do is edit it.
    """
    numbers = parse(version)
    if numbers is None:
        return ""
    major, minor = numbers.group(1), numbers.group(2)
    return f">={major}.{minor},<{int(major) + 1}"


def first_service(manifest: Mapping[str, Any]) -> Mapping[str, Any]:
    """The service a project's answers are read off: the first generated one `project.json` records."""
    deployables = manifest.get("deployables", {})
    rows = deployables.values() if isinstance(deployables, Mapping) else []
    for row in rows:
        if isinstance(row, Mapping) and row.get("kind") == "service" and row.get("generated") is not False:
            return row
    raise GenerationError("this project records no generated service, so there are no answers to save. "
                          "A quickstart is saved from a project this command made")


def from_project(name: str, suits: str, manifest: Mapping[str, Any],
                 elected: Mapping[str, tuple[str, ...]]) -> Quickstart:
    """What this project actually has, as a quickstart: its answers, its languages and its extensions.

    `elected` is what the project elected and agreed to — the keys, each with the guards the person said
    yes to — which is read off the project rather than off the catalogue: the question is what *this*
    project does, not what this machine happens to have installed.
    """
    service = first_service(manifest)
    recorded = (manifest.get("generator") or {}).get("languages") or {}
    language = str(service.get("language", ""))
    axes = service.get("selection") or {}
    one = quickstart.Quickstart(
        name=name, suits=suits,
        profile=str(manifest.get("profile", "")),
        target=str(manifest.get("target", "")),
        language=language,
        framework=str(service.get("framework", "")),
        frontend=str(manifest.get("frontend", "")),
        axes={axis: str(answer) for axis, answer in axes.items()} if isinstance(axes, Mapping) else {},
        languages=tuple(quickstart.Wanted(package_name, range_for(str(version)))
                        for package_name, version in sorted(recorded.items())),
        extensions=tuple(quickstart.Wanted(key, "", tuple(guards)) for key, guards in sorted(elected.items())),
    )
    # Written and read back, so that a `save` can never write one `find` would then refuse.
    return quickstart.read(quickstart.document(one))


def save(name: str, suits: str, root: Path, into: Path | None) -> Path:
    """Write this project's answers as a quickstart, and say where it went."""
    if not suits.strip():
        raise GenerationError(
            f"`--suits` is how `{this_command()} generate` offers this quickstart: one sentence about the "
            f"product it suits, not the packages it names. The person it is for does not know what an "
            f"extension is")
    manifest = read_json(root / MANIFEST)
    if not manifest:
        raise GenerationError(f"{root / MANIFEST} is not here, so there are no answers to save. Run this "
                              f"from a project this command generated, or pass `--from <directory>`")
    # The keel range this quickstart was written against, as `package new` writes one: a quickstart is a
    # package in 13.3, and one saved here is the same document as one published there.
    one = dataclasses.replace(from_project(name, suits, manifest, elected_in(root)),
                              core=core_range(CORE["schemaVersion"]))
    place = into or quickstart.directory()
    place.mkdir(parents=True, exist_ok=True)
    path = place / f"{name}{quickstart.SUFFIX}"
    path.write_text(json.dumps(quickstart.document(one), indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    return path


def check_quickstart(root: Path) -> int:
    """`package check` for a quickstart: that it reads, and what it would do. 0 when it does, 1 when not.

    There is no conformance suite to run, because there is no code to run it against — a quickstart is a
    document. What a publisher needs to know before they put one in front of a team is the same thing a
    person needs before they accept one, so this prints `show`'s own words rather than a second report:
    whether it reads, every package named by a range rather than a version, and the answers it gives.
    """
    try:
        one = quickstart.load(root / quickstart.MANIFEST)
    except GenerationError as fault:
        print(f"quickstart: {fault}")
        return 1
    print("\n".join(quickstart.in_words(one)))
    return 0


#: The verb that fetches each kind, because they are three different ones and a line naming the wrong verb
#: is worse than no line. `install` is `language install`, which is what a reader types after a search.
FETCHES = {"language": "install", "extension": "extension install", "target": "target install"}


def absent(one: Quickstart) -> dict[str, list[str]]:
    """What this quickstart names that this machine has not got, by the kind of package each is.

    **The target is in here, and that is the point of the shape.** A quickstart answers a target, and every
    target but the keel's own two is a package — so on a machine without it the interview offered the
    quickstart as usable, the person chose it, and the generator refused them several questions later. What
    the menu greys out and what the generator will accept are now read off the same list.

    The target is the one that is named by an *answer* rather than listed under `languages` or
    `extensions`, because that is what it is: nobody installs a target in order to have it, they install
    it because the project goes there. The keel's own two — `none` and `existing` — are in the catalogue
    on every machine, so they are never missing.
    """
    here = set(families())
    installed = {entry.name for entry in package_directory().iterdir()} if package_directory().is_dir() else set()
    return {
        "language": [each.name for each in one.languages
                     if each.name not in here and each.name not in installed],
        "extension": [each.name for each in one.extensions if each.name not in installed],
        "target": [one.target] if one.target and one.target not in CATALOG["targets"] else [],
    }


def missing(one: Quickstart) -> list[str]:
    """Every package the quickstart names that this machine has not got, in the order a person meets them."""
    return [name for kind in FETCHES for name in absent(one)[kind]]


def fetches(one: Quickstart) -> list[str]:
    """One command per kind that is missing — never one command carrying names three verbs apart."""
    return [f"{this_command()} {FETCHES[kind]} {' '.join(names)}"
            for kind, names in absent(one).items() if names]


def refuse_missing(one: Quickstart) -> None:
    """Refuse a quickstart whose packages are not here, with the commands that fetch them.

    Named rather than installed: see this module's own heading. The refusal carries every name at once, so
    nobody installs one package, runs the command again and is told about the next.
    """
    names = missing(one)
    if names:
        raise GenerationError(
            f"the {one.name} quickstart names {', '.join(names)}, which "
            f"{'is' if len(names) == 1 else 'are'} not installed here. Run: "
            f"{'; '.join(fetches(one))}")


def typed(argv: list[str]) -> set[str]:
    """Which flags the caller actually typed, so a quickstart fills in only what was not asked for.

    Read off the arguments rather than compared against the parser's defaults, because a flag whose default
    is the catalogue's answer — `--target`, `--profile` — is indistinguishable afterwards from one somebody
    typed, and a quickstart that overrode a typed flag would be the opposite of what it is.
    """
    return {word.split("=", 1)[0].lstrip("-").replace("-", "_") for word in argv if word.startswith("--")}


def quickstart_flag(parser: argparse.ArgumentParser) -> None:
    """`generate --quickstart <name-or-path>`, declared where the rest of the quickstart is."""
    parser.add_argument("--quickstart", default=None, metavar="<name-or-path>",
                        help="start from a saved quickstart: `slipwai quickstart list` names them, and "
                             "`slipwai quickstart show <name>` says what one would do")


def files_with_record(args: Any, apps: list[Any]) -> dict[str, str] | None:
    """The project's files with the quickstart's record among them, or None where there is no quickstart.

    One file, `.slipwai/quickstart.json`: which quickstart this project came from, which extensions it
    elects and which guards were already agreed to. `./init` reads it instead of showing the extension
    menu, and `guards.py --offer` instead of asking a question somebody answered when they wrote the
    quickstart (13.4). None is what `write_project` already takes to mean "assemble them yourself".

    Read off `args.quickstart` rather than passed in, because there are two ways a quickstart is chosen —
    the flag, and the interview's own offer — and a record written for only one of them would be a project
    that elects nothing because the person was asked rather than having typed it.
    """
    if not getattr(args, "quickstart", None):
        return None
    one = quickstart.find(args.quickstart)
    from .scaffold import project_files
    return {**project_files(args.name, args.profile, args.target, apps, shape=getattr(args, "shape", None)),
            quickstart.RECORD: quickstart.record(one)}


def applied(args: Any, named: dict[str, str | None], argv: list[str]) -> Quickstart | None:
    """Give the quickstart's answers to everything the caller did not answer itself, and say which.

    Printed, every one of them, with the flag that would have given it: the transcript is what shows
    somebody what was chosen on their behalf, and a quickstart whose answers only appeared in the generated
    tree would be a tool that decided things in the dark. None where no quickstart was named at all.
    """
    if not getattr(args, "quickstart", None):
        return None
    one = quickstart.find(args.quickstart)
    refuse_missing(one)
    already = typed(argv)
    print(f"\nFrom the {one.name} quickstart — {one.suits}")
    for flag, value in quickstart.answered(one).items():
        attribute = flag.replace("-", "_")
        if attribute in already:
            print(f"  {flag:<13} {getattr(args, attribute, named.get(flag))}  (yours, not the quickstart's)")
            continue
        if flag in named:
            named[flag] = value
        else:
            setattr(args, attribute, value)
        print(f"  {flag:<13} {value}")
    for each in one.extensions:
        print(f"  extension     {each.name}" + (f"  (may refuse: {', '.join(each.guards)})" if each.guards else ""))
    print("Every one of these is a flag you can give instead.\n")
    return one


def listing() -> list[str]:
    names = quickstart.saved_names()
    if not names:
        return [f"no quickstart is saved here. `{this_command()} quickstart save <name> --suits '<a sentence>'` "
                f"writes one from a project, and `{this_command()} search --kind quickstart` lists published ones"]
    width = max(len(name) for name in names)
    return [f"  {one.name:<{width}}  {one.suits}" for one in map(quickstart.find, names)]


def quickstart_main(argv: list[str]) -> None:
    prog = f"{this_command()} quickstart"
    parser = argparse.ArgumentParser(
        prog=prog,
        description="Install, save, read and list a named set of languages, answers and extensions",
        epilog="A quickstart is given to a generation: `%(prog)s show <name>` says what it would do, and "
               "`slipwai generate <project> --quickstart <name>` carries it out. A name is looked up in "
               "~/.slipwai/quickstarts; a path is read where it is.",
    )
    parser.add_argument("verb", choices=VERBS)
    parser.add_argument("name", nargs="*", help="the quickstart's name, or a path to one")
    parser.add_argument("--suits", default="", metavar="<sentence>",
                        help="`save` only: what the product this suits is like, in one sentence")
    parser.add_argument("--from", dest="root", default=".", metavar="<directory>",
                        help="`save` only: the project to read the answers off (default: here)")
    parser.add_argument("--into", default="", metavar="<directory>",
                        help="`save`, `install` and `remove`: which directory of quickstarts to work in "
                             "(default: ~/.slipwai/quickstarts)")
    parsed = parser.parse_args(argv)
    try:
        if parsed.verb == "list":
            print("\n".join(listing()))
            return
        if not parsed.name:
            raise GenerationError(f"`{prog} {parsed.verb}` names a quickstart")
        into = Path(parsed.into).expanduser() if parsed.into else None
        if parsed.verb in ("install", "remove"):
            run = quickstart_install.install if parsed.verb == "install" else quickstart_install.remove
            print("\n".join(run(parsed.name, into or quickstart.directory())))
            return
        first = parsed.name[0]
        if parsed.verb == "show":
            print("\n".join(quickstart.in_words(quickstart.find(first))))
            return
        path = save(first, parsed.suits, Path(parsed.root).expanduser(), into)
        print(f"{first} saved: {path}")
        print(f"  read it       {prog} show {first}")
        print(f"  use it        {this_command()} generate <name> --quickstart {first}")
    except GenerationError as error:
        refuse(prog, error)

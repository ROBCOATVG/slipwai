"""A quickstart: the languages, the answers and the extensions somebody settled once, under a name.

Generating a project is a language and nothing else today: the chandlery is searched, one language is
installed, and the extensions are a menu `./init` shows once and a person answers from memory. Somebody who
has decided *this is how we start a project here* has no way to say it once, and every repository after the
first is that decision re-made from recollection.

**It is called a quickstart because of who it is for.** The person this helps most is the one who does not
know what `uipro` is, or which of six languages answers the npm workspace, or that an extension has to be
elected as well as installed. So a quickstart carries a sentence about *the product it suits* — `suits` is
required, and a quickstart without one is refused — because a list of package names is no help at all to
the reader it exists for.

**It is not a profile, and the two must never be run together in a person's head.** A profile is the
delivery foundation, which section 4 calls the one answer that is hard to undo. Everything here is a
reversible choice — which languages, which axes, which extensions — and a quickstart may *name* a profile
but never replaces the question: `applied` puts every answer behind a flag a person typed, so a quickstart
is a default and never an override.

**Packages are named by range, never by snapshot** (`range_for`), so a quickstart written today does not
pin a team to the version that was installed the afternoon somebody saved it.
"""
from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .assets import moved_home, this_command
from .errors import GenerationError
from .language_shape import name_fault
from .versions import parse

#: What the document declares, and the one format this keel writes. A reader meeting a higher one says so
#: rather than guessing which fields moved, exactly as a log line's `v` does.
KEY = "quickstart"
FORMAT = 1
#: The manifest inside a published quickstart package, and the suffix a saved one is written under.
MANIFEST = "quickstart.json"
SUFFIX = ".json"
#: The one directory `--quickstart <name>` looks in, and the variable that replaces it whole.
VARIABLE = "SLIPWAI_QUICKSTARTS"
HOME = "quickstarts"
#: What a project generated from one carries, so `./init` elects without asking the menu again and the
#: guard question is not asked a second time (13.4).
RECORD = ".slipwai/quickstart.json"
#: The answers a quickstart may give, each named as the flag `generate` already takes. Not a second
#: vocabulary: the transcript shows a person what was chosen on their behalf in the words they could have
#: typed themselves.
FLAGS = ("profile", "target", "language", "framework", "frontend")


@dataclass(frozen=True)
class Wanted:
    """One package a quickstart names: by name, by range where it has one, and — for an extension — the
    guards the person who wrote it agreed to."""

    name: str
    version: str = ""
    guards: tuple[str, ...] = ()

    def said(self) -> str:
        return f"{self.name} {self.version}" if self.version else self.name


@dataclass(frozen=True)
class Quickstart:
    """One named set of answers, as the file holds it."""

    name: str
    suits: str
    profile: str = ""
    target: str = ""
    language: str = ""
    framework: str = ""
    frontend: str = ""
    core: str = ""
    axes: Mapping[str, str] = field(default_factory=dict)
    languages: tuple[Wanted, ...] = ()
    extensions: tuple[Wanted, ...] = ()


def directory() -> Path:
    """Where saved quickstarts live: the variable if set, otherwise `~/.slipwai/quickstarts`."""
    named = os.environ.get(VARIABLE)
    return Path(named) if named else moved_home(Path.home() / ".slipwai") / HOME


def text(document: Mapping[str, Any], key: str, required: bool = False) -> str:
    """One string field of the document, or the refusal naming what it has to be."""
    said = document.get(key, "")
    if not isinstance(said, str) or (required and not said.strip()):
        raise GenerationError(f"a quickstart's `{key}` is a string, and this one is {said!r}")
    return said.strip()


def wanted(entry: Any, kind: str) -> Wanted:
    """One package the document names, held to being a name and a range rather than anything else."""
    if not isinstance(entry, Mapping):
        raise GenerationError(f"a quickstart's `{kind}s` is a list of objects, each with a `name`; "
                              f"{entry!r} is not one")
    name = str(entry.get("name", ""))
    fault = name_fault(kind, name)
    if fault is not None:
        raise GenerationError(f"{fault}, so it is not a package a quickstart can name")
    version = entry.get("version", "")
    if not isinstance(version, str):
        raise GenerationError(f"{name}'s `version` is a range such as `>=1.2,<2`, and this one is {version!r}")
    guards = entry.get("guards", [])
    if not isinstance(guards, list) or not all(isinstance(one, str) for one in guards):
        raise GenerationError(f"{name}'s `guards` is the list of guard names agreed to when this quickstart "
                              f"was written, and this one is {guards!r}")
    return Wanted(name, version.strip(), tuple(guards))


def read(document: Mapping[str, Any]) -> Quickstart:
    """The document as a quickstart, or the one line saying why it is not one.

    Refused rather than read around, for every fault. A quickstart is answers given on somebody's behalf,
    and one whose answers were half-understood would generate a project nobody chose.
    """
    if not isinstance(document, Mapping):
        raise GenerationError("a quickstart is an object; this is not")
    declared = document.get(KEY, FORMAT)
    if declared != FORMAT:
        raise GenerationError(f"this quickstart declares format {declared!r} and this keel writes "
                              f"{FORMAT}: `{this_command()} upgrade` reads a newer one")
    name = text(document, "name", required=True)
    fault = name_fault(KEY, name)
    if fault is not None:
        raise GenerationError(f"{fault}. A quickstart's name is a file, a flag and what a person says out loud")
    # The one field with a refusal of its own, because it is the one the whole design rests on: the
    # interview lists a quickstart by this sentence, and one without it is offered to the person it exists
    # for as a row of package names.
    if not str(document.get("suits", "")).strip():
        raise GenerationError(f"{name} declares no `suits`, and that is the sentence the interview offers "
                              f"it by — what the product it is for is like, not which packages it names")
    suits = text(document, "suits", required=True)
    answers = document.get("answers", {})
    if not isinstance(answers, Mapping):
        raise GenerationError(f"{name}: `answers` is an object of the answers this quickstart gives")
    axes = answers.get("axes", {})
    if not isinstance(axes, Mapping):
        raise GenerationError(f"{name}: `answers.axes` is an object of one answer per axis")
    for axis, answer in axes.items():
        if not isinstance(answer, str) or not answer:
            raise GenerationError(f"{name}: the `{axis}` axis is answered with one option's name, and this "
                                  f"one is {answer!r}")
    return Quickstart(
        name, suits,
        **{flag: text(answers, flag) for flag in FLAGS},
        core=text(document, "core"),
        axes=dict(axes),
        languages=tuple(wanted(entry, "language") for entry in listed(name, document, "languages")),
        extensions=tuple(wanted(entry, "extension") for entry in listed(name, document, "extensions")),
    )


def listed(name: str, document: Mapping[str, Any], key: str) -> list[Any]:
    found = document.get(key, [])
    if not isinstance(found, list):
        raise GenerationError(f"{name}: `{key}` is a list of the packages this quickstart names")
    return found


def document(one: Quickstart) -> dict:
    """The quickstart as it is written: the shape `read` takes back, and the manifest a package carries."""
    answers = {flag: value for flag in FLAGS if (value := getattr(one, flag))}
    return {
        KEY: FORMAT,
        "name": one.name,
        "suits": one.suits,
        **({"core": one.core} if one.core else {}),
        "answers": {**answers, **({"axes": dict(one.axes)} if one.axes else {})},
        "languages": [package(each) for each in one.languages],
        "extensions": [package(each) for each in one.extensions],
    }


def package(one: Wanted) -> dict:
    return {"name": one.name, **({"version": one.version} if one.version else {}),
            **({"guards": list(one.guards)} if one.guards else {})}


def saved_names() -> list[str]:
    """Every quickstart saved in the directory, by name."""
    place = directory()
    return sorted(path.stem for path in place.glob(f"*{SUFFIX}")) if place.is_dir() else []


def load(path: Path) -> Quickstart:
    """One quickstart read off disk, with the refusal naming the file rather than the fault alone."""
    try:
        held = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError) as error:
        raise GenerationError(f"{path} cannot be read as a quickstart: {error}") from None
    try:
        return read(held)
    except GenerationError as error:
        raise GenerationError(f"{path}: {error}") from None


def is_path(request: str) -> bool:
    """Whether this reads as a path rather than a saved name. The same rule an extension install uses."""
    return "/" in request or "\\" in request or request.startswith((".", "~")) or request.endswith(SUFFIX)


def find(request: str) -> Quickstart:
    """One quickstart by saved name or by path — the second so a team's own lives beside their repository."""
    if is_path(request):
        return load(Path(request).expanduser())
    path = directory() / f"{request}{SUFFIX}"
    if not path.is_file():
        have = ", ".join(saved_names()) or "none"
        raise GenerationError(f"no quickstart named `{request}` is saved here (saved: {have}). "
                              f"`{this_command()} quickstart list` lists them, and `{this_command()} search "
                              f"--kind quickstart` lists what the chandlery has")
    return load(path)


def answered(one: Quickstart) -> dict[str, str]:
    """Every answer it gives, keyed by the flag `generate` takes it as."""
    return {**{flag: value for flag in FLAGS if (value := getattr(one, flag))}, **dict(one.axes)}


def applied(one: Quickstart, given: Mapping[str, Any]) -> dict[str, Any]:
    """`given`, with every answer it did not already hold filled in from the quickstart.

    A flag a person typed wins, always. Every question a quickstart answers stays visible and changeable,
    which is the difference between a default and a decision made on somebody's behalf.
    """
    taken = dict(given)
    for flag, value in answered(one).items():
        if taken.get(flag) is None:
            taken[flag] = value
    return taken


def record(one: Quickstart) -> str:
    """`.slipwai/quickstart.json`: what the generated project carries about the quickstart it came from.

    Two facts `./init` needs and cannot work out: which extensions to elect without showing the menu, and
    which guards were already agreed to, so the question that lets an extension refuse a tool call is asked
    once per quickstart rather than once per project (13.4).
    """
    return json.dumps({
        "v": FORMAT,
        "name": one.name,
        "suits": one.suits,
        "extensions": [each.name for each in one.extensions],
        "guards": {each.name: list(each.guards) for each in one.extensions if each.guards},
    }, indent=2) + "\n"


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
    one = Quickstart(
        name=name, suits=suits,
        profile=str(manifest.get("profile", "")),
        target=str(manifest.get("target", "")),
        language=language,
        framework=str(service.get("framework", "")),
        frontend=str(manifest.get("frontend", "")),
        axes={axis: str(answer) for axis, answer in axes.items()} if isinstance(axes, Mapping) else {},
        languages=tuple(Wanted(package_name, range_for(str(version)))
                        for package_name, version in sorted(recorded.items())),
        extensions=tuple(Wanted(key, "", tuple(guards)) for key, guards in sorted(elected.items())),
    )
    return read(document(one))  # written and read back, so a `save` cannot write one `find` would refuse


def in_words(one: Quickstart) -> list[str]:
    """What `quickstart show` prints: what it would do, in words, before it does any of it.

    In the order somebody decides in — what it is for, what it would install, what it would elect and what
    it would be allowed to refuse, then the answers — and ending with the command that carries it out,
    which is the shape every refusal in this keel has too.
    """
    lines = [f"{one.name} — {one.suits}", ""]
    for each in one.languages:
        lines.append(f"  install       {each.said()}")
    for each in one.extensions:
        lines.append(f"  elect         {each.said()}")
        if each.guards:
            lines.append(f"                may refuse: {', '.join(each.guards)} — agreed when this "
                         f"quickstart was written")
    for flag in FLAGS:
        if value := getattr(one, flag):
            lines.append(f"  {flag:<13} {value}")
    for axis, answer in sorted(one.axes.items()):
        lines.append(f"  {axis:<13} {answer}")
    lines += ["", f"Nothing above has happened. `{this_command()} generate <name> --quickstart {one.name}` "
                  f"carries it out, and every answer stays a flag you can give instead."]
    return lines

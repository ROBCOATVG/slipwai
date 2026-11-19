"""`slipwai upgrade`'s extension step and `slipwai extension upgrade`: an installed extension, moved as a language is.

`upgrade` said what was installed and what was published for the keel and for each language and nothing for an
extension, so a machine could hold `ux-gates` 1.0.0 for as long as nobody happened to look at the chandlery —
while 1.0.1 had already fixed the path a project's CI called. Then (#114) it listed them, and ended each line
that found a newer one with a command to run, while a language beside it was moved (#119).

**One policy, the languages'.** A compatible newer release moves the extension; `--check` says the command
that would run and runs nothing; a release that needs another core schema holds it back, in the words a
language held back for that reason gets; and where the keel itself was just replaced, the move is made by the
copy that will load the result, a new process. An extension depends on no other package, so the half of a
language's rules that is about a family and its frameworks has nothing here to say.

**It agrees to nothing.** A release from a publisher this machine has not accepted is refused, as an install
of it would be, with the command that accepts them — an upgrade that was to move extensions and did not is an
upgrade that failed. And a guard is agreed to in a project, at election, by a person: a newer package that
declares one changes no project's agreement, and a project takes the package at its next `slipwai migrate`.

**What is admitted is what an install admits**: the manifest read under this keel's schema, staged, and renamed
into place only then, so a release that would not load never replaces one that does.
"""
from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .assets import relaunch, this_command
from .catalog import CORE
from .errors import GenerationError
from .extension_install import catalogue, install, is_path, is_remote
from .index_schema import EXTENSION, Index, Release
from .language_directory import directory
from .language_index import Unreachable, compatible, counted, newest, read_index
from .manifest import package_version
from .upgrade import LanguagesNotUpgraded
from .versions import key

Step = Callable[[bool, bool, bool], list[str]]
Runner = Callable[..., Any]  # `subprocess.run`'s shape: the seam a test's fake child stands in at
SCHEMA = CORE["schemaVersion"]


def is_extension(release: Release) -> bool:
    return release.kind == EXTENSION


def newer(index: Index, name: str, version: str, prerelease: bool) -> Release | None:
    """The newest counted release above the installed version that this keel can load, or None."""
    release = newest(index, name, SCHEMA, prerelease, is_extension)
    return release if release is not None and (version == "unknown" or key(release.version) > key(version)) else None


def line(index: Index, name: str, version: str, prerelease: bool) -> tuple[str, bool]:
    """One installed extension's line for `slipwai upgrade`, and whether a compatible newer release moves it."""
    release = newer(index, name, version, prerelease)
    if release is not None:
        return f"  {name} {version} → {release.version} available", True
    listed = [found for found in index.releases.get(name, [])
              if is_extension(found) and counted(found.version, prerelease)]
    other = [found.version for found in listed if not compatible(found, SCHEMA)
             and (version == "unknown" or key(found.version) > key(version))]
    if other:
        return (f"  {name} {version} held back: {max(other, key=key)} needs another core schema than "
                f"{SCHEMA} — {this_command()} upgrade, once a slipwai that speaks it is published"), False
    if not any(compatible(found, SCHEMA) for found in listed):
        return f"  {name} {version} — {index.name} lists no release of it this keel can install", False
    return f"  {name} {version} (newest compatible)", False


def installed(packages: Path) -> dict[str, str]:
    return {name: package_version(packages / name) for name, _ in catalogue(packages)}


def planned(prerelease: bool, packages: Path, index_reader: Callable[[], Index]) -> tuple[list[str], list[str]]:
    """The listing, and the names a compatible newer release would move."""
    have = installed(packages)
    if not have:
        return ["extensions: no extension is installed"], []
    try:
        index = index_reader()
    except Unreachable as error:
        return ["extensions:", *[f"  {name} {version}" for name, version in have.items()], f"  {error}",
                f"  upgrade from a local source: {this_command()} extension install <path-or-url>"], []
    said = [(name, *line(index, name, version, prerelease)) for name, version in have.items()]
    return ["extensions:", *[text for _, text, _ in said]], [name for name, _, moves in said if moves]


def standing(prerelease: bool, packages: Path | None = None,
             index_reader: Callable[[], Index] = read_index) -> list[str]:
    """One line per installed extension: its version, and the newest the index lists where that is newer."""
    lines, moving = planned(prerelease, directory() if packages is None else packages, index_reader)
    return [*lines, *taken(moving)]


def taken(moving: list[str]) -> list[str]:
    """What moving an installed package does not do: a project's copy is its own until it migrates."""
    return [f"  a project takes the installed package at its next `{this_command()} migrate`"] if moving else []


def upgrade(requests: list[str], packages: Path, index_reader: Callable[[], Index] = read_index,
            prerelease: bool = False) -> list[str]:
    """`extension upgrade`: each named extension moved to the newest compatible release above it — every installed
    one where none is named — or a line saying it is there already. A refusal names what to do."""
    have = installed(packages)
    for request in requests:
        if is_path(request) or is_remote(request):
            raise GenerationError(f"`extension upgrade` takes the names of installed extensions. A directory, a "
                                  f"release file or a git URL replaces the installed one as it installs: "
                                  f"{this_command()} extension install {request}")
        if request not in have:
            raise GenerationError(f"{request} is not an installed extension; installed: "
                                  f"{', '.join(sorted(have)) or 'none'}")
    try:
        index = index_reader()
    except Unreachable as error:
        raise GenerationError(f"{error}: upgrade from a local source: {this_command()} extension install "
                              f"<path-or-url>") from error
    said: list[str] = []
    notes: list[str] = []
    for name in list(dict.fromkeys(requests)) or sorted(have):
        release = newer(index, name, have[name], prerelease)
        if release is None:
            notes.append(f"{name} {have[name]} is the newest compatible release")
            continue
        landed = install([name], packages, prerelease=prerelease)[0]
        moved = f"upgraded {name} {have[name]} → {release.version} from"
        said.append(landed.replace(f"{name} installed from", moved, 1))
    return [*said, *notes]


def after_languages(check: bool, prerelease: bool, moved: bool, packages: Path | None = None,
                    index_reader: Callable[[], Index] = read_index, run: Runner = subprocess.run) -> list[str]:
    """`slipwai upgrade`'s extension step: each installed extension, current and available, and those a compatible
    newer release moves, moved — by a new process where the keel itself was just replaced. Extensions a run was to
    move and did not are `LanguagesNotUpgraded`, with the lines to say: the upgrade failed."""
    where = directory() if packages is None else packages
    lines, moving = planned(prerelease, where, index_reader)
    if not moving:
        return lines
    finish = f"{this_command()} extension upgrade {' '.join(moving)}"
    if check:
        return [*lines, f"would run: {finish}", *taken(moving)]
    if moved:
        flags = ["--pre"] if prerelease else []
        try:
            done = run([*relaunch(), "extension", "upgrade", *flags, *moving], text=True, capture_output=True)
        except OSError as error:
            raise LanguagesNotUpgraded([*lines, not_moved(f"could not start the new slipwai: {error}",
                                                          finish)]) from error
        said = (done.stdout + done.stderr).strip().splitlines()
        if done.returncode != 0:
            raise LanguagesNotUpgraded([*lines, *said,
                                        not_moved(f"its extension upgrade exited {done.returncode}", finish)])
        return [*lines, *said, *taken(moving)]
    try:
        return [*lines, *upgrade(moving, where, index_reader, prerelease), *taken(moving)]
    except GenerationError as error:
        raise LanguagesNotUpgraded([*lines, f"the extensions were not upgraded: {error}",
                                    f"finish the job: {finish}"]) from error


def not_moved(why: str, finish: str) -> str:
    return f"core moved and the extensions did not — {why}. Finish the job: {finish}"


def with_extensions(languages: Step, extensions: Step = after_languages) -> Step:
    """The language step followed by this one, whatever the first did: languages that did not move are still an
    upgrade that failed, and still not a reason the extensions go unlisted or unmoved — nor they the languages."""
    def step(check: bool, prerelease: bool, moved: bool) -> list[str]:
        said: list[str] = []
        failed = False
        for part in (languages, extensions):
            try:
                said += part(check, prerelease, moved)
            except LanguagesNotUpgraded as error:
                said, failed = [*said, *error.lines], True
        if failed:
            raise LanguagesNotUpgraded(said)
        return said
    return step

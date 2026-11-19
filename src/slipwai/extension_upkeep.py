"""`slipwai upgrade`'s extension step: each installed extension, installed against published.

`upgrade` said this for the keel and for each language and nothing for an extension, and `slipwai extension`
had no verb that did, so a machine could hold `ux-gates` 1.0.0 for as long as nobody happened to look at the
chandlery — while 1.0.1 had already fixed the path a project's CI called. This is the listing. It moves
nothing: an extension is replaced by installing it again, and the line that finds a newer one ends with that
command. A project then takes the installed package at its next `slipwai migrate`.
"""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from .assets import this_command
from .catalog import CORE
from .extension_install import catalogue
from .index_schema import EXTENSION, Index
from .language_directory import directory
from .language_index import Unreachable, newest, read_index
from .manifest import package_version
from .upgrade import LanguagesNotUpgraded
from .versions import key

Step = Callable[[bool, bool, bool], list[str]]


def standing(prerelease: bool, packages: Path | None = None,
             index_reader: Callable[[], Index] = read_index) -> list[str]:
    """One line per installed extension: its version, and the newest the index lists where that is newer."""
    where = directory() if packages is None else packages
    have = [(name, package_version(where / name)) for name, _ in catalogue(where)]
    if not have:
        return ["extensions: no extension is installed"]
    try:
        index = index_reader()
    except Unreachable as error:
        return ["extensions:", *[f"  {name} {version}" for name, version in have], f"  {error}"]
    lines = ["extensions:"]
    for name, version in have:
        release = newest(index, name, CORE["schemaVersion"], prerelease, lambda one: one.kind == EXTENSION)
        if release is None:
            lines.append(f"  {name} {version} — {index.name} lists no release of it this keel can install")
        elif version == "unknown" or key(release.version) > key(version):
            lines.append(f"  {name} {version} → {release.version} available: "
                         f"{this_command()} extension install {name}")
        else:
            lines.append(f"  {name} {version} (newest published)")
    if any("→" in line for line in lines):
        lines.append(f"  a project takes the installed package at its next `{this_command()} migrate`")
    return lines


def with_extensions(languages: Step, extensions: Callable[[bool], list[str]] = standing) -> Step:
    """The language step followed by this one, whatever the first said: languages that did not move are still
    an upgrade that failed, and still not a reason the extensions go unlisted."""
    def step(check: bool, prerelease: bool, moved: bool) -> list[str]:
        try:
            said = languages(check, prerelease, moved)
        except LanguagesNotUpgraded as error:
            raise LanguagesNotUpgraded([*error.lines, *extensions(prerelease)]) from error
        return [*said, *extensions(prerelease)]
    return step

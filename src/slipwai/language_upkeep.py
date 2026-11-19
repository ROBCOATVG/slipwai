"""`language upgrade` and `language remove`: moving an installed language, or taking one out.

An upgrade is the newest counted release above the installed version that this keel can load and that keeps every
framework's `requires` true — the framework's own, against its family as it will be, and each installed framework's,
against a family that moves — or the local source given. It is carried out as an install is: staged, admitted beside
what stays, renamed into place. A removal is refused while a framework of the family stays installed. A language
built into the keel moves with slipwai itself, so neither verb touches one.
"""
from __future__ import annotations

import contextlib
import os
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .assets import relaunch
from .errors import GenerationError
from .language_directory import directory
from .language_index import Index, Release, Unreachable, compatible, counted
from .language_install import (
    LOCK_WAIT,
    Admission,
    Installed,
    Renamer,
    Step,
    admit,
    carry_out,
    locked,
    origin,
    staging_area,
    this_command,
    unwritable,
)
from .language_plan import SCHEMA, Resolver, family_of, held, is_path, local, local_form, needs, needs_newer_core
from .language_release import Source
from .upgrade import LanguagesNotUpgraded
from .versions import key

Runner = Callable[..., Any]  # `subprocess.run`'s shape: the seam a test's fake child stands in at


def ships_with_core(name: str) -> GenerationError:
    moves = f"it moves with slipwai itself — {this_command()} upgrade"
    return GenerationError(f"{name} ships with core (built in): {moves}")


def checked_name(resolver: Resolver, name: str) -> Installed:
    if name in resolver.built:
        raise ships_with_core(name)
    if name not in resolver.have:
        raise GenerationError(f"{name} is not installed")
    return resolver.have[name]


def after(resolver: Resolver, family: str, moving: dict[str, Step]) -> str | None:
    """The family's version once this command is done: moved by it, installed, or None (absent or built in)."""
    step = moving.get(family)
    if step is not None and step.source is not None:
        return step.source.version
    return resolver.have[family].version if family in resolver.have else None


def newer(resolver: Resolver, have: Installed, moving: dict[str, Step]) -> Release | None:
    """The newest release above `have` that keeps its `requires` true against its family as it will be."""
    family = have.family or have.name

    def fits(release: Release) -> bool:
        version = after(resolver, family, moving)
        framework = family_of(release.fragment) != have.name
        return key(release.version) > key(have.version) and (
            not framework or version is None or held(version, needs(release.fragment)))

    try:
        return resolver.release(have.name, fits)
    except GenerationError as error:
        raise GenerationError(str(error).replace(local_form(), f"{this_command()} language upgrade <release file or "
                                                               "directory>")) from error


def held_back(resolver: Resolver, have: Installed, moving: dict[str, Step]) -> str:
    """Why nothing was upgraded: nothing newer, or a newer release that needs its family moved with it."""
    family = have.family or have.name
    version = after(resolver, family, moving)
    above = resolver.release(have.name, lambda release: key(release.version) > key(have.version))
    if above is None or version is None or family == have.name:
        return f"{have.name} {have.version} is the newest compatible release"
    return (f"{have.name} {above.version} needs {family} {needs(above.fragment)}, and {family} {version} is installed: "
            f"upgrade them together, {this_command()} language upgrade {family} {have.name}")


def left_behind(resolver: Resolver, other: Installed, family: str, version: str, wanted: str | None) -> str:
    """Why a family cannot move to `version` past the range the installed framework `other` needs: upgrade both,
    where a newer release of `other` fits the family as it would be; where none does, that it does not and the family
    stays, with no command — the together upgrade would only refuse again."""
    said = f"{other.name} {other.version} needs {family} {wanted}"
    try:
        fits = resolver.release(other.name, lambda release: key(release.version) > key(other.version)
                                and held(version, needs(release.fragment))) is not None
    except GenerationError:  # the index cannot say: the together upgrade is the one to try
        fits = True
    if not fits:
        return (f"{said}, and no release of {other.name} fits {family} {version} yet: {family} stays at "
                f"{resolver.have[family].version}")
    return f"{said}, and {family} would be {version}: upgrade them together, {this_command()} language upgrade " \
           f"{family} {other.name}"


def plan_upgrade(requests: list[str], directory: Path, index_reader: Callable[[], Index] | None,
                 prerelease: bool) -> tuple[list[Step], list[str]]:
    """The steps `language upgrade` takes, families first, and the lines it says beside them."""
    resolver, notes = Resolver(directory, index_reader, prerelease), []
    moving: dict[str, Step] = {}
    named = [(local(request), request) if is_path(request) else (None, request) for request in requests]

    def framework(pair: tuple[Step | None, str]) -> bool:  # families first: a framework's choice reads its family's
        step, request = pair
        if step is not None and step.source is not None:
            return family_of(step.source.fragment) != step.name
        return request in resolver.have and resolver.have[request].framework

    for step, request in sorted(named, key=framework):
        name = step.name if step is not None else request
        have = checked_name(resolver, name)
        if step is None:
            release = newer(resolver, have, moving)
            if release is None:
                notes.append(held_back(resolver, have, moving))
                continue
            fetched = resolver.step(release, "upgrade")
            said = fetched.said.replace(f"upgraded {name} ", f"upgraded {name} {have.version} → ", 1)
            step = Step("upgrade", name, fetched.source, fetched.data, said, fetched.where)
        else:
            assert step.source is not None
            said = f"upgraded {name} {have.version} → {step.source.version} from {origin(step.source)}"
            step = Step("upgrade", name, step.source, None, said, step.where)
        moving[name] = step
    for name, step in moving.items():
        assert step.source is not None
        version = step.source.version
        for other in resolver.have.values():
            wanted = needs(other.fragment or {})
            if other.framework and other.family == name and other.name not in moving and not held(version, wanted):
                raise GenerationError(left_behind(resolver, other, name, version, wanted))
    return sorted(moving.values(), key=lambda step: resolver.have[step.name].framework), notes


def upgrade(requests: list[str], directory: Path, index_reader: Callable[[], Index] | None = None,
            admission: Admission = admit, prerelease: bool = False, wait: float = LOCK_WAIT) -> list[str]:
    """`language upgrade`: the report, or `GenerationError` having changed nothing."""
    with locked(directory, wait):
        steps, notes = plan_upgrade(requests, directory, index_reader, prerelease)
        return [*(carry_out(steps, directory, admission) if steps else []), *notes]


def remove(names: list[str], directory: Path, wait: float = LOCK_WAIT, rename: Renamer = os.rename) -> list[str]:
    """`language remove`: frameworks before their families, each taken out by one rename; or a refusal, having taken
    out nothing."""
    with locked(directory, wait):
        return removed(names, directory, rename)


def removed(names: list[str], directory: Path, rename: Renamer = os.rename) -> list[str]:
    resolver = Resolver(directory, None, False)
    leaving = [checked_name(resolver, name) for name in dict.fromkeys(names)]
    gone = {have.name for have in leaving}
    for have in leaving:
        staying = [other.name for other in resolver.have.values()
                   if other.framework and other.family == have.name and other.name not in gone]
        if staying:
            raise GenerationError(
                f"{', '.join(staying)} {'is' if len(staying) == 1 else 'are'} installed and "
                f"need{'s' if len(staying) == 1 else ''} {have.name}: {this_command()} language remove "
                f"{' '.join(staying)} first")
    ordered = sorted(leaving, key=lambda have: not have.framework)
    area = staging_area(directory)
    taken: list[Installed] = []
    try:
        for have in ordered:
            rename(have.root, area / f"removed-{have.name}")
            taken.append(have)
    except OSError as error:
        for have in reversed(taken):  # a removal is all of it or none: what was taken out goes back
            with contextlib.suppress(OSError):
                os.rename(area / f"removed-{have.name}", have.root)
        raise unwritable(directory, error) from error
    finally:
        shutil.rmtree(area, ignore_errors=True)
    return [f"removed {have.name} {have.version}" for have in ordered]


def standing(resolver: Resolver, have: Installed) -> tuple[str, bool]:
    """One installed language's line for `slipwai upgrade`, and whether a compatible newer release would move it."""
    try:
        release = newer(resolver, have, {})
        if release is not None:
            return f"  {have.name} {have.version} → {release.version} available", True
        why = held_back(resolver, have, {})
    except GenerationError as error:  # held back where only a newer keel reaches a release
        said = str(error).split(": install")[0]
        ahead = needs_newer_core(resolver.index(), have.name, resolver.prerelease)
        return f"  {have.name} {have.version}{' held back:' if ahead else ' —'} {said}", False
    other = [found.version for found in resolver.index().releases.get(have.name, [])
             if counted(found.version, resolver.prerelease) and key(found.version) > key(have.version)
             and not compatible(found, SCHEMA)]
    if other:
        return (f"  {have.name} {have.version} held back: {max(other, key=key)} needs another core schema than "
                f"{SCHEMA} — {this_command()} upgrade, once a slipwai that speaks it is published"), False
    if why.endswith("is the newest compatible release"):
        return f"  {have.name} {have.version} (newest compatible)", False
    return f"  {have.name} {have.version} held back: {why}", False


def moves_together(resolver: Resolver, have: list[Installed]) -> tuple[dict[str, Release], dict[str, str]]:
    """What `upgrade` would move, planned as `plan_upgrade` plans it — a framework's choice read against its family as
    it will be — and the families it would not, with why: one whose installed framework would block it alone, and
    has no newer release that works with it. (FR-027: `--check` shows the plan `upgrade` carries out.)"""
    held_off: dict[str, str] = {}
    while True:
        chosen: dict[str, Release] = {}
        steps: dict[str, Step] = {}
        for package in sorted(have, key=lambda found: found.framework):  # families first
            if package.name in held_off:
                continue
            try:
                release = newer(resolver, package, steps)
            except GenerationError:
                continue
            if release is not None:
                chosen[package.name] = release
                source = Source(release.name, release.version, release.fragment, Path(release.name), "index")
                steps[package.name] = Step("upgrade", package.name, source)
        blocked = False
        for name, release in chosen.items():
            for other in resolver.have.values():
                wanted = needs(other.fragment or {})
                if (other.framework and other.family == name and other.name not in chosen
                        and not held(release.version, wanted)):
                    held_off[name] = (f"{name} {release.version} would leave {other.name} {other.version} (needs "
                                      f"{name} {wanted}) with no newer release that works with it")
                    blocked = True
        if not blocked:
            return chosen, held_off


def after_core(check: bool, prerelease: bool, moved: bool, run: Runner = subprocess.run) -> list[str]:
    """`slipwai upgrade`'s language step (FR-027, Story 4 scenarios 6 and 11): each installed language, current and
    available, and those a compatible newer release moves, moved — by the copy that will load them, a new process,
    where the keel itself was just replaced. An index that cannot be reached is said, with the local-source form; the
    installed versions are listed either way, never an empty list. Built-in languages move with the keel. Languages that
    a run was to move and did not are `LanguagesNotUpgraded`, with the lines to say."""
    where = directory()
    resolver = Resolver(where, None, prerelease)
    # Languages only: the directory holds extensions and targets too, and each was listed here as a language
    # that could not be upgraded. An extension has its own step (`extension_upkeep`), a target its own verb.
    have = [package for name, package in resolver.have.items() if name not in resolver.built
            and not any((package.root / other).is_file() for other in ("extension.json", "target.json"))]
    if not have:
        return ["languages: no language is installed"]
    try:
        resolver.index()
    except Unreachable as error:
        return ["languages:", *[f"  {package.name} {package.version}" for package in have], f"  {error}",
                f"  upgrade from a local source: {this_command()} language upgrade <release file or directory>"]
    chosen, held_off = moves_together(resolver, have)
    lines = ["languages:"]
    for package in have:
        if package.name in chosen:
            lines.append(f"  {package.name} {package.version} → {chosen[package.name].version} available")
        elif package.name in held_off:
            lines.append(f"  {package.name} {package.version} held back: {held_off[package.name]}")
        else:
            line, upgradable = standing(resolver, package)
            lines.append(f"  {package.name} {package.version} held back: its newer release does not work with the "
                         f"family as it will be" if upgradable else line)
    moving = [package.name for package in have if package.name in chosen]
    if not moving:
        return lines
    finish = f"{this_command()} language upgrade {' '.join(moving)}"
    if check:
        return [*lines, f"would run: {finish}"]
    if moved:
        flags = ["--pre"] if prerelease else []
        try:
            done = run([*relaunch(), "language", "upgrade", *flags, *moving], text=True, capture_output=True)
        except OSError as error:
            why = not_moved(f"could not start the new slipwai: {error}", finish)
            raise LanguagesNotUpgraded([*lines, why]) from error
        said = (done.stdout + done.stderr).strip().splitlines()
        if done.returncode != 0:
            why = not_moved(f"its language upgrade exited {done.returncode}", finish)
            raise LanguagesNotUpgraded([*lines, *said, why])
        return [*lines, *said]
    try:
        return [*lines, *upgrade(moving, where, prerelease=prerelease)]
    except GenerationError as error:
        raise LanguagesNotUpgraded([*lines, f"the languages were not upgraded: {error}",
                                    f"finish the job: {finish}"]) from error


def not_moved(why: str, finish: str) -> str:
    return f"core moved and the languages did not — {why}. Finish the job: {finish}"

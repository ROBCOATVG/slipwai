"""Which packages `language install` places, and in what order: the plan `language_install` carries out.

A request is a local source when it is spelled as a path (it holds a `/`, ends in `.tar.gz`, or is `.`), and a
language's name otherwise, so `install go` never means a directory called `go` in the working directory. A framework
(a package whose `name` is not its `family`) brings its family; a family that names `default_framework` brings that
framework; families are placed before their frameworks (`contracts/language-index.md`, *What a verb resolves*).
"""
from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .catalog import CORE
from .errors import GenerationError
from .language_index import Index, Release, Unreachable, bare, counted, download, must_be_language, newest, read_index
from .language_install import (
    LOCK_WAIT,
    Admission,
    Step,
    admit,
    builtin,
    carry_out,
    installed,
    locked,
    origin,
    this_command,
)
from .language_release import Source, read_source
from .manifest import recorded_languages
from .versions import base, below, key, satisfies

LOCAL = "release file or directory"
SCHEMA = str(CORE["schemaVersion"])
Item = Step | Release  # a request: a local source read into a step, or the index's release for a name


def is_path(request: str) -> bool:
    """Whether a request is spelled as a path rather than as a name."""
    return os.sep in request or "/" in request or request.endswith(".tar.gz") or request in (".", "..")


def local_form(what: str = f"<{LOCAL}>") -> str:
    """The local-source form of the install command, for wherever the index could not answer."""
    return f"{this_command()} language install {what}"


def needs_newer_core(index: Index, name: str, prerelease: bool) -> bool:
    """Whether a counted release of `name` needs a newer keel: a slipwai upgrade, once published, would reach it."""
    def ahead(text: object) -> bool:
        try:
            return isinstance(text, str) and below(SCHEMA, text)
        except ValueError:
            return False

    return any(counted(r.version, prerelease) and ahead(r.fragment.get("core")) for r in index.releases.get(name, []))


def no_release(index: Index, name: str, prerelease: bool) -> str:
    """Why no release of `name` in the index loads here, by direction (D116 #7): the releases are ahead of this keel,
    and `upgrade` is the way once a slipwai speaking theirs is published; or all are behind it, and nothing is."""
    where = f"the language index at {index.url}"
    if needs_newer_core(index, name, prerelease):
        return (f"the releases of {name} in {where} need a newer core schema than {SCHEMA}: {this_command()} upgrade, "
                "once a slipwai that speaks it is published")
    return f"no release of {name} in {where} is built for core schema {SCHEMA} yet"


def fragment_of(item: Item) -> dict[str, Any]:
    if isinstance(item, Release):
        return item.fragment
    assert item.source is not None
    return item.source.fragment


def family_of(fragment: dict[str, Any]) -> str:
    return str(fragment.get("family", fragment.get("name")))


def is_framework(item: Item) -> bool:
    fragment = fragment_of(item)
    return family_of(fragment) != fragment.get("name")


def needs(fragment: dict[str, Any]) -> str | None:
    """The range a framework's `requires` holds its family to, or None."""
    wanted = fragment.get("requires")
    found = wanted.get(family_of(fragment)) if isinstance(wanted, dict) else None
    return found if isinstance(found, str) else None


def held(version: str, wanted: str | None) -> bool:
    """Whether a family at `version` satisfies `wanted`, a snapshot held as the release it heads for (ADR 0004)."""
    if wanted is None:
        return True
    release = base(version)
    try:
        return release is not None and satisfies(release, wanted)
    except ValueError:
        return False


def answers(fragment: dict[str, Any], framework: str) -> bool:
    """Whether a release carries a backend whose `framework` is `framework`."""
    rows = fragment.get("backends")
    rows = rows.values() if isinstance(rows, dict) else []
    return any(isinstance(row, dict) and row.get("framework") == framework for row in rows)


class Resolver:
    """What one command can see: what is installed, what is built in, and the index, read at most once."""

    def __init__(self, directory: Path, index_reader: Callable[[], Index] | None, prerelease: bool) -> None:
        self.have, self.built = installed(directory), builtin()
        self.reader, self.prerelease = index_reader or read_index, prerelease
        self.read: Index | None = None

    def index(self) -> Index:
        if self.read is None:
            self.read = self.reader()
        return self.read

    def release(self, name: str, where: Callable[[Release], bool] | None = None) -> Release | None:
        """The newest counted release of `name` this keel can load that `where` accepts; a refusal where the index
        cannot be read, has no `name`, or has none this keel can load."""
        try:
            index = self.index()
        except Unreachable as error:
            raise GenerationError(f"{error}: install from a local source: {local_form()}") from error
        must_be_language(index, name, local_form())
        if newest(index, name, SCHEMA, self.prerelease) is None:
            raise GenerationError(no_release(index, name, self.prerelease))
        return newest(index, name, SCHEMA, self.prerelease, where)

    def step(self, item: Item, action: str = "install", why: str = "") -> Step:
        """A local step as it is, or the index's release fetched, hash-checked and said with where it came from."""
        if isinstance(item, Step):
            return item
        index = self.index()
        source = Source(item.name, item.version, item.fragment, Path(item.name), "index")
        said = (f"{action.rstrip('e')}ed {item.name} {item.version} from the language index at {index.url} "
                f"(sha256 {item.sha256[:12]}…){why}")
        return Step(action, item.name, source, download(index, item), said, bare(item.url))

    def version_of(self, family: str, chosen: dict[str, Step]) -> str | None:
        """The version the family will be at: placed by this command, installed, or None (absent, or built in)."""
        placed = chosen.get(family)
        if placed is not None and placed.source is not None:
            return placed.source.version
        return self.have[family].version if family in self.have else None


def local(request: str) -> Step:
    source = read_source(Path(request).expanduser())
    return Step("install", source.name, source, None, f"installed {source.name} {source.version} from {origin(source)}",
                str(source.path))


def with_family(resolver: Resolver, item: Item, chosen: dict[str, Step]) -> list[Step]:
    """A framework's step, after the family step it brings; or the refusal that says why it cannot be placed."""
    fragment = fragment_of(item)
    name, family, wanted = str(fragment["name"]), family_of(fragment), needs(fragment)
    version = resolver.version_of(family, chosen)
    if family in resolver.built:
        return [resolver.step(item)]
    if version is not None:
        if isinstance(item, Step):
            if not held(version, wanted):
                where = "being installed" if family in chosen else "installed"
                raise GenerationError(f"{name} needs {family} {wanted}, and {family} {version} is {where}")
            return [item]
        fits = resolver.release(name, lambda release: held(version, needs(release.fragment)))
        if fits is None:
            raise GenerationError(
                f"no release of {name} in the language index at {resolver.index().url} works with the installed "
                f"{family} {version} ({name} {item.version} needs {family} {wanted})")
        return [resolver.step(fits)]
    try:
        family_release = resolver.release(family, lambda release: held(release.version, wanted))
    except GenerationError as error:
        if not isinstance(item, Step) or item.source is None:
            raise
        raise GenerationError(
            f"{name} needs its family {family}, which is not installed, and {error.args[0].split(': install')[0]}; "
            f"install both from local sources: {local_form(f'<{family} {LOCAL}> {item.source.path}')}") from error
    if family_release is None:
        raise GenerationError(f"no release of {family} in the language index at {resolver.index().url} satisfies "
                              f"{name}'s {family} {wanted}")
    return [resolver.step(family_release, why=f" — the family {name} needs"), resolver.step(item)]


def default_framework(resolver: Resolver, family: Step, chosen: dict[str, Step]) -> Step | str | None:
    """The step a family's `default_framework` brings, a line saying why it could not, or None where nothing is owed."""
    assert family.source is not None
    framework, name, version = family.source.fragment.get("default_framework"), family.name, family.source.version
    if not isinstance(framework, str):
        return None
    if any(have.framework and have.family == name for have in resolver.have.values()) or any(
        is_framework(step) and family_of(fragment_of(step)) == name for step in chosen.values()
    ):
        return None
    try:
        index = resolver.index()
    except Unreachable as error:
        return f"{name}'s default framework {framework} is not installed: {error}; install it from a local source: " \
               f"{local_form()}"

    def fits(release: Release) -> bool:
        fragment = release.fragment
        return family_of(fragment) == name and answers(fragment, framework) and held(version, needs(fragment))

    found = [r for r in (newest(index, other, SCHEMA, resolver.prerelease, fits) for other in index.releases) if r]
    if not found:
        return f"{name}'s default framework {framework} is in no release of the language index at {index.url} " \
               f"that works with {name} {version}"
    return resolver.step(found[0], why=f" — {name}'s default framework is {framework}")


def taken_by_installed(resolver: Resolver, family: Step) -> None:
    """Refuse a family placed at a version that an installed framework of it does not take: the rule an upgrade keeps
    (`language_upkeep.plan_upgrade`), kept where the family was absent and its frameworks refused for it."""
    assert family.source is not None
    name, version = family.name, family.source.version
    left = [have for have in resolver.have.values() if have.framework and have.family == name
            and not held(version, needs(have.fragment or {}))]
    if left:
        why = "; ".join(f"{have.name} {have.version} needs {name} {needs(have.fragment or {})}" for have in left)
        raise GenerationError(
            f"{name} {version} would leave {', '.join(have.name for have in left)} refused: {why}: install a release "
            f"of {name} they take, or {this_command()} language remove {' '.join(have.name for have in left)} first")


def plan_install(requests: list[str], directory: Path, index_reader: Callable[[], Index] | None,
                 prerelease: bool) -> tuple[list[Step], list[str]]:
    """The steps `language install` takes, families first, and the lines it says beside them."""
    resolver, notes, asked = Resolver(directory, index_reader, prerelease), [], []
    for request in requests:
        if not is_path(request) and request in resolver.built:
            notes.append(f"{request} is built in to this slipwai; nothing to install")
            continue
        item: Item | None = local(request) if is_path(request) else (
            None if request in resolver.have else resolver.release(request))
        name = item.name if item is not None else request
        if name in resolver.have:
            raise GenerationError(f"{name} is already installed ({resolver.have[name].version}): "
                                  f"{this_command()} language upgrade {name}")
        assert item is not None
        asked.append(item)
    chosen: dict[str, Step] = {}
    for item in [item for item in asked if not is_framework(item)]:
        chosen[item.name] = resolver.step(item)
    for item in [item for item in asked if is_framework(item)]:
        for placed in with_family(resolver, item, chosen):
            chosen.setdefault(placed.name, placed)
    for family in [step for step in list(chosen.values()) if not is_framework(step)]:
        taken_by_installed(resolver, family)
        brought = default_framework(resolver, family, chosen)
        if isinstance(brought, Step):
            chosen[brought.name] = brought
        elif brought is not None:
            notes.append(brought)
    return sorted(chosen.values(), key=is_framework), notes


def install(requests: list[str], directory: Path, index_reader: Callable[[], Index] | None = None,
            admission: Admission = admit, prerelease: bool = False, wait: float = LOCK_WAIT) -> list[str]:
    """`language install`: the report, a line a package placed, or `GenerationError` having placed nothing."""
    with locked(directory, wait):
        steps, notes = plan_install(requests, directory, index_reader, prerelease)
        return [*(carry_out(steps, directory, admission) if steps else []), *notes]


def framework_package(resolver: Resolver, language: str, framework: str) -> str | None:
    """The package answering `framework` of `language` for a 1.x project: installed first, then the index; None where
    neither says, which the caller refuses rather than guessing from the framework's name."""
    for have in resolver.have.values():
        if have.family == language and answers(have.fragment or {}, framework):
            return have.name
    found = [release for name in resolver.index().releases
             if (release := newest(resolver.index(), name, SCHEMA, resolver.prerelease,
                                   lambda r: family_of(r.fragment) == language and answers(r.fragment, framework)))]
    return found[0].name if found else None


def project_names(document: dict[str, Any], resolver: Resolver) -> list[str]:
    """Every package the project needs that is not installed or built in: the record's names, or for a 1.x project,
    each generated application's family and, for a service with a framework, the package carrying it."""
    recorded = recorded_languages(document)
    if recorded is not None:
        return [name for name in recorded if name not in resolver.have and name not in resolver.built]
    needed: list[str] = []
    for app, record in (document.get("deployables") or {}).items():
        if not isinstance(record, dict) or record.get("generated") is False:
            continue  # an application the keel did not make is in whatever language it is, and needs none
        if not isinstance(record.get("language"), str):
            continue
        language, framework = record["language"], record.get("framework") if record.get("kind") == "service" else None
        if language in resolver.built:  # a language still built in has every framework of it built in too
            continue
        if language not in resolver.have:
            needed.append(language)
        if isinstance(framework, str):
            try:
                found = framework_package(resolver, language, framework)
            except Unreachable as error:
                raise GenerationError(f"the service {app} needs {language}'s framework {framework}, which no installed "
                                      f"package answers, and {error}: install it from a local source: "
                                      f"{local_form()}") from error
            if found is None:
                raise GenerationError(f"the service {app} needs {language}'s framework {framework}, and neither an "
                                      f"installed package nor the language index at {resolver.index().url} answers "
                                      f"it: install it from a local source: {local_form()}")
            needed.append(found)
    return list(dict.fromkeys(name for name in needed if name not in resolver.have))


def held_to_record(steps: list[Step], recorded: dict[str, str]) -> None:
    """Refuse a plan that would place a package older than the version the project records for it (Story 4 scenario
    10): `refuse_older` would refuse that project at the very next run, on an upgrade nobody can follow."""
    for step in steps:
        wanted = recorded.get(step.name)
        if step.source is not None and wanted is not None and key(step.source.version) < key(wanted):
            raise GenerationError(
                f"this project records {step.name} {wanted}, and the newest {step.name} on offer that this slipwai "
                f"can load is {step.source.version}, which is older: install {step.name} {wanted} or newer")


def install_for(document: dict[str, Any], directory: Path, prerelease: bool,
                index_reader: Callable[[], Index] | None = None, admission: Admission = admit) -> list[str]:
    """What `migrate` installs before it replays: every package the project needs, in one plan and one
    transaction under the package directory's lock, or a refusal having installed nothing that names the install
    command and the local-source form. The report, a line a package placed; empty where nothing was missing."""
    if not project_names(document, Resolver(directory, index_reader, prerelease)):
        return []  # nothing missing: the package directory is not touched, not even by its lock
    with locked(directory):
        names = project_names(document, Resolver(directory, index_reader, prerelease))  # again, holding it
        if not names:
            return []
        try:
            steps, notes = plan_install(names, directory, index_reader, prerelease)
            held_to_record(steps, recorded_languages(document) or {})
            return [*carry_out(steps, directory, admission), *notes]
        except GenerationError as error:
            raise GenerationError(
                f"{error}. Nothing was installed and nothing in this project changed. Install what it needs, then run "
                f"migrate again: {this_command()} language install {' '.join(names)}; from a local source: "
                f"{local_form()}") from error

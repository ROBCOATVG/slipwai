"""What is installed, and an install, upgrade or removal as one transaction the loader admits before it lands.

The package directory is the record of what is installed: every directory in it that is not hidden, whether
or not the loader admits it, so a refused package can still be upgraded or removed. Everything a command brings is
staged in a hidden `.install-<token>/` beside them, which the loader skips; the staged set is admitted the way the
next start would load it — `language_directory.fault_in`, `catalog_merge.merge`, `loaded.build`, over what stays
installed plus what is staged — and only then is each package renamed into place. A language is therefore whole in
the directory or not there (`contracts/language-index.md`, *How an install lands*).
"""
from __future__ import annotations

import copy
import os
import shutil
import sys
import tempfile
import time
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .assets import ROOT, this_command  # noqa: F401 — the verbs read it from here
from .catalog import CORE
from .catalog_merge import merge
from .errors import GenerationError
from .language_directory import Package, fault_in, named, parse_fragment, read, refusal
from .language_release import ReleaseError, Source, copy_directory, read_directory, unpack
from .language_shape import name_fault
from .loaded import build
from .registry import registry

STAGING = ".install-"
LOCK = ".lock"
UNREADABLE = "unreadable VERSION"
LOCK_WAIT = 3.0  # seconds a writing verb waits for another's lock before it refuses


@dataclass(frozen=True)
class Installed:
    """One directory of the package directory: its name, its root, its `VERSION` and its fragment where readable."""

    name: str
    root: Path
    version: str
    fragment: dict[str, Any] | None

    @property
    def family(self) -> str | None:
        family = (self.fragment or {}).get("family")
        return family if isinstance(family, str) else None

    @property
    def framework(self) -> bool:
        return self.family is not None and self.family != self.name


@dataclass(frozen=True)
class Step:
    """One package a command places or takes out: the source it comes from (None for a removal), the bytes fetched for
    it from an index, the words the report says it with, and where a refusal says it came from."""

    action: str
    name: str
    source: Source | None = None
    data: bytes | None = None
    said: str = ""
    where: str = ""


def installed(directory: Path) -> dict[str, Installed]:
    """Every package directory in the package directory, by name; hidden entries (a staging area) are not."""
    found: dict[str, Installed] = {}
    if not directory.is_dir():
        return found
    for entry in sorted(directory.iterdir()):
        if entry.name.startswith(".") or not entry.is_dir():
            continue
        fragment, _ = parse_fragment(entry / "language.json")
        version = "unknown"
        if (entry / "VERSION").is_file():
            try:
                version = (entry / "VERSION").read_text(encoding="utf-8").strip()
            except (UnicodeDecodeError, OSError):
                version = UNREADABLE  # still listed, upgraded or removed: one bad file never locks the verbs out
        found[entry.name] = Installed(entry.name, entry, version, fragment if isinstance(fragment, dict) else None)
    return found


def builtin() -> dict[str, str]:
    """Each language built into the keel, by the name it would install as, and its family.

    Version 2 has none and this always answers empty: every language is a package, and the structure
    gate refuses a `slipwai_language_*` import anywhere in `src/`. It is still asked, and still reads
    the registry rather than returning a literal `{}`, because the question it answers — "is this name
    already answered by something the installer cannot replace?" — is the right question and the answer
    is a fact about the loaded registry, not a constant. A keel that grew one back would be caught here
    rather than by a silent overwrite.
    """
    loaded = registry()
    found = {name: name for name in loaded.families if loaded.root(name) == ROOT}
    found.update({key: backend.family for key, backend in loaded.backends.items()
                  if loaded.root(key) == ROOT and key != backend.family})
    return found


@contextmanager
def modules_kept() -> Iterator[None]:
    """Leave `sys.modules`' language packages as they were: admission imports each package again."""
    before = {name: module for name, module in sys.modules.items() if name.startswith("slipwai_language_")}
    try:
        yield
    finally:
        for name in [name for name in sys.modules if name.startswith("slipwai_language_")]:
            del sys.modules[name]
        sys.modules.update(before)


def outcome(packages: list[Package]) -> tuple[dict[str, str], list[str]]:
    """What the next start would refuse of `packages`: the merge's line by name, and the build's lines."""
    catalog, refused, _ = merge(CORE, packages)
    with modules_kept():
        # No built-in languages to put first: version 2's keel has none, and a `slipwai_language_*`
        # import anywhere in `src/` fails the structure gate. `build` still takes the argument, for the
        # conformance suite holding one package against a registry of nothing else.
        _, lines = build((), [p for p in packages if p.name not in refused], copy.deepcopy(catalog))
    return refused, lines


def refused_of(packages: list[Package], refused: dict[str, str], lines: list[str]) -> dict[str, list[str]]:
    """Each of `packages` the merge or the build refuses, with the lines that are its own."""
    found = {p.name: [refused[p.name]] if p.name in refused else
             [line for line in lines if line.startswith(f"{named(p.name, p.root)}:")] for p in packages}
    return {name: said for name, said in found.items() if said}


def admit(directory: Path, staged: dict[str, Path], leaving: set[str]) -> list[str]:
    """The loader's line for each staged package it would refuse, read beside what stays installed; or, where every
    one loads but leaves refused a package that loads now, the one line that names those; none where nothing
    is. `staged` maps a name to its staged root; `leaving` are the installed names being replaced or removed."""
    schema = str(CORE["schemaVersion"])
    kept, _ = read(directory, schema)
    view = [package for package in kept if package.name not in leaving and package.name not in staged]
    faults: list[str] = []
    candidates: list[Package] = []
    for name, root in staged.items():
        fragment, fault = fault_in(name, root, schema)
        if fragment is None:
            faults.append(refusal(name, root, fault or "has no language.json"))
        else:
            candidates.append(Package(name, root, fragment))
    if faults:
        return faults
    packages = sorted([*view, *candidates], key=lambda package: package.name)
    refused, lines = outcome(packages)
    if faults := [line for said in refused_of(candidates, refused, lines).values() for line in said]:
        return faults
    after = refused_of(view, refused, lines)
    before = refused_of(kept, *outcome(kept)) if after else {}
    broken = {name: said for name, said in after.items() if name not in before}
    if not broken:
        return []
    now = "it loads" if len(broken) == 1 else "they load"
    return [f"{', '.join(staged)} would leave {', '.join(broken)} refused, and {now} now: "
            + "; ".join(line for said in broken.values() for line in said)]


Admission = Callable[[Path, dict[str, Path], set[str]], list[str]]
Renamer = Callable[[Path, Path], object]  # the seam a test sets to make one rename fail; `os.rename` is the default


def cause(error: OSError) -> str:
    """What an `OSError` says in a refusal: its reason, never its text, which names the paths it was given — a hidden
    staging path among them, which is nobody's to act on."""
    return error.strerror or type(error).__name__


def unwritable(directory: Path, error: OSError) -> GenerationError:
    """The one line for a package directory the transaction cannot write: which directory, and the fault."""
    return GenerationError(f"the language directory {directory} cannot be written: {cause(error)}")


def try_lock(handle: Any) -> bool:
    """Take the exclusive lock on an open file without waiting; False where another holds it. The operating system
    drops it with the process, so a killed command never leaves a lock to clear."""
    try:
        if os.name == "nt":
            import msvcrt

            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)  # type: ignore[attr-defined]
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return False
    return True


@contextmanager
def locked(directory: Path, wait: float = LOCK_WAIT) -> Iterator[None]:
    """Hold the package directory's lock for the whole of a writing verb, plan and placement alike, so two commands
    never plan from one state or clear one another's staging area. A second waits up to `wait` seconds, then refuses
    in one line naming the lock."""
    path = directory / LOCK
    if path.is_symlink():  # opening it would create, or write, whatever it points at
        raise GenerationError(f"{path} is a link, and the language directory's lock must be a file of its own: "
                              "remove it and run this again")
    try:
        directory.mkdir(parents=True, exist_ok=True)
        handle = path.open("a+")
    except OSError as error:
        raise unwritable(directory, error) from error
    with handle:
        deadline = time.monotonic() + wait
        while not try_lock(handle):
            if time.monotonic() >= deadline:
                raise GenerationError(f"another slipwai language command is changing {directory} (it holds {path}): "
                                      "run this again when it has finished")
            time.sleep(0.05)
        yield


def staging_area(directory: Path) -> Path:
    """A fresh hidden staging directory, with whatever a stopped command left behind cleared first."""
    try:
        directory.mkdir(parents=True, exist_ok=True)
        for entry in directory.iterdir():
            if entry.name.startswith(STAGING) and entry.is_dir():
                shutil.rmtree(entry, ignore_errors=True)
        return Path(tempfile.mkdtemp(prefix=STAGING, dir=directory))
    except OSError as error:
        raise unwritable(directory, error) from error


def stage(step: Step, area: Path) -> Path:
    """The step's package written under the staging area as `<name>/`."""
    source, target = step.source, area / step.name
    assert source is not None
    if (fault := name_fault("language", step.name)) is not None:
        raise GenerationError(f"{fault}: refusing to place it")
    try:
        if step.data is not None:
            archive = area / f"{step.name}.tar.gz"
            archive.write_bytes(step.data)
            unpack(archive, target, step.name)
            held_to_entry(source, read_directory(target))
        elif source.kind == "directory":
            if area.resolve().is_relative_to(source.path.resolve()):
                raise ReleaseError(f"{source.path} contains the language directory {area.parent}: install from a "
                                   "package directory that does not")
            copy_directory(source.path, target)
        else:
            unpack(source.path, target)
    except ReleaseError:
        raise
    except (OSError, shutil.Error) as error:
        raise GenerationError(f"{step.name} could not be copied from {source.path}: {cause(error)}") from error
    for fragment in sorted((target / "changelog.d").glob("*.md")):
        try:
            fragment.read_bytes().decode("utf-8")
        except UnicodeDecodeError as error:
            raise ReleaseError(f"{step.name}: changelog.d/{fragment.name} is not UTF-8 text, so the changelog "
                               "it holds cannot be read") from error
        except OSError:
            continue
    return target


def held_to_entry(entry: Source, landed: Source) -> None:
    """A release fetched from an index is the release its entry describes: the same `VERSION` and `language.json`."""
    if landed.version != entry.version:
        raise ReleaseError(f"the release file for {entry.name} {entry.version} holds VERSION {landed.version}")
    if landed.fragment != entry.fragment:
        raise ReleaseError(f"the release file for {entry.name} {entry.version} holds a language.json other than the "
                           "one the index publishes")


def shown(line: str, staged: dict[str, Path], steps: Sequence[Step]) -> str:
    """A loader line with each staged root put back as the source the user named."""
    for step in steps:
        if step.name in staged:
            line = line.replace(str(staged[step.name]), step.where)
    return line


def place(steps: Sequence[Step], staged: dict[str, Path], directory: Path, area: Path,
          rename: Renamer = os.rename) -> None:
    """Rename each staged package into place, an installed one moved aside first. On a failure every step already
    taken is undone, last first — a new package moved back out, an old one moved back in — so the directory is what it
    was before the command, and the refusal says what is installed afterwards."""
    undo: list[tuple[Path, Path]] = []  # (where it is now, where it was), in the order they were done
    try:
        for step in steps:
            target = directory / step.name
            if target.exists():
                rename(target, area / f"left-{step.name}")
                undo.append((area / f"left-{step.name}", target))
            if step.name in staged:
                rename(staged[step.name], target)
                undo.append((target, area / f"placed-{step.name}"))
    except OSError as error:
        for here, there in reversed(undo):
            try:
                if here.exists() and not there.exists():
                    os.rename(here, there)
            except OSError:
                continue  # best effort: the next one may still be put back
        names = [step.name for step in steps]
        now = installed(directory)
        kept = [f"{name} {now[name].version}" for name in names if name in now]
        afterwards = ", ".join(kept) if kept else f"none of {', '.join(names)} is installed"
        said = f"{step.name} could not be moved into place: {cause(error)}; installed afterwards: "
        raise GenerationError(said + afterwards) from error


def carry_out(steps: Sequence[Step], directory: Path, admission: Admission = admit,
              rename: Renamer = os.rename) -> list[str]:
    """Stage every package the steps bring, admit them together, then rename each into place in order; or refuse,
    having renamed nothing. Returns the report, a line a step."""
    for step in steps:
        target = directory / step.name
        if step.source is not None and (target.is_symlink() or target.exists()) and not target.is_dir():
            raise GenerationError(f"{target} is not a package directory, and is not replaced: move it aside and "
                                  "run this again")
    area = staging_area(directory)
    try:
        staged = {step.name: stage(step, area) for step in steps if step.source is not None}
        leaving = {step.name for step in steps if (directory / step.name).exists()}
        faults = admission(directory, staged, leaving)
        if faults:
            raise GenerationError("; ".join(shown(fault, staged, steps) for fault in faults))  # one line
        place(steps, staged, directory, area, rename)
    finally:
        shutil.rmtree(area, ignore_errors=True)
    return [step.said for step in steps]


def origin(source: Source) -> str:
    return f"the local source {source.path}" if source.kind == "directory" else f"the local release file {source.path}"

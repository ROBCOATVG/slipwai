"""Putting a target in the package directory, and taking it out again.

An extension's install is a stage and a rename: it adds a catalogue entry and a directory of files, declares
no backend, answers no axis, and imports nothing into this process, so the admission is the manifest being
readable and the name being free.

**A target's install is a stage, an admission and a rename**, and the admission is the whole difference. A
target's Python is imported and asked for `TARGET`, and a managed one owes every member the protocol
requires. A cloud that cannot be imported, or that answers `shapes` with files it does not ship, is one a
project would be generated against and would fail at `make bootstrap` — partway through an apply, with half
a stack already created in somebody's account. That is the moment this factory refuses everywhere else to
leave a person at, so it is refused here, where the only thing lost is an install.

**The same four kinds of source the other two verbs take**, and all of them a directory in the end: a name,
looked up in the chandlery and fetched; a path to a package directory; a path to a release file; or a git
URL, cloned shallow with its history dropped. Those four are `extension_install`'s and are read from there
rather than written again — what arrives is the same question whichever kind of package is arriving, and the
only thing this module does differently is what it does with the directory once it has one.

**Nothing is installed half-way.** Staged under a hidden name the loader skips, admitted, then renamed into
place. An interrupted install leaves a hidden directory and nothing else, which the next install clears.
"""
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from .assets import this_command
from .catalog import CORE
from .errors import GenerationError
from .extension_install import CAME_FROM, cloned, is_path, is_remote, staged
from .index_schema import TARGET
from .language_directory import Refused
from .language_release import ReleaseError, unpack
from .target_directory import MANIFEST, fault_in, import_package
from .target_directory import TargetPackage as Package
from .trust import SAID, admitted, state_of

STAGING = ".install-target-"


def from_index(name: str, area: Path, accept_publisher: bool = False) -> Path:
    """One named target, fetched from the chandlery and unpacked. Raises with the reason it could not be.

    Imported here rather than at the top for `extension_install`'s reason: the index client reaches the
    network, and a verb installing from a directory should not pay for a module that exists to talk to a
    server.
    """
    from .language_index import Unreachable, download, newest, read_index, snapshots
    try:
        found = read_index()
    except Unreachable as error:
        raise GenerationError(f"{error}. `{this_command()} target install <path-or-url>` installs one from a "
                              f"directory, a release file or a git URL without the index") from None
    release = newest(found, name, CORE["schemaVersion"], snapshots(), lambda one: one.kind == TARGET)
    if release is None:
        raise GenerationError(f"{found.name} lists no target `{name}` this keel can install. "
                              f"`{this_command()} search --kind target` lists what it does")
    where = release.channel or found.name
    # The publisher before the bytes, as every other install does it: somebody who has not accepted this
    # publisher is asked before anything is fetched, not after.
    admitted(name, release.publisher, release.signature, confirm=accept_publisher)
    data = download(found, release)
    CAME_FROM[name] = (f"{where} {release.version}, "
                       f"{SAID[state_of(release.publisher, release.signature, data, where)]}")
    archive = area / "release.tar.gz"
    archive.write_bytes(data)
    unpacked = area / "unpacked"
    unpack(archive, unpacked)
    return unpacked


def sourced(request: str, area: Path, accept_publisher: bool = False) -> Path:
    """One request as a directory holding a `target.json`, whatever form it arrived in."""
    if is_remote(request):
        return cloned(request, area)
    path = Path(request).expanduser()
    if path.is_dir():
        return path
    if path.is_file():
        unpacked = area / "unpacked"
        unpack(path, unpacked)
        return unpacked
    if is_path(request):
        raise GenerationError(f"{request} is neither a package directory nor a release file. A name with no "
                              f"separator in it is looked up in the chandlery instead")
    return from_index(request, area, accept_publisher)


def name_of(root: Path, request: str) -> str:
    """The name this package installs under: its manifest's own, which is the directory, the Python module
    and what `--target <name>` is typed as.

    The directory's name is not it, for the reason an extension's key is not its clone's: a repository called
    `slipwai-target-cumulus` on the forge is `cumulus` everywhere a person says it, and installing under the
    first would make `--target cumulus` wrong on a machine where nothing was wrong.
    """
    try:
        manifest = json.loads((root / MANIFEST).read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        raise GenerationError(f"{request} holds no readable {MANIFEST}, so it is not a target") from None
    name = manifest.get("name") if isinstance(manifest, dict) else None
    if not isinstance(name, str) or not name.strip():
        raise GenerationError(f"{request}: its {MANIFEST} declares no `name`, which is what a person types "
                              f"after `--target` and what the installed directory is called")
    return name.strip()


def admit(name: str, root: Path, directory: Path, replacing: bool) -> None:
    """Refuse a staged target the next start would not load, or one whose name is already a language's.

    Both halves, because both are needed before a project can be written: the manifest, which is the row and
    the menus, and the `TARGET`, which is the stacks, the scripts, the pages and the pipeline. A target that
    passes the first and fails the second is a row in a menu that generates a project nothing can deploy.

    `replacing` is whether a *target* of that name is installed, not whether the directory exists: a language
    of the same name makes a directory too, and treating that as a replacement would have this verb delete a
    language to make room for a cloud.
    """
    manifest, fault = fault_in(name, root, CORE["schemaVersion"])
    if manifest is None:
        raise GenerationError(f"target {name} ({root}): {fault}")
    try:
        import_package(Package(name, root, manifest))
    except Refused as error:
        raise GenerationError(str(error)) from None
    if not replacing and (directory / name / "language.json").is_file():
        raise GenerationError(f"{name} is already installed as a language. Two packages cannot share a name: "
                              f"rename one, or `{this_command()} language remove {name}` first")


def install(requests: list[str], directory: Path, accept_publisher: bool = False) -> list[str]:
    """Install each request, and return a line each saying what landed. Every refusal names a fix."""
    if not requests:
        raise GenerationError(f"`{this_command()} target install` takes a name, a path, a release file or a "
                              f"git URL")
    directory.mkdir(parents=True, exist_ok=True)
    said: list[str] = []
    for request in requests:
        with tempfile.TemporaryDirectory(dir=directory, prefix=STAGING) as area:
            root = sourced(request, Path(area), accept_publisher)
            name = name_of(root, request)
            place = directory / name
            holding = staged(root, name, Path(area))
            admit(name, holding, directory, replacing=(place / MANIFEST).is_file())
            if place.is_dir():
                shutil.rmtree(place)
            shutil.move(str(holding), str(place))
            said.append(f"{name} installed from {CAME_FROM.pop(request, request)}")
    return said


def installed(directory: Path) -> list[str]:
    """Every installed target's name, in name order. A directory holding a `target.json` is a target,
    whether or not the loader admits it: a refused one can still be removed or replaced."""
    return [entry.name for entry in sorted(directory.iterdir())
            if not entry.name.startswith(".") and (entry / MANIFEST).is_file()] if directory.is_dir() else []


def remove(names: list[str], directory: Path) -> list[str]:
    """Take each named target out, or say which is not installed and what is."""
    said: list[str] = []
    for name in names:
        place = directory / name
        if not (place / MANIFEST).is_file():
            offered = ", ".join(installed(directory)) or "none"
            raise GenerationError(f"{name} is not an installed target; installed: {offered}")
        shutil.rmtree(place)
        said.append(f"{name} removed")
    return said


def catalogue(directory: Path) -> list[tuple[str, dict]]:
    """Every installed target's name and manifest, readable or not, in name order — what `list` prints."""
    found: list[tuple[str, dict]] = []
    for name in installed(directory):
        try:
            manifest = json.loads((directory / name / MANIFEST).read_text(encoding="utf-8"))
        except (OSError, ValueError, UnicodeDecodeError):
            manifest = {}
        found.append((name, manifest if isinstance(manifest, dict) else {}))
    return found


__all__ = ["ReleaseError", "catalogue", "install", "installed", "remove"]

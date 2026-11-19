"""Putting an extension in the package directory, and taking it out again.

A language's install is a transaction over a merge: the staged packages are admitted the way the next start
would load them — fragments read, catalog merged, registry built — because one language can make another's
backend key, axis option or family unloadable, and a directory where that is only discovered at the next
start is a directory that generates nothing.

**An extension collides with nothing but its own name.** It adds a catalogue entry and a directory of files;
it declares no backend, answers no axis and imports nothing into this process. So the admission is the
manifest being readable and the name being free, and the transaction is a stage and a rename rather than a
whole second load.

**Four kinds of source, all of them a directory in the end.** A name, which is looked up in the chandlery and
fetched; a path to a package directory; a path to a release file; or a git URL, which is cloned into a
temporary directory and read as the first kind. The clone is shallow and its `.git` is dropped on the way in:
what is installed is the package, not its history, and a package directory that is also a working checkout is
one `slipwai extension upgrade` would fight with.

**A name is the form a search result hands you.** `slipwai search` prints a name and `slipwai extension
install <name>` takes it, which is the one thing version 1's languages got right and that an extension had no
way to do at all — the three it shipped were in the keel, so nobody ever had to find one.

**Nothing is installed half-way.** Staged under a hidden name the loader skips, admitted, then renamed into
place. An interrupted install leaves a hidden directory and nothing else, which the next install clears.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from .assets import this_command
from .catalog import CORE
from .errors import GenerationError
from .extension_directory import MANIFEST, fault_in, files
from .index_schema import EXTENSION
from .language_release import ReleaseError, unpack
from .trust import SAID, admitted, state_of

STAGING = ".install-extension-"
#: What a request has to look like to be a git URL rather than a path. `git@` is included because that is
#: what a private chandlery's packages are cloned over until 6.3 gives them an index of their own.
REMOTE = ("https://", "http://", "git@", "ssh://")


def is_remote(request: str) -> bool:
    return request.startswith(REMOTE)


def cloned(url: str, into: Path) -> Path:
    """A git URL as a package directory: shallow, no history kept, and a refusal naming the command on failure."""
    root = into / "clone"
    run = subprocess.run(["git", "clone", "--depth", "1", "--quiet", url, str(root)],
                         capture_output=True, text=True)
    if run.returncode != 0:
        said = (run.stderr or run.stdout).strip().splitlines()
        raise GenerationError(f"{url} could not be cloned: {said[-1] if said else 'git failed'}")
    shutil.rmtree(root / ".git", ignore_errors=True)
    return root


#: Where the last index lookup came from, so the line that says what was installed can say it. A verb runs
#: one install at a time and prints as it goes, which is why this is a module variable and not a return value
#: threaded through four functions that have no other use for it.
CAME_FROM: dict[str, str] = {}


def from_index(name: str, area: Path, accept_publisher: bool = False, prerelease: bool | None = None) -> Path:
    """One named extension, fetched from the chandlery and unpacked. Raises with the reason it could not be.

    Imported here rather than at the top: the index client reaches the network, and a verb installing from a
    directory should not pay for a module that exists to talk to a server. `prerelease` is whether a snapshot
    counts, where the caller was told (`upgrade --pre`); None is whatever this copy follows.
    """
    from .catalog import CORE
    from .language_index import Unreachable, download, newest, read_index, snapshots
    try:
        found = read_index()
    except Unreachable as error:
        raise GenerationError(f"{error}. `{this_command()} extension install <path-or-url>` installs one "
                              f"from a directory, a release file or a git URL without the index") from None
    counting = snapshots() if prerelease is None else prerelease
    release = newest(found, name, CORE["schemaVersion"], counting, lambda one: one.kind == EXTENSION)
    if release is None:
        raise GenerationError(f"{found.name} lists no extension `{name}` this keel can install. "
                              f"`{this_command()} search --kind extension` lists what it does")
    # The publisher before the bytes: somebody who has not accepted this publisher is asked before anything
    # is fetched, not after. `download` then refuses a file that is not the one the index listed.
    where = release.channel or found.name
    admitted(name, release.publisher, release.signature, confirm=accept_publisher)
    data = download(found, release)
    # The bytes, now there are some: the publisher check above is about who, and this is about whether the
    # file the channel served is the one they signed. A mismatch raises here rather than being recorded.
    CAME_FROM[name] = (f"{where} {release.version}, "
                       f"{SAID[state_of(release.publisher, release.signature, data, where)]}")
    archive = area / "release.tar.gz"
    archive.write_bytes(data)
    unpacked = area / "unpacked"
    unpack(archive, unpacked)
    return unpacked


def sourced(request: str, area: Path, accept_publisher: bool = False, prerelease: bool | None = None) -> Path:
    """One request as a directory holding an `extension.json`, whatever form it arrived in."""
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
    return from_index(request, area, accept_publisher, prerelease)


def is_path(request: str) -> bool:
    """Whether this reads as a path rather than a name. A name has no separator and no leading dot."""
    return "/" in request or "\\" in request or request.startswith((".", "~"))


def key_of(root: Path, request: str) -> str:
    """The key this package installs under: its manifest's own name, lower-cased with spaces as dashes.

    The directory's name is not it. A clone is named after the repository, which is `slipwai-extension-uipro`
    on the forge and `uipro` everywhere a person says it, and installing under the first would make
    `./init --extension uipro` wrong on a machine where nothing was wrong. Nor is the manifest's `name`: that
    is the product's own, and "UI/UX Pro Max" is not a directory.
    """
    try:
        manifest = json.loads((root / MANIFEST).read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        raise GenerationError(f"{request} holds no readable {MANIFEST}, so it is not an extension") from None
    key = manifest.get("key")
    if not isinstance(key, str) or not key.strip():
        raise GenerationError(f"{request}: its {MANIFEST} declares no `key`, which is what a person types "
                              f"after `./init --extension` and what the installed directory is called")
    return key.strip()


def staged(root: Path, key: str, area: Path) -> Path:
    """The package copied into the staging area under the key it will be installed as."""
    destination = area / key
    if root != destination:
        shutil.copytree(root, destination, dirs_exist_ok=True, symlinks=False,
                        ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"))
    return destination


def admit(key: str, root: Path, directory: Path, replacing: bool) -> None:
    """Refuse a staged package the next start would not load, or one whose name is already a language's.

    `replacing` is whether an *extension* of that key is installed, not whether the directory exists: a
    language of the same name makes a directory too, and treating that as a replacement would have this
    verb delete a language to make room for an extension.
    """
    manifest, fault = fault_in(key, root, CORE["schemaVersion"])
    if manifest is None:
        raise GenerationError(f"extension {key} ({root}): {fault}")
    if not files(root):  # a manifest and nothing else runs nothing
        raise GenerationError(f"extension {key} holds only its {MANIFEST}. An extension is a manifest and the "
                              f"files its hooks name; this one names files it does not ship")
    if not replacing and (directory / key / "language.json").is_file():
        raise GenerationError(f"{key} is already installed as a language. Two packages cannot share a name: "
                              f"rename one, or `{this_command()} language remove {key}` first")


def install(requests: list[str], directory: Path, accept_publisher: bool = False,
            prerelease: bool | None = None) -> list[str]:
    """Install each request, and return a line each saying what landed. Every refusal names a fix."""
    if not requests:
        raise GenerationError(f"`{this_command()} extension install` takes a path, a release file or a git URL")
    directory.mkdir(parents=True, exist_ok=True)
    said: list[str] = []
    for request in requests:
        with tempfile.TemporaryDirectory(dir=directory, prefix=STAGING) as area:
            root = sourced(request, Path(area), accept_publisher, prerelease)
            key = key_of(root, request)
            place = directory / key
            holding = staged(root, key, Path(area))
            admit(key, holding, directory, replacing=(place / MANIFEST).is_file())
            if place.is_dir():
                shutil.rmtree(place)
            shutil.move(str(holding), str(place))
            said.append(f"{key} installed from {CAME_FROM.pop(request, request)}")
    return said


def remove(names: list[str], directory: Path) -> list[str]:
    """Take each named extension out, or say which is not installed and what is."""
    said: list[str] = []
    for name in names:
        place = directory / name
        if not (place / MANIFEST).is_file():
            have = sorted(entry.name for entry in directory.iterdir()
                          if (entry / MANIFEST).is_file()) if directory.is_dir() else []
            offered = ", ".join(have) if have else "none"
            raise GenerationError(f"{name} is not an installed extension; installed: {offered}")
        shutil.rmtree(place)
        said.append(f"{name} removed")
    return said


def catalogue(directory: Path) -> list[tuple[str, dict]]:
    """Every installed extension's key and manifest, readable or not, in name order — what `list` prints."""
    found: list[tuple[str, dict]] = []
    for entry in sorted(directory.iterdir()) if directory.is_dir() else []:
        if entry.name.startswith(".") or not (entry / MANIFEST).is_file():
            continue
        try:
            found.append((entry.name, json.loads((entry / MANIFEST).read_text(encoding="utf-8"))))
        except (OSError, ValueError, UnicodeDecodeError):
            found.append((entry.name, {}))
    return found


__all__ = ["ReleaseError", "catalogue", "install", "remove"]

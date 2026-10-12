"""Fetching a published quickstart out of the chandlery, and taking one out again.

A language install is a transaction over a merge, because one language can make another's backend key or
axis option unloadable. An extension install is a stage and a rename, because an extension collides with
nothing but its own name. **A quickstart install is a file**, because a quickstart is a document: it adds
no backend, answers no axis, runs no code and is read only when somebody names it. So what lands in
`~/.slipwai/quickstarts/` is the document alone, and the release file it came in is thrown away.

That is also why nothing here loads the packages it names. A quickstart says *toy >=1.0,<2*; whether this
machine has it is a question `generate` asks when the quickstart is used, with the install line in the
refusal, and asking it here would mean an install that reached the network twice and still could not
promise the answer would hold tomorrow.

**The name is what a search result hands you.** `slipwai search --kind quickstart` prints a name and
`slipwai quickstart install <name>` takes it, as does a path to a release file or a package directory.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from .assets import this_command
from .catalog import CORE
from .errors import GenerationError
from .index_schema import QUICKSTART
from .language_release import ReleaseError, unpack
from .quickstart import MANIFEST, SUFFIX, load
from .trust import SAID, admitted, state_of

#: Where the last index lookup came from, so the line that says what was installed can say it.
CAME_FROM: dict[str, str] = {}


def from_index(name: str, area: Path, accept_publisher: bool = False) -> Path:
    """One named quickstart, fetched from the chandlery and unpacked. Raises with the reason it could not be.

    Imported here rather than at the top: the index client reaches the network, and installing from a
    directory should not pay for a module that exists to talk to a server.
    """
    from .language_index import Unreachable, download, newest, read_index, snapshots
    try:
        found = read_index()
    except Unreachable as error:
        raise GenerationError(f"{error}. `{this_command()} quickstart install <path-or-file>` installs one "
                              f"from a directory or a release file without the index") from None
    release = newest(found, name, CORE["schemaVersion"], snapshots(), lambda one: one.kind == QUICKSTART)
    if release is None:
        raise GenerationError(f"{found.name} lists no quickstart `{name}` this keel can install. "
                              f"`{this_command()} search --kind quickstart` lists what it does")
    admitted(name, release.publisher, release.signature, confirm=accept_publisher)
    data = download(found, release)
    CAME_FROM[name] = (f"{release.channel or found.name} {release.version}, "
                       f"{SAID[state_of(release.publisher, release.signature, data, release.channel or found.name)]}")
    archive = area / "release.tar.gz"
    archive.write_bytes(data)
    unpacked = area / "unpacked"
    unpack(archive, unpacked)
    return unpacked


def is_path(request: str) -> bool:
    """Whether this reads as a path rather than a name. A name has no separator and no leading dot."""
    return "/" in request or "\\" in request or request.startswith((".", "~"))


def sourced(request: str, area: Path, accept_publisher: bool = False) -> Path:
    """One request as a directory holding a `quickstart.json`, whatever form it arrived in."""
    path = Path(request).expanduser()
    if path.is_dir():
        return path
    if path.is_file() and path.suffix != SUFFIX:
        unpacked = area / "unpacked"
        try:
            unpack(path, unpacked)
        except ReleaseError as error:
            raise GenerationError(str(error)) from None
        return unpacked
    if path.is_file():  # a bare document, which is what `quickstart save` writes
        return path.parent
    if is_path(request):
        raise GenerationError(f"{request} is neither a quickstart, a package directory nor a release file. "
                              f"A name with no separator in it is looked up in the chandlery instead")
    return from_index(request, area, accept_publisher)


def document_in(root: Path, request: str) -> Path:
    """The `quickstart.json` inside an unpacked package, which a release carries one directory down."""
    here = root / MANIFEST
    if here.is_file():
        return here
    inside = sorted(root.glob(f"*/{MANIFEST}"))
    if not inside:
        raise GenerationError(f"{request} holds no {MANIFEST}, so it is not a quickstart")
    return inside[0]


def install(requests: list[str], into: Path, accept_publisher: bool = False) -> list[str]:
    """Install each request into `into`, and return a line each saying what landed.

    The document is read before it is written, so a quickstart `generate` would refuse never arrives
    looking installed — the fault is the publisher's and the reader finds out here rather than on the day
    they try to start a project with it.
    """
    if not requests:
        raise GenerationError(f"`{this_command()} quickstart install` takes a name, a path or a release file")
    into.mkdir(parents=True, exist_ok=True)
    said: list[str] = []
    for request in requests:
        with tempfile.TemporaryDirectory(prefix=".install-quickstart-") as area:
            root = sourced(request, Path(area), accept_publisher)
            one = load(document_in(root, request))
            path = into / f"{one.name}{SUFFIX}"
            path.write_text(json.dumps(json.loads(document_in(root, request).read_text(encoding="utf-8")),
                                       indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            said.append(f"{one.name} installed from {CAME_FROM.pop(request, request)}: "
                        f"`{this_command()} generate <name> --quickstart {one.name}`")
    return said


def remove(names: list[str], into: Path) -> list[str]:
    """Take each named quickstart out, or say which is not installed and what is."""
    said: list[str] = []
    for name in names:
        path = into / f"{name}{SUFFIX}"
        if not path.is_file():
            have = sorted(one.stem for one in into.glob(f"*{SUFFIX}")) if into.is_dir() else []
            raise GenerationError(f"{name} is not a saved quickstart; saved: {', '.join(have) or 'none'}")
        path.unlink()
        said.append(f"{name} removed")
    return said

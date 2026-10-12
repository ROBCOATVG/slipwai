"""A language release file, and a local source read before anything is written.

A release is one gzip tar holding one top-level directory, `<name>/`: the package directory as
`contracts/language-package.md` lays it out. Its members are regular files and directories only, and it is made the
same way every time (`contracts/language-index.md`, *A release file*), so a digest published for it holds. A local
source is a release file or an unpacked package directory, a checkout of a language's own repository included: what
it installs as is the `name` its `language.json` gives, whatever the directory is called.

Unpacking never asks `tarfile` to extract: every member is held to the format first, and only then is any byte
written, so an archive with one bad member writes nothing.
"""
from __future__ import annotations

import gzip
import io
import json
import os
import re
import shutil
import stat
import tarfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from .errors import GenerationError
from .language_directory import parse_fragment
from .language_shape import name_fault

# What a package directory holds that is not the package: version control, and what tools leave behind.
EXCLUDED = frozenset({".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".venv"})


class ReleaseError(GenerationError):
    """A release file or a local source that cannot be installed, said in one line."""


@dataclass(frozen=True)
class Source:
    """What a local source or a fetched release is, read before anything is written: its name, its `VERSION`, its
    `language.json`, where it is and which kind (`directory`, `release file`)."""

    name: str
    version: str
    fragment: dict[str, Any]
    path: Path
    kind: str


def named(fragment: Any, where: Path) -> str:
    """The package name a fragment gives, or the refusal that says why it cannot be one."""
    if not isinstance(fragment, dict) or not isinstance(fragment.get("name"), str):
        raise ReleaseError(f"{where}: language.json gives no name")
    fault = name_fault("language", fragment["name"])
    if fault is not None:
        raise ReleaseError(f"{where}: {fault}")
    return str(fragment["name"])


def version_in(root: Path) -> str:
    """The package's `VERSION`, or `unknown` where it has none. Both kinds of package carry one the same way."""
    version_file = root / "VERSION"
    version = "unknown"
    if version_file.is_file():
        try:
            version = version_file.read_text(encoding="utf-8").strip()
        except (UnicodeDecodeError, OSError) as error:
            raise ReleaseError(f"{version_file} is not UTF-8 text, so the version it holds cannot be read") from error
    return version


def read_package(root: Path) -> Source:
    """Either kind of package directory as a source, read by whichever manifest it holds.

    `pack` and `copy_directory` do not care which kind they are moving — a package is a directory of files
    with a name and a version — so this is where the two kinds stop being different, rather than there being
    a second packer that differs in one `json.loads`.
    """
    quickstart = root / "quickstart.json"
    if quickstart.is_file():
        return read_quickstart(root, quickstart)
    manifest = root / "extension.json"
    if not manifest.is_file():
        return read_directory(root)
    try:
        declared = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError) as error:
        raise ReleaseError(f"{manifest} cannot be read as an extension.json: {error}") from None
    key = declared.get("key") if isinstance(declared, dict) else None
    if not isinstance(key, str) or name_fault("extension", key) is not None:
        raise ReleaseError(f"{manifest} gives no `key`, which is the name its release file is called after")
    return Source(key, version_in(root), declared, root, "directory")


def read_quickstart(root: Path, manifest: Path) -> Source:
    """A quickstart package directory as a source. It is listed under the name its document declares,
    which is also the name a person types after `--quickstart`."""
    try:
        declared = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError) as error:
        raise ReleaseError(f"{manifest} cannot be read as a quickstart.json: {error}") from None
    name = declared.get("name") if isinstance(declared, dict) else None
    if not isinstance(name, str) or name_fault("quickstart", name) is not None:
        raise ReleaseError(f"{manifest} gives no `name`, which is the name its release file is called after")
    return Source(name, version_in(root), declared, root, "directory")


def read_directory(root: Path) -> Source:
    """A language package directory as a source: its fragment, its name and its version."""
    fragment, fault = parse_fragment(root / "language.json")
    if fault is not None:
        raise ReleaseError(f"{root} {fault}")
    version_file = root / "VERSION"
    version = "unknown"
    if version_file.is_file():
        try:
            version = version_file.read_text(encoding="utf-8").strip()
        except (UnicodeDecodeError, OSError) as error:
            raise ReleaseError(f"{version_file} is not UTF-8 text, so the version it holds cannot be read") from error
    return Source(named(fragment, root), version, fragment, root, "directory")


def opened(archive: Path) -> tarfile.TarFile:
    try:
        return tarfile.open(archive, "r:gz")
    except (tarfile.TarError, OSError, EOFError) as error:
        raise ReleaseError(f"{archive} is not a release file: {error}") from error


def top(archive: Path, members: list[tarfile.TarInfo]) -> str:
    """The directory a release's first member sits under, which `checked` then holds every member to."""
    parts = PurePosixPath(members[0].name).parts if members else ()
    if not parts or parts[0] in ("/", ".."):
        raise ReleaseError(f"{archive} is not a release file: it must hold one directory, <name>/")
    return parts[0]


def plain(member_name: str) -> bool:
    """Whether a member name reads the same on every runtime a package is unpacked on: slash-separated components,
    none empty, `.` or `..`, none carrying a backslash or a colon (a Windows separator, a drive) or ending in a dot or
    a space (which Windows drops), so that what `checked` admits is exactly what `unpack` writes."""
    parts = member_name.split("/")
    if any(not part or part in (".", "..") or part != part.rstrip(". ") for part in parts):
        return False
    return not any(mark in member_name for mark in "\\:") and PureWindowsPath(member_name).parts == tuple(parts)


def checked(archive: Path, members: list[tarfile.TarInfo], name: str) -> None:
    """Refuse the first member that is not a regular file or a directory inside `<name>/`, named in normal form."""
    for member in members:
        path = PurePosixPath(member.name)
        outside = path.is_absolute() or ".." in path.parts or not path.parts or path.parts[0] != name
        if outside or not plain(member.name):
            raise ReleaseError(f"{archive}: member {member.name} is not inside {name}/")
        if not (member.isfile() or member.isdir()):
            raise ReleaseError(f"{archive}: member {member.name} is not a regular file or a directory")


def read_source(path: Path) -> Source:
    """A local source as it would install: a package directory, or a release file read without unpacking it."""
    if path.is_dir():
        return read_directory(path)
    if not path.is_file():
        raise ReleaseError(f"{path} is neither a release file nor a package directory")
    with opened(path) as tar:
        try:
            members = tar.getmembers()
        except (tarfile.TarError, OSError, EOFError) as error:
            raise ReleaseError(f"{path} is not a release file: {error}") from error
        name = top(path, members)
        checked(path, members, name)

        def text(relative: str, errors: str = "replace") -> str | None:
            try:
                handle = tar.extractfile(f"{name}/{relative}")
            except KeyError:
                return None
            return None if handle is None else handle.read().decode("utf-8", errors)

        body = text("language.json")
        if body is None:
            raise ReleaseError(f"{path} has no language.json")
        try:
            fragment = json.loads(body)
        except ValueError as error:
            raise ReleaseError(f"{path}: language.json is not valid JSON: {error}") from error
        try:
            version = (text("VERSION", "strict") or "unknown").strip()
        except UnicodeDecodeError as error:
            raise ReleaseError(f"{path}: VERSION is not UTF-8 text, so the version it holds cannot be read") from error
    if named(fragment, path) != name:
        raise ReleaseError(f"{path}: language.json names {fragment['name']}, and the release holds {name}/")
    return Source(name, version, fragment, path, "release file")


def unpack(archive: Path, destination: Path, expected: str | None = None) -> None:
    """Write the release's `<name>/` tree as `destination`, or refuse it having written nothing. `expected` is the
    name a release fetched from an index must hold, as a local release file's own `language.json` is held to."""
    with opened(archive) as tar:
        try:
            members = tar.getmembers()
        except (tarfile.TarError, OSError, EOFError) as error:
            raise ReleaseError(f"{archive} is not a release file: {error}") from error
        name = top(archive, members)
        if expected is not None and name != expected:
            raise ReleaseError(f"the release file for {expected} holds {name}/, not {expected}/")
        checked(archive, members, name)
        destination.mkdir(parents=True)
        for member in sorted(members, key=lambda found: found.name):
            relative = PurePosixPath(member.name).relative_to(name)
            target = destination.joinpath(*relative.parts)
            if not target.resolve().is_relative_to(destination.resolve()):
                raise ReleaseError(f"{archive}: member {member.name} is not inside {name}/")
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            handle = tar.extractfile(member)
            target.write_bytes(handle.read() if handle is not None else b"")
            if member.mode & stat.S_IXUSR:
                target.chmod(0o755)


def files_of(root: Path) -> list[Path]:
    """Every file and directory a release of `root` holds, sorted. Every `EXCLUDED` name is left out, whether a file,
    a directory or a link, at any depth; any other link refuses the release."""
    found: list[Path] = []
    for here, directories, files in os.walk(root):
        directories[:] = sorted(name for name in directories if name not in EXCLUDED)  # symlinked ones too
        for name in [*directories, *sorted(files)]:
            if name in EXCLUDED:  # a file or a link by that name, a submodule's `.git` among them
                continue
            path = Path(here) / name
            if path.is_symlink():
                raise ReleaseError(f"{path} is a link, and a release holds regular files and directories only")
            found.append(path)
    return sorted(found)


RELEASE_VERSION = re.compile(r"[0-9A-Za-z][0-9A-Za-z.+_-]*")


def pack(root: Path, out: Path) -> Path:
    """`<out>/<name>-<version>.tar.gz` from a package directory of either kind, the same bytes every time. A
    publisher's `.env` or `.env.*` anywhere in it refuses the release, naming the file, and a `VERSION` that is not a
    file name's worth of letters, digits and `.+_-` refuses it too: it becomes part of the file's name."""
    source = read_package(root)
    if not RELEASE_VERSION.fullmatch(source.version):
        raise ReleaseError(f"{root}: VERSION {source.version!r} cannot be part of a release file's name")
    for path in files_of(root):
        if path.name == ".env" or path.name.startswith(".env."):
            raise ReleaseError(f"{path} is a secrets file, and a release is public: move it out of {root}")
    out.mkdir(parents=True, exist_ok=True)
    target = out / f"{source.name}-{source.version}.tar.gz"
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w", format=tarfile.GNU_FORMAT) as tar:
        for path in [root, *files_of(root)]:
            relative = PurePosixPath(source.name, *path.relative_to(root).parts)
            info = tarfile.TarInfo(str(relative))
            info.mtime, info.uid, info.gid, info.uname, info.gname = 0, 0, 0, "", ""
            if path.is_dir():
                info.type, info.mode = tarfile.DIRTYPE, 0o755
                tar.addfile(info)
                continue
            data = path.read_bytes()
            info.size, info.mode = len(data), 0o755 if os.access(path, os.X_OK) else 0o644
            tar.addfile(info, io.BytesIO(data))
    with target.open("wb") as handle, gzip.GzipFile(filename="", mode="wb", fileobj=handle, mtime=0) as zipped:
        zipped.write(buffer.getvalue())
    return target


def copy_directory(source: Path, destination: Path) -> None:
    """A package directory copied as `destination`, version control and tool caches left behind. A link refuses it, as
    it refuses `pack`: a copy never follows one out of the directory."""
    files_of(source)
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns(*EXCLUDED))

"""Portable three-way merging of an installed old factory's tree, after declared renames.

Git's text merge is still the resolver. The explicit base is reconstructed by version 1, so it cannot be
replaced by whichever ancestor happened to retain factory authorship. The project history remains intact;
a clean crossing adds one merge commit, and a conflict leaves Git's normal three-stage index and undo point.
"""
from __future__ import annotations

import subprocess
import tempfile
from collections.abc import Collection
from dataclasses import dataclass
from pathlib import Path

from .assets import inside
from .errors import GenerationError

Tree = dict[str, bytes]
Stages = tuple[bytes | None, bytes | None, bytes | None]

#: The repositories whose `ORIG_HEAD` *this* run wrote. Most of a crossing's git calls read — the branch,
#: the claim refs, trunk's log, a blob, the clone — and they all run before `install` writes the undo point.
#: Until it does, nothing has been changed and `ORIG_HEAD` is wherever an unrelated earlier rebase, pull or
#: merge happened to leave it, so sending somebody to `git reset --hard ORIG_HEAD` then is the only step in
#: the whole sequence that loses their commits.
UNDOABLE: set[Path] = set()


def remedy(root: Path) -> str:
    """What to do about a failed git call: the undo once there is one, and otherwise the way back in."""
    if root.resolve() in UNDOABLE:
        return "Inspect `git status`; `git reset --hard ORIG_HEAD` undoes the crossing"
    return ("Nothing in this project was changed. Repair what the command above reports, then run "
            "`slipwai migrate` again")


def git(root: Path, *arguments: str, data: bytes | None = None) -> bytes:
    done = subprocess.run(["git", "-c", "maintenance.auto=false", "-c", "gc.auto=0", *arguments],
                          cwd=root, input=data, capture_output=True)
    if done.returncode:
        raise GenerationError(f"git {arguments[0]} failed: {done.stderr.decode(errors='replace').strip()}. "
                              f"{remedy(root)}")
    return done.stdout


#: How much of one command line this will fill with paths. Well under the smallest limit any supported
#: platform has — Windows refuses a command line over 32767 characters — because the alternative is an
#: `OSError` raised after `materialise` has already rewritten the working tree, which nothing on the way
#: out of `migrate` catches: it reaches the person as a traceback over a half-crossed project.
LINE = 24_000


def stage(root: Path, names: Collection[str]) -> None:
    """Stage every path by name, in as many commands as it takes. Never `-A`: `.python-tools` and every
    other untracked local thing stays untracked."""
    batch: list[str] = []
    length = 0
    for name in sorted(names):
        if batch and length + len(name) + 1 > LINE:
            git(root, "add", "-f", "--", *batch)
            batch, length = [], 0
        batch.append(name)
        length += len(name) + 1
    if batch:
        git(root, "add", "-f", "--", *batch)


def tracked(root: Path) -> Tree:
    """The committed project's files, never its ignored logs or local build state."""
    paths = git(root, "ls-files", "-z").decode("utf-8", errors="surrogateescape").split("\0")
    answer = {}
    for name in paths:
        if not name:
            continue
        try:
            path = inside(root, name)
        except ValueError as error:
            raise GenerationError(f"{name} leaves the project; remove its symlink before `slipwai migrate`") from error
        if (root / name).is_symlink():
            raise GenerationError(f"{name} is a symlink; remove it before `slipwai migrate`")
        if path.is_file():
            answer[name] = path.read_bytes()
    return answer


@dataclass(frozen=True)
class Merged:
    files: Tree
    conflicts: dict[str, Stages]


def comparable(body: bytes | None) -> bytes | None:
    """Text line endings are transport, not a competing edit; binary blobs remain byte-exact."""
    return body.replace(b"\r\n", b"\n") if body is not None and b"\0" not in body else body


def merge(base: Tree, ours: Tree, theirs: Tree) -> Merged:
    """Merge immutable trees before any change reaches the project's working directory."""
    files: Tree = {}
    conflicts: dict[str, Stages] = {}
    with tempfile.TemporaryDirectory(prefix="slipwai-merge-") as scratch:
        area = Path(scratch)
        for name in sorted(set(base) | set(ours) | set(theirs)):
            before, own, new = base.get(name), ours.get(name), theirs.get(name)
            if comparable(own) == comparable(before):
                chosen = new
            elif comparable(new) == comparable(before) or comparable(own) == comparable(new):
                chosen = own
            elif own is None or new is None or b"\0" in (own + new + (before or b"")):
                chosen = own if own is not None else new
                conflicts[name] = (before, own, new)
            else:
                paths = [area / side for side in ("ours", "base", "theirs")]
                for path, content in zip(paths, (own, before or b"", new), strict=True):
                    path.write_bytes(comparable(content) or b"")
                done = subprocess.run(["git", "merge-file", "-p", "--diff3", "-L", "ours/" + name,
                                       "-L", "base/" + name, "-L", "theirs/" + name,
                                       *map(str, paths)], capture_output=True)
                if done.returncode < 0 or done.returncode > 127:
                    raise GenerationError(f"{name} could not be merged: {done.stderr.decode(errors='replace')}. "
                                          "Repair it before `slipwai migrate`")
                chosen = done.stdout.replace(b"\n", b"\r\n") if b"\r\n" in own else done.stdout
                if done.returncode:
                    conflicts[name] = (before, own, new)
            if chosen is not None:
                files[name] = chosen
    return Merged(files, conflicts)


def modes(root: Path) -> dict[str, int]:
    """Committed executable bits, which a Windows filesystem alone cannot reliably tell us."""
    answer = {}
    for entry in git(root, "ls-files", "--stage", "-z").split(b"\0"):
        if entry:
            details, name = entry.split(b"\t", 1)
            answer[name.decode("utf-8", errors="surrogateescape")] = int(details.split()[0], 8)
    return answer


def validate(root: Path, files: Tree) -> None:
    """No offered path may cross a symlink or overwrite a person's ignored local file."""
    existing = tracked(root)
    for name in files:
        path = root / name
        if any(part.lower() == ".git" for part in Path(name).parts):
            raise GenerationError(f"{name} reaches Git's own metadata; "
                                  "restore the rename table before `slipwai migrate`")
        try:
            inside(root, name)
        except ValueError as error:
            raise GenerationError(f"{name} leaves the project; correct its path before `slipwai migrate`") from error
        parts = path.relative_to(root).parts
        if path.is_dir() or any(root.joinpath(*parts[:at]).is_file() for at in range(1, len(parts))):
            raise GenerationError(f"{name} collides with an existing file or directory; "
                                  "move it before `slipwai migrate`")
        if any(root.joinpath(*parts[:at]).is_symlink() for at in range(1, len(parts) + 1)):
            raise GenerationError(f"{name} reaches a symlink; remove it before `slipwai migrate`")
        if path.is_file() and name not in existing and path.read_bytes() != files[name]:
            raise GenerationError(f"{name} is an ignored or untracked file the crossing would replace; "
                                  "move or commit it before `slipwai migrate`")


def materialise(root: Path, files: Tree, executable: dict[str, int]) -> None:
    """Put the prepared tree on disk. Refuse a symlink before following it."""
    validate(root, files)
    for name in set(tracked(root)) - set(files):
        (root / name).unlink()
    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        path.chmod(0o755 if executable.get(name, 0) & 0o111 else 0o644)


def install(root: Path, result: Merged, theirs: str, message: str, executable: dict[str, int]) -> None:
    """One merge commit, or normal unresolved index entries the person can finish or abort."""
    validate(root, result.files)
    original = git(root, "rev-parse", "HEAD").decode().strip()
    git(root, "update-ref", "ORIG_HEAD", original)
    # From here the undo point is this run's own, and every later refusal may name it.
    UNDOABLE.add(root.resolve())
    materialise(root, result.files, executable)
    git(root, "add", "-A")
    stage(root, result.files)
    head_path = git(root, "rev-parse", "--git-path", "MERGE_HEAD").decode().strip()
    (root / head_path).write_text(theirs + "\n", encoding="ascii")
    mode_path = git(root, "rev-parse", "--git-path", "MERGE_MODE").decode().strip()
    (root / mode_path).write_text("no-ff", encoding="ascii")
    location = git(root, "rev-parse", "--git-path", "MERGE_MSG").decode().strip()
    (root / location).write_text(message + "\n", encoding="utf-8")
    if result.conflicts:
        index = bytearray()
        for name, entries in result.conflicts.items():
            shown = name.encode("utf-8", errors="surrogateescape")
            hashes = [(number, git(root, "hash-object", "-w", "--stdin", data=body).strip())
                      for number, body in enumerate(entries, 1) if body is not None]
            length = len(hashes[0][1])
            index.extend(b"0 " + b"0" * length + b"\t" + shown + b"\0")
            for number, digest in hashes:
                mode = f"{executable.get(name, 0o100644):o}".encode()
                index.extend(mode + b" " + digest + b" " + str(number).encode() + b"\t" + shown + b"\0")
        git(root, "update-index", "-z", "--index-info", data=bytes(index))
    else:
        git(root, "commit", "--quiet", "--no-edit", "-m", message)
    # MERGE_HEAD is Git's pseudo-ref; a normal successful commit removes it. On conflicts it stays
    # exactly where `git merge --abort` expects it, and ORIG_HEAD is the real project commit, not a shim.

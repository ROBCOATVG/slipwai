#!/usr/bin/env python3
"""Fail when the code index this project carries no longer describes the code that is here.

A code index is only worth asking while it is current, and a stale one does not say so: asked
which functions call a symbol it never read, it answers *none* — the same answer it gives when
nothing calls it, and exactly the failure an index is bought to avoid in a text search.

CodeGraph keeps `.codegraph/codegraph.db` up to date by watching the tree, but the watcher lives
in a daemon, and that daemon only runs while a CodeGraph client is attached to it — an MCP
client, or a `codegraph` command. It shuts down on an idle timeout once the last one goes away.
So a checkout opened somewhere that has the database and not the tooling — a container, a
sandbox, a CI runner, a machine where the CLI was never installed — keeps a file that looks like
an index, answers every question without complaint, and has not been written to since the last
client was attached. Nothing else in this repository would notice.

This does. It compares what the index holds with what version control tracks, and reports the two
ways an index goes wrong: a file it has never seen, and a file whose content changed after it was
read. The comparison is by SHA-256 — `files.content_hash` is the digest of the file's bytes —
rather than by modification time, because a checkout, a rebase or a `touch` moves an mtime
without changing a line, and a gate that cries stale over those is a gate that gets ignored. The
timestamp is still reported: `files.indexed_at` is the last moment anything was indexed, which is
the last moment a client was attached, and that is the number that says *why* it is behind.

No `.codegraph/` is not a failure: the code index is an optional extension (`./init --extension
codegraph`), and a project that never adopted one has nothing to keep fresh. Standard library
only, like every gate script here.
"""
from __future__ import annotations

import hashlib
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def project_root(script: Path, depth: int) -> Path:
    """The repository root: the nearest directory above this script holding `project.json`.

    This script's own tree is `<root>/scripts` in a generated project and `<root>/<layout.delivery>/scripts`
    where the method was installed beside an existing codebase (`project.json`'s `layout.delivery`), so how
    far below the root it sits is not something to count; `depth` is only the fallback for a tree with no
    manifest at all.
    """
    for candidate in script.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return script.parents[depth]


ROOT = project_root(Path(__file__).resolve(), 1)
INDEX = ROOT / ".codegraph/codegraph.db"
# How many offending paths to name before summarising the rest: enough to recognise the shape of
# what is missing, short enough that the gate's output stays readable.
LISTED = 8
RESTORE = """This is not a rebuild you forgot to run. CodeGraph keeps itself current only while a
client is attached: the watcher lives in a daemon that starts with an MCP client or a
`codegraph` command and shuts down on its idle timeout. A checkout opened where that
tooling is absent — a container, a sandbox, a CI runner, a machine where the CLI was
never installed — keeps this database and never writes to it again.

Attaching a client once catches the backlog up on its own. From a terminal, in this
directory: `codegraph sync`, or `npx -y @colbymchenry/codegraph sync` where the CLI is
not installed. From an agent session: configure the CodeGraph MCP server for this
project. To put the tooling back for good, install it and re-adopt the extension, which
is also what re-points the agent at the index:

  curl -fsSL https://raw.githubusercontent.com/colbymchenry/codegraph/main/install.sh | sh
  ./init --extension codegraph

Until one of those has run, treat this index as absent rather than empty: it answers
about the code it last read, and says nothing about the rest."""


def tracked() -> list[str] | None:
    """Every tracked path, or None where git cannot answer: an export, a tarball, no git at all."""
    try:
        completed = subprocess.run(
            ["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return [path for path in completed.stdout.decode("utf-8", "replace").split("\0") if path]


def rows_of(source: str) -> list[tuple[str, str, float]]:
    with sqlite3.connect(source, uri=True) as connection:
        return connection.execute("SELECT path, content_hash, indexed_at FROM files").fetchall()


def indexed() -> dict[str, tuple[str, float]] | None:
    """Each indexed path with its content digest and the moment it was indexed, or None where
    this database does not carry the table this check reads.

    CodeGraph owns that schema, and a version of it that renamed a column is its business rather
    than a reason to fail somebody's build — so an unreadable shape is reported and skipped, not
    failed. The read-only URI is the first attempt rather than the only one: a database left in
    WAL mode may need to create its shared-memory file before anything can be read, which
    read-only cannot do, and stopping there would be silence in the one state this reports.
    """
    try:
        rows = rows_of(f"{INDEX.as_uri()}?mode=ro")
    except sqlite3.Error:
        try:
            rows = rows_of(INDEX.as_uri())
        except sqlite3.Error:
            return None
    return {str(path): (str(digest), float(at or 0)) for path, digest, at in rows}


def digest(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            sha.update(block)
    return sha.hexdigest()


def moment(milliseconds: float) -> str:
    """A timestamp from the index, which records epoch milliseconds."""
    if not milliseconds:
        return "never"
    return datetime.fromtimestamp(milliseconds / 1000).strftime("%Y-%m-%d %H:%M:%S")


def listing(label: str, paths: list[str]) -> list[str]:
    lines = [f"  {len(paths)} tracked file(s) {label}:"]
    lines += [f"    - {path}" for path in sorted(paths)[:LISTED]]
    if len(paths) > LISTED:
        lines.append(f"    ... and {len(paths) - LISTED} more")
    return lines


def main() -> int:
    if not INDEX.is_file():
        print("check-codegraph: no .codegraph/ — this project carries no code index; nothing to "
              "check")
        return 0
    rows = indexed()
    if rows is None:
        print("check-codegraph: .codegraph/codegraph.db does not carry the `files` table this "
              "check reads; CodeGraph's schema may have moved on — skipped")
        return 0
    paths = tracked()
    if paths is None:
        print("check-codegraph: not a checkout — nothing to compare the index against; skipped")
        return 0
    # Which files belong in the index is CodeGraph's decision, not this script's: it parses the
    # languages it supports and ignores the rest. Taking the set of suffixes it has actually
    # indexed here as the answer keeps this check from inventing a language table of its own — and
    # from reporting every committed PNG as a hole in the graph.
    suffixes = {Path(path).suffix for path in rows} - {""}
    last = max((at for _, at in rows.values()), default=0.0)
    missing, changed = [], []
    for path in paths:
        if Path(path).suffix not in suffixes:
            continue
        absolute = ROOT / path
        if not absolute.is_file():
            continue
        row = rows.get(path)
        if row is None:
            # A file the index has never seen is a hole only where it appeared *after* the index last ran.
            # Matching the suffix is not enough: CodeGraph declines files of a language it indexes — a
            # vendored `bootstrap.min.js` beside a `src/app.js` it read — and which ones is its decision,
            # not this script's. Reported anyway, a real repository's vendored bundles failed a gate that
            # `codegraph sync` said was already up to date, and the two tools called each other wrong. The
            # index records milliseconds and the filesystem seconds.
            if last and absolute.stat().st_mtime * 1000 <= last:
                continue
            missing.append(path)
        elif row[0] and digest(absolute) != row[0]:
            changed.append(path)
    # An index holding nothing describes nothing, and cannot say which files it should hold — the
    # suffixes above come from what it has read. In a checkout with tracked files that is the same
    # failure as a missing one, reported rather than passed for want of anything to compare.
    if not rows and paths:
        print("check-codegraph: the code index holds no files at all — it was emptied, or "
              "nothing ever finished indexing\n", file=sys.stderr)
        print(RESTORE, file=sys.stderr)
        return 1
    if not missing and not changed:
        print(f"check-codegraph: index current — {len(rows)} file(s), indexed {moment(last)}")
        return 0
    report = ["check-codegraph: the code index no longer describes this working tree",
              f"  last indexed: {moment(last)}"]
    if missing:
        report += listing("the index has never seen", missing)
    if changed:
        report += listing("changed since they were indexed", changed)
    print("\n".join([*report, "", RESTORE]), file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

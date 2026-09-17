#!/usr/bin/env python3
"""Prove the upgrade path end to end: a project made by the last release, brought forward to this commit.

`docs/upgrading.md` says a generated project takes a newer factory's changes with one `slipwai migrate`, and
that its factory-owned surfaces come through while its own work is kept. Said and not gated, that rots
the way any asserted-only path does — so this generates a project with the factory as it was at the newest
release tag (or, on that tag's own commit, the one before it — generating from the commit under test proves
nothing), gives the project work of its own, migrates it with the factory as it is now, and holds the result
to two standards: outside the files the project changed it is byte-identical to a project this
commit would generate fresh, and its own `make verify` is green.

Conflicts are allowed only in the files the project changed — that is the stated story — and are resolved
the project's way. A conflict anywhere else, or a difference from the fresh project anywhere else, is the
gate failing, with the paths named. `make test-migration` runs it; CI runs it with the whole history checked
out, because the release tags are what it starts from.

The first public snapshot has no `v*` tag at all, the same way the first tagged release has no predecessor:
there is nothing older to generate from, so the gate exits 0 and says so. After `v1.0.0` exists, an empty
tag list is a shallow or unfetched checkout again.

The project is put through `./init`'s projection step first, because a project that has not been through it
is not the project anybody migrates. Every real repository has run `./init`, which copies `skills/` and
`commands/` into the installed agent harness and commits the copies — and those copies are derived from
files the factory owns while being files the factory has never written, so no merge can move them. Without
this step the gate ran against the one shape of project where that could not go wrong, and duly said the
upgrade path was green while every actual migration left `check-agents` red.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

FACTORY = Path(__file__).resolve().parents[1]
NAME = "migrating"
# The answers the old factory is asked for: TypeScript with the default store and transport, no frontend —
# the shape every release has been able to generate, so the oldest half of this proof does not move.
ANSWERS = ("--profile", "event-modelling", "--backend", "typescript", "--frontend", "none", "--skip-checks")
# What the project does to itself before the upgrade: a line in its own code, a page of its own.
OWN_LINE = "\n// a line the product wrote after it was generated\n"
OWN_PAGE = "docs/adr/0009-the-products-own-decision.md"
# The harness `./init` is told to install. Any projectable one proves the same thing; this is the state file
# Spec Kit writes, reproduced rather than installed, so the gate needs no network and no Spec Kit release.
HARNESS = "claude"
INTEGRATION = ".specify/integration.json"
# What `slipwai migrate` leaves for `/catch-up` to work through. Git-ignored local state rather than part
# of the tree the factory generates, so a project that has been migrated has it and one generated fresh
# never will — which is a difference this comparison must expect rather than report.
NOTES = ".slipwai/catch-up.md"
IDENTITY = (
    "-c", "user.name=product", "-c", "user.email=product@local", "-c", "maintenance.auto=false", "-c", "gc.auto=0",
)


def run(*command: str, cwd: Path, quiet: bool = False) -> str:
    result = subprocess.run(
        command, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE if quiet else None, check=False
    )
    if result.returncode != 0:
        raise SystemExit(f"test-migration: `{' '.join(command)}` failed in {cwd}\n{result.stderr or ''}{result.stdout}")
    return result.stdout.strip()


def source_revision(tags: list[str], head: str, newest_commit: str) -> str | None:
    """Which `v*` tag to generate from.

    On `main` that is the newest tag: a project the last release made, brought forward to this snapshot.
    On the tagged Release commit itself the newest tag *is* HEAD, so generating from it migrates a project
    to the factory that just made it — `nothing to migrate`, no catch-up notes, a red gate that proved
    nothing. The upgrade that tag has to carry is from the release before it. `None` when there is no
    release before it, which is only the first tag this repository ever cut.
    """
    if not tags:
        raise ValueError("no v* tag")
    if newest_commit == head:
        return tags[1] if len(tags) > 1 else None
    return tags[0]


FIRST_PUBLIC_SNAPSHOT = "1.0.0.dev0"


def generate_from(tags: list[str], head: str, newest_commit: str, version: str) -> str | None:
    """The revision to generate from, or `None` when this history has no older factory to migrate from.

    Empty tags on the first public snapshot (`1.0.0.dev0`) are that history, not a missing fetch. After
    the first tag exists, empty tags are still a mistake.
    """
    if not tags:
        if version == FIRST_PUBLIC_SNAPSHOT:
            return None
        raise ValueError("no v* tag")
    return source_revision(tags, head, newest_commit)


def files_of(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and ".git" not in path.parts
    }


def projection_prefix(path: str) -> str:
    """The directory a projected file belongs to, or the path itself where it is not nested.

    `.claude/skills/tdd/SKILL.md` and `.claude/commands/drive.md` belong to `.claude/skills` and
    `.claude/commands`; `.specify/integration.json` is only itself. Two segments rather than one, so that
    `.claude/settings.json` — which the factory *does* generate — stays in the comparison beside them.
    """
    parts = path.split("/")
    return "/".join(parts[:2]) if len(parts) > 2 else path


def without_provenance(manifest: bytes) -> bytes:
    """`project.json` with `generator` dropped: the one field a fresh project and an upgraded one differ on."""
    document = json.loads(manifest)
    document.pop("generator", None)
    return json.dumps(document, sort_keys=True).encode()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--from", dest="source", default=None, metavar="REV",
        help="the factory revision to generate with (default: the newest v* tag, "
             "or the one before it when HEAD is that tag)",
    )
    parser.add_argument(
        "--keep", type=Path, default=None, metavar="DIR",
        help="leave the project, the replay and the fresh generation under DIR",
    )
    args = parser.parse_args()
    here = run("git", "rev-parse", "--short", "HEAD", cwd=FACTORY)
    if args.source:
        source = args.source
    else:
        tags = run("git", "tag", "--list", "v*", "--sort=-v:refname", cwd=FACTORY).split()
        version = (FACTORY / "VERSION").read_text().strip()
        head = run("git", "rev-parse", "HEAD", cwd=FACTORY)
        newest_commit = (
            run("git", "rev-parse", f"{tags[0]}^{{commit}}", cwd=FACTORY) if tags else ""
        )
        try:
            source = generate_from(tags, head, newest_commit, version)
        except ValueError:
            raise SystemExit(
                "test-migration: no v* tag is reachable, so there is no release to generate from — "
                "`git fetch --tags`, or name a revision with --from"
            ) from None
        if source is None:
            if not tags:
                print("test-migration: no public release yet; nothing older to migrate from")
            else:
                print("test-migration: HEAD is the first release; nothing older to migrate from")
            return 0

    with tempfile.TemporaryDirectory(prefix="migration-") as scratch:
        work = Path(scratch)
        old = work / f"factory-{source}"
        run("git", "worktree", "add", "--quiet", "--detach", str(old), source, cwd=FACTORY)
        try:
            was = (old / "VERSION").read_text().strip()
            print(f"test-migration: generating {NAME} with the factory at {source} ({was})")
            run(str(old / "slipwai"), "generate", NAME, *ANSWERS, "--output", str(work / "old"), cwd=work, quiet=True)
        finally:
            run("git", "worktree", "remove", "--force", str(old), cwd=FACTORY)
        project = work / "old" / NAME

        # `./init`, as far as this gate needs it: a harness recorded as installed and the projections made
        # and committed, which is the state every project that has run it is in.
        generated = set(files_of(project))
        (project / ".specify").mkdir(exist_ok=True)
        (project / INTEGRATION).write_text(
            json.dumps({"installed_integrations": [HARNESS], "default_integration": HARNESS}, indent=2) + "\n"
        )
        run("python3", "scripts/agents/project.py", cwd=project, quiet=True)
        run("git", "add", "-A", cwd=project)
        run("git", *IDENTITY, "commit", "-q", "-m", "init: install an agent harness", cwd=project)
        # Whatever that added, taken as a difference rather than guessed at from path shapes: none of it is
        # generated by the factory, so a fresh generation has none of it and all of it belongs with the
        # project's own work in the comparison below.
        projected = set(files_of(project)) - generated
        if not projected:
            raise SystemExit("test-migration: projecting the harness added no files, so this gate proves nothing")
        print(f"test-migration: {len(projected)} harness projection(s) committed, as `./init` leaves them")

        # The project's own work.
        sources = sorted((project / "apps/service/src").rglob("*.ts"))
        own_file = next(path for path in sources if "test" not in path.name)
        own_file.write_text(own_file.read_text() + OWN_LINE)
        (project / OWN_PAGE).write_text("# The product's own decision\n\nRecorded by the product, not the factory.\n")
        run("git", "add", "-A", cwd=project)
        run("git", *IDENTITY, "commit", "-q", "-m", "The product's own work", cwd=project)
        changed = {own_file.relative_to(project).as_posix(), OWN_PAGE} | projected

        now = (FACTORY / "VERSION").read_text().strip()
        print(f"test-migration: migrating it with the factory at {here} ({now})")
        # The merge is committed as the project, the way a person's `git` would commit it; the registry is
        # not asked whether this checkout is the newest, because this checkout is what is under test.
        env = os.environ | {"GIT_AUTHOR_NAME": "product", "GIT_AUTHOR_EMAIL": "product@local",
                            "GIT_COMMITTER_NAME": "product", "GIT_COMMITTER_EMAIL": "product@local",
                            "SLIPWAI_INDEX": "http://127.0.0.1:9/none"}
        migrated = subprocess.run(
            [str(FACTORY / "slipwai"), "migrate"], cwd=project, env=env, text=True, capture_output=True
        )
        print(migrated.stdout.rstrip())
        conflicts = set(run("git", "diff", "--name-only", "--diff-filter=U", cwd=project).split())
        if migrated.returncode != 0 and not conflicts:
            raise SystemExit(f"test-migration: `slipwai migrate` failed\n{migrated.stderr}{migrated.stdout}")
        beyond = sorted(conflicts - changed)
        if beyond:
            raise SystemExit(
                "test-migration: the replay conflicts with files the project never touched, which the upgrade "
                "recipe promises cannot happen:\n  " + "\n  ".join(beyond)
            )
        for path in sorted(conflicts):
            run("git", "checkout", "--ours", "--", path, cwd=project)
            run("git", "add", "--", path, cwd=project)
        if conflicts:
            run("git", *IDENTITY, "commit", "-q", "--no-edit", cwd=project)
            print(
                f"test-migration: {len(conflicts)} conflict(s), each in a file the project changed, resolved the "
                f"project's way: {', '.join(sorted(conflicts))}"
            )
        else:
            print("test-migration: migrated clean")

        # Outside its own work, the upgraded project is the project this commit generates fresh — and it is
        # put through the same projection step, because the migrated project has been through one. Comparing
        # a projected tree against an unprojected one makes every projection this version introduced look
        # like drift: `roots` below is what the *old* factory projected, so a projection directory that did
        # not exist at that version is in neither tree's exclusion and fails the gate as unexplained.
        # Projecting both sides compares like with like and needs no list of what the directories are.
        fresh_project = work / "fresh" / NAME
        run(str(FACTORY / "slipwai"), "generate", NAME, *ANSWERS, "--output", str(work / "fresh"), cwd=work, quiet=True)
        (fresh_project / ".specify").mkdir(exist_ok=True)
        (fresh_project / INTEGRATION).write_text(
            json.dumps({"installed_integrations": [HARNESS], "default_integration": HARNESS}, indent=2) + "\n"
        )
        run("python3", "scripts/agents/project.py", cwd=fresh_project, quiet=True)
        fresh, merged = files_of(fresh_project), files_of(project)
        for tree in (fresh, merged):
            tree["project.json"] = without_provenance(tree["project.json"])
        # Everything under a directory `./init` created is the project's own copy of a file this compares in
        # its canonical place, so none of it belongs in the comparison — including a projection that did not
        # exist when the harness was installed, because the migration brought the command it is a copy of.
        # The catch-up notes join them for the same kind of reason: git-ignored local state that a migration
        # produces and a generation cannot, so its absence from the fresh tree is the design, not a drift.
        roots = {projection_prefix(path) for path in projected} | {projection_prefix(NOTES)}
        differing = sorted(
            path
            for path in (set(fresh) | set(merged)) - changed
            if fresh.get(path) != merged.get(path) and projection_prefix(path) not in roots
        )
        if differing:
            raise SystemExit(
                "test-migration: after the merge these files differ from a project generated fresh at HEAD, and "
                "the project never touched them:\n  " + "\n  ".join(differing)
            )
        kept = len(merged) - len(changed)
        print(f"test-migration: {kept} files identical to a fresh generation; {len(changed)} the project's own, kept")

        # The projections have to have moved with the command files, which is the whole of the reason the
        # step above exists: `check-agents` is inside `make verify` below and would catch a stale one, but
        # it would catch it as a puzzle rather than as this.
        drift = subprocess.run(
            ["python3", "scripts/agents/project.py", "--check"], cwd=project, text=True, capture_output=True
        )
        if drift.returncode != 0:
            raise SystemExit(
                "test-migration: the migration left the harness projections behind the command files they "
                f"are derived from — `migrate` is meant to re-derive them\n{drift.stderr}{drift.stdout}"
            )
        print("test-migration: harness projections re-derived by the migration")

        # The migration crossed 1.6.x to this commit, so the versions between them have entries and at least
        # one has something to say. Absent, `/catch-up` in the upgraded project would have nothing to read
        # and the half of an upgrade a merge cannot carry would be silently missing.
        if not (project / NOTES).is_file():
            raise SystemExit(f"test-migration: the migration left no {NOTES} for `/catch-up` to work through")
        print(f"test-migration: catch-up notes left at {NOTES}")

        print("test-migration: running the upgraded project's own gate")
        env = os.environ | {"CI": "1"}
        if subprocess.run(["make", "verify"], cwd=project, env=env).returncode != 0:
            raise SystemExit("test-migration: the upgraded project's `make verify` is red")
        if args.keep is not None:
            if args.keep.exists():
                shutil.rmtree(args.keep)
            shutil.copytree(work, args.keep, symlinks=True)
            print(f"test-migration: kept under {args.keep}")
    print(f"test-migration: a project generated at {source} and brought forward to {here} passes its own gate")
    return 0


if __name__ == "__main__":
    sys.exit(main())

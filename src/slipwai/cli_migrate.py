"""`slipwai migrate`: the crossing of a version 1 project to version 2.

Its own module rather than another verb in `cli_add.py`, which already held four. The crossing is the one
verb here that rewrites a repository somebody else owns, and it carries a preview (`--check`) that writes
nothing, a relaunch across the language install, and a claim pre-flight whose order against those two is
the whole of what makes `--check` answerable. That is a seam in the behaviour, not a paragraph: a reader
looking for what `migrate` does should not have to read `add-service` to find it.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from .assets import VERSION, relaunch
from .errors import GenerationError, refuse
from .language_directory import directory
from .language_index import snapshots
from .language_plan import Resolver, held_to_record, install_for, plan_install, project_names
from .manifest import recorded_languages
from .migrate import checked, migrate
from .migrate import report as migrate_report
from .upgrade import newer_published

RELAUNCHED = "SLIPWAI_MIGRATE_RELAUNCHED"


def migrate_main(argv: list[str]) -> None:
    """`migrate`, run inside a generated project: bring it up to this keel's version, as one merge.

    No flags to speak of — the project's `project.json` has every answer, and the merge base is read from its
    history. What it leaves behind is one merge commit, or a merge in progress with the conflicts named.
    """
    parser = argparse.ArgumentParser(
        prog="slipwai migrate",
        description="Bring the generated project in the current directory up to this factory's version: what "
        "the factory now generates for its answers is merged over what the project has become",
        epilog="First, the languages the project needs and this machine lacks are installed, as `slipwai language "
        "install` would, or nothing is and the command names how. One merge commit when it is clean (`git reset "
        "--hard ORIG_HEAD` undoes it); a merge left in progress with each conflicting file named when it is not. "
        "Nothing is pushed. `slipwai replay` is the same offer written beside the project instead of merged, to "
        "look at first. docs/upgrading.md in the factory says what to expect of each part of the tree.",
    )
    parser.add_argument(
        "--no-install", action="store_true",
        help="refuse, naming the install line, where a language the project needs is not installed, rather than "
        "installing it first",
    )
    parser.add_argument("--check", action="store_true",
                        help="prepare a crossing and report it without changing the project")
    parser.add_argument("--with-claims", action="store_true",
                        help="apply renames to inactive claims and leave them to rebase")
    args = parser.parse_args(argv)
    if not os.environ.get(RELAUNCHED):
        warn_if_behind()
    try:
        document = checked(Path.cwd())
        from .migration_claims import ahead
        from .migration_crossing import crossing, version
        if args.check:
            needed = project_names(document, Resolver(directory(), None, snapshots()))
            steps, notices = plan_install(needed, directory(), None, snapshots()) if needed else ([], [])
            held_to_record(steps, recorded_languages(document) or {})
            print("\n".join([f"Would install {step.name}" for step in steps] + notices))
            if steps:
                print("Install with `slipwai language install`, then rerun `slipwai migrate --check`.")
            elif version(document):
                print(crossing(Path.cwd(), document, with_claims=args.with_claims, check=True))
            else:
                print("Packages are installed; `slipwai replay` offers the current version beside this project.")
            return
        # After the check branch, never before it: a check writes nothing, and refusing an open claim here
        # was refusing to tell the person the one thing they ran `--check` to find out. Before the language
        # install, though, so nothing is installed for a crossing that is about to refuse.
        if version(document):
            ahead(Path.cwd(), with_claims=args.with_claims)
        if args.no_install:
            needed = project_names(document, Resolver(directory(), None, snapshots()))
            if needed:
                raise GenerationError(f"packages are not installed: {', '.join(needed)}; "
                                      f"run `slipwai language install {' '.join(needed)}` then `slipwai migrate`")
        if not args.no_install and (installed := install_for(document, directory(), snapshots())):
            print("\n".join(installed), flush=True)
            forwarded = ["--with-claims"] if args.with_claims else []
            finished = subprocess.run([*relaunch(), "migrate", "--no-install", *forwarded],
                                      env=os.environ | {RELAUNCHED: "1"})
            if finished.returncode != 0:
                print(f"The language(s) above stay installed in {directory()}: once what stopped this is dealt with, "
                      "`slipwai migrate` again finishes the job.", file=sys.stderr)
            raise SystemExit(finished.returncode)
        done = migrate(Path.cwd(), with_claims=args.with_claims)
    except GenerationError as error:
        refuse(parser.prog, error)
    print(migrate_report(done))
    if done.conflicts:
        raise SystemExit(1)



def warn_if_behind() -> None:
    """Say, before migrating, when this is not the newest slipwai published — and migrate anyway.

    A project brought up to a version that is already behind is a merge that will be done again next week;
    the person running this should know that before it starts. Not being able to ask the registry is a note
    rather than a refusal: the registry is not what is being migrated to, this copy is.
    """
    try:
        newest = newer_published()
    except GenerationError as error:
        print(
            f"note: could not ask the registry whether a newer slipwai is published — {str(error).splitlines()[0]}",
            file=sys.stderr,
        )
        return
    if newest is not None:
        print(
            f"warning: this is slipwai {VERSION} and {newest} is published; migrating to {VERSION} anyway — "
            "`slipwai upgrade` first to migrate to the newest",
            file=sys.stderr,
        )

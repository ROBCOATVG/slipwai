"""What every catch-up page shares, whoever writes it: the section it opens with, and where it goes when done.

Two things write `.slipwai/catch-up.md` — an ordinary migration's notes (`catch_up.py`) and the crossing from
version 1 (`migration_crossing.py`) — and `/catch-up` reads it. All three need the same two answers, so they
live here, below every one of them.

**The opening section** walks from a merge to a project its coding agent can work in. A migration that stopped
at conflicts used to leave the rest of that way — `migrate` again, `make agents`, a new session — to a report
that scrolled off, and a project could be merged with its agent still reading the old ladder.

**The archive.** The page is git-ignored, and it used to be thrown away: deleted when the work was done, and
overwritten by the next migration. That lost the one record of what a crossing asked of this project, the
answer to "what did the upgrade to 2.0.0.dev2 want of us?" a month later. So a page is never deleted or
overwritten. It is moved under `.slipwai/catch-up/archive/`, named for the versions it covered and when it was
written, which is also git-ignored and stays on the machine.
"""
from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from .assets import NOTES

#: Where `set_up` is found on the page, so the report and `/catch-up` can point at it by name.
SET_UP = "First: set the project up"
#: Where a finished or superseded page is moved, never deleted. Ignored, like the page itself.
ARCHIVE = ".slipwai/catch-up/archive"
# The line a page carries naming its own archive path, so whoever archives it later picks the same name.
STATED = re.compile(r"<!-- archive: (\S+) -->")
# A page written before pages named themselves: the versions are in its title, in one of the two shapes the
# writers used (`# Catch up: demo, 1.6.0 to 2.0.0`, `# demo: crossing from slipwai 1.3.0 to 2.0.0`).
TITLED = re.compile(r"(?m)^# .*?(\S+) to (\S+)\s*$")
# Characters a version may carry that a file name should not: anything outside a plain version's spelling.
UNSAFE = re.compile(r"[^0-9A-Za-z.+-]")


def stamp(when: datetime) -> str:
    """A UTC time as a file name can carry it, sortable as text."""
    return when.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def archive_name(was: str | None, now: str, when: datetime) -> str:
    """The archive path a page covering `was` to `now`, written at `when`, is moved to."""
    since = UNSAFE.sub("_", was) if was else "unrecorded"
    return f"{ARCHIVE}/{since}-to-{UNSAFE.sub('_', now)}-{stamp(when)}.md"


def stated(was: str | None, now: str, when: datetime) -> str:
    """The line a page ends with, naming where it is archived: read back by `archive`, and by `/catch-up`."""
    return f"<!-- archive: {archive_name(was, now, when)} -->"


def archive(root: Path) -> Path | None:
    """Move the page at `root` into the archive, and return where it went; None where there is no page.

    Before every new page is written, and safe to run any number of times. The name is the one the page states,
    or for a page from before pages stated one, its title's versions and the time it was last written. A page
    already archived under that name is not archived twice: the copy here is dropped as the duplicate it is.
    A different page under that name is never overwritten: this one takes the next free suffix.
    """
    page = root / NOTES
    if not page.is_file():
        return None
    text = page.read_text(encoding="utf-8")
    named = STATED.search(text)
    if named:
        relative = named.group(1)
    else:
        titled = TITLED.search(text)
        written = datetime.fromtimestamp(page.stat().st_mtime, UTC)
        was, now = titled.groups() if titled else (None, "unrecorded")
        # `an unrecorded version to 2.0.0` reads `version` as the lower bound, which is no version at all.
        relative = archive_name(was if was and re.search(r"\d", was) else None, now, written)
    target = root / relative
    if not target.resolve().is_relative_to((root / ARCHIVE).resolve()):
        # A page whose stated path leaves the archive was edited by hand; it is still kept, under the title's name.
        target = root / ARCHIVE / Path(relative).name
    target.parent.mkdir(parents=True, exist_ok=True)
    stem, suffix, count = target.stem, target.suffix, 1
    while target.exists():
        if target.read_text(encoding="utf-8") == text:
            page.unlink()
            return target
        count += 1
        target = target.with_name(f"{stem}-{count}{suffix}")
    page.replace(target)
    return target


def set_up(conflicts: Sequence[str] = ()) -> list[str]:
    """The section every catch-up page opens with: the steps from a merge to a project its coding agent can work in.

    On every page, conflicts or not. A clean run did most of it itself, but a section that appears only sometimes
    is a section a reader learns not to look for, and the last steps are owed either way. So the page says the
    whole path once, names the conflicted files when there were any, and says where a clean run starts.
    """
    if conflicts:
        state = [
            f"This migration stopped at {len(conflicts)} conflict(s). Nothing was re-derived over the merge in "
            "progress, so this project is merged but not yet set up:",
            "",
            *(f"- `{path}`" for path in conflicts),
            "",
            "Start at step 1.",
        ]
    else:
        state = [
            "This migration merged without a conflict and did steps 1 to 4 itself, unless its report said the "
            "projections could not be re-derived — then start at step 4. Otherwise start at step 5. Where "
            "`git status` says a merge is in progress, a later run stopped at conflicts: start at step 1.",
        ]
    return [
        "",
        f"## {SET_UP}",
        "",
        *state,
        "",
        "1. **Resolve each conflicted file.** `git diff --name-only --diff-filter=U` lists them. Edit each and "
        "`git add` it, or take a side whole: `git checkout --ours -- <file>` keeps this project's version, "
        "`--theirs` takes the factory's. A generated command, skill or agent page — `commands/sail.md` above "
        "all, and anything else under `commands/`, `skills/` or `agents/` — is the factory's text with this "
        "project's edits on top: take `--theirs` and re-apply your own change to it, because `--ours` keeps the "
        "old ladder and drops everything this version changed in it. `project.json` holds this project's "
        "answers: resolve it by hand, never by taking a side whole.",
        "2. **Commit the merge** with `git commit`, or walk away from all of it with `git merge --abort`.",
        "3. **Run `slipwai migrate` again.** It merges nothing this time; it takes the adoption label off the "
        "files no merge reaches and re-derives the projections, neither of which runs over a merge in progress.",
        "4. **Run `make agents`.** It re-derives the skills, commands and agent types of every coding agent this "
        "project has installed from `commands/`, `skills/` and `agents/` as they now stand — the step that "
        "carries a changed ladder into the agent. Run from inside a coding agent this project has moved to "
        "since `./init`, it installs that one too, where the agent says which it is in its environment; where "
        "it could not tell, it says so, and `./init --integration <agent>` installs it by name.",
        "5. **Run `make check-agents`.** It passes, or it names the projection that is still out of step.",
        "6. **Start a new session in your coding agent.** A harness reads its commands and agent types once, "
        "when a session starts, so the session that ran this migration still has the old ones.",
        "7. **Confirm the rest:** `make crossing` for what the crossing could not carry, then the sections "
        "below, ending with `make verify`.",
        f"8. **Archive this file when the work is done** — move it to the path its last line names, under "
        f"`{ARCHIVE}/`. Never delete it: it is the one record of what this upgrade asked of the project, and the "
        "next migration archives it there anyway before writing its own.",
    ]


def after_conflicts(written: bool) -> list[str]:
    """What `migrate`'s stop report says follows the resolving commit: a pointer to the page's opening section,
    which holds the whole path, or — where the page could not be `written` — that path itself, since nothing
    else would say it."""
    if written:
        return [
            f"Then work `{SET_UP}` at the top of {NOTES}: it names these files again and goes from the resolving "
            "commit to a project whose coding agent is set up — `slipwai migrate` again, `make agents`, "
            "`make check-agents`, and a new agent session. Until then the merge is in and the agent still reads "
            "the old commands.",
        ]
    return [
        "Then: `slipwai migrate` again, which takes the adoption label off the files no merge reaches; "
        "`make agents`, which carries the command and agent files this migration moved into every installed "
        "coding agent; `make check-agents`, which passes once they are; and a new agent session, because a "
        "harness reads its commands and agent types once, when a session starts.",
    ]

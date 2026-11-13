"""`.slipwai/run/`: the one folder a run's own state lives in since 2.1, and the move `slipwai migrate` makes.

Until 2.1 a project's `.slipwai/` held the record and the run side by side, and the run's half was ignored a
name at a time. The list fell behind three times — `preflight.json` and `logs.unread-*/`, then `activity/`,
then the ACP session files, the console's and the stages' sessions and two pid files — and each name it
missed was an untracked file in every berth that `check-slice-scope` failed every slice on. Now everything a
run writes about itself is under `logs.RUN`, the ignore file has one line for it, and what stays at
`.slipwai/` is the committed list in `logs.COMMITTED`.

**The move is a migration's, after the merge.** The merge brings the new `.gitignore` and the toolkit that
reads the new place; this then moves what is on disk to where both now look, and rewrites the ignore lines a
project's own `.gitignore` still has — an adopted repository's marked block is not the keel's to merge. It
moves only what git does not track, never overwrites a file already at the new place (that one is left and
named), and a second pass finds nothing to do.

**It refuses while a fleet is out.** A harbourmaster or a captain appending to a deck log while its folder is
moved loses the lines written in between, and nothing would say which. A live pid under `running/`, at
either place, stops the migration before the merge, with the command that stops the fleet.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from .errors import GenerationError
from .logs import COMMITTED, RUN
from .process_alive import alive

#: The one ignore line, which is also what `logs.run_dir` reads to tell the layout.
LINE = f"{RUN}/"
#: The folder a project not migrated yet keeps its run state in, beside the record. Only this module and
#: `logs.run_dir` name it as a place to read; everything else asks `run_dir`.
OLD = ".slipwai"
#: What stops a fleet, said at the end of the refusal.
STOP = "python3 scripts/agents/fleet.py stop"
#: An ignore line naming something under `.slipwai/`, and which name.
IGNORED = re.compile(r"^/?\.slipwai/(?P<name>[^/\s]+/?)\S*\s*$")


def live(root: Path) -> list[str]:
    """Every process the fleet recorded under `running/`, at either place, that is still running."""
    found: list[str] = []
    for place in (root / OLD / "running", root / RUN / "running"):
        for pid_file in sorted(place.glob("*.pid")) if place.is_dir() else []:
            try:
                pid = int(pid_file.read_text(encoding="utf-8").strip())
            except (OSError, ValueError):
                continue
            if alive(pid):
                found.append(f"{pid_file.stem} (pid {pid})")
    return found


def refuse_while_out(root: Path) -> None:
    """Stop here, before anything is merged or moved, where a fleet is still running in this project."""
    running = live(root)
    if running:
        raise GenerationError(
            f"a fleet is out in this project — {', '.join(running)} — and this migration moves the run's state "
            f"into {LINE}; moving a log under a process still appending to it loses the lines written in between. "
            f"Stop the fleet, let each process exit, then run `slipwai migrate` again: {STOP}"
        )


def stays(name: str, is_dir: bool) -> bool:
    """Whether `.slipwai/<name>` is the record, or the new folder itself, rather than run state to move."""
    return name == "run" or (f"{name}/" if is_dir else name) in COMMITTED


def dirt(porcelain: str) -> list[str]:
    """The lines of `git status --porcelain` that are a person's own changes, leaving out untracked run state.

    A 2.0 project carries untracked `.slipwai/console/`, `.slipwai/stages/` and the pid files the old ignore
    list missed, and `migrate` refused it as uncommitted — over the very files `move_in` exists to carry into
    `.slipwai/run/`. game-club-manager's had to be moved aside by hand. Untracked state under `.slipwai/` is
    the run's, never a change to merge over, so it does not make a tree dirty here."""
    kept = []
    for line in porcelain.splitlines():
        path = line[3:].strip().strip('"')
        top, _, rest = path.removeprefix(f"{OLD}/").partition("/")
        run_state = line.startswith("?? ") and path.startswith(f"{OLD}/") and not stays(top, bool(rest) or
                                                                                         path.endswith("/"))
        if line.strip() and not run_state:
            kept.append(line)
    return kept


def tracked(root: Path, relative: str) -> bool:
    """Whether git tracks anything at this path: a record, which `relocate` moves if anything does."""
    listed = subprocess.run(["git", "ls-files", "--", relative], cwd=root, text=True, capture_output=True,
                            check=False)
    return listed.returncode == 0 and bool(listed.stdout.strip())


def merged(source: Path, target: Path, left: list[str], root: Path) -> None:
    """Move `source` to `target`, into a folder already there one entry at a time, never over a file."""
    if not target.exists() and not target.is_symlink():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(target))
        return
    if source.is_dir() and not source.is_symlink() and target.is_dir():
        for child in sorted(source.iterdir()):
            merged(child, target / child.name, left, root)
        if not any(source.iterdir()):
            source.rmdir()
        return
    left.append(f"{source.relative_to(root).as_posix()} (already at {target.relative_to(root).as_posix()}; "
                f"nothing was written over — compare the two, keep one and remove the other)")


def ignore_lines(text: str) -> str:
    """`.gitignore` with each line naming run state under `.slipwai/` replaced by the one line, in place."""
    out: list[str] = []
    placed = LINE in (line.strip() for line in text.splitlines())
    for line in text.splitlines():
        match = IGNORED.match(line.strip())
        name = match.group("name") if match else ""
        if not match or name.rstrip("/") == "run" or name in COMMITTED or f"{name}/" in COMMITTED:
            out.append(line)
        elif not placed:
            out.append(LINE)
            placed = True
    if not placed:
        out += ["", "# Everything a run writes about itself, and never a record of it (slipwai 2.1).", LINE]
    return "\n".join(out) + "\n"


def move_in(root: Path, *, ignore: bool = True) -> tuple[tuple[str, ...], tuple[str, ...], bool]:
    """Move this project's run state into `.slipwai/run/` and say so in its `.gitignore`.

    Returns what moved, what was left with why, and whether `.gitignore` changed. `ignore=False` leaves the
    ignore file alone — a merge that conflicted in it is the person's to resolve — and moves the state
    anyway, so the toolkit the merge brought finds it."""
    changed = False
    gitignore = root / ".gitignore"
    if ignore:
        text = gitignore.read_text(encoding="utf-8") if gitignore.is_file() else ""
        rewritten = ignore_lines(text)
        if rewritten != text:
            gitignore.write_text(rewritten, encoding="utf-8")
            changed = True
    moved: list[str] = []
    left: list[str] = []
    old = root / OLD
    for path in sorted(old.iterdir()) if old.is_dir() else []:
        relative = f"{OLD}/{path.name}"
        if stays(path.name, path.is_dir()) or tracked(root, relative):
            continue
        before = len(left)
        merged(path, root / RUN / path.name, left, root)
        if len(left) == before:
            moved.append(f"{relative} -> {RUN}/{path.name}")
    return tuple(moved), tuple(left), changed

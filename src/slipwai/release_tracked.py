"""What a release of a package holds where the package is in a git repository: what `HEAD` tracks, and nothing else.

A release used to be the package directory as it stood, less a short list of names. So a clone holding anything a
clean checkout does not built a different file from the one CI built off the tag: `codegraph` 1.0.1 was registered by
hand from a clone with an empty `changelog.d/` left in it — git tracks no empty directory — and the digest written
into the index was of an archive nobody had published (#117). And whatever else sat in the directory, a `.DS_Store`
or an editor's backup, went into a public file.

Git is asked rather than the directory read: the tree at `HEAD` under the package, each submodule at the commit that
tree records for it. So an untracked file, an ignored one and an empty directory are not in the release whatever the
clone holds, and two clones of one commit build one file. Outside a repository there is nothing to ask, and
`language_release.files_of` walks the directory as it always has.

"Outside a repository" is not "git did not answer". Where a `.git` is at or above the package and git is not
installed, or refuses the directory — a checkout it takes for another user's, in a container or on a runner — there
is a tree to ask about and nobody to ask, and a release or a registration is refused with git's own line (#126).

`differences` is the other half. The bytes are still read from the working tree, so a tracked file somebody has edited
would be released as edited; `package release` and `package register` refuse while anything in the package differs
from `HEAD`, naming it, as `migrate` and `add-service` refuse a tree with uncommitted changes.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

from .errors import GenerationError

LINK, SUBMODULE = "120000", "160000"
#: How many differing paths a refusal names before it counts the rest: enough to recognise, not a screenful.
NAMED = 8


def ran(root: Path, argv: tuple[str, ...]) -> subprocess.CompletedProcess[bytes]:
    """Git, run there. The one place it is started, so a case can stand in a git that fails as git does."""
    return subprocess.run(["git", "--no-optional-locks", *argv], cwd=root, capture_output=True, check=False)


def asked(root: Path, *argv: str) -> tuple[str | None, str | None]:
    """What git answers there; or None and what it said in refusing; or None twice where it could not be run."""
    try:
        done = ran(root, argv)
    except OSError:
        return None, None
    if done.returncode == 0:
        return done.stdout.decode("utf-8", "surrogateescape"), None
    return None, done.stderr.decode("utf-8", "replace")


def git(root: Path, *argv: str) -> str | None:
    """What git answers there, or None where it refuses or is not installed."""
    return asked(root, *argv)[0]


def checkout(root: Path) -> Path | None:
    """The nearest directory at or above `root` that holds a `.git`: a directory in a clone, a file in a worktree or
    a submodule. Read off the disk, so it is known where git itself will not say."""
    here = root.resolve()
    return next((place for place in (here, *here.parents) if (place / ".git").exists()), None)


def line_of(said: str) -> str:
    """Git's own line out of what it printed: its `fatal:` one, or the first it wrote."""
    lines = [line.strip() for line in said.splitlines() if line.strip()]
    return next((line for line in lines if line.startswith("fatal:")), lines[0] if lines else "nothing")


def unanswered(root: Path, said: str | None) -> GenerationError:
    """The refusal where `root` is in a checkout and git did not answer for it, quoting git and naming the fix.

    Not walked instead: a walk holds whatever the clone holds, which is the release nobody published of #117, and
    the machines git refuses on — a container, a runner with a mounted checkout — are the ones a release is cut on
    (#126)."""
    top = checkout(root)
    where = f"{root} is in a git checkout ({top})"
    held = "A release is what the tag holds, so it is not packed from the directory instead"
    if said is None:
        return GenerationError(f"{where} and git could not be run, so what HEAD holds of it cannot be read. {held}. "
                               f"Install git, or put it on PATH, and run this again")
    if "safe.directory" in said or "dubious ownership" in said:
        named = re.search(r"safe\.directory[ \t]+(\S.*)", said)
        path = named.group(1).strip() if named else (top or root.resolve()).as_posix()
        fix = f"Tell git the checkout is yours, `git config --global --add safe.directory {path}`"
    else:
        fix = f"Ask it yourself, `git -C {root} status`, mend what it names"
    return GenerationError(f"{where} and git would not answer for it: {line_of(said)}. {held}. {fix}, and run "
                           f"this again")


def prefix(root: Path) -> str | None:
    """Where `root` is inside its repository's working tree (`''` at the top), or None where it is in none. Where
    there is a `.git` at or above it and git is missing or refuses, that is not "in none", and it is refused."""
    if not root.is_dir():
        return None
    inside, said = asked(root, "rev-parse", "--is-inside-work-tree")
    if inside is None and checkout(root) is not None:
        raise unanswered(root, said)
    if (inside or "").strip() != "true":
        return None
    return (git(root, "rev-parse", "--show-prefix") or "").strip().rstrip("/")


def listed(root: Path, tree: str) -> list[tuple[str, str, tuple[str, ...]]]:
    """Every entry of a tree, as (mode, object, path parts). Nothing where the tree is not there: a directory `HEAD`
    does not hold, or a repository with no commit yet."""
    answered = git(root, "ls-tree", "-r", "-z", "--full-tree", tree) or ""
    found = []
    for record in filter(None, answered.split("\0")):
        described, _, path = record.partition("\t")
        mode, _, name = described.split(" ")
        found.append((mode, name, tuple(path.split("/"))))
    return found


def tracked(root: Path) -> list[tuple[str, ...]] | None:
    """The files `HEAD` tracks under `root`, as path parts in a fixed order, or None where `root` is in no
    repository. A submodule is read at the commit `HEAD` records for it; one not checked out refuses, and so does a
    tracked link, as a link in a directory that is walked does."""
    here = prefix(root)
    return None if here is None else sorted(under(root, f"HEAD:{here}"))


def under(root: Path, tree: str) -> list[tuple[str, ...]]:
    """Every file under a tree, each submodule in it read at the commit the tree records."""
    found: list[tuple[str, ...]] = []
    for mode, name, parts in listed(root, tree):
        if mode == LINK:
            raise GenerationError(f"{root.joinpath(*parts)} is a link, and a release holds regular files and "
                                  f"directories only")
        if mode != SUBMODULE:
            found.append(parts)
            continue
        submodule = root.joinpath(*parts)
        if not (submodule / ".git").exists() or git(submodule, "cat-file", "-e", f"{name}^{{commit}}") is None:
            raise GenerationError(f"{submodule} is a submodule that is not checked out at the commit this package "
                                  f"records for it, so what a release holds of it cannot be read. Check it out: "
                                  f"`git submodule update --init --recursive`")
        found.extend((*parts, *held) for held in under(submodule, name))
    return found


def differences(root: Path) -> list[str]:
    """Where the working tree under `root` differs from `HEAD`, a line each: an uncommitted change to a tracked
    file, or a file git does not track. Ignored files and empty directories are not differences — they are in no
    release either way. Nothing outside a repository."""
    here = prefix(root)
    if here is None:
        return []
    answered, said = asked(root, "status", "--porcelain=v1", "-z", "--untracked-files=all", "--", ".")
    if answered is None:  # it said this is a working tree, and will not say what differs in it
        raise unanswered(root, said)
    fields = answered.split("\0")
    found = []
    while fields:
        entry = fields.pop(0)
        if len(entry) <= 3:
            continue
        if entry[0] in "RC" and fields:  # a rename or a copy names where it came from next
            fields.pop(0)
        path = entry[3:]
        path = path[len(here) + 1:] if here and path.startswith(f"{here}/") else path
        found.append(f"{path} ({'untracked' if entry.startswith('??') else 'uncommitted change'})")
    return sorted(found)


def only_release_output(found: list[str]) -> bool:
    """Whether all that differs is an untracked `dist/` holding a release: what a package scaffolded before its
    scaffold ignored `dist/` is left with by its own first `make release` (#126)."""
    return (all(line.startswith("dist/") and line.endswith(" (untracked)") for line in found)
            and any(line.endswith(".tar.gz (untracked)") for line in found))


def refuse_differences(root: Path) -> None:
    """Refuse a release of a package whose working tree is not what `HEAD` holds, naming what differs.

    Refused rather than warned about, as every other verb here treats a tree with uncommitted changes: a warning
    above a digest is read after the digest has been published. A package `HEAD` holds nothing of is refused too,
    because its release would be an empty directory.
    """
    if prefix(root) is None:
        return
    found = differences(root)
    if found and only_release_output(found):
        raise GenerationError(
            f"{root} differs from what its repository holds at HEAD only by `dist/`, which holds an earlier "
            f"release and is not ignored: {'; '.join(found[:NAMED])}. A release is what the tag holds, so it is "
            f"refused rather than packed around. Ignore it, once: `echo dist/ >> .gitignore && git add .gitignore "
            f"&& git commit -m 'Ignore dist/'`, and run this again")
    if found:
        named = "; ".join(found[:NAMED]) + (f"; and {len(found) - NAMED} more" if len(found) > NAMED else "")
        raise GenerationError(
            f"{root} is not what its repository holds at HEAD, and a release is what the tag holds: {named}. "
            f"Commit them, or put them aside with `git stash --include-untracked`, and run this again. A file "
            f"that belongs in no release goes in `.gitignore`")
    if not tracked(root):
        raise GenerationError(
            f"{root} is inside a git repository that tracks none of it at HEAD, and a release is what the tag "
            f"holds. Commit the package first: `git add . && git commit`")

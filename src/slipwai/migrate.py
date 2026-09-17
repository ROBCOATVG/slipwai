"""`slipwai migrate`: bring a generated project up to this factory's version, in one command.

`replay` writes what this factory generates for the project's answers as a commit on the project's own
history; `migrate` is that plus the merge, because the two `git` commands between them are the same every
time and nobody should have to remember them. Run inside a generated project on a clean tree, it replays
into a temporary directory beside the project, fetches that one commit into the project — after which the
directory has nothing the project's `.git` does not — and merges it. A clean merge is one commit, and
`git reset --hard ORIG_HEAD` is its undo. A merge with conflicts is left in progress, exactly as `git` leaves
it, with each conflicting file named and the two ways out spelled: resolve and commit, or abort.

The tree has to be clean first, for the same reason `add-service` asks: so that everything uncommitted
afterwards is this command's, and the way back is one command. Nothing is pushed.

One thing the merge cannot do, and this command finishes afterwards: a project *derives* local files from
factory-owned sources. `./init` projects elected extension guidance into `AGENTS.md`, then commands, skills
and agent types into each installed harness. Neither the adopted marker region nor those harness-local
copies exists on the factory's side of the merge. Re-derive them here, extension first so copied contexts
receive its current block. The committed `.slipwai/extensions.json` records the election; a legacy project
with no record is inferred once from markers. Setup and the interactive menu never run during migration.
"""
from __future__ import annotations

import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .assets import NOTES, VERSION
from .catch_up import notes
from .errors import GenerationError
from .layout import AT_ROOT, Layout, layout_of
from .manifest import read_manifest
from .replay import Replay, git, replay
from .scaffold import NO_MAINTENANCE

# The project's own projectors: extension guidance first, then the agent files and contexts that may copy
# that guidance. Named here rather than shelling out to `make`, so refresh cannot pick up an unrelated
# target the project has since defined.
EXTENSION_PROJECTOR = "scripts/extensions/project.py"
PROJECTOR = "scripts/agents/project.py"
# What `./init` writes once it has installed a harness. Absent, nothing has been projected yet, so there is
# nothing committed that could be out of step — the generated `Makefile`'s `install` target asks exactly
# this question before it runs `agents`, and this is the same question asked for the same reason.
PROJECTED = ".specify/integration.json"
EXTENSION_STATE = ".slipwai/extensions.json"


@dataclass(frozen=True)
class Refresh:
    """Re-deriving the project's own projections after the merge: what moved, or why it could not run."""

    changed: tuple[str, ...] = ()
    # Whether the projector ran and wrote: the projections are ignored by Git, so a re-derivation that changed every
    # one of them stages nothing, and `changed` is only what a project still tracks from before they were ignored.
    written: bool = False
    # Why the projector could not be run to completion, for a report that says so rather than swallowing it.
    failed: str | None = None


@dataclass(frozen=True)
class Migration:
    """What `migrate` did: the replay it merged, the version the project was on, and how the merge ended."""

    offered: Replay
    was: str | None
    # Files with conflict markers, in path order; empty when the merge committed.
    conflicts: tuple[str, ...]
    # `git diff --stat`'s last line for what the factory changed since the base, or None when it changed nothing.
    changed: str | None
    # Whether the merge was a fast-forward: the project had nothing of its own since the last factory commit.
    fast_forward: bool = False
    # The projections re-derived after a clean merge; nothing at all where the merge stopped at a conflict.
    refresh: Refresh = Refresh()
    # Why the catch-up notes could not be written, or None when they were — which is every migration that
    # changed anything, whatever the versions crossed asked.
    unwritten: str | None = None


def migrate(root: Path) -> Migration:
    """Replay the project at `root` with this factory and merge the result into it."""
    document = read_manifest(root, verb="migrate")
    if not git(root, "rev-parse", "--verify", "--quiet", "HEAD", check=False):
        raise GenerationError(
            f"{root} has no Git history to merge into; `slipwai replay` writes the tree beside it instead"
        )
    if git(root, "status", "--porcelain"):
        raise GenerationError(
            "this project has uncommitted changes; commit or stash them first, so that the merge is the only "
            "thing this command leaves behind and `git reset --hard ORIG_HEAD` undoes exactly that"
        )
    generator = document.get("generator")
    was = generator.get("updatedWith") if isinstance(generator, dict) else None
    with tempfile.TemporaryDirectory(prefix=f".{document['name']}-migrate-", dir=root.parent) as staging:
        offered = replay(root, Path(staging) / "offered")
        git(root, *NO_MAINTENANCE, "fetch", "--quiet", str(offered.destination), "main")
    stat, conflicts, fast_forward = merge_offered(root, offered, f"Migrate {document['name']} to slipwai {VERSION}")
    if stat is None:
        refreshed = refresh(root, document["name"], layout_of(document), set_undo=True)
        return Migration(offered, was, (), None, refresh=refreshed)
    # Written either way, and before the projections: the notes are what the *versions* asked for, which a
    # conflict does not change, and a merge left in progress is exactly when somebody wants to know what
    # they are resolving towards.
    unwritten = write_notes(root, document["name"], was)
    if conflicts:
        # Nothing is re-derived over a merge still in progress: the command files are half the project's
        # and half the factory's until somebody decides, and projecting a conflicted file would write the
        # markers into every harness. The report asks for it after the resolving commit instead.
        return Migration(offered, was, conflicts, stat, fast_forward, unwritten=unwritten)
    refreshed = refresh(root, document["name"], layout_of(document))
    return Migration(offered, was, conflicts, stat, fast_forward, refreshed, unwritten)


def merge_offered(root: Path, offered: Replay, message: str) -> tuple[str | None, tuple[str, ...], bool]:
    """Merge the fetched replay into the project: `git diff --stat`'s last line (None where the factory changed
    nothing since the base, and nothing was merged), the conflicting files, and whether it fast-forwarded. The
    replay's commit is in the project's object store by now; the directory it came from may be gone."""
    stat = git(root, "diff", "--stat", str(offered.base), "FETCH_HEAD").splitlines()
    if not stat:
        return None, (), False
    merge = subprocess.run(
        ["git", *NO_MAINTENANCE, "merge", "--no-edit", "-m", message, "FETCH_HEAD"],
        cwd=root, text=True, capture_output=True, check=False,
    )
    conflicts = tuple(git(root, "diff", "--name-only", "--diff-filter=U").split())
    if merge.returncode != 0 and not conflicts:
        raise GenerationError(f"git merge failed without a conflict to resolve: {merge.stderr.strip()}")
    return stat[-1].strip(), conflicts, git(root, "rev-parse", "HEAD") == git(root, "rev-parse", "FETCH_HEAD")


def write_notes(root: Path, name: str, was: str | None) -> str | None:
    """Leave the catch-up notes in the project; None when they were left, else why they could not be.

    The one thing a merge cannot carry: what each version crossed asks of a repository that already exists is
    written in the factory's `CHANGELOG.md`, which a generated project has no copy of and — installed as a
    frozen executable — cannot be given one. So it is written here, where `/catch-up` can read it with `cat`.

    Always written, once the merge changed anything — where the versions crossed cannot be told, the page says
    why and lists what it can, because an absent file is read as "nothing owed" and that is the one thing a
    migration must never say by accident. Never a reason to fail either: the merge is the valuable thing and
    it is already committed by this point. A project whose notes could not be written is told so, with the
    reason, and reads them in the factory's changelog instead.
    """
    try:
        destination = root / NOTES
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(notes(name, was))
    except OSError as error:
        return str(error)
    return None


def refresh(root: Path, name: str, layout: Layout = AT_ROOT, *, set_undo: bool = False) -> Refresh:
    """Re-derive factory-owned extension and agent projections after a clean merge.

    Its own commit, and never an amend of the one before it. On a fast-forward the merge *is* the factory's
    replay commit, and `replay.base_commit` finds the base for the next migration by looking for the newest
    commit the factory authored — so amending it would put files the factory does not generate into the very
    tree the next replay is measured against, and the next merge would read that as the factory *deleting*
    the projections, because the factory's side genuinely has no such file. Left alone, the base stays
    exactly the tree the factory wrote. Two commits are still one `git reset --hard ORIG_HEAD`, which is what
    the report promises and all it has to.

    A projector that cannot run is reported, not raised: the merge is done and good either way, and losing
    it to a failure in a follow-up step would be the worse outcome by far.
    """
    extension_projector = layout.place(EXTENSION_PROJECTOR)
    agent_projector = layout.place(PROJECTOR)
    commands: list[list[str]] = []
    extensions = root / layout.place("scripts/extensions")
    agents = root / "AGENTS.md"
    marked = agents.read_text() if agents.is_file() else ""
    extension_elected = False
    if extensions.is_dir():
        extension_elected = (root / EXTENSION_STATE).is_file() or any(
            (candidate / "init.py").is_file()
            and f"<!-- extension:{candidate.name}:begin -->" in marked
            for candidate in extensions.iterdir()
        )
    if (root / extension_projector).is_file() and extension_elected:
        commands.append(["python3", extension_projector])
    if (root / agent_projector).is_file() and (root / PROJECTED).is_file():
        commands.append(["python3", agent_projector])
    if not commands:
        return Refresh()
    for command in commands:
        projected = subprocess.run(command, cwd=root, text=True, capture_output=True, check=False)
        if projected.returncode != 0:
            return Refresh(
                failed=(projected.stderr.strip() or projected.stdout.strip() or "no reason given")
            )
    # The tree was clean before the merge and the merge committed, so everything uncommitted now is the
    # projector's — which is why this can stage everything rather than work out what it wrote. Staging
    # first and asking the index second also spares this the two ways parsing `status --porcelain` goes
    # wrong: a path is quoted when it needs to be, and the status letters are positional against a leading
    # space that `git` here strips off the first line with the rest of the trailing whitespace.
    git(root, "add", "-A")
    changed = tuple(git(root, "diff", "--cached", "--name-only").splitlines())
    if not changed:
        return Refresh(written=True)
    if set_undo:
        # No merge populated ORIG_HEAD. Set it only when this path is about to commit; a no-op migration
        # must not overwrite the undo point left by the previous real migration.
        git(root, "update-ref", "ORIG_HEAD", "HEAD")
    committed = subprocess.run(
        ["git", *NO_MAINTENANCE, "commit", "--quiet", "-m",
         f"Re-derive {name}'s factory projections for slipwai {VERSION}"],
        cwd=root, text=True, capture_output=True, check=False,
    )
    if committed.returncode != 0:
        return Refresh(changed, written=True, failed=committed.stderr.strip() or "the commit was refused")
    return Refresh(changed, written=True)


def report(done: Migration) -> str:
    """What happened and what to do next, for the person who ran it."""
    name = done.offered.name
    was = f"from {done.was} " if done.was and done.was != VERSION else ""
    if done.changed is None:
        if done.refresh.changed:
            return (
                f"nothing generated to migrate: {name} already has everything slipwai {VERSION} generates "
                f"for its answers; one commit refreshed {len(done.refresh.changed)} factory-owned "
                "projection(s). Nothing pushed; `git reset --hard ORIG_HEAD` undoes it."
            )
        if done.refresh.failed:
            return (
                f"nothing generated to migrate, but factory-owned projections could not be refreshed: "
                f"{done.refresh.failed}. Run `make agents`."
            )
        return (
            f"nothing to migrate: {name} already has everything slipwai {VERSION} generates for its answers "
            f"(measured from {str(done.offered.base)[:12]}, the last commit here the factory made)"
        )
    if done.conflicts:
        files = "\n".join(f"  {path}" for path in done.conflicts)
        return "\n".join([
            f"migrating {name} {was}to slipwai {VERSION} stopped at {len(done.conflicts)} conflict(s) — each a file "
            "both this project and the factory changed since the last migration, and the project decides:",
            files,
            "",
            "Every other file is merged and staged. For each file above, edit it and `git add` it — or take a "
            "side whole: `git checkout --ours -- <file>` keeps this project's version, `--theirs` takes the "
            "factory's — then `git commit`. Or `git merge --abort` to walk away from all of it.",
            "Then: make agents, to re-derive the harness projections from the command and agent files this "
            "migration moved — the factory never writes those, so the merge cannot, and `check-agents` fails "
            "until they are re-derived.",
            *(catch_up(done)),
        ])
    how = (
        "One commit, fast-forwarded — this project had no changes of its own since the last factory commit."
        if done.fast_forward
        else "One merge commit. The files this project had changed itself were kept; the rest are what the "
        "factory now generates for its answers."
    )
    lines = [f"migrated {name} {was}to slipwai {VERSION}: {done.changed}", how]
    if done.refresh.changed:
        lines.append(
            f"A second commit re-derives {len(done.refresh.changed)} factory-owned projection(s) from the "
            "extension, command and agent sources this brought in — the merge could not update local copies."
        )
    elif done.refresh.written:
        lines.append(
            "The extension and harness projections were re-derived from the sources this brought in; they are "
            "ignored by Git or already current, so there is nothing to commit."
        )
    lines.append("Nothing pushed; `git reset --hard ORIG_HEAD` undoes all of it.")
    if done.unwritten is None:
        lines.append(
            f"What the versions crossed ask of code already here — which no merge can do — is written to "
            f"{NOTES}, git-ignored and disposable."
        )
    if done.refresh.failed:
        lines += [
            "",
            f"The factory-owned projections could not be re-derived: {done.refresh.failed}",
            "The merge is committed and unaffected. Run `make agents` and commit the result, or "
            "the extension or agent projection gate will fail against the sources this migration moved.",
        ]
    lines += catch_up(done, "Next")
    return "\n".join(lines)


def catch_up(done: Migration, then: str = "Then") -> list[str]:
    """The report's last step: `/catch-up` over the notes, or — the one case the notes are not there — why
    not and where to read them instead. Never a bare `make verify`, which reads as nothing being owed."""
    if done.unwritten is None:
        return [f"{then}: /catch-up, which reads {NOTES} — what these versions ask of code already here — and "
                "runs make verify against it."]
    return [
        f"The catch-up notes could not be written to {NOTES}: {done.unwritten}",
        f"Read the factory's CHANGELOG.md from {done.was or 'its first entry'} to {VERSION} instead — what those "
        f"versions ask of code already here, which no merge can do. {then}: make verify",
    ]

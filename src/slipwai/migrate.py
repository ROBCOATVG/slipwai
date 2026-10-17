"""`slipwai migrate`: bring a generated project up to this keel's version, in one command.

`replay` writes what this keel generates for the project's answers as a commit on the project's own
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
copies exists on the keel's side of the merge. Re-derive them here, extension first so copied contexts
receive its current block. The committed `.slipwai/extensions.json` records the election; a legacy project
with no record is inferred once from markers. Setup and the interactive menu never run during migration.
"""
# budget: 375 — a clean merge also leaves the intake proposal beside the catch-up notes, and moves the records
# a newer keel keeps elsewhere (`relocate`) in the commit after it.
from __future__ import annotations

import subprocess
import tempfile
from dataclasses import replace
from pathlib import Path

from . import githooks
from .assets import NOTES, VERSION
from .catch_up import moved_languages, notes
from .errors import GenerationError
from .layout import AT_ROOT, Layout, layout_of
from .manifest import read_manifest, refuse_older
from .migration_result import Migration
from .relocate import relocate
from .replay import Replay, git, replay
from .scaffold import NO_MAINTENANCE
from .unlabel import Refresh, read_page, unlabel

# Project extension guidance first, then agent files: explicit paths avoid a project-defined make target.
EXTENSION_PROJECTOR = "scripts/extensions/project.py"
PROJECTOR = "scripts/agents/project.py"
# What `./init` writes once it has installed a harness. Absent, nothing has been projected yet, so there is
# nothing committed that could be out of step — the generated `Makefile`'s `install` target asks exactly
# this question before it runs `agents`, and this is the same question asked for the same reason.
PROJECTED = ".specify/integration.json"
EXTENSION_STATE = ".slipwai/extensions.json"


def checked(root: Path) -> dict:
    """`project.json`, once every check that needs no language has passed — readable, paths inside, a history, a clean
    tree, no package older than its record: nothing is installed before these hold."""
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
    refuse_older(document)
    return document


def migrate(root: Path, *, with_claims: bool = False) -> Migration:
    """Replay the project at `root` with this keel and merge the result into it."""
    document = checked(root)
    from .migration_crossing import crossing, version
    if version(document):
        done = crossing(root, document, with_claims=with_claims)
        if not done.conflicts:
            done = replace(done, refresh=refresh(root, document["name"], layout_of(document)))
        return done
    name, generator = document["name"], document.get("generator")
    was = generator.get("updatedWith") if isinstance(generator, dict) else None
    with tempfile.TemporaryDirectory(prefix=f".{name}-migrate-", dir=root.parent) as staging:
        offered = replay(root, Path(staging) / "offered")
        git(root, *NO_MAINTENANCE, "fetch", "--quiet", str(offered.destination), "main")
    stat, conflicts, fast_forward = merge_offered(root, offered, f"Migrate {name} to slipwai {VERSION}")
    if stat is None:
        return Migration(offered, was, (), None, refresh=refresh(root, name, layout_of(document), set_undo=True))
    # Written either way, and before the projections: the notes are what the *versions* asked for, which a
    # conflict does not change, and a merge left in progress is exactly when somebody wants to know what
    # they are resolving towards.
    unwritten = write_notes(root, name, was, document)
    if conflicts:
        # Nothing is re-derived over a merge still in progress: the command files are half the project's
        # and half the keel's until somebody decides, and projecting a conflicted file would write the
        # markers into every harness. The report asks for it after the resolving commit instead.
        return Migration(offered, was, conflicts, stat, fast_forward, unwritten=unwritten)
    from .project.intake_cleanup import write_proposal
    write_proposal(root)
    return Migration(offered, was, conflicts, stat, fast_forward, refresh(root, name, layout_of(document)), unwritten)


def merge_offered(root: Path, offered: Replay, message: str) -> tuple[str | None, tuple[str, ...], bool]:
    """Merge the fetched replay into the project: `git diff --stat`'s last line (None where the keel changed
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


def write_notes(root: Path, name: str, was: str | None, document: dict | None = None) -> str | None:
    """Leave the catch-up notes in the project; None when they were left, else why they could not be.

    The one thing a merge cannot carry: what each version crossed asks of a repository that already exists is
    written in the keel's `CHANGELOG.md`, which a generated project has no copy of and — installed as a
    frozen executable — cannot be given one. So it is written here, where `/catch-up` can read it with `cat`.

    Always written, once the merge changed anything — where the versions crossed cannot be told, the page says
    why and lists what it can, because an absent file is read as "nothing owed" and that is the one thing a
    migration must never say by accident. Never a reason to fail either: the merge is the valuable thing and
    it is already committed by this point. A project whose notes could not be written is told so, with the
    reason, and reads them in the keel's changelog instead. `document` is `project.json` as it was before the
    merge: each language it needs whose version moved gets a section of its own.
    """
    try:
        destination = root / NOTES
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(notes(name, was, languages=moved_languages(document) if document else ()))
    except Exception as error:  # the merge is committed: whatever a recorded value did, say so and never raise
        return str(error) or type(error).__name__
    return None


def refresh(root: Path, name: str, layout: Layout = AT_ROOT, *, set_undo: bool = False) -> Refresh:
    """Re-derive factory-owned extension and agent projections after a clean merge.

    Its own commit, and never an amend of the one before it. On a fast-forward the merge *is* the keel's
    replay commit, and `replay.base_commit` finds the base for the next migration by looking for the newest
    commit the keel authored — so amending it would put files the keel does not generate into the very
    tree the next replay is measured against, and the next merge would read that as the keel *deleting*
    the projections, because the keel's side genuinely has no such file. Left alone, the base stays
    exactly the tree the keel wrote. Two commits are still one `git reset --hard ORIG_HEAD`, which is what
    the report promises and all it has to.

    A projector that cannot run is reported, not raised: the merge is done and good either way, and losing
    it to a failure in a follow-up step would be the worse outcome by far.
    """
    # Records the project wrote that this keel keeps elsewhere: staged by `git mv`, committed below with the rest.
    relocated, left = relocate(root)
    respelled, skipped = unlabel(root, layout)
    skipped += left
    # Per-checkout config and not a file, so no merge carried it and a project predating the hook has it
    # set nowhere. It writes nothing into the tree, so it cannot fail the commit below.
    hooked = githooks.install(root, layout)
    extension_projector = layout.place(EXTENSION_PROJECTOR)
    agent_projector = layout.place(PROJECTOR)
    commands: list[list[str]] = []
    extensions = root / layout.place("scripts/extensions")
    agents = root / "AGENTS.md"
    marked = (read_page(agents) if agents.is_file() else None) or ""
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
    for command in commands:
        projected = subprocess.run(command, cwd=root, text=True, capture_output=True, check=False)
        if projected.returncode != 0:
            return Refresh(
                uncommitted=respelled, skipped=skipped,
                hooked=hooked.set, hooks=hooked.why,
                failed=(projected.stderr.strip() or projected.stdout.strip() or "no reason given")
            )
    # The tree was clean before the merge and the merge committed, so everything uncommitted now is the
    # projector's — which is why this can stage everything rather than work out what it wrote. Staging
    # first and asking the index second also spares this the two ways parsing `status --porcelain` goes
    # wrong: a path is quoted when it needs to be, and the status letters are positional against a leading
    # space that `git` here strips off the first line with the rest of the trailing whitespace.
    if commands:
        # Everything but the catch-up note, which this command wrote and a project that does not ignore it must
        # not have committed as though a projector had.
        git(root, "add", "-A")
        git(root, "reset", "--quiet", "--", NOTES)
    elif respelled:
        git(root, "add", "--", *respelled)
    elif not relocated:
        # Nothing to project, respell or move: nothing of this command's is in the tree to stage.
        return Refresh(skipped=skipped, hooked=hooked.set, hooks=hooked.why)
    staged = tuple(git(root, "diff", "--cached", "--name-only").splitlines())
    respelled = tuple(path for path in respelled if path in staged)
    ends = {end for move in relocated for end in move.split(" -> ")}
    changed = tuple(path for path in staged if path not in respelled and path not in ends)
    if not staged:
        return Refresh(written=bool(commands), skipped=skipped, hooked=hooked.set, hooks=hooked.why)
    before = git(root, "rev-parse", "HEAD")
    if respelled and changed:
        subject = (f"Take the adoption label off {', '.join(respelled)} and re-derive {name}'s factory "
                   f"projections for slipwai {VERSION}")
    elif respelled:
        subject = f"Take the adoption label off {', '.join(respelled)} for slipwai {VERSION}"
    elif changed:
        subject = f"Re-derive {name}'s factory projections for slipwai {VERSION}"
    else:
        subject = f"Move {name}'s records to where slipwai {VERSION} keeps them"
    if relocated and (respelled or changed):
        subject += ", and move its records to where that version keeps them"
    committed = subprocess.run(
        ["git", *NO_MAINTENANCE, "commit", "--quiet", "-m", subject],
        cwd=root, text=True, capture_output=True, check=False,
    )
    if committed.returncode != 0:
        reason = committed.stderr.strip() or committed.stdout.strip() or "the commit was refused"
        return Refresh(written=True, refused=reason, uncommitted=staged, skipped=skipped,
                       hooked=hooked.set, hooks=hooked.why, relocated=relocated)
    if set_undo:
        # No merge populated ORIG_HEAD. Set it only once the commit exists: a refused commit moved nothing, and a
        # no-op migration must not overwrite the undo point left by the previous real migration.
        git(root, "update-ref", "ORIG_HEAD", before)
    return Refresh(changed, respelled, True, skipped=skipped, hooked=hooked.set, hooks=hooked.why,
                   relocated=relocated)


def commit_says(refresh: Refresh, *, merge: bool = False) -> str:
    """What the commit after the merge, or on its own, changed: the label off the named files, projections as
    projections, or both — never one described as the other."""
    said = [f"moved {', '.join(refresh.relocated)}"] if refresh.relocated else []
    if refresh.respelled:
        said.append(f"took the adoption label off {', '.join(refresh.respelled)}")
    if refresh.changed:
        after = (" from the extension, command and agent sources this brought in — the merge could not update "
                 "local copies") if merge else ""
        verb = ("re-derived" if refresh.respelled else "re-derives") if merge else "refreshed"
        said.append(f"{verb} {len(refresh.changed)} factory-owned projection(s){after}")
    return " and ".join(said)


def report(done: Migration) -> str:
    """What happened and what to do next, for the person who ran it."""
    text = report_of(done)
    left = [f"Left alone: {page}." for page in done.refresh.skipped]
    return "\n".join([text, *left]) if left and not done.conflicts else text


def report_of(done: Migration) -> str:
    name = done.offered.name
    was = f"from {done.was} " if done.was and done.was != VERSION else ""
    if done.changed is None:
        if done.refresh.failed:
            return (
                f"nothing generated to migrate, but factory-owned projections could not be refreshed: "
                f"{done.refresh.failed}. Run `make agents`." + not_committed(done.refresh)
            )
        if done.refresh.refused:
            return (
                f"nothing generated to migrate, but the commit was refused: {done.refresh.refused}."
                + not_committed(done.refresh)
            )
        if done.refresh.changed or done.refresh.respelled or done.refresh.relocated:
            return (
                f"nothing generated to migrate: {name} already has everything slipwai {VERSION} generates "
                f"for its answers; one commit {commit_says(done.refresh)}. "
                "Nothing pushed; `git reset --hard ORIG_HEAD` undoes it."
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
            "until they are re-derived. And run `slipwai migrate` again once the conflict is committed: nothing is "
            "respelled over a merge in progress, so that run takes the adoption label off the files no merge reaches.",
            *(catch_up(done)),
        ])
    how = (
        "One commit, fast-forwarded — this project had no changes of its own since the last factory commit."
        if done.fast_forward
        else "One merge commit. The files this project had changed itself were kept; the rest are what the "
        "factory now generates for its answers."
    )
    lines = [f"migrated {name} {was}to slipwai {VERSION}: {done.changed}", how]
    if not (done.refresh.failed or done.refresh.refused) and (
        done.refresh.changed or done.refresh.respelled or done.refresh.relocated
    ):
        lines.append(f"A second commit {commit_says(done.refresh, merge=True)}.")
    elif not (done.refresh.failed or done.refresh.refused) and done.refresh.written:
        lines.append(
            "The extension and harness projections were re-derived from the sources this brought in; they are "
            "ignored by Git or already current, so there is nothing to commit."
        )
    lines += githooks.note(done.refresh.hooked, done.refresh.hooks)
    lines.append("Nothing pushed; `git reset --hard ORIG_HEAD` undoes all of it.")
    if done.unwritten is None:
        lines.append(
            f"What the versions crossed ask of code already here — which no merge can do — is written to "
            f"{NOTES}, git-ignored and disposable. `.slipwai/intake-cleanup.json` proposes where loose "
            f"requirements could be recorded; nothing in it is moved until `/catch-up` confirms a row."
        )
    if done.refresh.failed:
        lines += [
            "",
            f"The factory-owned projections could not be re-derived: {done.refresh.failed}",
            "The merge is committed and unaffected. Run `make agents` and commit the result, or "
            "the extension or agent projection gate will fail against the sources this migration moved."
            + not_committed(done.refresh),
        ]
    if done.refresh.refused:
        lines += [
            "",
            f"The commit after the merge was refused: {done.refresh.refused}",
            "The merge is committed and unaffected." + not_committed(done.refresh),
        ]
    lines += catch_up(done, "Next")
    return "\n".join(lines)


def not_committed(refresh: Refresh) -> str:
    """What is left over when the commit after the merge was not made, and what to do about it."""
    if not refresh.uncommitted:
        return ""
    files = ", ".join(refresh.uncommitted)
    if refresh.refused:
        return (f" That commit was not made: {files} stay staged. Deal with what refused it and run `git commit`, "
                "or `git reset --hard HEAD` to drop them.")
    return (f" The adoption label came off {files} in the working tree, but that is not committed: commit it with "
            "the result, or `git checkout HEAD -- <file>` to put it back.")


def catch_up(done: Migration, then: str = "Then") -> list[str]:
    """The report's last step: `/catch-up` over the notes, or — the one case the notes are not there — why
    not and where to read them instead. Never a bare `make verify`, which reads as nothing being owed."""
    # `make crossing` first: what it asks about is state the merge could not carry — a second feature with
    # no chart, a slice still `modelled` that is in trunk, a log ref nothing has pushed — and none of it
    # fails a gate, which is exactly why it needs saying once while somebody is looking.
    owed = ["Then: make crossing, for what this crossing could not carry."]
    if done.unwritten is None:
        return [*owed,
                f"Then: /catch-up, which reads {NOTES} — what these versions ask of code already here — and "
                "runs make verify against it."]
    return [
        f"The catch-up notes could not be written to {NOTES}: {done.unwritten}",
        f"Read the factory's CHANGELOG.md from {done.was or 'its first entry'} to {VERSION} instead — what those "
        f"versions ask of code already here, which no merge can do.",
        *owed,
        f"{then}: make verify",
    ]

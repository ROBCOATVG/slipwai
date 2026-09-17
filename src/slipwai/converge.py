"""`slipwai converge`: the end of an adoption — every row of the map reads *as generated*, so the delivery material
moves from `layout.delivery` to the root as one merge, and the repository is a generated one from then on.

Brownfield adoption (experimental as `AGENTS.md` defines the word) starts wherever the repository is and
climbs one rung per slice. This is the verb for the day nothing on the map differs from a generated project. It
is `migrate` with the layout moved: the replay is assembled for the root, the base's files are taken out from
under the delivery directory, and the merge carries the move; then what the factory does not list in `.written`
but wrote or kept under the delivery directory — the survey, the ledgers, the ratchet baseline, a person's ADRs —
is moved with `git mv`, the marked blocks in `AGENTS.md` and `.gitignore` are respelled for the root, and the
harness projections are re-derived. `origin: adopted` stays, with the survey and the map, as history.

`--check` says whether the repository is ready and why not: a row below its target, a row the tree contradicts
(`check-convergence`), a file at the root the move would write over — a `Makefile` of the repository's own is the
usual one — an unclean tree. Nothing is moved on a refusal, and the refusal is the report.
"""
from __future__ import annotations

import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from .assets import VERSION
from .errors import GenerationError
from .layout import AT_ROOT, Layout, layout_of
from .manifest import apps_from_manifest, read_manifest
from .migrate import Refresh, merge_offered, refresh
from .origin import Adoption, adoption_of
from .project.adopted import OWN, WRITTEN, agents_block, gitignore_block
from .project.gitignore import build_artifacts
from .replay import Replay, git, replay
from .scaffold import NO_MAINTENANCE, project_files

AGENTS_MARKERS = ("<!-- extension:delivery:begin -->", "<!-- extension:delivery:end -->")
GITIGNORE_MARKERS = ("# slipwai:delivery:begin", "# slipwai:delivery:end")
MAKEFILE_MARKER = "# slipwai:delivery:begin"


@dataclass(frozen=True)
class Check:
    """Whether the repository is ready to converge, and everything that says it is not."""

    name: str
    layout: Layout
    below: list[dict] = field(default_factory=list)
    gate: str | None = None
    clashes: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)

    @property
    def ready(self) -> bool:
        return not (self.below or self.gate or self.clashes or self.reasons)


@dataclass(frozen=True)
class Converged:
    check: Check
    offered: Replay
    conflicts: tuple[str, ...]
    changed: str | None
    moved: tuple[str, ...] = ()
    refresh: Refresh = Refresh()
    # What is still under the delivery directory afterwards: untracked or ignored files Git never carried.
    left: tuple[str, ...] = ()


def check(root: Path) -> Check:
    """Read, never write: the rows, the gate, the tree and the root, against what the move needs."""
    document = read_manifest(root, verb="converge")
    adoption = adoption_of(document)
    if adoption is None:
        raise GenerationError("this project was generated, not adopted: there is nothing to converge")
    layout = layout_of(document)
    name = str(document["name"])
    reasons: list[str] = []
    if adoption.converged:
        reasons.append(f"already converged with slipwai {adoption.converged.get('with')}; nothing left to move")
    if not layout.moved:
        reasons.append("the delivery material is already at the root (`layout.delivery` is `.`)")
    if not git(root, "rev-parse", "--verify", "--quiet", "HEAD", check=False):
        reasons.append("no Git history to merge into")
    elif git(root, "status", "--porcelain"):
        reasons.append("the tree has uncommitted changes; commit or stash them so that the move is one merge and "
                       "`git reset --hard ORIG_HEAD` undoes exactly that")
    below = [row for row in adoption.convergence if row.get("rung") != row.get("target")]
    if not adoption.convergence:
        reasons.append("no convergence map is recorded; `slipwai adopt --refresh` writes it")
    gate = None
    checker = root / layout.under("scripts/check-convergence.py")
    if checker.is_file() and layout.moved:
        result = subprocess.run(["python3", str(checker)], cwd=root, text=True, capture_output=True, check=False)
        if result.returncode != 0:
            gate = (result.stderr.strip() or result.stdout.strip())
    return Check(name, layout, below, gate, clashes(root, document, adoption, layout) if layout.moved else [], reasons)


def clashes(root: Path, document: dict, adoption: Adoption, layout: Layout) -> list[str]:
    """Every path at the root the move would write over: what the root layout generates and the repository already
    has, and what sits under the delivery directory whose place at the root is taken. The `Makefile` `adopt` wrote
    is the factory's and is replaced; a `Makefile` of the repository's own is a clash, and the usual one."""
    apps = apps_from_manifest(document)
    generated = project_files(str(document["name"]), document["profile"], document["target"], apps, AT_ROOT, adoption)
    listing = root / layout.under(WRITTEN)
    already = set(listing.read_text().split()) if listing.is_file() else set()
    found = []
    for path in sorted(generated):
        # The factory's own files at the root — the manifest, the Spec Kit presets, the CI gate — are replaced.
        if path in OWN or path in already or path.startswith(f"{layout.delivery}/"):
            continue
        target = root / path
        adopt_wrote = path == "Makefile" and target.read_text(errors="replace").startswith(MAKEFILE_MARKER)
        if target.exists() and not adopt_wrote:
            found.append(path)
    for path in git(root, "ls-files", "--", layout.delivery).splitlines():
        destination = path[len(layout.delivery) + 1:]
        if destination and destination not in generated and (root / destination).exists():
            found.append(destination)
    return sorted(dict.fromkeys(found))


def converge(root: Path) -> Converged:
    """Move the delivery material to the root as one merge, once every row reads *as generated*."""
    readiness = check(root)
    if not readiness.ready:
        raise GenerationError(check_report(readiness))
    document = read_manifest(root, verb="converge")
    layout = readiness.layout
    converged = {"with": VERSION, "from": layout.delivery}
    message = f"Converge {readiness.name}: the delivery material moves from {layout.delivery}/ to the root"
    with tempfile.TemporaryDirectory(prefix=f".{readiness.name}-converge-", dir=root.parent) as staging:
        # Parented on HEAD rather than on the last factory commit: everything under `.written` is the factory's,
        # `adopt --refresh`'s redrawn pages included, and is replaced whole — so the move is one fast-forward rather
        # than a modify/delete conflict over every page the factory itself redrew. A hand edit inside a factory
        # file goes with it, and the report says where to look for one.
        offered = replay(
            root, Path(staging) / "offered", base="HEAD", converge_to=AT_ROOT, converged=converged, message=message
        )
        git(root, *NO_MAINTENANCE, "fetch", "--quiet", str(offered.destination), "main")
    stat, conflicts, _ = merge_offered(root, offered, message)
    if conflicts:
        return Converged(readiness, offered, conflicts, stat)
    moved, left = finish(root, document, layout)
    return Converged(readiness, offered, (), stat, moved, refresh(root, readiness.name, AT_ROOT), left)


def finish(root: Path, document: dict, layout: Layout) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """After the merge: move what is still under the delivery directory to the root — the factory did not list it
    in `.written`, so the merge did not carry it — respell the marked blocks, and commit the lot as one commit of
    the repository's own, never the factory's, so the next replay measures from the factory's tree."""
    moved = []
    for path in git(root, "ls-files", "--", layout.delivery).splitlines():
        destination = path[len(layout.delivery) + 1:]
        if not destination:
            continue
        (root / destination).parent.mkdir(parents=True, exist_ok=True)
        git(root, "mv", "-k", path, destination)
        moved.append(f"{path} -> {destination}")
    # `git mv` leaves the directories it emptied; what is not empty afterwards is untracked or ignored, and stays.
    delivery = root / layout.delivery
    for directory in sorted((p for p in delivery.rglob("*") if p.is_dir()), key=lambda p: -len(p.parts)):
        if not any(directory.iterdir()):
            directory.rmdir()
    if delivery.is_dir() and not any(delivery.iterdir()):
        delivery.rmdir()
    left = tuple(
        sorted(p.relative_to(root).as_posix() for p in delivery.rglob("*") if p.is_file())
    ) if delivery.is_dir() else ()
    apps = apps_from_manifest(document)
    respell(root / "AGENTS.md", AGENTS_MARKERS, agents_block(AT_ROOT, VERSION).strip("\n"))
    ignored = build_artifacts(document["profile"] == "event-modelling", apps, document["target"])
    respell(root / ".gitignore", GITIGNORE_MARKERS, gitignore_block(ignored, AT_ROOT).strip("\n"))
    git(root, "add", "-A")
    if git(root, "diff", "--cached", "--name-only"):
        subprocess.run(
            ["git", *NO_MAINTENANCE, *identity(root), "commit", "--quiet", "-m",
             f"Move what the merge did not carry from {layout.delivery}/ to the root, and respell the marked blocks"],
            cwd=root, check=True, text=True, capture_output=True,
        )
    return tuple(moved), left


def identity(root: Path) -> list[str]:
    """The repository's own identity for the finishing commit, or a named fallback where none is configured — a
    CI runner, say — so the commit is never refused and never the factory's, which the next replay measures from.

    Git refuses the commit unless it has *both* a name and an email, so both have to be configured before the
    fallback stands aside. Checking only the email let a checkout with one and not the other — a machine whose
    global config sets `user.email` alone — through to a commit that exits 128.
    """
    if all(git(root, "config", key, check=False) for key in ("user.name", "user.email")):
        return []
    return ["-c", "user.name=slipwai converge", "-c", "user.email=converge@local"]


def respell(path: Path, markers: tuple[str, str], block: str) -> None:
    """Replace the marked block in a file the repository owns with its root-layout spelling; leave the rest alone."""
    if not path.is_file():
        return
    text = path.read_text()
    begin, end = (re.escape(marker) for marker in markers)
    respelled, count = re.subn(rf"{begin}.*?{end}[^\n]*", lambda _match: block, text, count=1, flags=re.S)
    if count:
        path.write_text(respelled)


def check_report(readiness: Check) -> str:
    lines = [f"converge --check for {readiness.name}: " + ("ready" if readiness.ready else "not yet")]
    for reason in readiness.reasons:
        lines.append(f"  - {reason}")
    for row in readiness.below:
        lines.append(
            f"  - {row.get('axis')} stands at `{row.get('rung')}`, target `{row.get('target')}` "
            f"({row.get('provenance')}" + (f"; planned as {row['planned']}" if row.get("planned") else "") + ")"
        )
    if readiness.gate:
        lines.append("  - the tree contradicts the map — check-convergence says:")
        lines += [f"      {line}" for line in readiness.gate.splitlines()]
    for path in readiness.clashes:
        lines.append(f"  - `{path}` exists at the root and the move would write over it")
    if readiness.clashes:
        lines.append("    A `Makefile` of the repository's own is the usual one: the root layout's Makefile is the "
                     "factory's, so move your targets into a file of your own that includes it, or keep the delivery "
                     "directory.")
    if readiness.ready:
        lines.append(f"  every row is at its target and the tree agrees; `slipwai converge` moves "
                     f"{readiness.layout.delivery}/ to the root as one merge")
    return "\n".join(lines)


def report(done: Converged) -> str:
    name = done.check.name
    if done.conflicts:
        files = "\n".join(f"  {path}" for path in done.conflicts)
        return "\n".join([
            f"converging {name} stopped at {len(done.conflicts)} conflict(s) — each a file under "
            f"{done.check.layout.delivery}/ this repository changed and the factory now removes:",
            files, "",
            "Resolve each (`git checkout --theirs -- <file>` takes the factory's side, which is the removal) and "
            "`git commit`, then run `slipwai converge` again to finish the move — or `git merge --abort`.",
        ])
    lines = [
        f"converged {name} with slipwai {VERSION}: {done.changed or 'the material moved'}",
        f"One merge commit moves the factory's files from {done.check.layout.delivery}/ to the root; a second moves "
        f"{len(done.moved)} file(s) the factory does not list — the survey, the ledgers, the baseline, your ADRs — "
        "and respells the marked blocks in AGENTS.md and .gitignore.",
    ]
    if done.refresh.changed:
        lines.append(f"A third re-derives {len(done.refresh.changed)} factory projection(s) for the new paths.")
    if done.refresh.failed:
        lines.append(f"The factory projections could not be re-derived: {done.refresh.failed}; run `make agents`.")
    if done.left:
        lines.append(
            f"Still under {done.check.layout.delivery}/, because Git never carried them (untracked or ignored): "
            + ", ".join(done.left) + " — move or delete them by hand."
        )
    lines += [
        "project.json keeps `origin: adopted` and the map as history and records `converged`; from here on this is a "
        "generated project — `slipwai migrate` brings it forward like any other.",
        f"Every file the factory listed in {done.check.layout.delivery}/.written was replaced whole; a hand edit "
        "inside one of them went with it, and `git diff ORIG_HEAD HEAD~1 -- "
        f"{done.check.layout.delivery}/` shows what.",
        "Nothing pushed. Then: make verify.",
    ]
    return "\n".join(lines)

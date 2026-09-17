"""`slipwai replay`: this factory's output for a project's recorded answers, as a commit that project can merge.

A generated project owns every one of its files, and the factory never reaches in to overwrite one. What it
can do is *offer*: emit, from the answers `project.json` records, what this version of the factory would
generate for them — into an empty directory beside the project, as a Git repository whose one commit sits on
the commit the project was scaffolded as. Everything a three-way merge needs is then in place. The project's
root commit is the base, the project's `main` is one side, the replay is the other, and `git merge` says
which files the factory alone changed (taken silently), which the project alone changed (kept silently), and
which both changed (a conflict, decided by the project). That is the upgrade path: a proposed merge, never a
mutation, and `docs/upgrading.md` is the recipe around it.

Two things make the replay a fair "theirs" rather than a fresh project that happens to share a name. The
manifest's provenance is carried through — `generatedWith` stays what it was, `updatedWith` becomes this
version — so the merge moves exactly the field that changed. And the features the project has since taken
away with `./init` stay away: what is on the project's disk decides, as it does for `add-service`, so a
project that dropped Keycloak is not offered it back.

The base is the newest commit in the project's history that the factory itself made: the scaffold the first
time, and after that the last replay the project merged — so a second upgrade measures from the first, not
from the beginning, and a field both moved (`updatedWith`, the README's version line) merges rather than
conflicts. A history that has lost that authorship falls back to its root commit, and `--base` names another
parent outright. A project that is not a Git repository gets the tree and no parentage — a diff by hand is
still a diff the project could not have had.
"""
from __future__ import annotations

import dataclasses
import json
import shlex
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .assets import PRUNER, STYLE_CHECKER, VERSION
from .errors import GenerationError
from .layout import Layout, layout_of
from .manifest import apps_from_manifest, check_known, read_manifest, wrote_here
from .origin import adoption_of
from .project.adopted import WRITTEN
from .project.design_page import DESIGN, existing_design_page
from .scaffold import FACTORY_EMAIL, FACTORY_IDENTITY, NO_MAINTENANCE, project_files, write_project
from .services import App, web_apps

STARTER_STYLES = ("src/styles/tokens.css", "src/styles/base.css")
STARTER_IMPORTS = ("import './styles/tokens.css';\n", "import './styles/base.css';\n")


@dataclass(frozen=True)
class Replay:
    """What `replay` wrote, for the report and for a caller that merges it."""

    project: Path
    destination: Path
    name: str
    files: int
    generated_with: str | None
    # The commit the replay sits on: the newest the factory made, or `--base`; `None` where there is no history.
    base: str | None
    # Whether that base is one the factory made, rather than the root commit fallen back to or `--base`.
    base_is_factory: bool = False


def replay(
    root: Path, into: Path | None = None, base: str | None = None, converge_to: Layout | None = None,
    converged: dict | None = None, message: str | None = None,
) -> Replay:
    """Write this factory's output for the project at `root` into `into`, parented on `base`.

    `converge_to` assembles the output for another layout than the one `project.json` records — how `slipwai
    converge` moves an adopted repository's material to the root: the base's files are taken out from where the
    record says they are, and this factory's are written where the new layout puts them — and `converged` is the
    record of that, carried into the manifest."""
    document = read_manifest(root, verb="replay")
    apps = apps_from_manifest(document)
    check_known(apps)
    layout = layout_of(document)
    adoption = adoption_of(document)
    if converged is not None and adoption is not None:
        adoption = dataclasses.replace(adoption, converged=converged)
    target = converge_to or layout
    name = document["name"]
    destination = (root.parent / f"{name}-at-{VERSION}") if into is None else into
    destination = destination.resolve()
    if destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
        raise GenerationError(
            f"refusing to write into {destination}, which is not an empty directory: a replay is written "
            "into an empty one so that everything in it is the factory's — name another with --into"
        )
    if destination == root.resolve() or root.resolve() in destination.parents:
        raise GenerationError(f"--into {destination} is inside the project being replayed; name a directory beside it")
    parent, from_factory = base_commit(root, base)

    # What this project actually has, read off its disk rather than off its recorded answers.
    try:
        services = PRUNER.project_services(root)
    except ValueError as error:
        raise GenerationError(f"project.json cannot be read by this factory's pruner: {error}") from error
    installed = PRUNER.features_installed(root, services)
    present = PRUNER.features_present(root, services)

    files = project_files(name, document["profile"], document["target"], apps, target, adoption)
    preserve_project_styles(root, parent, apps, files, target)
    manifest = json.loads(files["project.json"])
    manifest["generator"] = wrote_here(document.get("generator"))
    files["project.json"] = json.dumps(manifest, indent=2) + "\n"

    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        destination.rmdir()  # empty, checked above: the staging directory takes its place whole
    with tempfile.TemporaryDirectory(prefix=f".{destination.name}-", dir=destination.parent) as staging:
        staged = Path(staging)
        if adoption is not None and parent is not None:
            inherit(root, parent, staged, layout)
        write_project(
            staged, name, document["profile"], document["target"], apps,
            files=files, keep=installed, settled=installed - present, layout=target, adoption=adoption,
        )
        if parent is not None:
            graft(staged, root, parent, message or f"Replay {name} with slipwai {VERSION}")
        staged.rename(destination)
    return Replay(
        root, destination, name, len(files), manifest["generator"]["generatedWith"], parent, from_factory
    )


def unchanged_from(root: Path, parent: str, relative: str) -> bool:
    """Whether the project left one path exactly as the replay base recorded it."""
    compared = subprocess.run(
        ["git", "diff", "--quiet", parent, "--", relative],
        cwd=root,
        check=False,
    )
    return compared.returncode == 0


def preserve_project_styles(
    root: Path, parent: str | None, apps: list[App], files: dict[str, str], layout: Layout
) -> None:
    """Keep an imported project design system without replaying the generated baseline beside it.

    An imported non-starter stylesheet with root custom properties is the project's declaration that it
    has replaced the baseline. Starter files unchanged from the merge base are still factory-owned and can
    be omitted from the offered tree, which makes the three-way merge delete them. A changed starter file
    is project work: refusing names the decision instead of silently deleting it.
    """
    if parent is None:
        return
    token_paths: list[str] = []
    styled_apps: list[str] = []
    for web in web_apps(apps):
        app = root / web.path
        starter = {(app / relative).resolve() for relative in STARTER_STYLES}
        project_tokens = [
            path for path in STYLE_CHECKER.token_files(app) if path not in starter
        ]
        if not project_tokens:
            continue
        changed = [
            f"{web.path}/{relative}"
            for relative in STARTER_STYLES
            if (root / web.path / relative).exists()
            and not unchanged_from(root, parent, f"{web.path}/{relative}")
        ]
        if changed:
            listed = ", ".join(changed)
            tokens = ", ".join(path.relative_to(root).as_posix() for path in project_tokens)
            raise GenerationError(
                f"{web.path} imports its own root tokens from {tokens}, but also changed the generated "
                f"baseline at {listed}. Refusing to choose which design system owns the bundle: remove the "
                "obsolete starter files and imports, or consolidate the tokens before replaying."
            )
        for relative in STARTER_STYLES:
            files.pop(f"{web.path}/{relative}", None)
        entry = f"{web.path}/src/main.tsx"
        for imported in STARTER_IMPORTS:
            files[entry] = files[entry].replace(imported, "")
        token_paths.extend(path.relative_to(root).as_posix() for path in project_tokens)
        styled_apps.append(web.path)
    if token_paths:
        design = existing_design_page(apps, token_paths, styled_apps)
        files[layout.place(DESIGN)] = layout.repoint(DESIGN, design)


def base_commit(root: Path, base: str | None) -> tuple[str | None, bool]:
    """The commit the replay sits on, and whether it is one the factory made.

    `base` resolved in the project when given; else the newest commit behind `HEAD` the factory authored —
    the scaffold, or the last replay merged; else, in a history that has lost that authorship, the one root
    commit."""
    if not git(root, "rev-parse", "--is-inside-work-tree", check=False).startswith("true"):
        if base is not None:
            raise GenerationError(f"--base {base} names a commit, and {root} is not a Git repository")
        return None, False
    if base is not None:
        resolved = git(root, "rev-parse", "--verify", "--quiet", f"{base}^{{commit}}", check=False)
        if not resolved:
            raise GenerationError(f"--base {base} is not a commit in {root}")
        return resolved, False
    if not git(root, "rev-parse", "--verify", "--quiet", "HEAD", check=False):
        return None, False  # a repository with no commits yet: nothing to sit on
    made_here = git(root, "rev-list", "-1", f"--author={FACTORY_EMAIL}", "HEAD")
    if made_here:
        return made_here, True
    roots = git(root, "rev-list", "--max-parents=0", "HEAD").split()
    if len(roots) != 1:
        raise GenerationError(
            f"no commit in this project's history is the factory's, and it has {len(roots)} root commits, so "
            "the one it was scaffolded as cannot be told apart; name it with --base"
        )
    return roots[0], False


def inherit(project: Path, parent: str, staged: Path, layout: Layout) -> None:
    """For an adopted repository: start the replay from the tree the factory last committed, minus what it
    wrote then, so that the factory's files are the whole of the difference.

    A generated project's base commit is the factory's tree and nothing else, so a replay that writes only
    the factory's files is a complete tree. An adopted repository's base is the factory's files *inside*
    somebody else's tree — and a replay of the factory's files alone would read, against that base, as the
    deletion of everything the repository owns. So the parent's tree is unpacked first, the files listed in
    `<delivery>/.written` at that commit are taken out (an older factory's, replaced whole by this one's), and
    the factory writes over the rest.
    """
    archive = subprocess.run(["git", "archive", "--format=tar", parent], cwd=project, capture_output=True, check=True)
    staged.mkdir(parents=True, exist_ok=True)
    subprocess.run(["tar", "-x", "-C", str(staged)], input=archive.stdout, check=True)
    listed = git(project, "show", f"{parent}:{layout.under(WRITTEN)}", check=False)
    for relative in listed.splitlines():
        path = staged / relative.strip()
        if relative.strip() and path.is_file():
            path.unlink()


def graft(replayed: Path, project: Path, parent: str, message: str) -> None:
    """Re-parent the replay's one commit onto `parent`, a commit in the project, keeping its tree.

    The tree the factory just wrote is what matters; the commit around it exists to give a merge a base.
    Fetching the parent from the project and committing the same tree over it is the whole trick. The fetch
    carries the same no-maintenance flags as the commit: `git fetch` also launches a detached
    `git maintenance run --auto`, whose lock lands in `.git/objects/` after this returns — and a caller that
    deletes the directory next (`migrate`, every test) finds it not empty.
    """
    git(replayed, *NO_MAINTENANCE, "fetch", "--quiet", str(project), parent)
    git(replayed, "reset", "--quiet", "--soft", "FETCH_HEAD")
    subprocess.run(
        ["git", *NO_MAINTENANCE, "commit", "--quiet", "--allow-empty", "-m", message],
        cwd=replayed, check=True, env=FACTORY_IDENTITY,
    )


def git(cwd: Path, *arguments: str, check: bool = True) -> str:
    """`git` in `cwd`, its standard output stripped; empty rather than raised when `check` is off."""
    result = subprocess.run(["git", *arguments], cwd=cwd, text=True, capture_output=True, check=False)
    if check and result.returncode != 0:
        raise GenerationError(f"git {arguments[0]} failed in {cwd}: {result.stderr.strip()}")
    return result.stdout.strip() if result.returncode == 0 else ""


def report(done: Replay) -> str:
    """What was written and how the project takes it, for the person who ran it."""
    where = shlex.quote(str(done.destination))
    origin = (
        f"generated with {done.generated_with}"
        if done.generated_with
        else "generated before the factory recorded its version"
    )
    lines = [
        f"replayed {done.name} with slipwai {VERSION} into {done.destination}: {done.files} files, {origin}, "
        f"project.json now says updatedWith {VERSION}",
        f"Nothing in {done.project} was touched.",
    ]
    if done.base is None:
        lines += [
            "",
            f"{done.project} is not a Git repository with a commit to sit on, so the replay is a tree and not a "
            "merge: compare the two by hand —",
            f"  diff -r --exclude=.git {shlex.quote(str(done.project))} {where}",
        ]
    else:
        what = (
            "the newest commit in this project's history the factory made, so the merge measures from there"
            if done.base_is_factory
            else "the commit named as its base"
        )
        lines += [
            f"Its one commit sits on {done.base[:12]}, {what}. To offer it to the project:",
            "",
            f"  git fetch {where} main",
            "  git merge FETCH_HEAD",
            "",
            "A file only the factory changed since then is taken; a file only this project changed is kept; a "
            "file both changed merges where the hunks differ and conflicts where they do not — the project "
            "decides each one. `git merge --abort` walks away from all of it. Then: make verify.",
        ]
    lines.append("docs/upgrading.md in the factory has the recipe and what to expect of each part of the tree.")
    return "\n".join(lines)

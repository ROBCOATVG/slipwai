"""The `frontends` check: every browser app a family ships, read the way the pipeline reads it, then generated.

A frontend is a tree the keel copies by name and a `frontends` entry the keel and a project's pruner read as data
(`docs/frontend-protocol.md`). The loader has already refused an answer that is not a record, a root outside
`assets/frontends/<name>`, a name in the answer and not the block, and a browser app with no npm workspace or no
`shared_code`. What it cannot see is what is *inside* the tree, and that is what a project would find missing:
a variant the pipeline copies by name, a feature's directory, a file the entry says carries a marked region, a
design path, a lock for one of the dependency sets the entry implies, or a Biome pin disagreeing with the family's.

**Then a project, because nothing short of one says a frontend works.** Each frontend is generated at the
richest profile beside a backend: the family's own where it has one, and where it ships browser apps alone, the
first backend loaded beside it — which is what a publisher's `beside`, or a checkout holding a language next to
the package, is for. With no backend anywhere there is nothing to generate one with, and the check says so
rather than passing.
"""
from __future__ import annotations

import itertools
import json
from pathlib import Path

from ..catalog import CATALOG
from ..npm_workspace import BrowserApp, frontends
from ..project.biome import biome_version
from ..project.frontend import web_lock_features, web_lock_suffix
from ..registry import NPM_WORKSPACE, Registry
from ..services import web_features
from . import child
from .generation import PROJECT, REFUSED, richest

#: The trees `project/frontend.web_files` and `api_client_files` copy by name, each a directory.
TREES = ("app", "app-flags-local", "app-flags-target", "app-route-client", "app-route-plain", "api-client")
#: Why the check did not run, for a family that ships none and for one with nothing to generate beside.
SHIPS_NONE = "does not apply: it ships no browser app"
NOTHING_BESIDE = ("{family} ships browser apps and no backend, and none is loaded beside it to generate one with: "
                  "install a language beside it, or name one in the workflow's `beside`")


def shipped(families: list[str]) -> dict[str, BrowserApp]:
    """The browser apps these families answer, by name."""
    return {name: app for name, app in frontends().items() if app.family in families}


def tree_findings(app: BrowserApp) -> list[str]:
    """What the tree lacks that the pipeline reads, one line each."""
    entry = CATALOG["frontends"].get(app.name, {})
    said = f"frontend {app.name}"
    findings = [f"{said} has no {tree}/, which the pipeline copies by name"
                for tree in TREES if not (app.root / tree).is_dir()]
    manifest = app.root / "app/package.json"
    try:
        pinned = json.loads(manifest.read_text(encoding="utf-8")).get("devDependencies", {}).get("@biomejs/biome")
    except (OSError, ValueError):
        pinned = None
    if not pinned:
        findings.append(f"{said}'s app/package.json pins no @biomejs/biome, and the workspace lints with one")
    for marked in entry.get("marked", ()):
        if not (app.root / "app" / marked).is_file():
            findings.append(f"{said} lists {marked} as marked, and app/ has no such file")
    for feature, row in web_features(app.name).items():
        files = app.root / row["files"]
        if not files.is_dir():
            findings.append(f"{said}'s feature {feature} names {row['files']}/, which is not there")
            continue
        for owned in row.get("owned", ()):
            if not (files / owned).exists():
                findings.append(f"{said}'s feature {feature} owns {owned}, which its files do not hold, so pruning "
                                f"the feature would leave behind whatever does")
    design = entry.get("design", {})
    for key in ("tokens", "base", "shell", "entry"):
        if key in design and not (app.root / "app" / design[key]).is_file():
            findings.append(f"{said}'s design names its {key} as {design[key]}, which app/ does not hold")
    if "route" in design and not any((app.root / tree / design["route"]).is_file()
                                     for tree in ("app-route-client", "app-route-plain")):
        findings.append(f"{said}'s design names its route as {design['route']}, which neither route tree holds")
    features = web_lock_features(app.name)
    for size in range(len(features) + 1):
        for chosen in itertools.combinations(features, size):
            lock = f"locks/frontend-only{web_lock_suffix(set(chosen), app.name)}.json"
            if not (app.root / lock).is_file():
                findings.append(f"{said} has no {lock}, the workspace lock of a project with "
                                f"{', '.join(chosen) or 'none of its features'} and no npm service")
    return findings


def pin_findings(loaded: Registry, family: str) -> list[str]:
    """The family's Biome and every browser app it ships pin one version, or a project lints with whichever won."""
    if NPM_WORKSPACE not in loaded.families[family].answers:
        return []
    try:
        biome_version(family=family)
    except (AssertionError, KeyError, OSError, ValueError) as error:
        return [f"family {family}: {error}"]
    return []


def backend_for(loaded: Registry, family: str) -> str | None:
    """The backend a frontend of `family` is generated beside: its own, or the first loaded outside every npm family
    but its own, which is the one generation would not refuse (`project/frontend.frontend_files`)."""
    own = next((key for key, backend in loaded.backends.items() if backend.family == family), None)
    if own is not None:
        return own
    npm = {name for name, one in loaded.families.items() if NPM_WORKSPACE in one.answers}
    return next((key for key, backend in loaded.backends.items() if backend.family not in npm), None)


def generated(output: Path, backend: str, name: str) -> str | None:
    """Generate a project with `name` beside `backend`; None where it was written, else the line generate ended on."""
    parent = output / name
    parent.mkdir(parents=True)
    done = child.run("slipwai", ["generate", PROJECT, "--profile", richest(), "--backend", backend,
                                 "--frontend", name, "--output", str(parent), "--skip-checks"])
    if done.returncode == 0 and (parent / PROJECT / "apps/web").is_dir():
        return None
    return REFUSED.sub("", done.last_line(), count=1) or f"exit {done.returncode}"


def frontend_findings(loaded: Registry, families: list[str], output: Path) -> tuple[list[str], str | None]:
    """The check's findings over every browser app `families` ship, and why it did not run where it did not."""
    apps = shipped(families)
    if not apps:
        return [], SHIPS_NONE
    findings: list[str] = []
    for family in dict.fromkeys(app.family for app in apps.values()):
        findings += pin_findings(loaded, family)
    for app in apps.values():
        findings += tree_findings(app)
    if findings:
        return findings, None
    for name, app in apps.items():
        backend = backend_for(loaded, app.family)
        if backend is None:
            return findings, NOTHING_BESIDE.format(family=app.family)
        said = generated(output, backend, name)
        if said is not None:
            findings.append(f"frontend {name} beside backend {backend} does not generate: {said}")
    return findings, None

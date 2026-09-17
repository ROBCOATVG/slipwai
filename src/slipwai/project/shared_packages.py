"""The npm workspace: `node_modules`, `packages/`, and what has to be true for either to work.

A generated project starts with an empty `packages/` and the documentation to fill it — `docs/architecture.md`
says what a shared package is in each language family. This module is the npm half of that promise, which is
the half with a build step: a workspace package emits declarations its consumers import, its `dist/` is not
committed, and so a fresh checkout has none. Four things have to hold, and they are spelled here together
because they are one decision:

- the root `package.json` lists `packages/*` as a workspace, so `npm --workspace packages/<name>` resolves;
- `node_modules/.package-lock.json` is a target that runs `npm ci`, and nothing else in the Makefile runs one;
- `make build-packages` builds every package under it that declares a build script;
- every target that compiles or runs this project's own *npm* code takes those targets as *prerequisites*.

The prerequisite is the part worth insisting on, and it is the same argument twice. A step remembered inside
each recipe is a step that will one day be forgotten in one of them, and that target then passes on a machine
where `dist/` happens to exist and fails in CI — which is exactly how the omission was found downstream. One
line naming every target that needs it cannot be forgotten in one of them. The install had the opposite
failure: it was remembered in *every* recipe, as a guard before every npm line, which is the same decision
copied sixteen times in a default project and re-copied with each recipe added. Make already knows how to run
a thing once per invocation and skip it when it is up to date; a file target says so in one place.

Only the npm family has this problem: a Go module under `packages/` is compiled on demand inside the
workspace, a Python package is installed in place, and the Java answer (an aggregator pom) is the day a
shared module arrives, which `SHARED_CODE` in `rules.py` says where a reader of the generated project will look for it.
"""
from __future__ import annotations

from ..catalog import CATALOG
from ..services import App, services_of, web_apps
from ..targets import managed

# Where shared code lives. `project.json` records it as `layout.packages` (`readme.metadata`), the root
# manifest globs it as a workspace, and `scripts/deploy.py` reads it back from the manifest rather than
# assuming it — one name, spelled once.
PACKAGES = "packages"
WORKSPACE = f"{PACKAGES}/*"

# npm's own marker for "this tree has been installed", and so the name of the target that installs it.
# The marker rather than the directory: a `node_modules` that exists and is empty is the normal state of a
# container that mounts a volume over it — which `make demo` does, to keep a Linux container's binaries out
# of the host's working tree — and of a host whose install was interrupted, and testing the directory skips
# precisely the install those cases need. npm writes `.package-lock.json` at the end of a successful install
# and nothing else does.
NODE_DEPS = "node_modules/.package-lock.json"


def npm_dependency(app: App) -> str:
    """The npm dependency target, for an application whose dependencies are npm's, and nothing otherwise.

    The caller puts it on the target's prerequisite line. Of the family, not of the framework that owns
    startup: what decides this is whether the application's dependencies come out of the root `package.json`.
    """
    return NODE_DEPS if app.language == "typescript" else ""


def node_workspace(apps: list[App]) -> bool:
    """Whether this project has an npm workspace at its root — a Node service, a browser app, or both.

    The same condition that decides whether a root `package.json` is written at all, so nothing here
    emits an npm command into a project that has no npm.
    """
    return bool(web_apps(apps)) or any(service.language == "typescript" for service in services_of(apps))


def consumers(apps: list[App], target: str) -> list[str]:
    """Every Make target that compiles or runs code a shared package could be part of, in Makefile order.

    Not every target: `migrate` runs the migration tool over SQL, `audit` reads the lockfile, and `mutation`
    asks for a decision the project has not made yet — none of them reads a package's build output. What is
    here is what would fail on a missing `dist/`, which is the test to apply when a target is added.

    And only npm-family work. A package under `packages/` with a `package.json` is importable by TypeScript
    and by nothing else, so a Go or Python service's own targets cannot need it built — while `typecheck`,
    `lint`, `test` and `adversarial` are aggregates that always include the npm half in a project that has
    an npm workspace at all. That distinction is not cosmetic: the integration job runs in that service's
    `ci_image` (`golang:1.26-bookworm`, `python:3.13-bookworm`, …), which ships no node, so an `npm ci`
    reached through a prerequisite there dies with `npm: command not found` before a test runs. Found in a
    generated Go-plus-React project, whose `integration` job failed on exactly that while `verify` — which
    does set Node up — passed.
    """
    services = services_of(apps)
    # A service whose own code an npm package can be part of. `web_apps` are all of them by construction.
    npm_services = [service for service in services if service.language == "typescript"]
    if len(services) > 1:
        integration = [f"test-integration-{service.name}" for service in npm_services]
    else:
        integration = ["test-integration"] if npm_services else []
    return [
        # `format` beside `lint`: it runs Biome out of the same `node_modules`, and a project with an npm
        # workspace always has a formatter to run.
        "typecheck", "lint", "format", "test", *integration, "adversarial",
        *(service.dev_target for service in npm_services if service.transport is not None),
        *(app.dev_target for app in web_apps(apps)),
        # The image build compiles the service the same way — for a Node service, with the very same
        # `npm --workspace ... run build` the gate runs. Named per service rather than as the `build`
        # aggregate they hang off: `build` already has those as prerequisites, and a second one appended
        # after them would be satisfied *after* the image it was meant to precede was already built.
        *(f"build-{service.name}" for service in npm_services if managed(CATALOG, target)),
    ]


def npm_workspace_targets(apps: list[App], target: str) -> str:
    """The two npm targets a project's own npm code hangs off, and the one line that makes them prerequisites.

    Nothing at all for a project with no npm workspace. For one that has an empty `packages/` — which is how
    every project starts — `build-packages` is a loop over a directory with nothing in it, and the first
    shared package somebody adds is built by the gate from the moment it exists.
    """
    if not node_workspace(apps):
        return ""
    return f"""
# The one place `npm ci` is spelled for the gate. A file target rather than a guard repeated inside every
# recipe: Make runs it at most once per invocation however many targets below need it, and not at all when
# the marker is newer than the manifests it was installed from — so a fresh clone installs once and a second
# `make verify` installs nothing. Touched afterwards because a filesystem with one-second timestamps can
# otherwise date the marker to the same second as the lockfile and install a second time on the next run.
{NODE_DEPS}: package.json package-lock.json
\tnpm ci
\t@touch {NODE_DEPS}

.PHONY: build-packages
build-packages: {NODE_DEPS} ## Build every shared package under {PACKAGES}/ that declares a build script
\t@for package in {PACKAGES}/*/; do \\
\t\t[ -f "$$package/package.json" ] || continue; \\
\t\tnpm --workspace "$${{package%/}}" run build --if-present; \\
\tdone

# Everything that compiles or runs this project's own npm code, in one line rather than a step remembered
# inside each recipe: the day it is forgotten in one, that target passes wherever `{PACKAGES}/*/dist` happens
# to exist already and fails on a fresh checkout. `--if-present` leaves a package that declares no build
# alone. The install comes with it, through `build-packages`. Its own npm code only: a package here is
# importable by TypeScript and by nothing else, and a native service's integration job runs inside an image
# that has no node in it.
{' '.join(consumers(apps, target))}: build-packages
"""



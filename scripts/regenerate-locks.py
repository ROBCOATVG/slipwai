#!/usr/bin/env python3
"""Rebuild every committed dependency lock, one per dependency set the axes can produce.

Covers npm lockfiles for the TypeScript backend and the frontend, `uv.lock` for the Python backend, and
`go.mod`/`go.sum` for the Go backend. All three ecosystems have the same rule: a manifest and its
checksums have to be produced together, because the toolchain refuses a lock that disagrees with its
manifest.

`npm ci` refuses to install from a lockfile that disagrees with its package.json, so a generated project
cannot be handed a lockfile that is patched after the fact — the manifest and the lock have to be produced
together. That is why a lock is committed per combination rather than per project, and why this script
exists: the combinations multiply with every dependency-adding option, and building them by hand is how one
of them silently stops matching.

    python3 scripts/regenerate-locks.py            # every lock
    python3 scripts/regenerate-locks.py --check    # fail if any is stale, changing nothing

Needs network access, because resolving a dependency tree is what npm does here. `--package-lock-only` means
nothing is downloaded into a node_modules anywhere; only the resolution is written down.
"""

from __future__ import annotations

import argparse
import itertools
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# Path setup has to happen first, hence the E402s.
from slipwai.assets import FRONTEND_ROOT  # noqa: E402
from slipwai.project.languages.go import go_module_variant  # noqa: E402
from slipwai.project.languages.python import (  # noqa: E402
    LOCK_FEATURES as PYTHON_LOCK_FEATURES,
)
from slipwai.project.languages.python import (  # noqa: E402
    lock_suffix as python_lock_suffix,
)
from slipwai.project.languages.python import python_pyproject  # noqa: E402
from slipwai.project.languages.typescript import (  # noqa: E402
    LOCK_FEATURES,
    WEB_LOCK_FEATURES,
    lock_suffix,
    service_package_json,
    web_lock_suffix,
    web_package_json,
)
from slipwai.scaffold import write_project  # noqa: E402
from slipwai.selection import Selection  # noqa: E402
from slipwai.services import default_apps  # noqa: E402

TYPESCRIPT_APP = ROOT / "assets/languages/typescript/app"
TYPESCRIPT_LOCKS = ROOT / "assets/languages/typescript/locks"
FRONTEND_APP = FRONTEND_ROOT / "react-vite/app"
# The typed client is a workspace package like the apps, so `npm ci` compares it against the lock like
# one. Its manifest is committed as it stands — the generator only renames it — so the resolution here is
# the resolution a project gets.
API_CLIENT_PACKAGE = FRONTEND_ROOT / "react-vite/api-client/package.json"

# The names the generator renames *from*. They appear in the committed locks as
# `node_modules/delivery-starter` links, and `frontend_files` rewrites them per project.
SERVICE_NAME = "delivery-starter"
WEB_NAME = "delivery-starter-web"
CLIENT_NAME = "delivery-starter-api-client"


def stage_api_client(directory: Path) -> None:
    """Put the typed client's manifest in the staging tree, so the lock holds its records too."""
    (directory / "packages/api-client").mkdir(parents=True)
    (directory / "packages/api-client/package.json").write_text(API_CLIENT_PACKAGE.read_text())


def subsets(features: tuple[str, ...]) -> list[set[str]]:
    """Every subset of a tuple of features, smallest first — one per dependency set they can produce."""
    return [
        set(chosen)
        for size in range(len(features) + 1)
        for chosen in itertools.combinations(features, size)
    ]


def selections() -> list[Selection]:
    """One Selection per service dependency set: every subset of the dependency-adding features.

    Built from `LOCK_FEATURES` rather than listed, so adding a dependency-adding option to the catalog adds
    its lockfiles here without this file changing.
    """
    combinations: list[Selection] = []
    for chosen in subsets(LOCK_FEATURES):
        # A Selection is normally built from axis answers; here only the features matter, so it is
        # constructed directly against the axes that own them.
        axes = {}
        if "postgres" in chosen:
            axes["event-store"] = "postgres"
        if "fastify" in chosen:
            axes["http"] = "fastify"
        combinations.append(Selection(axes))
    return combinations


def service_manifest(selection: Selection) -> str:
    return service_package_json((TYPESCRIPT_APP / "package.json").read_text(), selection)


def web_manifest(web_features: set[str]) -> str:
    return web_package_json((FRONTEND_APP / "package.json").read_text(), web_features)


def resolve(directory: Path) -> str:
    result = subprocess.run(
        ["npm", "install", "--package-lock-only", "--no-audit", "--no-fund", "--loglevel=error"],
        cwd=directory,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise SystemExit(f"npm could not resolve {directory}:\n{result.stderr.strip()}")
    return (directory / "package-lock.json").read_text()


def backend_lock(selection: Selection) -> str:
    """The service's own lock, as `language_files` restructures it into a project root lock."""
    with tempfile.TemporaryDirectory() as staging:
        directory = Path(staging)
        (directory / "package.json").write_text(service_manifest(selection))
        return resolve(directory)


def combined_lock(selection: Selection, web_features: set[str]) -> str:
    """The workspace lock for a TypeScript backend beside the React frontend."""
    with tempfile.TemporaryDirectory() as staging:
        directory = Path(staging)
        (directory / "package.json").write_text(
            json.dumps(
                {
                    "name": SERVICE_NAME,
                    "version": "0.1.0",
                    "private": True,
                    "workspaces": ["apps/service", "apps/web", "packages/*"],
                },
                indent=2,
            )
            + "\n"
        )
        (directory / "apps/service").mkdir(parents=True)
        (directory / "apps/service/package.json").write_text(service_manifest(selection))
        (directory / "apps/web").mkdir(parents=True)
        (directory / "apps/web/package.json").write_text(web_manifest(web_features))
        stage_api_client(directory)
        return resolve(directory)


def frontend_only_lock(web_features: set[str]) -> str:
    with tempfile.TemporaryDirectory() as staging:
        directory = Path(staging)
        (directory / "package.json").write_text(
            json.dumps(
                {
                    "name": SERVICE_NAME,
                    "version": "0.1.0",
                    "private": True,
                    "workspaces": ["apps/web", "packages/*"],
                },
                indent=2,
            )
            + "\n"
        )
        (directory / "apps/web").mkdir(parents=True)
        (directory / "apps/web/package.json").write_text(web_manifest(web_features))
        stage_api_client(directory)
        return resolve(directory)


PYTHON_APP = ROOT / "assets/languages/python/app"
PYTHON_LOCKS = ROOT / "assets/languages/python/locks"


def python_locks() -> dict[Path, str]:
    """`uv.lock` per Python dependency set, resolved from the very manifest the generator writes.

    One lock per subset of the dependency-adding features, the way the npm ones are built, and from
    `python_pyproject` rather than from a hand-written stub so the manifest and its lock cannot disagree.
    uv resolves universally — one lock covers every interpreter the `requires-python` floor admits — so
    the Python version on this machine is not part of the answer.
    """
    wanted: dict[Path, str] = {}
    for chosen in subsets(PYTHON_LOCK_FEATURES):
        axes = {}
        if "postgres" in chosen:
            axes["event-store"] = "postgres"
        if "fastapi" in chosen:
            axes["http"] = "fastapi"
        selection = Selection(axes)
        with tempfile.TemporaryDirectory() as staging:
            directory = Path(staging)
            (directory / "pyproject.toml").write_text(
                python_pyproject((PYTHON_APP / "pyproject.toml").read_text(), selection)
            )
            result = subprocess.run(
                ["uv", "lock", "--quiet"],
                cwd=directory,
                capture_output=True,
                text=True,
                env={**os.environ, "UV_NO_PROGRESS": "1"},
            )
            if result.returncode != 0:
                raise SystemExit(f"`uv lock` failed for {python_lock_suffix(selection) or 'the base'} "
                                 f"dependency set:\n{result.stderr.strip()}")
            wanted[PYTHON_LOCKS / f"uv{python_lock_suffix(selection)}.lock"] = (
                directory / "uv.lock"
            ).read_text()
    return wanted


GO_MODULES = ROOT / "assets/languages/go/modules"


def go_module_files() -> dict[Path, str]:
    """`go.mod` and `go.sum` per Go dependency set.

    Resolved by generating a real project and running `go mod tidy` in it, rather than by tidying a
    hand-written stub: the requirements follow from what the emitted adapters actually import, and a
    stub is a second thing to keep in step.

    The generated project starts from the *base* module file, which requires nothing — tidy is what
    adds the requirement and writes the checksums, and where a dependency needs a newer language
    version it raises the `go` directive too.
    """
    wanted: dict[Path, str] = {}
    for answer in ("memory", "sqlite", "postgres"):
        selection = Selection({"event-store": answer, "http": "net-http", "auth": "keycloak"})
        variant = go_module_variant(selection)
        with tempfile.TemporaryDirectory() as staging:
            project = Path(staging) / "tidy"
            write_project(project, "tidy", "event-modelling", "none", default_apps("go", "none", selection))
            service = project / "apps/service"
            result = subprocess.run(
                ["go", "mod", "tidy"],
                cwd=service,
                capture_output=True,
                text=True,
                env={**os.environ, "GOFLAGS": "-mod=mod"},
            )
            if result.returncode != 0:
                raise SystemExit(f"`go mod tidy` failed for the {variant} variant:\n{result.stderr}")
            # The module path is rewritten per project, so it is put back before committing.
            module = (service / "go.mod").read_text().replace(
                "example.com/tidy/service", "example.com/delivery-starter"
            )
            wanted[GO_MODULES / variant / "go.mod"] = module
            checksums = service / "go.sum"
            if checksums.is_file() and checksums.read_text().strip():
                wanted[GO_MODULES / variant / "go.sum"] = checksums.read_text()
    return wanted


def targets() -> dict[Path, str]:
    """Every lockfile this repository commits, mapped to the content it should hold."""
    wanted: dict[Path, str] = {}
    for selection in selections():
        suffix = lock_suffix(selection)
        wanted[TYPESCRIPT_LOCKS / f"package-lock{suffix}.json"] = backend_lock(selection)
        for web_features in subsets(WEB_LOCK_FEATURES):
            name = f"typescript-backend{suffix}{web_lock_suffix(web_features)}.json"
            wanted[FRONTEND_ROOT / f"react-vite/locks/{name}"] = combined_lock(selection, web_features)
    for web_features in subsets(WEB_LOCK_FEATURES):
        name = f"frontend-only{web_lock_suffix(web_features)}.json"
        wanted[FRONTEND_ROOT / f"react-vite/locks/{name}"] = frontend_only_lock(web_features)
    wanted.update(python_locks())
    wanted.update(go_module_files())
    return wanted


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="report stale lockfiles without writing any")
    arguments = parser.parse_args()

    for tool in ("npm", "uv", "go"):
        if shutil.which(tool) is None:
            print(f"{tool} is required to resolve a dependency tree.", file=sys.stderr)
            return 2

    stale: list[Path] = []
    targets_cache = targets()

    # A variant that requires nothing has no go.sum, and one left behind would be a checksum file
    # for requirements the module no longer has.
    for variant in ("base", "sqlite", "postgres"):
        checksums = GO_MODULES / variant / "go.sum"
        if checksums.is_file() and checksums not in targets_cache:
            if arguments.check:
                stale.append(checksums)
            else:
                checksums.unlink()
                print(f"removed {checksums.relative_to(ROOT)} (nothing requires anything)")
    for path, content in targets_cache.items():
        current = path.read_text() if path.is_file() else None
        if current == content:
            continue
        stale.append(path)
        if arguments.check:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        print(f"wrote {path.relative_to(ROOT)}")

    if arguments.check and stale:
        print("stale lockfiles:", file=sys.stderr)
        for path in stale:
            print(f"  {path.relative_to(ROOT)}", file=sys.stderr)
        print("\nRun `python3 scripts/regenerate-locks.py`.", file=sys.stderr)
        return 1
    if not stale:
        print("every lockfile is current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

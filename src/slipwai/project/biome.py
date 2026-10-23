"""`biome.jsonc` and the domain-purity plugin beside it: the npm workspace's lint and format gate.

One configuration at the repository root rather than one per package, because a formatter with two
opinions is a diff that moves back and forth depending on which directory it was run from. Every npm
package in the project — each Node service, each browser app, anything shared under `packages/` — spells
`lint` as `biome check`, which finds this file by walking up from wherever npm started it. The `.jsonc`
extension and not `.json`: the configuration is worth a paragraph of reasons, and Biome reads comments
only in the one it can parse as JSONC.

It is written whenever the project has an npm workspace at all, which is the condition that decides
whether there is a root `package.json` (`shared_packages.node_workspace`): a Python or Go service beside a
browser app still has TypeScript to lint, and that browser app had no linter before this.

The pinned Biome is read back out of the service manifest rather than written down a second time here —
the version in the `$schema` URL and the version npm installs have to be the same one, and the manifest is
the one npm locks.
"""
from __future__ import annotations

import json
from pathlib import Path

from ..npm_workspace import NpmWorkspace, browser_language, frontends, npm, workspace
from ..services import App, services_of, web_apps
from .shared_packages import node_workspace

VERSION = "__BIOME_VERSION__"
# Where the plugin lands, and what `biome.json` names it as. Root-relative rather than `./`-prefixed so
# that `Layout.repoint` moves the pointer with the directory when the delivery material lives elsewhere.
PLUGIN = "scripts/domain-purity.grit"


def pinned_in(answer: NpmWorkspace | None = None, family: str | None = None) -> tuple[Path, ...]:
    """Where the pin lives: the manifests that declare the dependency, the workspace family's and every browser
    app's that family ships. They must agree, because npm hoists one copy to the workspace root and a project
    with two would lint itself with whichever won.

    Every frontend the family ships, rather than the one this project asked for, and the check is the reason: a
    frontend whose Biome has drifted from its family's is a project that cannot be generated, and finding that
    out at the generation that asked for it makes it the fault of somebody who only wanted a project. Another
    family's frontends are its own business: they are never in a workspace with this family's services
    (`project/frontend.frontend_files` refuses the pair).
    """
    family = browser_language() if family is None else family
    answer = workspace(family) if answer is None else answer
    apps = (app for app in frontends().values() if app.family == family)
    return (*answer.biome_pins, *(app.at("app/package.json") for app in apps))


def workspace_family(apps: list[App]) -> str:
    """The family whose Biome the workspace runs: the browser apps' where there are any, since a project's are
    one frontend's, and otherwise its first npm service's."""
    web = web_apps(apps)
    if web:
        return web[0].language
    return next(service.language for service in services_of(apps) if npm(service.language))


def biome_version(answer: NpmWorkspace | None = None, family: str | None = None) -> str:
    """The exact `@biomejs/biome` the manifests pin."""
    pins = {
        json.loads(path.read_text(encoding="utf-8"))["devDependencies"]["@biomejs/biome"]
        for path in pinned_in(answer, family)
    }
    if len(pins) != 1:
        raise AssertionError(f"the manifests pin more than one Biome: {sorted(pins)}")
    return pins.pop()


def biome_files(apps: list[App]) -> dict[str, str]:
    """The configuration and its plugin, or nothing at all in a project with no npm workspace."""
    if not node_workspace(apps):
        return {}
    # The workspace runs one Biome: the browser apps' family's, or with none its first npm service's.
    family = workspace_family(apps)
    answer = workspace(family)
    return {
        "biome.jsonc": (answer.biome / "biome.jsonc").read_text(encoding="utf-8").replace(
            VERSION, biome_version(answer, family)),
        PLUGIN: (answer.biome / "domain-purity.grit").read_text(encoding="utf-8"),
    }

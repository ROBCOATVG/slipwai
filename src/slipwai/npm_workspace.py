"""The project's one npm workspace, as the keel asks about it: which languages are in it, and what a browser app is.

A browser app is an npm package, and so is every service of a language whose code npm installs. The keel's `react-vite`
frontend owns the browser app and the workspace's root; a language joins the workspace by answering
`npm_workspace` on its family, with what only it knows: its services' committed locks, the lock of a workspace
that holds one of them beside a browser app, the image a browser app's dev server runs in, and the lint and format
configuration every package in the workspace shares. The keel never names the language: it asks the registry
(`contracts/npm-workspace.md`, FR-034, D50).

A browser app is written in the first family, in registry order, that answers the member. With none loaded there
is no language to write one in, and asking for one is refused in a line (S09's Q1).

**And so the browser app's own material is the same family's.** A family that answers `npm_workspace` already
commits the lock that resolves a browser app's dependencies and already pins the Biome it must agree with, so
`browser_apps` is where it says which browser apps it writes and hands over each one's directory (`BrowserApp`).
The keel still carries one, under `KEEL_APPS`, and that is the last answer of any kind shipped inside it.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NamedTuple, cast

from .assets import FRONTEND_ROOT, inside
from .errors import GenerationError
from .registry import BROWSER_APPS, NPM_WORKSPACE, Registry, registry

# What a refusal for a browser app with no language to write it in says first. Each verb says what it was asked, and
# `browser_app` how it ends: the language the index says answers, and its install line (D122, over D63).
BROWSER = "needs a language that answers the npm workspace, and none is loaded"


class NoBrowserLanguage(GenerationError):
    """No loaded family answers `npm_workspace`: the verb that meets it says which language would (`browser_app`)."""


class NpmWorkspace(NamedTuple):
    """What a language tells the keel about its part of the npm workspace (`contracts/npm-workspace.md`)."""

    member_lock: Callable[[Any], Path]
    """One of its services' committed `package-lock.json`, for that service's selection."""
    workspace_lock: Callable[[Any, str], Path]
    """The workspace lock for a first member service of this selection beside browser apps whose lock suffix is the
    `str` (`''` or `-users-keycloak`)."""
    image: str
    """The image a browser app's dev server runs in, under Compose."""
    biome: Path
    """The directory holding `biome.jsonc` and `domain-purity.grit`, the workspace's one lint and format gate."""
    biome_pins: tuple[Path, ...]
    """Its manifests that pin `@biomejs/biome`, which must agree with the browser app's."""


def workspaces(held: Registry | None = None) -> dict[str, NpmWorkspace]:
    """Each family of `held` (the process's registry by default) that answers `npm_workspace`, in registry order."""
    families = (registry() if held is None else held).families
    return {
        name: cast(NpmWorkspace, family.answers[NPM_WORKSPACE])
        for name, family in families.items()
        if NPM_WORKSPACE in family.answers
    }


@dataclass(frozen=True)
class BrowserApp:
    """One browser app a project may be given, and the directory its material is copied from.

    `name` is what `--frontend <name>` is typed as, what `catalog.json`'s `frontends` block lists it under,
    and what `project.json` records as the web deployable's framework. `root` is the directory the material
    sits in, laid out the way `project/frontend.py` reads it — `app/` and the variants beside it — so that
    moving the material out of the keel is a change of root and of nothing else.

    A record rather than the files themselves, for the reason `loaded_targets.root_of` gives about a
    target's stacks: a browser app is a tree copied as written, and a package that had to hand it over as
    strings would be a package that had to keep it as strings.
    """

    name: str
    root: Path

    def at(self, relative: str) -> Path:
        """One of its trees or files, refused where that path leaves the root.

        Held here rather than at each of the six places `project/frontend.py` reaches in, because the root
        becomes a package's own directory and a frontend that could read `../..` out of it would be a
        frontend that could carry any file on the machine into somebody's repository.
        """
        try:
            return inside(self.root, relative)
        except ValueError as error:
            raise GenerationError(f"frontend {self.name} {error}") from error


#: The one browser app the keel still carries, and the last answer of any kind that ships inside it: every
#: language, extension, target and quickstart is a package already. Named here — in one place, rather than at
#: each of the paths that read it — so that the slice which moves it into the family that writes it is a
#: change of this dictionary and of nothing else.
KEEL_APPS: dict[str, BrowserApp] = {"react-vite": BrowserApp("react-vite", FRONTEND_ROOT / "react-vite")}


def frontends(held: Registry | None = None) -> dict[str, BrowserApp]:
    """Every browser app this keel can write, by name: each family's own in registry order, the keel's last.

    A family wins a name the keel also carries, because a family that ships a browser app ships the lock
    that resolves it — and a project given the keel's files under a family's lock is a project whose
    `npm ci` refuses the tree it was handed.
    """
    found: dict[str, BrowserApp] = {}
    for family in (registry() if held is None else held).families.values():
        for name, app in cast(dict, family.answers.get(BROWSER_APPS, {})).items():
            found.setdefault(name, app)
    for name, app in KEEL_APPS.items():
        found.setdefault(name, app)
    return found


def frontend(name: str) -> BrowserApp:
    """The browser app `--frontend <name>` means, or a refusal naming what is offered instead.

    A refusal rather than a `KeyError` from the middle of a copy: the names come from the merged catalogue
    and the material from whichever family answers, so a row with nothing behind it is a state a person can
    actually meet, and one they have to be told about in a sentence naming both halves.
    """
    offered = frontends()
    if name not in offered:
        raise GenerationError(f"no loaded language writes a {name} browser app; this keel offers "
                              f"{', '.join(sorted(offered)) or 'none'}")
    return offered[name]


def npm(language: str) -> bool:
    """Whether a family's code is an npm package in the project's workspace."""
    return language in workspaces()


def browser_language() -> str:
    """The family a browser app is written in: the first that answers `npm_workspace`."""
    found = next(iter(workspaces()), None)
    if found is None:
        raise NoBrowserLanguage(f"a browser app {BROWSER}")
    return found


def workspace(language: str) -> NpmWorkspace:
    """A family's answer to `npm_workspace`."""
    return workspaces()[language]


def held_lock(language: str, field: str, path: object, root: Path | None = None) -> Path:
    """The lock a family answered `field` with, refused in one line where it is not a file inside the family's
    package (`root`, the registry's by default) — at generation, since a lock is answered for a selection."""
    home = (registry().root(language) if root is None else root).resolve()
    if not isinstance(path, Path):
        raise GenerationError(f"family {language} answers {field} with {type(path).__name__}, where a Path is wanted")
    if not path.resolve().is_relative_to(home):
        raise GenerationError(f"family {language} reaches outside its directory for {field}")
    if not path.is_file():
        raise GenerationError(f"family {language} reaches for {field}, which is not a file in its directory")
    return path

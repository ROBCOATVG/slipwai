"""`project.json`: the manifest — every answer this project was given, written once for everything that reads it.

Split from `readme.py`, which had reached its budget, and kept apart from `manifest.py`: that module reads a
written manifest back for `add-service` and `replay`, and this one writes it, so the shape is spelled in
two places on purpose — a factory that means something else by these fields is refused by the reader, not
silently accepted by the writer.
"""
from __future__ import annotations

import json

from ..assets import VERSION
from ..capabilities import app_capabilities
from ..catalog import CATALOG
from ..layout import AT_ROOT, Layout
from ..manifest import MANIFEST_SCHEMA
from ..origin import Adoption
from ..services import App, frontend_of
from .pins import SPECKIT_SOURCE
from .shared_packages import PACKAGES


def metadata(
    project_name: str, profile: str, target: str, apps: list[App], layout: Layout = AT_ROOT,
    adoption: Adoption | None = None,
) -> str:
    """`project.json`: the answers this project was generated from, for a tool rather than a reader.

    `deployables` is the list of applications everything else reads — the Makefile, Compose, CI, the import
    gate and the pruner are generated from it or read it, and `add-service` appends to it. Each service
    carries its own language, framework and selection; there is no project-wide backend, because a project
    may have several. `schema` says which shape those readers expect; see `services.py`.

    `generator` is provenance, not configuration — nothing generated reads it: `generatedWith` created this
    repository and never changes, `updatedWith` is the newest to have written a file here (`add-service`
    moves it forward), and against the factory's `CHANGELOG.md` the pair says what it has yet to hear.
    `speckitSource` is the Spec Kit `./init` installs — a pinned release, so a rerun that restores the
    gitignored projections reinstalls the same version; `slipwai migrate` moves it as a visible diff.

    `adoption` is how the repository came to have this material: None for a generated one; for one the method
    was installed around, `"origin": "adopted"` after the generator and its facts after the layout, with its
    applications recorded `"generated": false`, claiming no capability and event-sourced in nobody's eyes.
    `layout` is where things live: `applications` and `packages` as constants (`scripts/deploy.py` reads the
    second), and
    `delivery`, where the factory's own material sits — `.` here, and a directory such as `delivery` where
    the method was installed beside an existing codebase (`layout.py`)."""
    event = profile == "event-modelling"
    frontend = frontend_of(apps)
    capabilities = CATALOG["profiles"][profile]["capabilities"]
    document = {
        "schema": MANIFEST_SCHEMA,
        "generator": {"name": "slipwai", "generatedWith": VERSION, "updatedWith": VERSION},
        "speckitSource": SPECKIT_SOURCE,
        **({"origin": "adopted"} if adoption else {}),
        "name": project_name,
        "profile": profile,
        # The browser framework, derived from the browser apps below; `none` when there are none.
        "frontend": frontend,
        # Where it goes to production; `none` is local only. The project's own pruner reads this, so a
        # later `./init` offers an axis only the answers this target carries.
        "target": target,
        "capabilities": capabilities,
        "deployables": {
            app.name: {
                **app.record(),
                "eventSourced": event if app.is_service and app.generated else False,
                # What this application gives the project (`capabilities.py`) — the list `toolkit.py` takes
                # the union of to decide which skills the project has anything to use, and the generated
                # gate reads back to say when one of them no longer has.
                "capabilities": app_capabilities(profile, app),
            }
            for app in apps
        },
        "layout": {"applications": "apps", "packages": PACKAGES, **layout.record()},
        **(adoption.record() if adoption else {}),
    }
    return json.dumps(document, indent=2) + "\n"

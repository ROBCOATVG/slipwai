"""What `slipwai package new --kind language` writes, by part: the Python, and a browser app's trees.

Beside `package_templates` rather than inside it, because a language is the one kind assembled from parts — it
ships services, browser apps or both (`docs/frontend-protocol.md`) — and those parts are most of a scaffold.
"""
from __future__ import annotations

import json

#: A scaffolded language's Python, assembled from its parts by `package_new.language_module`. Its placeholders
#: are `@NAME@`, `@TITLE@` and `@FRONTEND@`, filled by replacement rather than `str.format`: the text is full of
#: Python braces, and a template that had to double every one was a template nobody could read.
LANGUAGE_MODULE = '''"""@TITLE@: the protocol, as this keel's registry asks it.

The loader imports this module from the package directory and reads `LANGUAGE`: the family, and each backend
`language.json` declares. A backend must answer every member the registry declares `required` (its own answer,
or its family's); `slipwai package check .` lists every one still missing — the loader names them all at once —
and then generates a project and holds it to its own gate. `slipwai-language-template` answers every member
with a placeholder, which is the quicker start for a backend. `docs/backend-protocol.md` and
`docs/frontend-protocol.md` in the keel say what each member is.
"""
from __future__ import annotations
@IMPORTS@
from slipwai import registry as protocol
@ANSWERS@
#: TODO: what every backend of the family shares — `formatter`, `ci_toolchain_setup`, `shared_code`, `pin_files`,
#: `makefile_variables`, `renovate_rules`, `prune_rows` — and, for a browser app, what its project asks.
FAMILY_ANSWERS: dict = {@ENTRIES@}
@BACKENDS@
LANGUAGE = protocol.Language((protocol.Family("@NAME@", FAMILY_ANSWERS),), BACKENDS)
'''

#: The backend half: one backend answering nothing yet. The loader refuses it with a line naming every required
#: member still missing, which is the list to work through.
LANGUAGE_BACKEND = '''
#: TODO: answer the required members — `service_files`, `name_service`, `tooling` and the rest.
BACKENDS = (protocol.Backend("@NAME@", "@NAME@", {}),)
'''

#: A package of browser apps alone has none.
LANGUAGE_NO_BACKEND = '''
BACKENDS: tuple = ()
'''

#: The frontend half: a browser app that loads and generates as written, every file in it a placeholder for the
#: framework's own (`docs/frontend-protocol.md`, *Adding a frontend*).
LANGUAGE_FRONTEND_IMPORTS = '''
from pathlib import Path

from slipwai.npm_workspace import FRONTENDS_DIRECTORY, BrowserApp, NpmWorkspace
'''

LANGUAGE_FRONTEND_ANSWERS = '''
ROOT = Path(__file__).resolve().parents[1]


def no_services(*_asked: object) -> Path:
    """TODO, where this family has npm services: their committed locks. Asked of none until then."""
    raise AssertionError("@NAME@ has no npm services, so no service lock is asked of it")


#: The npm workspace its browser app is a member of: the dev server's image, Biome and its pins, and the locks.
WORKSPACE = NpmWorkspace(
    member_lock=no_services,
    workspace_lock=no_services,
    image="node:22-bookworm",
    biome=ROOT / "assets/biome",
    biome_pins=(),
)

BROWSER_APPS = {"@FRONTEND@": BrowserApp("@FRONTEND@", ROOT / FRONTENDS_DIRECTORY / "@FRONTEND@")}
'''

LANGUAGE_FRONTEND_ENTRIES = '''
    # What a project asks of the family its browser app is written in.
    protocol.SHARED_CODE: "TODO: where code shared between this project's packages lives",
    protocol.FORMATTER: None,
    protocol.NPM_WORKSPACE: WORKSPACE,
    protocol.BROWSER_APPS: BROWSER_APPS,
'''

#: The frontend's trees, each laid out like the app it is copied into, every token in place
#: (`docs/frontend-protocol.md`). Relative to `assets/frontends/<frontend>/`.
#: The workspace lock of a project with this browser app and no npm service, in the shape every lock takes: one
#: app at `apps/web` named `delivery-starter-web`, and the typed client at `packages/api-client`. Placeholder
#: records — `npm install` over the app's real manifest writes the real one.
FRONTEND_LOCK = {
    "name": "delivery-starter",
    "lockfileVersion": 3,
    "requires": True,
    "packages": {
        "": {"name": "delivery-starter", "workspaces": ["apps/web", "packages/api-client"]},
        "apps/web": {"name": "delivery-starter-web"},
        "packages/api-client": {"name": "api-client"},
        "node_modules/delivery-starter-web": {"resolved": "apps/web", "link": True},
        "node_modules/@packages/api-client": {"resolved": "packages/api-client", "link": True},
    },
}
FRONTEND_MANIFEST = {
    "name": "web",
    "private": True,
    "scripts": {"verify": "echo TODO: the app gate"},
    "dependencies": {},
    "devDependencies": {"@biomejs/biome": "2.0.0"},
}
FRONTEND_TREE = {
    "app/package.json": json.dumps(FRONTEND_MANIFEST, indent=2) + "\n",
    "app/index.html": '<!doctype html><title>__PROJECT_NAME__</title><div id="root"></div>\n',
    "app/src/App.ts": "// TODO: the shell of __PROJECT_NAME__, served on __WEB_PORT__ (__WEB_PORT_VARIABLE__)\n",
    "app-flags-local/src/flags.ts": "// TODO: the flag reader that reads .env through the bundle\n",
    "app-flags-target/src/flags.ts": "// TODO: the flag reader that asks GET /api/flags\n",
    "app-route-client/src/routes/Home.ts": "// TODO: the route calling __STATUS_PATH__ through __API_CLIENT__\n",
    "app-route-plain/src/routes/Home.ts": "// TODO: the route fetching __STATUS_PATH__ by hand\n",
    "api-client/package.json": json.dumps(
        {"name": "api-client", "scripts": {"build": "echo TODO: generate from __DOCUMENT__"}}, indent=2) + "\n",
    "api-client/src/index.ts": "// TODO: the typed client for __DOCUMENT__\n",
    "locks/frontend-only.json": json.dumps(FRONTEND_LOCK, indent=2) + "\n",
}
#: Biome, which every package in the workspace is linted with: the family's, relative to the package.
BIOME_TREE = {
    "assets/biome/biome.jsonc": '{ "$schema": "https://biomejs.dev/schemas/__BIOME_VERSION__/schema.json" }\n',
    "assets/biome/domain-purity.grit": "// TODO: the domain-purity rule, in GritQL\n",
}

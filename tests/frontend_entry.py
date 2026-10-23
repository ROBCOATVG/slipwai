"""The `react-vite` catalogue entry, as the TypeScript family declares it, for the suites that pin its pages.

The keel ships no frontend, so a suite running against the checkout's packages — the toy and the targets — has no
`react-vite` in its catalogue. The suites that pin what a project with a browser app reads (its README, its
`docs/design.md`, its manifest's capabilities) build that browser app directly and read the entry by name; this
is the entry they read, installed into the catalogue for the module that needs it and taken out after. It is a
copy of `frontends.react-vite` in `slipwai-language-typescript`'s `language.json`, and it is a fixture: what it
pins is the keel's prose around a frontend, not the frontend.
"""
from __future__ import annotations

from slipwai.catalog import CATALOG

REACT_VITE: dict = {
    "label": "React and Vite — a TypeScript browser app, Biome, Vitest and Testing Library",
    "stack": "TypeScript/React/Vite",
    "gate": "Biome, TypeScript and React component tests",
    "capabilities": [
        "frontend",
        "typescript",
        "react",
        "vite"
    ],
    "marked": [
        "vite.config.ts",
        "src/main.tsx",
        "src/App.tsx",
        "tests/App.test.tsx"
    ],
    "features": {
        "users-keycloak": {
            "files": "features/users-keycloak",
            "owned": [
                "src/auth",
                "tests/auth"
            ],
            "dependencies": {
                "oidc-client-ts": "3.5.0",
                "react-oidc-context": "3.3.1"
            },
            "where": "`src/auth/users.tsx`, react-oidc-context over oidc-client-ts"
        }
    },
    "design": {
        "tokens": "src/styles/tokens.css",
        "base": "src/styles/base.css",
        "shell": "src/App.tsx",
        "entry": "src/main.tsx",
        "imports": [
            "import './styles/tokens.css';\n",
            "import './styles/base.css';\n"
        ],
        "route": "src/routes/Home.tsx"
    },
    "family": "typescript"
}


def install() -> None:
    """Put the entry in the catalogue, as the TypeScript family's merge would."""
    CATALOG["frontends"]["react-vite"] = REACT_VITE


def remove() -> None:
    CATALOG["frontends"].pop("react-vite", None)

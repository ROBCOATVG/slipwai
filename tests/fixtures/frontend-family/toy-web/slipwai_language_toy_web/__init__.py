"""The `toy-web` fixture: a family with no backend and one browser app, answering what a browser app's family is asked.

A frontend-only family answers exactly what a project asks of the family its browser app is written in:
`browser_apps`, `npm_workspace` (the dev server's image, Biome and its pins), `shared_code` (the architecture page's
paragraph) and `formatter` (here None: no `make format` line). `member_lock` and `workspace_lock` are asked only of
a family with npm services, which this one has none of, so they refuse if asked. Nothing else is read of it: pins,
Renovate rules, CI's toolchain and prune rows are asked of service families.
"""
from __future__ import annotations

from pathlib import Path

from slipwai import registry as protocol
from slipwai.npm_workspace import FRONTENDS_DIRECTORY, BrowserApp, NpmWorkspace

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"


def no_services(*_asked: object) -> Path:
    raise AssertionError("toy-web has no npm services, so no service lock is ever asked of it")


WORKSPACE = NpmWorkspace(
    member_lock=no_services,
    workspace_lock=no_services,
    image="node:22-bookworm",
    biome=ASSETS / "biome",
    biome_pins=(),
)

BROWSER_APPS = {"toy-vite": BrowserApp("toy-vite", ROOT / FRONTENDS_DIRECTORY / "toy-vite")}

LANGUAGE = protocol.Language(
    (protocol.Family("toy-web", {
        protocol.FORMATTER: None,
        protocol.SHARED_CODE: "a placeholder: the toy frontend shares nothing",
        protocol.NPM_WORKSPACE: WORKSPACE,
        protocol.BROWSER_APPS: BROWSER_APPS,
    }),),
    (),
)

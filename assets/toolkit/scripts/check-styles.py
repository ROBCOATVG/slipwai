#!/usr/bin/env python3
"""Refuse two imported stylesheets that both own one custom property at ``:root``.

Custom properties are global at ``:root``. Two files can each be valid alone while their bundle is not:
the cascade silently chooses one value by import order, and a token expected to be a colour can become a
border shorthand everywhere it is used. This gate follows CSS imports from the web app's TypeScript and
from other CSS files, then names every property with more than one owning file.

An override inside the same file is deliberate ownership, including the generated token file's
``prefers-color-scheme: dark`` block, so it is allowed. An unimported stylesheet is not in the bundle and
is not judged.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def project_root(script: Path, depth: int) -> Path:
    """The nearest parent holding ``project.json``, with a source-tree fallback."""
    for candidate in script.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return script.parents[depth]


ROOT = project_root(Path(__file__).resolve(), 1)
COMMENTS = re.compile(r"/\*.*?\*/|//[^\n]*", re.DOTALL)
TS_CSS_IMPORT = re.compile(
    r"\b(?:import|export)\s+(?:[^\"']*?\s+from\s+)?[\"']([^\"']+?\.css)(?:\?[^\"']*)?[\"']"
)
CSS_IMPORT = re.compile(
    r"@import\s+(?:url\(\s*)?[\"']?([^\"')\s]+?\.css)(?:\?[^\"')\s]*)?[\"']?\s*\)?",
    re.IGNORECASE,
)
ROOT_BLOCK = re.compile(r":root\b[^{}]*\{")
CUSTOM_PROPERTY = re.compile(r"(?<![a-zA-Z0-9_-])(--[a-zA-Z0-9_-]+)\s*:")


def web_paths(root: Path = ROOT) -> list[Path]:
    """Generated browser applications recorded by the project."""
    manifest = root / "project.json"
    if not manifest.is_file():
        return []
    records = json.loads(manifest.read_text()).get("deployables", {}).values()
    return [
        root / record["path"]
        for record in records
        if isinstance(record, dict)
        and record.get("kind") == "web"
        and record.get("generated") is not False
        and isinstance(record.get("path"), str)
    ]


def resolve_import(owner: Path, specifier: str, app: Path) -> Path | None:
    """A local CSS import as a path, or none for a package import."""
    if specifier.startswith("."):
        candidate = owner.parent / specifier
    elif specifier.startswith("/"):
        candidate = app / specifier.lstrip("/")
    else:
        return None
    resolved = candidate.resolve()
    try:
        resolved.relative_to(app.resolve())
    except ValueError:
        return None
    return resolved if resolved.is_file() else None


def imported_styles(app: Path) -> set[Path]:
    """Every local stylesheet reachable from source imports in one web app."""
    source = app / "src"
    found: set[Path] = set()
    pending: list[Path] = []
    if not source.is_dir():
        return found
    for path in sorted(source.rglob("*")):
        if path.suffix not in {".ts", ".tsx"} or not path.is_file():
            continue
        text = COMMENTS.sub("", path.read_text(errors="ignore"))
        for specifier in TS_CSS_IMPORT.findall(text):
            imported = resolve_import(path, specifier, app)
            if imported is not None and imported not in found:
                found.add(imported)
                pending.append(imported)
    while pending:
        path = pending.pop()
        text = COMMENTS.sub("", path.read_text(errors="ignore"))
        for specifier in CSS_IMPORT.findall(text):
            imported = resolve_import(path, specifier, app)
            if imported is not None and imported not in found:
                found.add(imported)
                pending.append(imported)
    return found


def root_properties(path: Path) -> set[str]:
    """Custom properties declared by any ``:root`` block in one stylesheet."""
    text = COMMENTS.sub("", path.read_text(errors="ignore"))
    properties: set[str] = set()
    for match in ROOT_BLOCK.finditer(text):
        depth = 1
        cursor = match.end()
        while cursor < len(text) and depth:
            if text[cursor] == "{":
                depth += 1
            elif text[cursor] == "}":
                depth -= 1
            cursor += 1
        properties.update(CUSTOM_PROPERTY.findall(text[match.end() : cursor - 1]))
    return properties


def token_files(app: Path) -> list[Path]:
    """Imported stylesheets that declare at least one root custom property."""
    return sorted(path for path in imported_styles(app) if root_properties(path))


def collisions(app: Path) -> dict[str, list[Path]]:
    """Root custom properties owned by more than one imported stylesheet."""
    owners: dict[str, list[Path]] = {}
    for path in token_files(app):
        for prop in root_properties(path):
            owners.setdefault(prop, []).append(path)
    return {prop: paths for prop, paths in owners.items() if len(paths) > 1}


def main() -> int:
    violations: list[str] = []
    apps = web_paths()
    for app in apps:
        for prop, paths in sorted(collisions(app).items()):
            names = ", ".join(path.relative_to(ROOT).as_posix() for path in paths)
            violations.append(f"{prop}: declared at :root in {names}")
    if violations:
        print(
            "check-styles: imported stylesheets compete for global custom properties\n",
            file=sys.stderr,
        )
        for violation in violations:
            print(f"  {violation}", file=sys.stderr)
        print(
            "\nOne imported file owns each :root property. Remove the obsolete token import or rename "
            "the token deliberately; bundle order is not ownership.",
            file=sys.stderr,
        )
        return 1
    print(
        f"check-styles: {len(apps)} web app(s), no :root custom property has two imported owners"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

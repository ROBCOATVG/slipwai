#!/usr/bin/env python3
"""Shared state and marker projection for optional extensions."""
from __future__ import annotations

import json
import re
from pathlib import Path


def project_root(script: Path) -> Path:
    for candidate in script.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return script.parents[2]


ROOT = project_root(Path(__file__).resolve())
HERE = Path(__file__).resolve().parent
AGENTS = ROOT / "AGENTS.md"
STATE = ROOT / ".slipwai/extensions.json"
SCHEMA = 1
BLOCK = re.compile(
    r"<!-- extension:([a-z0-9][a-z0-9-]*):begin -->.*?<!-- extension:\1:end -->",
    re.DOTALL,
)


def marker(key: str, edge: str) -> str:
    return f"<!-- extension:{key}:{edge} -->"


def canonical_block(key: str, guidance: str) -> str:
    block = guidance.strip("\n")
    if not block.startswith(marker(key, "begin")) or not block.endswith(marker(key, "end")):
        raise ValueError(f"{key}: GUIDANCE must be fenced by its extension markers")
    return block


def recorded_extensions() -> list[str]:
    if not STATE.is_file():
        return []
    document = json.loads(STATE.read_text())
    if document.get("schemaVersion") != SCHEMA or not isinstance(document.get("extensions"), list):
        raise ValueError(f"{STATE.relative_to(ROOT)} is not extension election schema {SCHEMA}")
    if not all(isinstance(key, str) and key for key in document["extensions"]):
        raise ValueError(f"{STATE.relative_to(ROOT)} has a non-string extension key")
    return list(dict.fromkeys(document["extensions"]))


def marked_extensions() -> list[str]:
    if not AGENTS.is_file():
        return []
    return [
        match.group(1)
        for match in BLOCK.finditer(AGENTS.read_text())
        if (HERE / match.group(1) / "init.py").is_file()
    ]


def adopted_extensions(*, persist_legacy: bool) -> list[str]:
    recorded = recorded_extensions()
    adopted = list(dict.fromkeys([*recorded, *marked_extensions()]))
    if persist_legacy and adopted != recorded:
        write_elections(adopted)
    return adopted


def write_elections(keys: list[str]) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps({"schemaVersion": SCHEMA, "extensions": sorted(set(keys))}, indent=2) + "\n")


def record_extension(key: str) -> None:
    write_elections([*recorded_extensions(), key])


def installed_block(key: str) -> str | None:
    if not AGENTS.is_file():
        return None
    matches = [match.group(0) for match in BLOCK.finditer(AGENTS.read_text()) if match.group(1) == key]
    if len(matches) != 1:
        return None
    return matches[0]


def replace_block(key: str, guidance: str) -> None:
    """Replace the factory-owned region in place, or append it once when first adopted."""
    if not AGENTS.is_file():
        return
    canonical = canonical_block(key, guidance)
    content = AGENTS.read_text()
    matches = [match for match in BLOCK.finditer(content) if match.group(1) == key]
    if matches:
        first = matches[0]
        suffix = content[first.end():]
        suffix = re.sub(
            rf"\n*{re.escape(marker(key, 'begin'))}.*?{re.escape(marker(key, 'end'))}\n*",
            "\n",
            suffix,
            flags=re.DOTALL,
        )
        updated = content[:first.start()] + canonical + suffix
    else:
        updated = content.rstrip("\n") + f"\n\n{canonical}\n"
    AGENTS.write_text(updated)

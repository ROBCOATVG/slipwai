#!/usr/bin/env python3
"""Shared state and marker projection for optional extensions, and the one writer that puts an extension's MCP
server into the project-scoped config file of every harness installed here."""
from __future__ import annotations

import json
import os
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
INTEGRATION = ROOT / ".specify/integration.json"
REGISTRY = HERE.parent / "agents/registry.json"
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



# --- an MCP server that travels with the checkout ---------------------------------------------------------------
#
# A tool reached over MCP is reached through a config file, and the file a tool's own installer writes lives in the
# user's home — on the one machine `./init` ran on. A container, a CI runner and the fresh session a `/cruise`
# iteration is all open the checkout with the tool's data and no way to ask it. So an extension names its server in
# the project-scoped file each installed harness reads, as `scripts/agents/registry.json`'s `projectMcp` column
# spells that file and its shape, and commits it. Every file here is a merge target (docs/extensions.md, 6): a
# server a person configured stays, a second run rewrites nothing, and a file that cannot be parsed is left alone
# and said.


def installed_harnesses() -> list[str]:
    """The harness keys Spec Kit recorded here, plus the one this `./init` is installing — its record is written
    by the same run and may not be there yet when an extension hook runs (`SLIPWAI_INTEGRATION`)."""
    keys: list[str] = []
    if INTEGRATION.is_file():
        state = json.loads(INTEGRATION.read_text())
        recorded = state.get("installed_integrations")
        if isinstance(recorded, list) and recorded:
            keys = [key for key in recorded if isinstance(key, str)]
        elif isinstance(state.get("default_integration"), str):
            keys = [state["default_integration"]]
    chosen = os.environ.get("SLIPWAI_INTEGRATION")
    if chosen and chosen not in keys:
        keys.append(chosen)
    return list(dict.fromkeys(keys))


def harness_rows() -> dict[str, dict]:
    return {row["key"]: row for row in json.loads(REGISTRY.read_text())["harnesses"]}


def write_project_mcp(name: str, command: list[str]) -> list[str]:
    """Name the server `name`, started by `command`, in the project MCP file of every harness installed here whose
    file the registry knows. Returns one line per thing worth saying: a file written, a harness with no known
    file, a file that could not be merged — and nothing for a file that already says so."""
    installed = installed_harnesses()
    if not installed:
        return [f"no harness is recorded here (`.specify/integration.json`), so no project MCP file names `{name}` yet; "
                "`./init --integration <agent>` records one and `make agents` then writes the file"]
    rows = harness_rows()
    lines: list[str] = []
    for key in installed:
        row = rows.get(key)
        if row is None:
            continue
        spec = row.get("projectMcp")
        if not isinstance(spec, dict):
            lines.append(f"{row['name']}: no project MCP file is known for it, so it reaches `{name}` through the CLI — "
                         f"{row.get('projectMcpReason', 'not verified')}")
            continue
        said = write_project_mcp_entry(spec, name, command)
        if said:
            lines.append(f"{row['name']}: {said}")
    return lines


def write_project_mcp_entry(spec: dict, name: str, command: list[str]) -> str | None:
    path = ROOT / str(spec["file"])
    if spec["format"] == "toml-codex":
        return write_toml_table(path, f"mcp_servers.{name}", {"command": command[0], "args": command[1:]})
    if spec["format"] == "json-opencode":
        # opencode reads either spelling; an existing `.jsonc` is the person's choice and is merged rather than shadowed.
        jsonc = path.with_suffix(".jsonc")
        if jsonc.is_file() and not path.is_file():
            path = jsonc
        return write_json_entry(path, "mcp", name, {"type": "local", "command": command, "enabled": True})
    # What the harness's row adds to the entry beyond how the server starts: Claude Code's `alwaysLoad`, which
    # loads this server's tools at session start rather than behind its tool-search step (registry `serverFields`).
    fields = spec.get("serverFields") if isinstance(spec.get("serverFields"), dict) else {}
    return write_json_entry(path, "mcpServers", name,
                            {"type": "stdio", "command": command[0], "args": command[1:], **fields})


def write_json_entry(path: Path, key: str, name: str, entry: dict) -> str | None:
    shown = path.relative_to(ROOT)
    document: dict = {}
    if path.is_file():
        try:
            loaded = json.loads(path.read_text())
        except ValueError:
            loaded = None
        if not isinstance(loaded, dict):
            return (f"{shown} is not a JSON object (comments, perhaps); left as it is — add the server by hand: "
                    f"{json.dumps({key: {name: entry}})}")
        document = loaded
    servers = document.get(key)
    if not isinstance(servers, dict):
        servers = document[key] = {}
    if servers.get(name) == entry:
        return None
    servers[name] = entry
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2) + "\n")
    return f"{shown} names `{name}`; commit it"


def write_toml_table(path: Path, table: str, values: dict) -> str | None:
    """One `[table]` of scalar and string-array values, replaced in place where the file has it and appended where
    it does not. Standard library only, so the file is not parsed as TOML: the table runs from its header to the
    next header, which is what a table is, and a file with the header twice is left alone and said."""
    shown = path.relative_to(ROOT)
    rendered = "".join(f"{field} = {json.dumps(value)}\n" for field, value in values.items())
    block = f"[{table}]\n{rendered}"
    text = path.read_text() if path.is_file() else ""
    header = re.compile(rf"^\[{re.escape(table)}\][ \t]*(?:#.*)?$\n?", re.MULTILINE)
    starts = [match for match in header.finditer(text)]
    if len(starts) > 1:
        return f"{shown} declares [{table}] more than once; left as it is — keep one and put in it:\n{rendered}"
    if starts:
        begin = starts[0].start()
        after = text[starts[0].end():]
        following = re.search(r"^\[", after, re.MULTILINE)
        end = starts[0].end() + (following.start() if following else len(after))
        current = text[begin:end]
        if current.rstrip("\n") == block.rstrip("\n"):
            return None
        text = text[:begin] + block + ("\n" if following else "") + text[end:]
    else:
        text = (text.rstrip("\n") + "\n\n" if text.strip() else "") + block
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return f"{shown} names `{table.rpartition('.')[2]}`; commit it"

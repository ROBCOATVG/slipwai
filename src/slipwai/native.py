"""The same material, laid out where a harness that is not Claude Code reads it.

12.1 gives Claude Code a plugin, which is its own mechanism and nobody else's. Every other harness installs
material by putting files where it looks for them, and `registry.json` already says where that is for
thirty-six of them — the skills directory, the commands directory and its extension, the agent file's
directory, and the project-scoped MCP file under `projectMcp`.

**One renderer, one row per harness.** Nothing here is written per harness. Each answer comes out of the
row, so a thirty-seventh harness is a row in the registry and no code at all — which is the whole point,
because every one of these is somebody else's format and a keel that shipped a manifest apiece is a keel
edited whenever any of them changes its mind.

**What a harness cannot be given, it is told it cannot be given.** A gap written down is a gap somebody can
read; a gap left out is one the next person assumes the harness is holding. `unplaceable` is that list, and
the verb prints it.

**This is the material without a project, and it stops where a project starts.** An agent type whose
harness reads TOML is rendered by `scripts/agents/project.py` inside a project, where there is a
`.specify/models.json` to resolve the stage's model from. With no project there is no model to resolve, so
the canonical markdown file is placed where the harness reads markdown and the gap is said where it is not.
Rendering a second TOML here would be a second answer to what a delegate may do.
"""
from __future__ import annotations

import json
import shlex

from .assets import contained, this_command
from .errors import GenerationError
from .harness import keys, name_of, row_of
from .plugin import DEFAULT_PROFILE
from .plugin import files as plugin_files

#: What the MCP server is called in every harness's configuration. One name, so a person reading two
#: harnesses' files sees the same server in both.
SERVER = "slipwai"
#: The spellings of the project MCP file the registry declares, and the only ones this renders. A format
#: the registry grows and this does not know is a failing test rather than a file silently not written —
#: `tests/test_native.py` holds the two lists in step.
FORMATS = ("json-mcpServers", "json-opencode", "toml-codex")
#: A location a tree cannot hold: the harness reads it from the person's home rather than the project.
ELSEWHERE = ("~", "/")


def row(key: str) -> dict:
    """One harness's row, or a refusal naming the keys there are."""
    found = row_of(key)
    if not found:
        raise GenerationError(f"`{key}` is not a harness `registry.json` knows. There are {len(keys())}: "
                              f"{', '.join(keys())}")
    return found


def placeable(where: object) -> str | None:
    """A directory from a row that a rendered tree can actually hold, or None."""
    if not isinstance(where, str) or not where or where.startswith(ELSEWHERE):
        return None
    return where


def server_command() -> list[str]:
    """How this copy of slipwai starts the read-side server, as a configuration file names it."""
    return [*shlex.split(this_command()), "mcp", "--root", "."]


def mcp_file(spec: dict) -> str:
    """The project-scoped MCP file, in the spelling this harness's row declares.

    Written fresh rather than merged, because there is no project here to merge into: what this produces is
    material a person copies in. Inside a project the merge is `scripts/extensions/guidance.py`'s, which
    reads the same three formats off the same rows.
    """
    said = server_command()
    kind = str(spec.get("format", ""))
    if kind == "toml-codex":
        arguments = ", ".join(json.dumps(part) for part in said[1:])
        return (f"# The slipwai read side, as `slipwai mcp` serves it.\n"
                f"[mcp_servers.{SERVER}]\ncommand = {json.dumps(said[0])}\nargs = [{arguments}]\n")
    if kind == "json-opencode":
        return json.dumps({"mcp": {SERVER: {"type": "local", "command": said, "enabled": True}}}, indent=2) + "\n"
    if kind == "json-mcpServers":
        declared = spec.get("serverFields")
        fields: dict = declared if isinstance(declared, dict) else {}
        entry = {"type": "stdio", "command": said[0], "args": said[1:], **fields}
        return json.dumps({"mcpServers": {SERVER: entry}}, indent=2) + "\n"
    raise GenerationError(f"`{kind}` is not a project MCP format this renders. There are {len(FORMATS)}: "
                          f"{', '.join(FORMATS)}")


def commands_of(found: dict[str, str], harness: dict) -> dict[str, str]:
    """Each canonical command at the path this harness reads commands from, in its own placeholder.

    Only where the row says the harness reads *markdown* commands. A harness whose commands are TOML or
    YAML has them rendered by `scripts/agents/project.py` inside a project, and a second rendering here
    would be a second answer to what the command says.
    """
    where = placeable(harness.get("commandsDir"))
    if where is None or (harness.get("commandFormat") or "markdown") != "markdown":
        return {}
    extension = str(harness.get("commandExtension") or ".md")
    placeholder = str(harness.get("argPlaceholder") or "$ARGUMENTS")
    return {
        f"{where}/{path.removeprefix('commands/').removesuffix('.md')}{extension}":
            text.replace("$ARGUMENTS", placeholder)
        for path, text in found.items() if path.startswith("commands/")
    }


def agents_of(found: dict[str, str], harness: dict) -> dict[str, str]:
    """Each canonical agent type where this harness reads a markdown agent file."""
    file_row = harness.get("agentFile")
    if not isinstance(file_row, dict) or file_row.get("format") != "markdown":
        return {}
    where = placeable(file_row.get("dir"))
    if where is None:
        return {}
    extension = str(file_row.get("extension") or ".md")
    return {f"{where}/{path.removeprefix('agents/').removesuffix('.md')}{extension}": text
            for path, text in found.items() if path.startswith("agents/")}


def skills_of(found: dict[str, str], harness: dict) -> dict[str, str]:
    """Each canonical skill where this harness reads skills. Copied, never rewritten: a skill is prose."""
    where = placeable(harness.get("skillsDir"))
    if where is None:
        return {}
    return {f"{where}/{path.removeprefix('skills/')}": text
            for path, text in found.items() if path.startswith("skills/")}


def files(key: str, profile: str = DEFAULT_PROFILE) -> dict[str, str]:
    """Everything this harness can be given, keyed by its path relative to a project root."""
    harness = row(key)
    found = plugin_files(profile)
    rendered: dict[str, str] = {}
    rendered.update(skills_of(found, harness))
    rendered.update(commands_of(found, harness))
    rendered.update(agents_of(found, harness))
    spec = harness.get("projectMcp")
    if isinstance(spec, dict) and placeable(spec.get("file")):
        rendered[str(spec["file"])] = mcp_file(spec)
    return rendered


def unplaceable(key: str) -> list[str]:
    """One line per thing this harness has no native location for, and what it reaches it by instead."""
    harness = row(key)
    said = []
    if placeable(harness.get("skillsDir")) is None:
        said.append(f"{name_of(key)} reads no project skills directory this can write, so the skills are "
                    f"not here. `./init` in a generated project installs its commands as skills where it "
                    f"has a skills directory and this does not")
    if not commands_of({"commands/x.md": ""}, harness):
        said.append(f"{name_of(key)} reads no markdown commands directory, so `/sail` is not installed as "
                    f"a command. `./init` in a generated project renders its own spelling "
                    f"(`commandFormat: {harness.get('commandFormat')}`)")
    if not agents_of({"agents/x.md": ""}, harness):
        said.append(f"{name_of(key)} reads no markdown agent file, so the stage delegates are not here. "
                    f"`./init` renders them in its own spelling, with each stage's model resolved")
    spec = harness.get("projectMcp")
    if not isinstance(spec, dict):
        said.append(f"{name_of(key)} has no project MCP file the registry knows "
                    f"({harness.get('projectMcpReason', 'not verified')}), so it reaches the read side by "
                    f"running `slipwai fleet` in a terminal")
    return said


def write(key: str, into, profile: str = DEFAULT_PROFILE) -> list[str]:
    """Render one harness's material into a directory, and say what was written."""
    rendered = files(key, profile)
    for path, text in rendered.items():
        place = contained(into, path)
        place.parent.mkdir(parents=True, exist_ok=True)
        with place.open("w", encoding="utf-8", newline="") as handle:
            handle.write(text)
    return sorted(rendered)

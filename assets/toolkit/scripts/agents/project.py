#!/usr/bin/env python3
"""Project the canonical skills, commands, agent types and extension pointers into native coding-agent locations."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# `models.py` beside this script resolves a stage to a model, and this script writes that model into the agent
# types it projects. Importing it rather than shelling out keeps one resolver; `dont_write_bytecode` is what
# keeps the import from leaving a `__pycache__/` beside the script — an untracked directory in the project
# that the next `git status` reports and `add-service` refuses to work around.
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

import models  # noqa: E402 — after the path that makes this script's sibling importable


def project_root(script: Path, depth: int) -> Path:
    """The repository root: the nearest directory above this script holding `project.json`.

    This script's own tree is `<root>/scripts` in a generated project and `<root>/<layout.delivery>/scripts`
    where the method was installed beside an existing codebase (`project.json`'s `layout.delivery`), so how
    far below the root it sits is not something to count; `depth` is only the fallback for a tree with no
    manifest at all.
    """
    for candidate in script.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return script.parents[depth]


ROOT = project_root(Path(__file__).resolve(), 2)
# The canonical `skills/`, `commands/` and `agents/` are siblings of this script's `scripts/`, wherever it sits.
DELIVERY = Path(__file__).resolve().parents[2]
# What the stamp names as the canonical source, from the repository root: `skills/x` in a generated project,
# `<layout.delivery>/skills/x` where the delivery material lives elsewhere.
PREFIX = "" if DELIVERY == ROOT else f"{DELIVERY.relative_to(ROOT).as_posix()}/"
REGISTRY = Path(__file__).with_name("registry.json")
AGENTS = ROOT / "AGENTS.md"
STAMP = "Generated from {source}. Edit the canonical file and rerun ./init."
CHECK = "--check" in sys.argv[1:]
LIST = "--list" in sys.argv[1:]
# `--context` projects only the extension pointers, for the pass `./init` makes after the extension hooks
# have run: the skills and commands are already in place by then and copying them again would be work with
# no change in it.
CONTEXT_ONLY = "--context" in sys.argv[1:]
FLAGS = {"--check", "--list", "--context"}
# What an extension appends to AGENTS.md to point the agent at itself (docs/extensions.md).
EXTENSION_BLOCK = re.compile(
    r"<!-- extension:([a-z0-9][a-z0-9-]*):begin -->.*?<!-- extension:\1:end -->", re.DOTALL
)
# What an `import` harness's context file carries: one line pulling AGENTS.md in, inside a marker-fenced
# region this script owns. The region is the whole of this script's claim on that file — the rest is the
# user's.
IMPORT_BEGIN = "<!-- slipwai:agents-import:begin -->"
IMPORT_END = "<!-- slipwai:agents-import:end -->"
IMPORT_REGION = f"""\
{IMPORT_BEGIN}
<!-- Maintained by scripts/agents/project.py. Write repository guidance in AGENTS.md, not here. -->
@AGENTS.md
{IMPORT_END}"""
IMPORT_REGION_PATTERN = re.compile(re.escape(IMPORT_BEGIN) + r".*?" + re.escape(IMPORT_END), re.DOTALL)
FINDINGS: list[str] = []
EXPECTED: set[Path] = set()
# What a skill says it is about, in its own frontmatter: `capabilities: frontend, react`, one line,
# comma-separated, a trailing `*` matching every capability that starts with it. A skill that declares
# nothing is about the way work is done here and belongs in every project.
DECLARATION = "capabilities:"
# Harnesses whose projection directories are absent under `--check`: not drift, a clone `./init` has not run in.
NOT_PROJECTED: list[str] = []
# The canonical agent types: one per stage `/drive` sends to a fresh context, declaring in words no harness owns
# what its delegate may write (`none`, `tasks`, `manifest`, `report`) and what it may run (`read-only`,
# `tasks-command`, `any`).
# `registry.json`'s `agentFile` says how each harness spells those, and `null` there is a harness that cannot.
NO_WRITES = "none"
TASK_WRITES = "tasks"
READ_ONLY = "read-only"
TASK_COMMAND = "tasks-command"
# A type that declares no stage takes no stage's model: `drive-slice` runs a whole slice and chooses a model
# per stage inside itself, so resolving one here would pick a model for the lot.
NO_STAGE = "none"
# The MCP servers this repository's own extensions install, spelled as the harnesses below name a server's
# whole tool surface. A `tools` list is the whole grant on Gemini and Copilot, so a read-only type that lists
# only built-ins is one that cannot reach the code index `./init --extension codegraph` just installed — the
# route drops with no error to read, which is the failure the extension's own guidance exists to prevent.
# Granting them back costs nothing that was being held: both lists already carry the whole shell, so an MCP
# tool adds no write surface `writes: none` was withholding. Gemini has a wildcard for every connected
# server; Copilot has none, so its servers are named, and an unrecognized name there is ignored rather than
# an error (docs.github.com custom-agents-configuration, Tools) — which is what makes naming one a
# repository has not configured safe. `codegraph` is the server key CodeGraph's own installer writes
# (`installer/targets/*.js` in the v1.6.0 bundle, read 2026-09-17); see registry.json's `agentFile.mcp`.
EXTENSION_MCP_SERVERS = ("codegraph",)
# Gemini CLI names every built-in tool, and a list is the only way to withhold one, so a read-only type gets
# every tool but the two that edit — `write_file` and `replace` (gemini-cli docs/tools/, read 2026-09-15) —
# plus `mcp_*`, every tool from every connected MCP server (docs/core/subagents.md, Tool wildcards,
# read 2026-09-17).
GEMINI_READING_TOOLS = ("list_directory", "read_file", "glob", "grep_search", "run_shell_command", "web_fetch",
                        "google_web_search", "mcp_*")
# Copilot's aliases, minus `edit` — and minus `agent`, since a delegate of one stage does not spawn another
# (docs.github.com custom-agents-configuration, Tool aliases, read 2026-09-15) — plus one entry per server
# above, because this harness has no wildcard for every MCP server at once.
COPILOT_READING_TOOLS = ("execute", "read", "search", "web", "todo",
                         *(f"{server}/*" for server in EXTENSION_MCP_SERVERS))


def selected_integrations(arguments: list[str]) -> list[str]:
    if arguments:
        return list(dict.fromkeys(arguments))
    state_path = ROOT / ".specify/integration.json"
    if not state_path.is_file():
        raise RuntimeError("cannot determine the selected integration; rerun ./init --integration <agent>")
    state = json.loads(state_path.read_text())
    installed = state.get("installed_integrations", [])
    if isinstance(installed, list) and installed:
        return list(dict.fromkeys(value for value in installed if isinstance(value, str)))
    default = state.get("default_integration")
    if isinstance(default, str):
        return [default]
    raise RuntimeError("Spec Kit did not record an installed integration")


def materialize(path: Path, content: str) -> None:
    EXPECTED.add(path)
    if CHECK:
        if not path.is_file():
            FINDINGS.append(f"{path.relative_to(ROOT)}: missing")
        elif path.read_text() != content:
            FINDINGS.append(f"{path.relative_to(ROOT)}: differs from its canonical source")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def parse_command(path: Path) -> tuple[str, str, str]:
    source = path.read_text()
    description = f"Run the {path.stem} project workflow"
    argument_hint = ""
    body = source
    if source.startswith("---\n"):
        end = source.find("\n---\n", 4)
        if end != -1:
            header = source[4:end]
            body = source[end + 5 :].lstrip("\n")
            for line in header.splitlines():
                key, separator, value = line.partition(":")
                if not separator:
                    continue
                if key == "description":
                    description = value.strip().strip('"')
                elif key == "argument-hint":
                    argument_hint = value.strip().strip('"')
    return description, argument_hint, body


def stamp_markdown(source: str, canonical: str) -> str:
    stamp = f"<!-- {STAMP.format(source=canonical)} -->"
    if not source.startswith("---\n"):
        return f"{stamp}\n\n{source}"
    end = source.find("\n---\n", 4)
    if end == -1:
        return f"{stamp}\n\n{source}"
    boundary = end + 5
    return f"{source[:boundary]}\n{stamp}\n{source[boundary:]}"


def command_as_skill(name: str, description: str, hint: str, body: str, source: str) -> str:
    arguments = f"\n**Arguments:** {hint}\n" if hint else ""
    return (
        "---\n"
        f"name: {name}\n"
        f"description: {json.dumps(description, ensure_ascii=False)}\n"
        "---\n\n"
        f"<!-- {STAMP.format(source=source)} -->\n"
        f"{arguments}\n{body}"
    )


def rendered_command(path: Path, harness: dict[str, object]) -> tuple[str, str]:
    name = path.stem
    source = f"{PREFIX}commands/{path.name}"
    description, hint, body = parse_command(path)
    body = body.replace("$ARGUMENTS", str(harness.get("argPlaceholder") or "$ARGUMENTS"))
    command_format = harness.get("commandFormat") or "markdown"
    if command_format == "toml":
        if "'''" in body:
            raise RuntimeError(f"{source} cannot be represented as a TOML literal string")
        rendered = (
            f"# {STAMP.format(source=source)}\n"
            f"description = {json.dumps(description, ensure_ascii=False)}\n"
            f"prompt = '''\n{body.rstrip()}\n'''\n"
        )
    elif command_format == "yaml":
        indented = "\n".join(f"  {line}" if line else "" for line in body.rstrip().splitlines())
        title = re.sub(r"[-_.]+", " ", name).title()
        rendered = (
            f"# {STAMP.format(source=source)}\n"
            "version: 1.0.0\n"
            f"title: {json.dumps(title)}\n"
            f"description: {json.dumps(description, ensure_ascii=False)}\n"
            "parameters:\n"
            "  - key: args\n"
            "    input_type: string\n"
            "    requirement: optional\n"
            "    default: ''\n"
            "    description: User input passed to the command.\n"
            "extensions:\n"
            "  - type: builtin\n"
            "    name: developer\n"
            "activities:\n"
            "  - Spec-Driven Development\n"
            f"prompt: |2\n{indented}\n"
        )
    else:
        header = ["---", f"description: {json.dumps(description, ensure_ascii=False)}"]
        if hint:
            header.append(f"argument-hint: {json.dumps(hint, ensure_ascii=False)}")
        rendered = "\n".join(header + ["---", "", f"<!-- {STAMP.format(source=source)} -->", "", body])
    return name, rendered


def parse_agent(path: Path) -> tuple[dict[str, str], str]:
    """A canonical `agents/<name>.md`: its neutral declaration, and the standing brief below it."""
    source = path.read_text()
    if not source.startswith("---\n"):
        raise RuntimeError(f"{PREFIX}agents/{path.name} has no frontmatter; a type declares name, description, "
                           "stage, writes and commands")
    end = source.find("\n---\n", 4)
    if end == -1:
        raise RuntimeError(f"{PREFIX}agents/{path.name} has an unterminated frontmatter block")
    declared = {}
    for line in source[4:end].splitlines():
        key, separator, value = line.partition(":")
        if separator:
            declared[key.strip()] = value.strip()
    missing = [key for key in ("name", "description", "stage", "writes", "commands") if not declared.get(key)]
    if missing:
        raise RuntimeError(f"{PREFIX}agents/{path.name} declares no {', '.join(missing)}")
    return declared, source[end + 5 :].lstrip("\n")


def agent_model(stage: str, harness: dict[str, object]) -> tuple[str | None, str]:
    """The model this type's stage resolves to on this harness, and why — the same resolution `/drive` reads.

    The agent file is a *projection* of `.specify/models.json`, never a second place a model is written: five
    of the six harnesses that can give a sub-task its own model can only do it here, so if this file decided
    for itself, `/who-runs` would stop being the answer to "which model runs implement".
    """
    if stage == NO_STAGE:
        return None, ("this type runs a whole slice and reads the table stage by stage inside itself, so it "
                      "inherits the session's model")
    if not models.MODELS.is_file():
        return None, f"no {models.MODELS.relative_to(ROOT)} yet, so this type inherits the session's model"
    try:
        table = json.loads(models.MODELS.read_text())
        _, model, why = models.resolve(stage, table, harness)
    except (ValueError, KeyError) as error:
        return None, f"{models.MODELS.relative_to(ROOT)} could not be read ({error}); `make check-agents` says why"
    if model is None:
        return None, f"{why}, so this type inherits the session's model"
    return model, f"`{stage}` resolves to {model} in {models.MODELS.relative_to(ROOT)}"


def agent_notes(declared: dict[str, str], file_row: dict[str, object], why: str) -> list[str]:
    """What this projection is, where its model came from, and every part of the declaration it cannot hold.

    The last of those is the point. `writes` and `commands` are asked for in words no harness owns, and no
    harness expresses all of them: Claude Code can drop the editing tools but `Bash` is one tool, granted or
    not, and an adversary has to run a reproduction. A gap written into the stamp is a gap somebody can read;
    a gap left out is one the next person assumes the harness is holding.
    """
    notes = [STAMP.format(source=f"{PREFIX}agents/{declared['name']}.md"), why + "."]
    if declared["writes"] == NO_WRITES:
        notes.append(f"`writes: none` is enforced here by {file_row['writes']}." if file_row.get("writes")
                     else "`writes: none` is NOT enforced here. This harness's agent file cannot withhold editing. "
                          "The body asks for it instead.")
    elif declared["writes"] == TASK_WRITES:
        notes.append("`writes: tasks` is the fixed scope of this slice's tasks.md. This harness can grant "
                     "workspace writes but cannot restrict them to one path; the body asks for that boundary "
                     "instead.")
    else:
        notes.append(f"`writes: {declared['writes']}` is a per-call manifest, which no agent file can name: the "
                     "brief names the files, and the body says to treat that scope literally.")
    if declared["commands"] == READ_ONLY:
        notes.append(f"`commands: read-only` is enforced here by {file_row['commands']}."
                     if file_row.get("commands") else
                     f"`commands: read-only` is NOT enforced here: {file_row.get('commandsReason')}. The body "
                     "asks for it instead.")
    elif declared["commands"] == TASK_COMMAND:
        notes.append("`commands: tasks-command` permits read-only inspection and the installed Spec Kit tasks "
                     "command only. This harness cannot express that allowlist; the body asks for it instead.")
    # And the route the body tells a delegate to take first. Withholding it is silent — a harness whose write
    # scope is a tool list withholds every MCP tool the list leaves out, and the delegate reads that as a
    # project with no code index rather than as a grant it was never given.
    mcp = file_row.get("mcp")
    if isinstance(mcp, dict):
        notes.append(f"A delegate here {mcp['reaches']}.")
        if mcp.get("grant") and declared["writes"] == NO_WRITES:
            notes.append(f"This type's tool list grants them back with {mcp['grant']}.")
    return notes


def frontmatter(entries: list[tuple[str, str]]) -> str:
    """YAML from key/value pairs; a value already written as indented lines follows its key on the next line."""
    return "".join(f"{key}:{value}\n" if value.startswith("\n") else f"{key}: {value}\n" for key, value in entries)


def rendered_agent(declared: dict[str, str], body: str, harness: dict[str, object],
                   file_row: dict[str, object]) -> str:
    """One canonical type in the spelling its harness reads, with the resolved model and the enforceable scope."""
    key = harness["key"]
    model, why = agent_model(declared["stage"], harness)
    notes = agent_notes(declared, file_row, why)
    read_only = declared["writes"] == NO_WRITES
    if key == "codex":
        if "'''" in body:
            raise RuntimeError(f"{PREFIX}agents/{declared['name']}.md cannot be represented as a TOML literal string")
        settings = [f"name = {json.dumps(declared['name'])}",
                    f"description = {json.dumps(declared['description'], ensure_ascii=False)}"]
        if model:
            settings.append(f"model = {json.dumps(model)}")
        settings.append(f"sandbox_mode = {json.dumps('read-only' if read_only else 'workspace-write')}")
        commented = "".join(f"# {note}\n" for note in notes)
        joined = "\n".join(settings)
        return f"{commented}{joined}\ndeveloper_instructions = '''\n{body.rstrip()}\n'''\n"
    entries: list[tuple[str, str]] = []
    if key != "opencode":
        entries.append(("name", declared["name"]))
    entries.append(("description", json.dumps(declared["description"], ensure_ascii=False)))
    if key == "opencode":
        entries.append(("mode", "subagent"))
    if model:
        entries.append(("model", model))
    if read_only:
        if key == "claude":
            entries.append(("disallowedTools", "Edit, Write, NotebookEdit"))
        elif key == "copilot":
            entries.append(("tools", json.dumps(list(COPILOT_READING_TOOLS))))
        elif key == "cursor-agent":
            entries.append(("readonly", "true"))
        elif key == "gemini":
            entries.append(("tools", "\n" + "\n".join(f"  - {tool}" for tool in GEMINI_READING_TOOLS)))
        elif key == "opencode":
            entries.append(("permission", "\n  edit: deny"))
    stamped = "".join(f"<!-- {note} -->\n" for note in notes)
    return f"---\n{frontmatter(entries)}---\n\n{stamped}\n{body}"


def project_agents(harness: dict[str, object]) -> None:
    """Every canonical type into this harness's own agent directory, or nothing where it has none."""
    file_row = harness.get("agentFile")
    if not isinstance(file_row, dict):
        return
    target = ROOT / str(file_row["dir"])
    for path in sorted((DELIVERY / "agents").glob("*.md")):
        declared, body = parse_agent(path)
        materialize(target / f"{declared['name']}{file_row['extension']}",
                    rendered_agent(declared, body, harness, file_row))


def copy_skills(destination: Path) -> None:
    for source in sorted((DELIVERY / "skills").rglob("*")):
        if not source.is_file():
            continue
        relative = source.relative_to(DELIVERY / "skills")
        target = destination / relative
        content = source.read_text()
        materialize(
            target,
            stamp_markdown(content, f"{PREFIX}skills/{relative.as_posix()}") if source.suffix == ".md" else content,
        )


def extension_blocks(text: str) -> list[tuple[str, str]]:
    """Every marker-fenced extension pointer in `text`, as (key, block), in the order they appear."""
    return [(match.group(1), match.group(0)) for match in EXTENSION_BLOCK.finditer(text)]


def sync_context(harness: dict[str, object]) -> None:
    """Make sure AGENTS.md reaches the file this harness actually reads, without parent-session context.

    `canonical` reads AGENTS.md itself. An `import` harness includes the whole file through a pointer this
    script owns. A `copy` harness reads a context file Spec Kit wrote before extension hooks ran, so only
    marker-fenced extension guidance is carried across afterwards. That keeps CodeGraph and every other
    optional tool visible without appending a second copy of the baseline repository context.
    """
    if not AGENTS.is_file():
        return
    context = harness.get("contextFile")
    if not isinstance(context, str):
        return
    mode = harness.get("contextMode")
    path = ROOT / context
    if mode == "import":
        write_context_import(path, str(harness.get("name") or harness.get("key")))
    elif mode == "copy":
        copy_context_blocks(path)


def write_context_import(path: Path, name: str) -> None:
    """Own a marker-fenced `@AGENTS.md` include in an import harness's context file."""
    content = path.read_text() if path.is_file() else ""
    found = IMPORT_REGION_PATTERN.search(content)
    if found is not None and found.group(0) == IMPORT_REGION:
        EXPECTED.add(path)
        return
    if CHECK:
        relative = path.relative_to(ROOT)
        if found is not None:
            FINDINGS.append(f"{relative}: its AGENTS.md import is out of date")
        else:
            missing = "carries no" if path.is_file() else "is missing, so there is no"
            FINDINGS.append(f"{relative}: {missing} import of AGENTS.md — none of it reaches a {name} session")
        return
    if found is not None:
        updated = content[: found.start()] + IMPORT_REGION + content[found.end() :]
    else:
        outside = content.rstrip("\n")
        updated = f"{outside}\n\n{IMPORT_REGION}\n" if outside.strip() else f"{IMPORT_REGION}\n"
    EXPECTED.add(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(updated)


def copy_context_blocks(path: Path) -> None:
    """Carry AGENTS.md's marker-fenced extension guidance into a copy-mode context file."""
    if not path.is_file():
        # Spec Kit wrote no context file for this harness, so there is no copy to keep in step. Silent
        # rather than a finding: an absent file is that integration's business, not a drifted projection.
        return
    content = path.read_text()
    expected = extension_blocks(AGENTS.read_text())
    findings: list[str] = []
    updated = content
    for key, block in expected:
        pattern = re.compile(
            rf"<!-- extension:{re.escape(key)}:begin -->.*?<!-- extension:{re.escape(key)}:end -->",
            re.DOTALL,
        )
        matches = list(pattern.finditer(updated))
        if len(matches) == 1 and matches[0].group(0) == block:
            continue
        findings.append(f"{key} ({'missing' if not matches else 'out of date'})")
        if not CHECK:
            if matches:
                first = matches[0]
                suffix = pattern.sub("", updated[first.end():])
                updated = updated[:first.start()] + block + suffix
            else:
                updated = updated.rstrip("\n") + f"\n\n{block}\n"
    if findings and CHECK:
        FINDINGS.append(
            f"{path.relative_to(ROOT)}: extension pointer(s) do not match AGENTS.md: {', '.join(findings)}"
        )
        return
    EXPECTED.add(path)
    if updated != content:
        materialize(path, updated)


def unprojected(directory: object) -> bool:
    """Under `--check`, whether this projection directory is simply absent.

    The projections are derived and ignored by Git — `./init`, `make agents` and `slipwai migrate` write them —
    so a fresh clone has none, and none is not drift: it is a clone nobody has run `./init` in yet, and the gate
    says so rather than failing a repository for the copy it deliberately does not commit. Judged per directory
    rather than per harness, because a harness's skills, commands and agent types land in different places: a
    version that adds one of the three finds the other two already written, and a hundred `missing` findings for
    files nobody deleted is a worse answer than one line saying `make agents` has not run yet.
    """
    return CHECK and isinstance(directory, str) and not (ROOT / directory).exists()


def project(harness: dict[str, object]) -> None:
    if CONTEXT_ONLY:
        sync_context(harness)
        return
    skills_dir = harness.get("skillsDir")
    commands_dir = harness.get("commandsDir")
    file_row = harness.get("agentFile")
    agents_dir = file_row["dir"] if isinstance(file_row, dict) else None
    absent = [directory for directory in (skills_dir, commands_dir, agents_dir) if unprojected(directory)]
    if absent:
        NOT_PROJECTED.append(f'{harness["name"]}: not projected here ({", ".join(absent)})')
    if isinstance(skills_dir, str) and skills_dir not in absent:
        skill_target = ROOT / skills_dir
        copy_skills(skill_target)
    else:
        skill_target = None

    commands = sorted((DELIVERY / "commands").glob("*.md"))
    if isinstance(commands_dir, str) and commands_dir not in absent:
        target_dir = ROOT / commands_dir
        extension = harness.get("commandExtension") or ".md"
        for command in commands:
            name, rendered = rendered_command(command, harness)
            materialize(target_dir / f"{name}{extension}", rendered)
    elif skill_target is not None:
        for command in commands:
            description, hint, body = parse_command(command)
            target = skill_target / command.stem / "SKILL.md"
            materialize(
                target,
                command_as_skill(command.stem, description, hint, body, f"{PREFIX}commands/{command.name}"),
            )

    if agents_dir not in absent:
        project_agents(harness)
    declared = [directory for directory in (skills_dir, commands_dir, agents_dir) if isinstance(directory, str)]
    if declared and len(absent) == len(declared):
        # Every one of this harness's directories is missing, so `./init` has not run in this checkout and
        # its context file is as unwritten as the rest — the same `unprojected` reasoning, which has to
        # cover the context file too or a fresh clone fails the gate for a copy nobody has made yet.
        return
    sync_context(harness)


def project_capabilities() -> set[str]:
    """What this project can do: the union of what every deployable in `project.json` declares.

    A deployable whose directory is no longer here contributes nothing — deleting the browser app is how a
    project drops its frontend, and the whole point of this check is to say so out loud rather than leave
    eleven thousand words about a backend for a frontend sitting in `skills/`.
    """
    manifest = ROOT / "project.json"
    if not manifest.is_file():
        return set()
    document = json.loads(manifest.read_text())
    deployables = document.get("deployables")
    if not isinstance(deployables, dict):
        return set()
    return {
        capability
        for deployable in deployables.values()
        if isinstance(deployable, dict) and (ROOT / str(deployable.get("path", ""))).is_dir()
        for capability in deployable.get("capabilities", [])
        if isinstance(capability, str)
    }


def declared_capabilities(text: str) -> list[str] | None:
    """The capabilities a `SKILL.md` declares, or None where it declares none and so belongs everywhere."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for line in lines[1:]:
        if line.strip() == "---":
            return None
        if line.startswith(DECLARATION):
            named = [part.strip() for part in line[len(DECLARATION):].split(",") if part.strip()]
            return named or None
    return None


def serves(declared: list[str], capabilities: set[str]) -> bool:
    """One match is enough: a skill about the browser edge earns its place as soon as there is one."""
    return any(
        any(capability.startswith(pattern[:-1]) for capability in capabilities)
        if pattern.endswith("*")
        else pattern in capabilities
        for pattern in declared
    )


def report_unjustified_skills() -> None:
    """Name every skill here that is about something this project cannot do.

    A report, never a failure. `skills/` belongs to this project once it is generated — a team that drops
    its browser app and keeps `front-end-testing` because one is coming back has made a decision, and a
    gate that failed for it would be a gate telling a repository what to want. What it is not allowed to
    be is *silent*: an irrelevant skill is context an agent is invited to load and a wrong turn
    `find-skills` can take, and nothing else in the repository would ever mention it.
    """
    capabilities = project_capabilities()
    if not capabilities:
        return
    for skill in sorted((DELIVERY / "skills").glob("*/SKILL.md")):
        declared = declared_capabilities(skill.read_text())
        if declared is None or serves(declared, capabilities):
            continue
        print(
            f"check-agents: {skill.parent.relative_to(ROOT).as_posix()} serves {', '.join(declared)}, which "
            "nothing in this project does — delete it, or `slipwai migrate` will offer to; keeping it is a "
            "choice this line only reports"
        )


def check_registry(registry: list[dict[str, object]]) -> None:
    """Every `agentFile` row is whole, or there is no row: a half-written one renders a half-true projection.

    `commands` is the exception that has to be present and may be null — a harness that cannot bound what a
    delegate runs says so with a reason, rather than by leaving the key out and letting the stamp claim an
    enforcement nobody verified.
    """
    for harness in registry:
        row = harness.get("agentFile")
        if row is None:
            continue
        if not isinstance(row, dict):
            FINDINGS.append(f"registry.json: `{harness['key']}`'s agentFile is neither an object nor null")
            continue
        for field in ("dir", "extension", "format", "model", "writes", "source"):
            if not row.get(field):
                FINDINGS.append(f"registry.json: `{harness['key']}`'s agentFile says no {field}")
        if "commands" not in row:
            FINDINGS.append(f"registry.json: `{harness['key']}`'s agentFile does not say how it bounds commands "
                            "— an identifier, or null with a `commandsReason`")
        elif row["commands"] is None and not row.get("commandsReason"):
            FINDINGS.append(f"registry.json: `{harness['key']}` cannot bound commands and says no reason why")


def list_harnesses(registry: list[dict[str, object]]) -> None:
    installed: set[str] = set()
    state_path = ROOT / ".specify/integration.json"
    if state_path.is_file():
        state = json.loads(state_path.read_text())
        installed = set(value for value in state.get("installed_integrations", []) if isinstance(value, str))
    for harness in registry:
        marker = "*" if harness["key"] in installed else " "
        support = "skills + commands" if harness.get("skillsDir") else "commands"
        if isinstance(harness.get("agentFile"), dict):
            support += " + agents"
        print(f'{marker} {harness["key"]:<18} tier {harness["tier"]}  {support:<28} {harness["name"]}')
    print("\n* installed by Spec Kit")


def main() -> None:
    registry = json.loads(REGISTRY.read_text())["harnesses"]
    if LIST:
        list_harnesses(registry)
        return
    by_key = {entry["key"]: entry for entry in registry}
    arguments = [argument for argument in sys.argv[1:] if argument not in FLAGS]
    if CHECK:
        # Before anything about projections, and whether or not Spec Kit has been initialized: a skill the
        # project has no use for is in `skills/` from the first clone, projected or not, and a registry row
        # that is half-written would render a projection that claims more than it holds.
        report_unjustified_skills()
        check_registry(registry)
    if CHECK and not arguments and not (ROOT / ".specify/integration.json").is_file():
        print("check-agents: not initialized; no projections expected yet")
        return
    selected = selected_integrations(arguments)
    for key in selected:
        harness = by_key.get(key)
        if harness is None:
            raise RuntimeError(f'unknown Spec Kit integration "{key}"')
        if harness.get("projectable") is False:
            raise RuntimeError(f'{harness["name"]} keeps its skills outside the repository and cannot be projected')
        project(harness)
        if not CHECK:
            done = ("Extension pointers projected" if CONTEXT_ONLY
                    else "Project skills, commands and agent types installed"
                    if isinstance(harness.get("agentFile"), dict)
                    else "Project skills and commands installed")
            print(f'{done} for {harness["name"]} ({key}).')
    if CHECK:
        if FINDINGS:
            raise RuntimeError("agent projection drift:\n  - " + "\n  - ".join(FINDINGS))
        for entry in NOT_PROJECTED:
            print(f"check-agents: {entry} — the projections are ignored by Git; `make agents` (or ./init) "
                  "writes them")
        if EXPECTED:
            print(f"check-agents: {len(EXPECTED)} projected files match")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError) as error:
        print(f"agent projection failed: {error}", file=sys.stderr)
        raise SystemExit(1)

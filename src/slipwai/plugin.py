"""The delivery material as a Claude Code plugin: what `./init` writes, with the project taken away.

Today the material is files in a generated project — `commands/`, `skills/`, `agents/` — and reaching it
means having generated something. A plugin is the other door: a person with no slipwai project installs one
thing and `/sail` is there.

**The plugin is rendered, never kept.** Every file in it comes out of the same function `scaffold.py` calls
for the same path — `command_files`, `agent_files`, the toolkit's own skills. Nothing here holds a second
copy of a command, which is the whole reason the slice is shaped this way: two install routes that each
carried their own `sail.md` would be two answers to what `/sail` says, both live, and the one you were
reading would be whichever you happened to open.

**A plugin cannot carry a skill that is written around a language's code.** Four of them are — the two
modelling skills, the architecture one and `testing` — because their prose is built out of
`{{example: <skill>/<id>}}` markers a *language package* answers. The keel names no language, and a plugin
is rendered with no project, so there is nobody to ask. Those four are left out whole, by the marker rather
than by a list: a skill half of whose resources resolved would be worse than one that is not there.

**The hooks are guarded, and that is not the same file as `.claude/settings.json`'s block.** The rows are
the same rows and the verbs are the same closed set `session.py` answers, so there is still one control
plane. What differs is that a plugin is installed once and used in every directory a person opens, most of
which are not projects: a command naming `scripts/agents/session.py` where there is no project would fail
on every tool call, for ever, in all of them. So each command runs the script only where it is, and where
it is, the script's own exit status — 2 refuses the call — is what the harness sees.
"""
from __future__ import annotations

import json
from pathlib import Path

from .assets import PROFILE_ROOT, TOOLKIT_ROOT, VERSION, asset_files, contained, read_faithfully
from .capabilities import pruning_capabilities
from .catalog import CATALOG
from .errors import GenerationError
from .examples import EXAMPLE_MARKER
from .layout import AT_ROOT
from .project.agent_settings import harness_hooks
from .project.agents import agent_files
from .project.commands import command_files
from .toolkit import skill_of, toolkit_treatment

#: What the plugin is called wherever a harness lists it. The keel's own name, because the material is the
#: keel's: a person who installed `slipwai` and a person who installed the plugin have the same commands.
NAME = "slipwai"
#: The one file a harness reads before it reads anything else.
MANIFEST = ".claude-plugin/plugin.json"
#: Claude Code's own moments, in the plugin's own file rather than a project's settings.
HOOKS = "hooks/hooks.json"
#: The profile a plugin is rendered for where nobody said. The standard one: the material a project gets
#: before it has decided to model anything.
DEFAULT_PROFILE = "standard"
EVENT = "event-modelling"
#: The one script every hook row points at, as a project holds it.
SESSION = "$CLAUDE_PROJECT_DIR/" + AT_ROOT.under("scripts/agents/session.py")
#: What makes a hook harmless in a directory that is not a project: absent, nothing runs and the call
#: proceeds; present, the script's own exit status is the harness's answer.
GUARD = f'! [ -f "{SESSION}" ] || '
#: What the manifest says this is, in a sentence a person reads in a plugin list.
DESCRIPTION = ("The slipwai delivery loop: `/sail` and its commands, the stage delegates, and the skills "
               "they work under — without generating a project")
KEYWORDS = ("slipwai", "delivery", "vertical-slice", "event-modeling")


def profiles() -> list[str]:
    """The profiles a plugin may be rendered for, in the catalogue's own order."""
    return list(CATALOG["profiles"])


def manifest(profile: str) -> str:
    """`.claude-plugin/plugin.json`, as somebody else's parser reads it.

    The version is `VERSION` and is not written anywhere else here: a plugin that carried its own number
    would be a second thing to bump, and the first to be wrong about which material it holds.
    """
    return json.dumps({
        "name": NAME,
        "description": DESCRIPTION if profile == DEFAULT_PROFILE else f"{DESCRIPTION}, modelled first",
        "version": VERSION,
        "author": {"name": NAME},
        "keywords": list(KEYWORDS),
    }, indent=2) + "\n"


def verbs(declared: dict) -> list[str]:
    """Every verb a table of hook rows fires, which is the closed set `session.py` answers.

    Read off the command rather than listed here, so a point added to `harness_hooks` reaches the plugin
    without this module being told: a verb the plugin did not fire would be a guard that works in a
    generated project and silently nowhere else, which is the failure the closed sets exist to end.
    """
    return sorted({
        str(hook["command"]).rsplit(" ", 1)[-1]
        for rows in declared.values() for row in rows
        for hook in row["hooks"]
    })


def guarded(declared: dict) -> dict:
    """The same rows, each command run only where the script it names is there."""
    return {
        point: [
            {**row, "hooks": [{**hook, "command": GUARD + str(hook["command"])} for hook in row["hooks"]]}
            for row in rows
        ]
        for point, rows in declared.items()
    }


def hooks_file() -> str:
    """`hooks/hooks.json`: `.claude/settings.json`'s own block, guarded, in the shape a plugin declares it."""
    return json.dumps({"hooks": guarded(harness_hooks(AT_ROOT))}, indent=2) + "\n"


#: Which of the canonical directories are read straight off the assets. `agents/` is not among them: the
#: briefs under `assets/toolkit/agents/` are the *standing* half of a type, and `agent_files` is what makes
#: a type out of one.
COPIED = ("skills/", "commands/")


def canonical_assets(profile: str) -> dict[str, str]:
    """The canonical skills and commands a plugin carries: the sources, less what needs a language."""
    found = sources(profile)
    spoken_by_a_language = languages_own(found)
    return {path: text for path, text in found.items()
            if skill_of(path) not in spoken_by_a_language and path not in spoken_by_a_language}


def sources(profile: str) -> dict[str, str]:
    """Every canonical skill and command this profile ships, as the toolkit holds it.

    The capabilities are `None` — ship all of it — for exactly the reason an adopted repository's are
    (`capabilities.pruning_capabilities`): there is no application here whose answers could withhold a
    skill, and pruning on that would be pruning on ignorance. A project prunes; a plugin cannot.

    The overlay is read after the toolkit for the same reason generation reads it after: a profile's
    rewrite of a file *is* that profile's answer for the path.
    """
    capabilities = pruning_capabilities(profile, [])
    found: dict[str, str] = {}
    for root, overlay in ((TOOLKIT_ROOT, False), (PROFILE_ROOT / profile, True)):
        if not root.is_dir():
            continue
        for source in asset_files(root):
            path = source.relative_to(root).as_posix()
            if not path.startswith(COPIED):
                continue
            treatment = toolkit_treatment(path, profile, capabilities)
            if treatment == "capability-excluded" or (not overlay and treatment != "copied"):
                continue
            found[path] = read_faithfully(source)
    return found


def languages_own(found: dict[str, str]) -> set[str]:
    """Every skill in `found` one of whose files is written around a language's own code, and every file
    outside a skill that is.

    By the marker and not by a list, so a skill that grows its first example leaves the plugin on the same
    commit rather than on the one somebody remembered.
    """
    return {skill_of(path) or path for path, text in found.items() if EXAMPLE_MARKER.search(text)}


def files(profile: str = DEFAULT_PROFILE) -> dict[str, str]:
    """Every file the plugin is, keyed by its path inside it."""
    if profile not in CATALOG["profiles"]:
        raise GenerationError(
            f"`{profile}` is not a profile this keel has. There are {len(profiles())}: "
            f"{', '.join(profiles())}. Name one of them after --profile")
    rendered = {MANIFEST: manifest(profile), HOOKS: hooks_file()}
    # The copied assets first, so that anything generated below wins where both have an opinion — the same
    # order, for the same reason, as `scaffold.project_files`.
    rendered.update(canonical_assets(profile))
    rendered.update(command_files(profile == EVENT, [], "none", AT_ROOT, None))
    rendered.update(agent_files(AT_ROOT))
    return rendered


def write(into: Path, profile: str = DEFAULT_PROFILE) -> list[str]:
    """Render the plugin into a directory, and say what was written."""
    rendered = files(profile)
    for path, text in rendered.items():
        place = contained(into, path)
        place.parent.mkdir(parents=True, exist_ok=True)
        with place.open("w", encoding="utf-8", newline="") as handle:
            handle.write(text)
    return sorted(rendered)

"""`docs/skills-and-commands.md`: which skills this project was given, which it was not, and why.

The catalogue is not the same in every project. A skill that serves a capability the project has no answer
for — a backend for a frontend with no browser app, an OAuth guide with no identity provider — is left out
(`capabilities.py`), and a page that listed the whole catalogue regardless would be the first thing an
agent read and the first thing it was wrong about. So the list is drawn from what actually shipped, and the
withheld ones are named with the capability each was waiting for: a reader who wonders where
`react-testing` went is told, rather than left to guess whether it was a mistake.
"""
from __future__ import annotations

from ..assets import TOOLKIT_ROOT, asset_files
from ..capabilities import pruning_capabilities
from ..services import App
from ..toolkit import skill_declarations, toolkit_treatment

# Not in the catalogue: `scaffold` writes it from this project's own answers, so it is in every project and
# there is no asset to read its name from.
GENERATED_SKILL = "run-the-app"


def shipped_and_withheld(profile: str, apps: list[App]) -> tuple[list[str], list[tuple[str, str]]]:
    """Every skill in the catalogue, split: the names that ship, and the (name, capabilities) that do not."""
    capabilities = pruning_capabilities(profile, apps)
    declared = skill_declarations()
    shipped, withheld = [GENERATED_SKILL], []
    for source in asset_files(TOOLKIT_ROOT / "skills"):
        if source.name != "SKILL.md":
            continue
        name = source.parent.name
        if toolkit_treatment(f"skills/{name}/SKILL.md", profile, capabilities) == "capability-excluded":
            withheld.append((name, ", ".join(declared[name] or ())))
        else:
            shipped.append(name)
    return sorted(shipped), sorted(withheld)


def withheld_section(withheld: list[tuple[str, str]]) -> str:
    if not withheld:
        return (
            "Nothing was withheld: this project has an answer for every capability the catalogue knows how "
            "to be about.\n"
        )
    rows = "\n".join(f"| `{name}` | {capabilities} |" for name, capabilities in withheld)
    return f"""The rest of the catalogue is not here, and each one is waiting for a capability this project does not
have. Gain the capability and the skills it earns arrive with it, the same way the files that list the
applications do: `slipwai add-frontend` brings the browser ones, `slipwai add-service --language typescript`
brings the TypeScript one, an identity provider brings the OAuth one. The event capabilities are the
profile's rather than an axis answer, and a standard project gains them by being replayed as an
event-modelling one.

| Not shipped | Serves |
|---|---|
{rows}
"""


def skills_page(profile: str, apps: list[App], language: str, frontend: str, command_list: str) -> str:
    """The page, for the shape this project was actually given."""
    shipped, withheld = shipped_and_withheld(profile, apps)
    listed = ", ".join(f"`{name}`" for name in shipped)
    return f"""# Skills and commands

Skills under `skills/` are active working guidance owned by this project. **{len(shipped)} of them shipped
here**, and every one is about something this project can do:

{listed}

`run-the-app` is written from this project's own answers rather than taken from the catalogue. The rest of
them carry examples in every language this project's services are written in, one labelled block per
language where there are several, and a skill whose examples have not been translated yet says so under its
title rather than being withheld — guidance in the wrong language still reads, and that is a different
question from guidance about something that is not here.

{withheld_section(withheld)}
`make check-agents` names a skill that is here and no longer justified, so a project that drops its browser
app is told rather than left carrying the pages about one.

Commands are adapted to this repository's {language} backend toolchain, `{frontend}` frontend, and
`{profile}` workflow:

{command_list}

Agent types under `agents/` are the fifth thing projected. Each stage `/drive` sends to a fresh context has
one — `drive-gaps`, `drive-tasks`, `drive-implement`, `drive-converge`, `drive-adversary`, `drive-mutation`, and
`drive-slice` for a whole slice — carrying that stage's standing brief, the model `.specify/models.json` resolves for it, and what its delegate may write and
run. `make agents` renders each into the installed harness's own agent file so the harness holds the scope
it can hold; `docs/agent-harnesses.md` says what each one can.

Run `./init --integration <agent>` to install Spec Kit's scripts, templates, workflow, and agent commands.
Those generated files are owned by Spec Kit rather than the scaffolding factory. After native Spec Kit
initialization, `./init` projects the project-owned catalogue into the selected agent's native locations.
For example, Cursor receives skills and command wrappers under `.cursor/skills/`, while Codex receives them
under `.agents/skills/`. Keep editing the canonical `skills/`, `commands/` and `agents/` files and rerun
`./init` to refresh the agent projections.
"""

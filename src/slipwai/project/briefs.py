"""The standing brief each agent type carries, read from `assets/toolkit/agents/` instead of written in Python.

Three quarters of `src/slipwai/project/` is English inside string literals, and the 350-line budget therefore
cuts a module wherever the prose happens to reach it rather than where the code has a seam: `cruise_agents.py`
held the skipper's, the hand's and the bosun's briefs only because `agents.py` had reached its budget, and no
reader looking for the bosun's words would guess to open a file named for the cruise. A brief is prose a person
edits a paragraph at a time, so it belongs where the rest of the toolkit's prose already is — one `.md` per
type, beside `skills/` and `commands/` — and what stays here is the part that is not prose: which file belongs
to which type, and the closed set of values a brief is allowed to name.

The frontmatter of a brief carries its `description` and nothing else. `name`, `stage`, `writes` and
`commands` are generated from `stage_models.STAGES`, because they are the scope a harness enforces: a file
that hand-wrote `writes: none` could disagree with the table that projects the same stage into every other
harness, and the harness would then enforce the wrong thing. A brief that names one of those four is refused
rather than merged, so the drift cannot start.

Nothing under `assets/` was templated before this — every asset is copied byte for byte — and that is the
reason the substitution below is a closed set rather than `str.format`. `format` would read every `{` in a
brief as a field, which makes a shell `${VAR}` or a JSON example an escaping question a person writing prose
should never have to think about, and it answers a misspelt name with a `KeyError` from the middle of a
generation instead of a line saying which file named what. The doubled-brace marker is the one the toolkit
already uses for language examples (`examples.py`), so a brief's placeholders look like every other
placeholder under `assets/`.

A brief is also copied into a generated project unresolved, by the same loop that copies every toolkit file,
and then written over by the resolved one at the same path — the arrangement `toolkit.py` describes for
`docs/first-slice.md`, where `scaffold` lets the generated text win by construction rather than keeping a
second list of which assets are also generated. That is why this directory holds exactly one file per type
and nothing else: a shared preamble or a note to whoever edits these would be copied in like the rest and
written over by nothing, so it would ship with its `{{make}}` still in it.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..assets import TOOLKIT_ROOT
from ..errors import GenerationError
from ..layout import Layout
from .converge_stage import levels
from .cruise_agents import (
    BOSUN,
    BROWSER,
    BROWSER_INSTALL,
    DECISIONS,
    DEMO_LOG,
    DOMAIN,
    EVIDENCE,
    OWNER_BRIEF,
)
from .design_stage import tasks_brief as design_tasks_brief
from .prose import resolve

# Where the briefs live, beside the skills and the commands a project receives.
BRIEFS = TOOLKIT_ROOT / "agents"
# What `agents.py` generates from the stage table, and what a brief may therefore never declare for itself.
DECLARED = ("name", "stage", "writes", "commands")
FENCE = "---\n"


def values(layout: Layout) -> dict[str, str]:
    """Every value a brief may name, and the whole of what one may name.

    Small on purpose. A brief says `make` where a project that keeps its delivery material in a subdirectory
    says `make -f delivery/Makefile`, it points at the paths the `/cruise` delegates read, which are declared
    once in `cruise_agents.py`, and it quotes two passages the ladder owns rather than the brief — the
    convergence levels and the design steps a styling task carries. Everything else a brief says, it says in
    its own words, which is what makes it editable without opening a Python file.
    """
    return {
        "make": layout.make,
        "convergence-levels": levels(),
        "design-tasks": design_tasks_brief(),
        "owner-brief": OWNER_BRIEF,
        "decisions": DECISIONS,
        "domain": DOMAIN,
        "demo-log": DEMO_LOG,
        "demo-evidence": EVIDENCE,
        "browser": BROWSER,
        "browser-install": BROWSER_INSTALL,
        "bosun": BOSUN,
    }


@dataclass(frozen=True)
class Brief:
    """One type's standing brief as its file holds it: the line a harness shows, and the body it shows it for."""

    summary: str
    body: str


def read(name: str) -> Brief:
    """The brief named, exactly as its file holds it, with its placeholders still in it."""
    path = BRIEFS / f"{name}.md"
    if not path.is_file():
        raise GenerationError(f"{name} has no standing brief: {path} is missing")
    return parse(name, path.read_text(encoding="utf-8"))


def parse(name: str, text: str) -> Brief:
    """A brief's frontmatter and body, or a refusal naming the file and what is wrong with it."""
    if not text.startswith(FENCE):
        raise GenerationError(f"{name}.md does not open with frontmatter carrying its description")
    head, fence, rest = text[len(FENCE):].partition(f"\n{FENCE}")
    if not fence:
        raise GenerationError(f"{name}.md opens its frontmatter and never closes it")
    fields: dict[str, str] = {}
    for line in head.splitlines():
        key, separator, value = line.partition(": ")
        if not separator:
            raise GenerationError(f"{name}.md has a frontmatter line that is not `key: value`: {line!r}")
        fields[key] = value
    declared = [key for key in DECLARED if key in fields]
    if declared:
        raise GenerationError(
            f"{name}.md declares {', '.join(declared)} in its frontmatter, which `stage_models.STAGES` "
            "generates: a brief that writes its own scope can disagree with the table every harness is "
            "projected from, and the harness would enforce whichever it was handed"
        )
    if set(fields) != {"description"}:
        raise GenerationError(
            f"{name}.md carries {sorted(fields) or 'nothing'} in its frontmatter; a brief carries exactly "
            "one field, the description a harness shows to whatever is choosing a delegate"
        )
    return Brief(fields["description"], rest.strip("\n"))


def brief(name: str, layout: Layout) -> Brief:
    """One type's brief, resolved for this project: what `agents.py` puts under the frontmatter it generates."""
    found = read(name)
    return Brief(found.summary, resolve(f"{name}.md", found.body, values(layout)))

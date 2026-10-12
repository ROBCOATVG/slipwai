"""`survey/big-picture.md` and `docs/event-model/actors.yaml`: Phase 1, written on the day of adoption.

Beside `survey/structure.md`, and for the same reason it is: both are the tree read back to the people who
own it, with the line each fact was read off, so that what follows is a confirmation rather than a quiz.
The page is the territory — who acts, what this system talks to, what starts — and the catalogue is the one
part of it that has nowhere else to live: a slice's `actor` field says who acts, and there is nowhere in
the model to say who may **not**.

Nothing here names an event. Phase 1 maps the territory and stops; a name for something that happened is a
reading of behaviour, which is `/observe`'s work against one capability (15.12).
"""
from __future__ import annotations

from ..big_picture import Actor, BigPicture, Read
from ..layout import Layout
from ..origin import Adoption

BIG_PICTURE = "survey/big-picture.md"
ACTORS = "docs/event-model/actors.yaml"


def listed(values: tuple[str, ...], empty: str) -> str:
    return ", ".join(f"`{value}`" for value in values) or empty


def actor_rows(actors: tuple[Actor, ...]) -> str:
    if not actors:
        return (
            "Nothing in the code names a role: nothing in the code names a role in a form this reading "
            "knows, so no actor is proposed and none is invented. `/gaps` below asks for them.\n"
        )
    lines = ["| Actor | Kind | Reaches | Cannot reach | Read off |", "|---|---|---|---|---|"]
    lines += [
        f"| `{actor.name}` | {actor.kind} | {listed(actor.does, '—')} | {listed(actor.cannot, '—')} | "
        f"{', '.join(f'`{where}`' for where in actor.evidence)} |"
        for actor in actors
    ]
    return "\n".join(lines) + "\n"


def read_rows(found: tuple[Read, ...], heading: str, empty: str) -> str:
    if not found:
        return f"{empty}\n"
    lines = [f"| {heading} | What the line says | Read off |", "|---|---|---|"]
    lines += [f"| `{seen.what}` | {seen.how} | `{seen.where}` |" for seen in found]
    return "\n".join(lines) + "\n"


def gap_lines(found: BigPicture) -> str:
    return "\n".join(
        f"{number}. **{gap.question}**\n\n   *Intention:* {gap.intention}\n\n   *Proceeded on:* "
        f"{gap.assumption}\n"
        for number, gap in enumerate(found.gaps, start=1)
    )


def catalogue(actors: tuple[Actor, ...]) -> str:
    """`docs/event-model/actors.yaml` in the shape the modelling skill's Phase 1 writes for every project.

    Derived here rather than asked for, with the line each row was read off kept beside it: an adopted
    repository holds the answer in its own authorisation, and asking a person for what a file says is how a
    question set becomes a wall to skim. What the file cannot derive is whether the code's rule is the
    business's rule, and that is a `/gaps` line rather than a blank.
    """
    lines = [
        "# The role catalogue: each actor, what it does, and — the part nothing else records — what it",
        "# cannot do. Derived from this repository's own routes and authorisation by `slipwai adopt`, with",
        "# the line each row was read off. `cannot` here is what the code enforces; what the *business*",
        "# means is the question `survey/big-picture.md` asks, and this file is the answer it is written",
        "# into. Keep it in step as the model grows: a new actor in a slice is a new row here.",
        "version: 1",
        "actors:",
    ]
    for actor in actors:
        lines.append(f"  - name: {actor.name}")
        lines.append(f"    kind: {actor.kind}")
        lines.append("    does: [" + ", ".join(actor.does) + "]")
        lines.append("    cannot: [" + ", ".join(actor.cannot) + "]")
        if actor.kind == "system" and not actor.cannot:
            lines.append("    # Nothing in a scheduler says what this may not do; `survey/big-picture.md` asks.")
        lines.append("    read-off: [" + ", ".join(actor.evidence) + "]")
    return "\n".join(lines) + "\n"


def big_picture_page(found: BigPicture, layout: Layout, adoption: Adoption | None = None) -> str:
    structure = layout.under("survey/structure.md")
    catalogue_path = layout.under(ACTORS)
    return f"""# The big picture

Phase 1 of the modelling method, read off this repository's own code on the day the method was installed
around it — the territory, mapped once for the whole system, which is cheap and is why it is done once
rather than per capability. Every row below was read off a line, and the line is named. Nothing was asked
of anybody to write it, and nothing here was invented: where the code says nothing, this page says that.

**This page names no event.** A name for something that happened is a reading of *behaviour* — the nine
steps against one capability, which is `/observe`'s work — and a big picture that turns `PUT /orders/:id`
into `OrderUpdated` has named a row rather than a business fact. The processes below are **proposed
slices**: a capability each, for somebody to run the nine steps against when work lands there.

## Who acts

Read off the routes and the authorisation this code already holds. `{catalogue_path}` is the same list as
the role catalogue the modelling method keeps, and is the file to edit: a slice's `actor` field says who
acts, and there is nowhere in the model to say who may not.

{actor_rows(found.actors)}
## What this system talks to

{read_rows(found.externals, "External system", "No outbound call and no inbound hook were found.")}
## What starts here

The entry points `{structure}` lists, read as what this system does. One proposed slice each.

{read_rows(found.processes, "Process", "Nothing in the tree says where anything starts.")}
## What the code cannot answer

Each question below carries what it was for and what was assumed in the meantime, because it was left by
an agent working where nobody was watching. Put them to the people who own this system, one at a time, and
write the answers into `{catalogue_path}` and the model.

{gap_lines(found)}
"""


def big_picture_files(found: BigPicture, layout: Layout, adoption: Adoption | None = None) -> dict[str, str]:
    """The page always; the role catalogue only where there is an actor to put in it.

    An empty catalogue is a file somebody fills in later from memory, which is the opposite of what it is
    for: every row in it is supposed to name the line it was read off.
    """
    files = {layout.under(BIG_PICTURE): big_picture_page(found, layout, adoption)}
    if found.actors:
        files[layout.under(ACTORS)] = catalogue(found.actors)
    return files

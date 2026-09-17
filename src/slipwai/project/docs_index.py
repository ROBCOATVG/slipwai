"""`docs/README.md`: the index a reader of a generated project lands on, and the order it reads in.

Split out of `docs.py` for the ordinary reason — that module writes the pages, this one lists them, and
the table below is most of the bytes of neither. Called last, over the complete file set, so a page
contributed by a profile, a target or an asset tree is indexed the same as a generated one.
"""
from __future__ import annotations

# One line per page a project can ship, under the heading a reader meets it. Built from files that actually ship
# (`docs_index`), so an unknown page is listed under its own title rather than silently left out.
DOC_HOOKS: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = (
    ("Start here", (
        ("getting-started.md", "bootstrap Spec Kit, run the gate, and start the first slice"),
        ("workflow.md", "the delivery loop each slice travels, drawn from the constitution to the hardening passes"),
        ("first-slice.md", "what a slice looks like on disk, and the four things that cost real debugging to learn"),
    )),
    ("This project", (
        ("whats-included.md", "everything that was generated, in one list"),
        ("architecture.md", "the hexagonal boundary, the services, and the bounded contexts they hold"),
        ("design.md", "what this project's screens look like, where each decision lives, and what a slice with a browser surface reads first"),
        ("gates.md", "what `make verify` runs, and the gates beyond it"),
        ("skills-and-commands.md", "the skill catalogue and the commands adapted to this project"),
        ("agent-harnesses.md", "how `skills/`, `commands/` and `agents/` are projected into each coding agent"),
        ("delegated-agent-safety.md", "the standing safety boundary every delegated brief references"),
        ("speckit-preset.md", "how this project's templates are installed into Spec Kit without editing it"),
        ("evolving-the-project.md", "this repository owns every file: change anything, and merge a newer factory's output when offered"),
    )),
    ("Production", (
        ("deployment.md", "what runs in AWS for this project's services and how a commit gets there, drawn from its own answers"),
        ("adr/0002-production-target.md", "why each part of the production target is what it is, and what it costs"),
    )),
    ("The event model", (
        ("event-model/README.md", "the global event model: the format of `model.yaml` and the four patterns"),
        ("event-modeling-to-code.md", "what each box in the model becomes in a file"),
    )),
    ("Decisions", (
        ("adr/0001-record-architecture-decisions.md", "the decision to record decisions, and the ADR shape"),
    )),
    ("Adopted here", (
        ("adoption.md", "how the method was installed around the code that was here, what that forfeits, and where each fact came from"),
        ("convergence.md", "where this repository stands on every ladder a generated project sits at the top of, and what is planned to move it"),
        ("change-strategy.md", "strangler fig, modular monolith in place or rewrite — and when to leave it"),
    )),
)


def docs_index(files: dict[str, str]) -> str:
    """`docs/README.md`, built from the docs the project actually ships.

    Called last, over the complete file set, so a page contributed by a profile, a target or an asset tree
    is indexed the same as a generated one. A page `DOC_HOOKS` does not know is listed under its own first
    heading, at the end — an unlisted page is how a reader fails to find a diagram that exists.
    """
    pages = {
        path.removeprefix("docs/"): text
        for path, text in files.items()
        if path.startswith("docs/") and path.endswith(".md") and path != "docs/README.md"
    }
    sections = []
    for heading, hooks in DOC_HOOKS:
        lines = [f"- [`{page}`]({page}) — {hook}" for page, hook in hooks if page in pages]
        if lines:
            sections.append(f"## {heading}\n\n" + "\n".join(lines) + "\n")
    named = {page for _, hooks in DOC_HOOKS for page, _ in hooks}
    others = []
    for page in sorted(pages):
        if page in named:
            continue
        heading = next((line[2:].strip() for line in pages[page].splitlines() if line.startswith("# ")), page)
        others.append(f"- [`{page}`]({page}) — {heading}")
    if others:
        sections.append("## Also here\n\n" + "\n".join(others) + "\n")
    return (
        "# Documentation\n\nStart with [getting started](getting-started.md), then use [the workflow](workflow.md). "
        "Every page under `docs/` is listed here.\n\n" + "\n".join(sections)
    )

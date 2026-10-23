"""The voyage's card for a repository that was adopted rather than generated: the sequence `adopt --next` reads.

The voyage's strip is a generated project's — a PRD, `./init`, the constitution, the specification — and an
adopted repository walks other steps first: the survey's candidates confirmed, the map grounded, the gate's
first run, a strategy decided. Those are read off the tree by `next_steps`, and the terminal shows them as
`slipwai adopt --next`; this is the same reading, put where a person who adopted from the board is now looking,
so the board does not end at "`./init` is done" with nothing said about what comes next.

It stands where the strip does until the repository's first specification exists, and then gives way to it:
from there on the two flows are the same one.
"""
from __future__ import annotations

from pathlib import Path

from . import next_steps
from .errors import GenerationError
from .layout import layout_of
from .manifest import apps_from_manifest, read_manifest
from .origin import adoption_of
from .page_shell import esc


def adoption_card(root: Path) -> str:
    """The sequence, each step marked, the first unfinished one as the one to do now; nothing where the
    project was generated, or has no manifest to read."""
    if not (root / "project.json").is_file():
        return ""
    try:
        document = read_manifest(root, "the board")
    except GenerationError:
        return ""
    adoption = adoption_of(document)
    if adoption is None:
        return ""
    found = next_steps.steps(root, layout_of(document), adoption, apps_from_manifest(document, True))
    # From the first specification on, an adopted repository's voyage is a generated project's: the strip
    # takes over, and this card has said all it has to say.
    if any(step.done and step.action.startswith("/speckit-specify") for step in found):
        return ""
    rows, seen = [], False
    for step in found:
        mark = "done" if step.done else ("then" if seen else "now")
        seen = seen or not step.done
        rows.append(f'<li class="{mark}"><b>{esc(mark)}</b> {esc(step.action)} — {esc(step.why)}</li>')
    return ('<div class="card" id="adoption"><h2>Where this adoption stands</h2>'
            '<p class="empty">The steps after the adoption happen in the coding agent, opened in '
            f'{esc(root.resolve())}; this card reads the tree, so it moves as they are done. '
            '<code>slipwai adopt --next</code> says the same in a terminal.</p>'
            f'<ol class="lines">{"".join(rows)}</ol></div>')

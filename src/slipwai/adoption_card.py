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
from .adoption_flow import GROUND, PRD, STRATEGY, control, key_of
from .adoption_flow import SCRIPT as STEPPING
from .errors import GenerationError
from .folder_field import SCRIPT as CHOOSING
from .ground_card import SCRIPT as GROUNDING
from .ground_card import card as ground_card
from .harness import detect, keys, name_of
from .interview_form import field_html
from .interview_page import extensions_asked
from .layout import layout_of
from .manifest import apps_from_manifest, read_manifest
from .origin import adoption_of
from .page_shell import esc
from .stack_proposal import proposed


def adoption_card(root: Path, running: bool = False) -> str:
    """The sequence, each step marked, the first unfinished one as the one to do now; nothing where the
    project was generated, or has no manifest to read. While a step is `running`, nothing to press: the
    card below follows it, and the voyage is drawn again when it ends."""
    if not (root / "project.json").is_file():
        return ""
    try:
        document = read_manifest(root, "the board")
    except GenerationError:
        return ""
    adoption = adoption_of(document)
    if adoption is None:
        return ""
    layout = layout_of(document)
    found = next_steps.steps(root, layout, adoption, apps_from_manifest(document, True))
    # From the first specification on, an adopted repository's voyage is a generated project's: the strip
    # takes over, and this card has said all it has to say.
    if any(step.done and step.action.startswith("/speckit-specify") for step in found):
        return ""
    rows, seen, now = [], False, None
    for step in found:
        now = now or (None if step.done else step)
        mark = "done" if step.done else ("then" if seen else "now")
        seen = seen or not step.done
        rows.append(f'<li class="{mark}"><b>{esc(mark)}</b> {esc(step.action)} — {esc(step.why)}</li>')
    key = key_of(now.action) if now else ""
    harness = detect(root).harness
    agents = "".join(f'<option value="{esc(one)}"{" selected" if one == harness else ""}>{esc(name_of(one))}</option>'
                     for one in keys())
    # The step the board can take itself, under the checklist: `/ground`'s questions one row at a time, or the
    # control that runs or records the step. The rest happen in the agent, and the card says which.
    here = ('<p class="empty" id="step-running">Running — the card below follows it, and this moves on when it '
            "ends.</p>" if running else
            ground_card(root) + f"<script>{GROUNDING}</script>" if key == GROUND else
            control(key, (adoption.strategy or {}).get("recommended"), agents,
                    str((root / layout.under(PRD)).resolve()) if (root / layout.under(PRD)).is_file() else "",
                    field_html(tooling) if (tooling := extensions_asked({})) else "",
                    proposed(root, document) if key == STRATEGY else None,
                    f"{document.get('name') or root.name}-next".lower().replace("_", "-"), now.action if now else ""))
    return ('<div class="card" id="adoption"><h2>Where this adoption stands</h2>'
            '<p class="empty">Read off the tree, so it moves as each step is done — on this board where it can '
            f'be, and in the coding agent opened in {esc(root.resolve())} where it cannot. '
            '<code>slipwai adopt --next</code> says the same in a terminal.</p>'
            f'<ol class="lines">{"".join(rows)}</ol>'
            + (f'{here}<pre class="said bad" id="step-said" hidden></pre><script>{STEPPING}</script>'
               f"<script>{CHOOSING}</script>"
               if here and (running or key != GROUND) else "")
            + "</div>" + (here if key == GROUND and not running else ""))

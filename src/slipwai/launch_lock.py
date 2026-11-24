"""Continue the build, locked: shown disabled, with why and the way to unlock it, never hidden.

manda's third feature was approved and modelled and the board's one next step was Continue the build, but
the button was hidden: drawing the third feature had changed two pages the second feature's verdict
covered, and `Board.held_back` held the launch until that storyboard was approved again. The reason
existed, word for word, and the only way to read it was to press a button nobody could see — so a person
looked at a page whose only control was *Open spec.md* and concluded the run had stopped for nothing.

So while the chart is the stage the person is on, the button stays in its row, disabled, and the line
under it says what holds it and links to where that is undone. Elsewhere a held launch is not the next
step, and nothing changes.
"""
from __future__ import annotations

import re
from html import escape as esc
from pathlib import Path

from .passage import Stage, current

STYLE = """
.lock-why{margin:0;padding:0;border:0;color:var(--ink-2);display:flex;flex-wrap:wrap;gap:8px 12px;align-items:center}
.lock-why b{color:var(--critical)}
.unlock{display:grid;gap:8px}
.lock-why a{font:inherit;padding:8px 14px;border-radius:8px;background:var(--brass);color:var(--paper);
  text-decoration:none;font-weight:600}
"""

#: Run by the strip's paint after the buttons are shown or hidden: the poll carries `held` beside `launchable`.
SCRIPT = """
function paintHeld(found){
  const line = document.getElementById('launch-held'), button = document.getElementById('launch');
  if (!line || !button) return;
  const held = found.held || '';
  button.hidden = !(found.launchable || held);
  button.disabled = !found.launchable;
  line.hidden = !held;
  line.querySelector('span').textContent = held;
  line.querySelector('a').hidden = !/storyboard/.test(held);
}
"""


def held_for(found: list[Stage], held: str) -> str:
    """Why Continue the build is locked, where it is the next step; `""` everywhere else."""
    now = current(found)
    return held if now is not None and now.key == "chart" else ""


#: The feature whose storyboard verdict a later drawing withdrew, as `Board.held_back` names it.
CHANGED = re.compile(r"the storyboard for (?P<feature>[\w.-]+) has changed since its verdict")


def unlock(root: Path, held: str, seat: str = "") -> str:
    """The verdict that unlocks a launch held by an earlier feature's changed storyboard, drawn right here.

    The Screens tab draws the verdict of the feature in hand only, so manda's lock said to approve 002's
    storyboard again over a page whose one Approve was 003's, already given and disabled: the person was told
    what to press and there was nothing to press. The route takes any feature's verdict; this draws its form.
    """
    from .storyboard_card import verdict_form  # noqa: PLC0415 — the page tier, reached only when locked
    from .voyage import mockup_href  # noqa: PLC0415

    found = CHANGED.search(held)
    if not found:
        return ""
    feature = found.group("feature")
    return (f'<div class="unlock"><a href="{esc(mockup_href(feature, "storyboard.html", seat))}" target="_blank" '
            f'rel="noopener">Open {esc(feature)}&#8217;s storyboard</a>{verdict_form(root, feature)}</div>')


def line(held: str, form: str = "") -> str:
    """The sentence under the locked button, always in the page so the poll can fill or empty it; `form` is
    the verdict that unlocks it, where an earlier feature's changed storyboard is what holds it (`unlock`)."""
    return (f'<p class="lock-why" id="launch-held"{"" if held else " hidden"}><b>Locked:</b> '
            f'<span>{esc(held)}</span><a href="#mockups"{"" if "storyboard" in held and not form else " hidden"}>'
            f"Open the storyboard to approve it</a></p>{form if held else ''}")

"""An answer a person placed, shown on the row they placed it from, with the way to change it.

A park's row, a question's row and a group's button each send a message now rather than write a line that
answers at once (`talk_placed`), so until the captain carries it the thing still stands on the board. What
stands with it is the answer: its words, when it was sent, where it is, and **Change my answer** while
nothing has read it — which opens the box again with the answer it replaces riding on its button, so sending
withdraws the first and places the second. There is never a second box beside a first answer.
"""
from __future__ import annotations

from typing import Any

from .page_shell import esc
from .talk_fold import clock

STYLE = """
.ask[hidden]{display:none}
.placed{display:grid;gap:2px;margin:6px 0;padding:8px 10px;border:1px solid var(--rule);border-radius:8px;
  background:var(--ground);font-size:.86rem;overflow-wrap:anywhere}
.placed small{font-size:.8rem;color:var(--ink-2)}.placed small.good{color:var(--good)}
.placed small.wait{color:var(--brass)}.placed small.bad{color:var(--critical)}
.placed button{justify-self:start;font:inherit;font-size:.8rem;padding:4px 10px;margin-top:4px;border-radius:6px;
  border:1px solid var(--rule);background:var(--paper);color:var(--ink);cursor:pointer}
"""

SCRIPT = """
// Change my answer: the box comes back, and the answer it replaces rides on its button.
document.addEventListener('click', event => {
  const change = event.target.closest('[data-change-answer]');
  if (!change) return;
  const box = document.getElementById(change.dataset.changeAnswer);
  const row = box && box.closest('.ask');
  if (!row) return;
  row.hidden = false;
  row.querySelectorAll('button.go').forEach(one => { one.dataset.replaces = change.dataset.replaces; });
  box.focus();
});
"""


def placed_html(answer: dict[str, Any] | None, box: str = "") -> str:
    """The answer, its time and where it stands; and Change my answer while it can still be taken back."""
    if not answer:
        return ""
    sent = clock(str(answer.get("t", "")))
    change = (f'<button type="button" data-change-answer="{esc(box)}" data-replaces="{esc(answer["id"])}">'
              f"Change my answer</button>") if box and answer.get("changeable") else ""
    return (f'<div class="placed"><span><b>Your answer:</b> {esc(answer.get("text", ""))}</span>'
            f'<small class="{esc(answer.get("tone", ""))}">Sent {esc(sent)} · '
            f'{esc(str(answer.get("line", "")).removeprefix("sent · "))}</small>'
            f"{change}</div>")


def every_placed(parks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The answers placed for a group's parks, where every one of them has one."""
    found = [park["answer"] for park in parks if park.get("answer")]
    return found if parks and len(found) == len(parks) else []

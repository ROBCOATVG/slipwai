"""A slice's conversation on its card: a marker and the last thing said, a one-line quick send, its window.

The card is where a slice is and what it is doing; its conversation is in its window. So the card carries
only the door to it: closed, a marker and the newest words when something in the thread is news to a person
(what "news" is, `talk_fold` says); opened, the last message with its receipt, a line to send something
after its current turn, a product question waiting on a person with a box to answer it, and **Open its
window**. The rows carry it as one field, `talk`, which `slice_card.lit` adds where the slice has a thread.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .live_page import window_address
from .page_shell import esc
from .talk_waits import IN_FLIGHT, held_line, summaries

STYLE = """
.slice .talk-new{font-size:.78rem;line-height:1.4;padding:4px 8px;border-radius:6px;background:var(--teal-soft);
  color:var(--ink);overflow-wrap:anywhere}
.slice .talk-new b{color:var(--teal);font-weight:600}
.slice .held-by{font-size:.78rem;line-height:1.4;padding:4px 8px;border-radius:6px;border:1px solid var(--brass);
  background:var(--brass-soft);color:var(--ink);overflow-wrap:anywhere}
.slice .talk-card{display:grid;gap:6px;margin:8px 0 0;padding-top:8px;border-top:1px solid var(--rule-2)}
.slice .talk-card .last{display:grid;gap:2px;padding:8px;border-radius:6px;border:1px solid var(--rule);
  background:var(--ground);font-size:.8rem;overflow-wrap:anywhere}
.slice .talk-card .last small{color:var(--ink-2)}.slice .talk-card .last small.bad{color:var(--critical)}
.slice .talk-card .last small.wait{color:var(--brass)}.slice .talk-card .last small.good{color:var(--good)}
.slice .talk-card label{font-size:.76rem;color:var(--ink-2)}
.slice .talk-card input{font:inherit;font-size:.82rem;min-height:36px;padding:0 8px;border-radius:6px;
  border:1px solid var(--rule);background:var(--paper);color:var(--ink);min-width:0;width:100%}
.slice .talk-card .row{display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.slice .talk-card button{font:inherit;font-size:.8rem;min-height:36px;padding:0 12px;border-radius:6px;cursor:pointer}
.slice .talk-card a.window{font-size:.8rem;min-height:36px;display:inline-flex;align-items:center;padding:0 12px;
  border-radius:6px;border:1px solid var(--teal);color:var(--teal);text-decoration:none}
.slice .talk-card .asked{padding:8px;border-radius:6px;border:1px solid var(--brass);background:var(--brass-soft);
  font-size:.8rem;overflow-wrap:anywhere}
.slice .talk-card .said{font-size:.76rem;color:var(--ink-3)}
"""

SCRIPT = """
// The quick send on a slice's card: a message after its current turn, or an answer to its question. Posted
// without a reload, so the board does not jump; the band repaints the card with its receipt.
document.addEventListener('click', async event => {
  const go = event.target.closest('[data-quick]');
  if (!go) return;
  const line = document.getElementById(go.dataset.box), said = go.closest('.talk-card').querySelector('.said');
  if (!line || !line.value.trim()) { if (line) line.focus(); return; }
  go.disabled = true;
  const answer = await fetch('/talk/say', {method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({fairway: go.dataset.fairway, slice: go.dataset.quick, text: line.value.trim(),
                          of: go.dataset.of || ''})});
  go.disabled = false;
  if (said) said.textContent = answer.ok ? 'Sent. Its receipt shows here in a moment.' : await answer.text();
  if (answer.ok) { line.value = ''; line.blur(); }
});
"""


def fields(root: Path, rows: list[dict[str, str]]) -> dict[str, str]:
    """The `talk` field of each row that has a conversation, keyed by slice."""
    return {slice_id: json.dumps(found) for slice_id, found in summaries(root, rows).items()}


def held(row: dict[str, str]) -> dict[str, Any]:
    try:
        found = json.loads(row.get("talk") or "{}")
    except ValueError:
        return {}
    return found if isinstance(found, dict) else {}


def marker_html(row: dict[str, str]) -> str:
    """On a closed card: the newest words, marked, while the thread holds something a person has not seen."""
    found = held(row)
    said = found.get("last") or {}
    if not found.get("new") or not said:
        return ""
    who = f"{said['who']}: " if said.get("who") else ""
    return f'<span class="talk-new"><b>New · </b>{esc(who)}{esc(said.get("text", ""))}</span>'


def held_html(row: dict[str, str]) -> str:
    """On a closed card: who holds the slice and since when, where a person paused or stopped it or its captain
    paused it — none of which any rule lifts, so the card is where it must be seen."""
    said = held_line(held(row))
    return f'<span class="held-by">{esc(said)}</span>' if said else ""


def card_html(row: dict[str, str]) -> str:
    """In an opened card: the last message and its receipt, the quick send, the question waiting on a
    person, and the door to the slice's window."""
    if not row.get("fairway"):
        return ""
    found, live = held(row), row["state"] in IN_FLIGHT
    said = found.get("last") or {}
    last = ""
    if said:
        who = f"<b>{esc(said['who'])}:</b> " if said.get("who") else ""
        receipt = f'<small class="{esc(said.get("tone", ""))}">{esc(said["line"])}</small>' if said.get("line") else ""
        last = f'<div class="last"><span>{who}{esc(said.get("text", ""))}</span>{receipt}</div>'
    box, slice_id, fairway = f"quick-{row['slice']}", esc(row["slice"]), esc(row["fairway"])
    asked = found.get("ask") or {}
    question = ""
    if asked and live:
        question = (f'<div class="asked"><b>{slice_id} asks:</b> {esc(asked.get("text", ""))}</div>'
                    f'<label for="{esc(box)}-ask">Your answer</label><input id="{esc(box)}-ask">'
                    f'<span class="row"><button type="button" class="go" data-quick="{slice_id}" data-fairway='
                    f'"{fairway}" data-box="{esc(box)}-ask" data-of="{esc(asked.get("id", ""))}">Answer</button>'
                    f"</span>")
    quick = (f'<label for="{esc(box)}">Say something to {slice_id}</label><input id="{esc(box)}" '
             f'placeholder="Goes in when its current turn ends"><span class="row"><button type="button" class="go" '
             f'data-quick="{slice_id}" data-fairway="{fairway}" data-box="{esc(box)}">Send</button>'
             f'<a class="window" href="{esc(window_address(row["fairway"], row["slice"]))}" target="_blank" '
             f'rel="noopener">Open its window</a></span>') if live else ""
    if not (last or quick or question):
        return ""
    return f'<div class="talk-card">{last}{question}{quick}<span class="said" role="status"></span></div>'

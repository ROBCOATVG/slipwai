"""A stream's captain, in a window of its own: its slices at a glance, what it decided today, its conversation.

What is said to a stream as a whole goes to its captain, which works out which of its slices it is for and
sends it on; this is where that is said and where the captain says what it did. Its slices are a line each,
each opening that slice's window. What it decided is read from the orders it gave and the events the rule
closed in its place (`captain_files`), and its conversation is `talk/<stream>/_captain/` with the same
receipts a slice's has — beside each message, the slices its captain sent it on to.

A project whose captain is the program alone has a window too, saying so, with its slices still listed: the
program starts slices in chart order, retries by its fixed rule and parks what it cannot decide.
The captain's whole log, deck and harbour lines with its output, stays in its log window (`captain_page`).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import quote

from .board_read import read
from .captain_files import agent, decided_today, routes, said_to_you
from .deck import feature_of
from .live_page import window_address
from .page_shell import document, esc
from .slice_card import chip_of, step_now
from .talk_fold import clock
from .talk_page import SCRIPT as TALK_SCRIPT
from .talk_page import SHOWN, pane, payload
from .talk_page import STYLE as TALK_STYLE

STYLE = TALK_STYLE + """
.cap-win{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.2fr);gap:18px;align-items:start}
@media (max-width:900px){.cap-win{grid-template-columns:minmax(0,1fr)}}
.cap-win>*{min-width:0}
.cap-win .card{margin-top:0}
.cap-win .side{display:grid;gap:18px}
.cap-slices{list-style:none;margin:0;padding:0;display:grid;gap:6px}
.cap-slices a{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:2px 10px;align-items:baseline;min-height:44px;
  padding:6px 10px;border:1px solid var(--rule);border-radius:8px;color:inherit;text-decoration:none}
.cap-slices a:hover{border-color:var(--teal)}
.cap-slices b{font-weight:500;overflow-wrap:anywhere}.cap-slices .state{font-size:.78rem;color:var(--ink-3)}
.cap-slices .where{grid-column:1 / -1;font-size:.82rem;color:var(--ink-2)}
.cap-slices .waiting .state{color:var(--critical)}
.decided{list-style:none;margin:0;padding:0;display:grid;gap:6px;font-size:.86rem}
.decided li{display:grid;grid-template-columns:44px minmax(0,1fr);gap:8px;overflow-wrap:anywhere}
.decided .t{font-family:var(--mono);font-size:.76rem;color:var(--ink-3)}
.decided small{display:block;color:var(--ink-3)}.decided small.bad{color:var(--critical)}
.decided small.wait{color:var(--brass)}
.program{border-left:3px solid var(--rule);padding:4px 0 4px 10px;color:var(--ink-2);font-size:.86rem;margin:0}
"""

#: What a stream's captain is, where no agent is in it.
PROGRAM = ("This stream's captain is the program alone: it starts its slices in chart order, retries a failed gate "
           "by its fixed rule and parks what it cannot decide. It decides nothing else, so there is nothing "
           "listed here. What you say to it waits in its inbox for a captain agent; to change what a slice is "
           "doing now, say it in that slice's own window.")
ORDER = {"waiting": 0, "working": 1, "queued": 2}


def address(fairway: str) -> str:
    return f"/captain-window?fairway={quote(fairway, safe='')}"


def slices_html(rows: list[dict[str, str]], fairway: str) -> str:
    """Its slices in flight, waiting first, each opening its window; and how many are still to do or done."""
    mine = [row for row in rows if row.get("fairway") == fairway]
    flying = sorted((row for row in mine if row["state"] in ORDER), key=lambda row: ORDER[row["state"]])
    lines = ""
    for row in flying:
        name = f'{row["slice"]} · {row["title"]}' if row.get("title") else row["slice"]
        where = step_now(row) or row.get("live", "") or row.get("why", "")
        lines += (f'<li><a class="{esc(row["state"])}" href="{esc(window_address(fairway, row["slice"]))}" '
                  f'target="_blank" rel="noopener"><b>{esc(name)}</b>'
                  f'<span class="state">{esc(chip_of(row) or row["state"])}'
                  f'</span><span class="where">{esc(where)}</span></a></li>')
    rest = [f"{len([r for r in mine if r['state'] == state])} {word}"
            for state, word in (("todo", "to do"), ("done", "done")) if any(r["state"] == state for r in mine)]
    tail = f'<p class="empty">{esc(" · ".join(rest))}</p>' if rest else ""
    listed = (f'<ul class="cap-slices">{lines}</ul>' if lines
              else '<p class="empty">None of its slices is in flight.</p>')
    return f'<div class="card"><h2>Its slices</h2>{listed}{tail}</div>'


def decided_html(root: Path, fairway: str) -> str:
    if not agent(root, fairway):
        return f'<div class="card"><h2>What it decided today</h2><p class="program">{esc(PROGRAM)}</p></div>'
    lines = "".join(f'<li><span class="t">{esc(clock(one["t"]))}</span><span>{esc(one["text"])}'
                    f'<small class="{esc(one["tone"])}">{esc(one["after"])}</small></span></li>'
                    for one in decided_today(root, fairway))
    shown = f'<ul class="decided">{lines}</ul>' if lines else '<p class="empty">Nothing yet today.</p>'
    return f'<div class="card"><h2>What it decided today</h2>{shown}</div>'


def talk_parts(root: Path, fairway: str) -> tuple[list[dict[str, Any]], dict[str, str], int]:
    """The captain's own words, from its `say` and `ask` orders; beside each of a person's messages, where it
    went; and how many lines speak to a person beyond the thread's."""
    extra = [{"kind": "agent", "t": one["t"], "who": f"Captain · {fairway}" + (" asks" if one["verb"] == "ask" else ""),
              "text": one["text"]} for one in said_to_you(root, fairway)]
    went = routes(root, fairway)
    sent = {ident: f"went to {', '.join(named)}" for ident, named in went.items() if named}
    return extra, sent, len(extra)


def window_payload(root: Path, fairway: str, limit: int = SHOWN) -> str:
    kept = read(root)
    extra, sent, said = talk_parts(root, fairway)
    found = payload(root, fairway, "", extra, sent, said, limit)
    found.update(slices=slices_html(kept.rows, fairway), decided=decided_html(root, fairway))
    return json.dumps(found, ensure_ascii=False)


SCRIPT = TALK_SCRIPT + """
// The slices and what it decided move with the conversation's own poll, each swapped when its words moved.
document.addEventListener('talk:found', event => {
  for (const name of ['slices', 'decided']) {
    const node = document.querySelector('[data-cap="' + name + '"]');
    if (node && event.detail[name] !== undefined && node.dataset.said !== event.detail[name]) {
      node.innerHTML = event.detail[name];
      node.dataset.said = event.detail[name];
    }
  }
});
"""


def page(root: Path, fairway: str) -> tuple[int, str]:
    """The window, or a 404 naming the streams this project has."""
    if not feature_of(root, fairway):
        return 404, document(f"No stream called {fairway}", "captain", f'<div class="card"><p>This project has no '
                             f"stream called <code>{esc(fairway)}</code>.</p></div>", now="/captain")
    kept = read(root)
    extra, sent, said = talk_parts(root, fairway)
    poll = f"/captain-window.json?fairway={quote(fairway, safe='')}"
    log = f'/captain?fairway={quote(fairway, safe="")}'
    body = (f"<style>{STYLE}</style><p class=\"empty\">One stream's captain: it decides what starts, retries and "
            f'parks, and who hears what. <a href="{esc(log)}" target="_blank" rel="noopener">Its whole log</a></p>'
            f'<div class="cap-win"><div class="side"><div data-cap="slices">{slices_html(kept.rows, fairway)}</div>'
            f'<div data-cap="decided">{decided_html(root, fairway)}</div></div>'
            f"{pane(root, fairway, '', poll, extra, sent, said)}</div>")
    return 200, document(f"Captain · {fairway}", f"{root.resolve().name} · {feature_of(root, fairway)}", body,
                         SCRIPT, now="/captain")

"""The captains on the board: a button a stream, Tell every captain, and Ask about this project.

Under *Waiting on you* and above the tabs, one button a stream says what its slices are doing — *2 at work ·
1 queued · 1 waiting on you* — and carries a marker when its captain has said something a person has not
seen; it opens that captain's window. Beside them, **Tell every captain**: one message placed in each
captain's inbox, with a line a captain underneath saying where its copy stands and, once the captain has
routed it, which slices it went to. And **Ask about this project**, which opens the console that is already
on the page: it reads the run and answers, and never acts — what a person wants done goes to a captain or a
slice. A band of the one poll, so the states and the lines under the message move with the rest.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from . import talk
from .captain_files import routed, said_to_you
from .page_shell import esc
from .talk_card import SCRIPT as CARD_SCRIPT
from .talk_card import STYLE as CARD_STYLE
from .talk_fold import heard as thread_heard
from .talk_fold import seen, unseen
from .talk_placed import running
from .talk_placed import said as placed_said
from .talk_said import every_stream, home, told_all
from .talk_waits import captain_window

STYLE = CARD_STYLE + """
#captains{display:grid;gap:8px;margin-top:18px}
#captains .say{font-size:.82rem;color:var(--ink-2);margin:0}
#captains .row{display:flex;flex-wrap:wrap;gap:8px;align-items:stretch}
#captains a.cap{flex:1 1 200px;min-height:56px;display:flex;flex-direction:column;justify-content:center;gap:2px;
  padding:8px 12px;border-radius:8px;border:1px solid var(--rule);background:var(--paper);color:inherit;
  text-decoration:none}
#captains a.cap:hover{border-color:var(--teal)}
#captains a.cap.new{border-color:var(--teal);box-shadow:inset 3px 0 0 var(--teal)}
#captains a.cap b{font-weight:600;font-size:.88rem}#captains a.cap b i{font-style:normal;font-weight:400;
  font-size:.78rem;color:var(--teal)}
#captains a.cap span{font-size:.8rem;color:var(--ink-2)}
#captains .row>details,#captains .row>button{flex:0 0 auto}
#captains summary,#captains button.ask-console{list-style:none;min-height:56px;display:flex;align-items:center;
  padding:0 16px;border-radius:8px;border:1px solid var(--teal);color:var(--teal);cursor:pointer;font:inherit;
  font-size:.86rem;background:transparent}
#captains summary::-webkit-details-marker{display:none}
#captains button.ask-console{border-color:var(--rule);color:var(--ink)}
#captains details[open]{flex:1 1 100%}
#captains details[open] summary{display:none}
#captains .all{display:grid;gap:8px;padding:12px 14px;border:1px solid var(--teal);border-radius:8px;
  background:var(--paper)}
#captains .all label{font-size:.82rem;color:var(--ink-2)}
#captains .all .ask{margin-top:0;flex-wrap:wrap}
#captains .all .ask input{min-width:0;flex:1 1 240px;min-height:44px}
#captains .told{display:grid;gap:3px;padding:8px 10px;border:1px solid var(--rule);border-radius:6px;font-size:.84rem;
  overflow-wrap:anywhere}
#captains .told span{font-size:.8rem;color:var(--ink-2)}#captains .told span.good{color:var(--good)}
#captains .told span.bad{color:var(--critical)}#captains .told span.wait{color:var(--brass)}
#captains .fault{color:var(--critical);font-size:.82rem;margin:0}
"""

SCRIPT = CARD_SCRIPT + """
// Tell every captain, and the console opened from the strip: no reload, so the board does not jump.
document.addEventListener('click', async event => {
  if (event.target.closest('[data-open-console]')) {
    const launch = document.querySelector('#console .launch'), panel = document.querySelector('#console .panel');
    if (launch && panel && panel.hidden) launch.click();
    return;
  }
  const go = event.target.closest('[data-tell-all]');
  if (!go) return;
  const box = document.getElementById('tell-all'), fault = document.querySelector('#captains .fault');
  if (!box.value.trim()) { box.focus(); return; }
  go.disabled = true;
  const answer = await fetch('/talk/all', {method: 'POST', headers: {'Content-Type': 'application/json'},
                                           body: JSON.stringify({message: box.value.trim()})});
  go.disabled = false;
  fault.textContent = answer.ok ? '' : await answer.text();
  if (answer.ok) { box.value = ''; box.blur(); }
});
"""


def state(rows: list[dict[str, str]], fairway: str, held: set[str]) -> str:
    """A stream's slices in a line: how many are at work, queued, and waiting on a person."""
    mine = [row for row in rows if row.get("fairway") == fairway]
    waiting = len([row for row in mine if row["slice"] in held])
    working = len([row for row in mine if row["state"] == "working" and row["slice"] not in held])
    queued = len([row for row in mine if row["state"] in ("queued", "waiting") and row["slice"] not in held])
    parts = [f"{working} at work"] + ([f"{queued} queued"] if queued else []) \
        + ([f"{waiting} waiting on you"] if waiting else [])
    return " · ".join(parts)


def heard(root: Path, fairway: str) -> int:
    """How many lines of a captain's conversation speak to a person: its thread's and its own words."""
    return thread_heard(talk.thread(home(root, fairway))) + len(said_to_you(root, fairway))


def told_lines(root: Path, record: dict[str, Any], live: bool) -> str:
    """Under a "Tell every captain": where each captain's copy honestly stands, and the slices it went to."""
    lines = ""
    for fairway, ident in sorted(record["ids"].items()):
        try:
            said, tone = placed_said(root, fairway, "", str(ident), live)
        except ValueError:
            continue
        went = routed(root, fairway, str(ident))
        if went:
            said, tone = f"{said} · went to {', '.join(went)}", "good"
        lines += f'<span class="{esc(tone)}">Captain · {esc(fairway)} · {esc(said)}</span>'
    return (f'<div class="told"><b>You told every captain:</b> {esc(record.get("text", ""))}{lines}</div>')


def strip_html(root: Path, rows: list[dict[str, str]], held: set[str]) -> str:
    """The captains, one button a stream, with Tell every captain and Ask about this project beside them.
    Nothing where the project has no stream yet: there is no captain to open."""
    streams = every_stream(root)
    if not streams:
        return ""
    kept = seen(root)
    buttons = ""
    for fairway in streams:
        try:
            fresh = unseen(root, fairway, "", heard(root, fairway), kept)
        except ValueError:
            continue
        mark = " <i>· new</i>" if fresh else ""
        buttons += (f'<a class="cap{" new" if fresh else ""}" href="{esc(captain_window(fairway))}" target="_blank" '
                    f'rel="noopener"><b>Captain · {esc(fairway)}{mark}</b>'
                    f"<span>{esc(state(rows, fairway, held))}</span></a>")
    records = told_all(root)
    live = running(root)
    told = "".join(told_lines(root, one, live) for one in records)
    tell = (f'<details id="tell-every"{" open" if records else ""}><summary>Tell every captain</summary>'
            f'<div class="all"><label for="tell-all">One message to every captain. Each works out which of its own '
            f"slices it is for, and its line below says where it went.</label><div class=\"ask\">"
            f'<input id="tell-all" autocomplete="off"><button type="button" class="go" data-tell-all>Tell every '
            f'captain</button></div><p class="fault" role="alert"></p>{told}</div></details>')
    return (f'<div id="captains"><p class="say">Captains, one a stream. Open one to see what it decided and to tell '
            f'its slices something.</p><div class="row">{buttons}{tell}<button type="button" class="ask-console" '
            f'data-open-console>Ask about this project</button></div></div>')

"""The Next features tab of the Voyage window: the ideas that wait, and the way to hand over another.

Two acts, kept apart. *Hand over a further feature* is a conversation with the project's agent
(`intake_talk.py`) that ends in one idea captured under `docs/intake/`; *Continue the next feature* is the
person's yes that an idea is a new feature, and then its assessment. The tab is there once the project has
its first specification, with ideas waiting or without: before this the card was drawn only when an idea
already existed, and the only way to make one was a terminal.

**The box is not repainted.** This card is in none of the bands the window's poll swaps (`voyage_live.py`),
and its own poll only ever appends turns to the log above the box: what a person is typing, and a file they
have chosen, are never taken away. The window reloads when an idea appears, and holds that reload while a box
on the page holds words.

Everything the agent said is drawn with `textContent` by the cards every conversation on the board shares
(`turn_cards.py`); the styles here are the console's and the first page's, under this card's own id.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .errors import Busy
from .init_run import assess
from .intake_document import LIMIT
from .intake_talk import for_root
from .page_shell import esc
from .passage import specifications
from .project.intake import CONFIRMED, PLACE, ideas

TEXT = "text/plain; charset=utf-8"
#: What the earliest-idea button answers with nothing to move: where an idea starts, on this tab or off it.
NOTHING = ("nothing waiting under docs/intake; hand over a further feature in the box on this tab, or to /sail "
           "in the agent")

STYLE = """
#handover{display:grid;gap:8px;margin-top:16px;border-top:1px solid var(--rule-2);padding-top:12px}
#handover .head{display:flex;align-items:baseline;gap:10px}
#handover h3{font-size:.85rem;font-weight:500;color:var(--ink-2);margin:0}
#handover .head button{font:inherit;font-size:.8rem;background:none;border:0;color:var(--ink-3);cursor:pointer;
  white-space:nowrap}
#handover .log{max-height:min(26rem,50vh);overflow:auto;display:grid;gap:8px;align-content:start;padding:2px}
#handover .log:empty{display:none}
#handover .turn{max-width:min(46rem,92%);padding:8px 12px;border-radius:10px;border:1px solid var(--rule);
  white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.45;font-size:.9rem}
#handover .turn.person{justify-self:end;background:var(--teal);border-color:var(--teal);color:#fff}
#handover .turn.agent{justify-self:start;background:var(--paper)}
#handover .turn.attached{justify-self:end;border:0;padding:0 4px;color:var(--ink-3);font-size:.78rem}
#handover .turn.attached::before{content:"Attached · "}
#handover .turn.error{justify-self:start;border-color:var(--brass);color:var(--brass)}
#handover form{display:grid;gap:6px;margin:0}
#handover form>label{font-size:.85rem;font-weight:500;color:var(--ink-2)}
#handover textarea{width:100%;box-sizing:border-box;min-height:6rem;font:inherit;font-size:.9rem;padding:8px 10px;
  border:1px solid var(--rule);border-radius:8px;background:var(--paper);color:var(--ink);resize:vertical}
#handover label.file{display:flex;align-items:center;gap:10px;font-size:.84rem;color:var(--ink-3);cursor:pointer}
#handover label.file input{position:absolute;width:1px;height:1px;opacity:0}
#handover .pick{display:inline-block;font-size:.84rem;padding:6px 12px;border-radius:8px;
  border:1px solid var(--rule);background:var(--paper);color:var(--ink-2)}
#handover label.file:focus-within .pick{outline:2px solid var(--teal);outline-offset:1px}
#handover .row{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
#handover .said{color:var(--brass);font-size:.88rem;margin:0}
"""

SCRIPT = """
// Next features: the earliest idea moved on, and the hand-over's conversation. Its poll appends turns to the
// log and paints the buttons; it never touches the box or the chosen file, which may hold a person's words.
document.addEventListener('click', event => {
  if (event.target.id === 'intake-go') { event.target.disabled = true; send('/intake', {}); }
});
{
  const home = document.getElementById('handover');
  if (home) {
    const log = home.querySelector('.log'), box = home.querySelector('textarea');
    const file = home.querySelector('input[type=file]'), named = home.querySelector('.name');
    const go = home.querySelector('button[type=submit]'), stop = home.querySelector('button.stop');
    const take = home.querySelector('[data-capture]'), fault = home.querySelector('.said');
    const on = home.querySelector('.on'), again = home.querySelector('[data-clear]');
    let at = 0, busy = false, timer = null;
    const post = (where, body) => fetch(where, {method: 'POST', headers: {'Content-Type': 'application/json'},
                                                 body: JSON.stringify(body)});
    const refuse = words => { fault.textContent = words; fault.hidden = !words; };
    const draw = turn => drawTurn(log, turn, (id, body) => post('/handover/answer', {id, ...body}));
    const paint = said => {
      go.disabled = busy; stop.hidden = !busy;
      go.textContent = busy ? (said && said.thinking ? 'Thinking…' : 'Reading…') : 'Say';
      if (!said) return;
      take.hidden = !said.ready; again.hidden = !said.open;
      on.textContent = said.agent ? 'on ' + said.agent + (said.model ? ' · ' + said.model : '') : '';
    };
    const poll = async () => {
      let said;
      try { said = await (await fetch('/handover.json?since=' + at)).json(); }
      catch (gone) { return; }   // the board went away: stop asking
      const stuck = log.scrollTop + log.clientHeight >= log.scrollHeight - 24;
      said.turns.forEach(draw);
      at = said.at; busy = said.busy;
      drawWaiting(log, busy, said.thinking);
      if (stuck) log.scrollTop = log.scrollHeight;
      paint(said);
      clearTimeout(timer);
      timer = setTimeout(poll, busy ? 700 : 4000);  // and while idle, for a turn another window started
    };
    file.addEventListener('change', () => {
      const one = file.files && file.files[0];
      named.textContent = one ? one.name : '';
    });
    home.querySelector('form').addEventListener('submit', async event => {
      event.preventDefault();
      if (busy) return;
      const one = file.files && file.files[0], body = {message: box.value};
      if (!box.value.trim() && !one) { refuse('Say what the feature is, or choose its document.'); return; }
      if (one && one.size > %LIMIT%) { refuse(one.name + ' is more than %KB% KB.'); return; }
      if (one) body.document = {name: one.name, text: await one.text()};
      go.disabled = true;
      const answer = await post('/handover/say', body);
      if (answer.status === 409) { busy = true; paint(); poll(); return; }  // another window's turn
      if (!answer.ok) { refuse(await answer.text()); go.disabled = false; return; }
      refuse(''); box.value = ''; file.value = ''; named.textContent = '';
      busy = true; drawWaiting(log, true, false); paint(); poll();
    });
    stop.addEventListener('click', () => post('/handover/cancel', {}));
    const emptied = () => { log.querySelectorAll('.turn').forEach(one => one.remove()); on.textContent = ''; };
    again.addEventListener('click', async () => { await post('/handover/reset', {}); emptied(); poll(); });
    take.addEventListener('click', async () => {
      take.disabled = true;
      const answer = await post('/handover/capture', {});
      take.disabled = false;
      refuse(await answer.text());
      if (!answer.ok) return;
      emptied(); take.hidden = true;
      // The idea is a new card on this tab: drawn by a reload, unless the box holds the next thing to say.
      if (!box.value.trim() && !file.value) location.reload(); else poll();
    });
    poll();
  }
}
""".replace("%LIMIT%", str(LIMIT)).replace("%KB%", str(LIMIT // 1024))


def handover_html() -> str:
    """The hand-over: the conversation's log, written empty and filled by the script, and the box under it."""
    return ('<div id="handover"><div class="head"><h3>Hand over a further feature</h3><span class="on"></span>'
            '<button type="button" data-clear hidden>Start again</button></div>'
            '<p class="empty">Say what it is, or attach its document. The project\'s agent reads it, asks what '
            "it needs to, and says when it is one clear idea; Capture this idea then writes it under "
            f"<code>{PLACE}/</code>. Nothing is assessed or built until you press Continue the next feature.</p>"
            '<div class="log turns" role="log" aria-live="polite"></div>'
            '<form><label for="handover-said">The feature, in your words</label>'
            '<textarea id="handover-said" placeholder="What it is and who it is for. Text from a document can be '
            'pasted here too."></textarea>'
            '<label class="file"><input type="file" accept=".md,.txt,text/*"><span class="pick">Attach a document'
            f'</span><span class="name"></span><span>Markdown or plain text, up to {LIMIT // 1024} KB</span></label>'
            '<div class="row"><button class="go" type="submit">Say</button>'
            '<button class="stop" type="button" hidden>Stop</button>'
            '<button class="go" type="button" data-capture hidden>Capture this idea</button></div>'
            '<p class="said" role="status" hidden></p></form></div>')


def next_features(root: Path, found: list) -> str:
    """The card: each idea not yet specified or killed, the button that moves the earliest, and — once the
    project has its first specification — the hand-over, whether or not anything waits."""
    pending = [one for one in found if one.state not in ("specified", "kill")]
    specified = bool(specifications(root))
    if not pending and not specified:
        return ""
    rows = "".join(f"<p><b>{esc(one.slug)}</b> — {esc(one.state)}. {esc(one.detail)}</p>" for one in pending)
    move = '<div class="ask"><button class="go" id="intake-go">Continue the next feature</button></div>'
    none = '<p class="empty">No idea is waiting. A further feature starts here, or with /sail in the agent.</p>'
    return (f'<div class="card" id="intake"><h2>Next features</h2>{rows + move if pending else none}'
            f'{handover_html() if specified else ""}</div>')


def carry_on(bridge: Any) -> str:
    """*Continue the next feature*: the earliest waiting idea confirmed, or assessed once it is."""
    pending = [one for one in ideas(bridge.root) if one.state not in ("specified", "kill")]
    if not pending:
        raise ValueError(NOTHING)
    idea = pending[0]
    if idea.state == "confirm":
        (bridge.root / PLACE / idea.slug / CONFIRMED).write_text("yes\nperson\n", encoding="utf-8")
        return f"confirmed {idea.slug}"
    if idea.state not in ("assessing", "go", "changed"):
        raise ValueError(f"{idea.slug} is {idea.state}; /sail is what moves an idea in that state")
    if bridge.fitting and not bridge.fitting.said()["done"]:
        raise ValueError("this board is already running something; wait for it to finish, "
                         f"then press Continue the next feature for {idea.slug}")
    bridge.fitting = assess(bridge.root, idea.slug, bridge.fitting.said()["lines"] if bridge.fitting else None)
    return f"assessing {idea.slug}"


def route_get(bridge: Any, where: str, query: str) -> bool:
    """`/handover.json`: the conversation's turns after `since`, and a kept one picked up again."""
    if where != "/handover.json":
        return False
    from .seats import parameter  # noqa: PLC0415 — the one thing here that reads an address

    since = parameter(query, "since")
    talk = for_root(bridge.root)
    talk.resume()
    bridge.send(200, json.dumps(talk.said(int(since) if since.isdigit() else 0)), "application/json; charset=utf-8")
    return True


def route_post(bridge: Any, where: str, held: dict) -> bool:
    """The tab's POSTs — the earliest idea moved on, and a turn, a card's answer, a stop, a new conversation or
    the capture of the hand-over — or `False` where it was none of them."""
    if where != "/intake" and not where.startswith("/handover/"):
        return False
    try:
        if where == "/intake":
            said = carry_on(bridge)
        elif where == "/handover/say":
            if not specifications(bridge.root):
                raise ValueError("this project has no specification yet: its first feature is drafted from "
                                 "docs/prd.md, with Draft the specification on this window")
            document = held.get("document")
            if document is not None and not isinstance(document, dict):
                raise ValueError("a document is posted as its name and its text")
            said = for_root(bridge.root).ask(str(held.get("message") or ""), document)
        elif where == "/handover/answer":
            given = None if held.get("decline") else held.get("option") or held.get("answer")
            if not for_root(bridge.root).answer(str(held.get("id") or ""), None if given is None else str(given)):
                raise ValueError("nothing is waiting on that answer")
            said = "answered"
        elif where == "/handover/cancel":
            said = for_root(bridge.root).cancel()
        elif where == "/handover/reset":
            said = for_root(bridge.root).reset()
        elif where == "/handover/capture":
            said = for_root(bridge.root).capture()
        else:
            return False
        bridge.send(200, said, TEXT)
    except Busy as wait:
        bridge.send(409, str(wait), TEXT)  # a turn under way: the page waits
    except (ValueError, OSError) as refused:
        bridge.send(400, str(refused) or type(refused).__name__, TEXT)
    return True

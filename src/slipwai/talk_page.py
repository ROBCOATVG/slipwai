"""A conversation, drawn: for a slice's window and a captain's, in the look the first page's turns have.

What a person said is a turn on the right with its receipt beneath it; what the agent answered, asked or did
is on the left; a pause, a resume or a stop is a quiet line saying who made it. Under the turns, a box with
**Send** (after the turn under way) and **Interrupt** (now) — or, where the thread says the slice runs in print
mode, the sentence saying why there is none — and beside a slice's, **Pause**, **Resume** and **Stop**, each
with what it does.

**The poll swaps only the turns and the controls**, and each only when what it says has moved, nobody is
typing in it and nothing in it is focused: the box is never redrawn, an answer half-typed into an ask's card
is not thrown away, a card a person opened stays open, and the turns stay where they were scrolled — at the
foot when they were at the foot. Every word is escaped here: a message's text is whatever a person typed.
"""
# budget: 360 — an ask drawn three ways, a captain's own among them, with the box and buttons each one needs
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .board_read import read
from .page_shell import esc
from .talk_fold import person_answers, placed_for, turns
from .talk_said import home
from .turn_cards import STYLE as CARDS

STYLE = CARDS + """
.talk{display:flex;flex-direction:column;gap:10px;min-width:0}
.talk h2{margin:0}
.talk .talk-log{display:grid;gap:8px;align-content:start;max-height:min(60vh,560px);overflow:auto;
  overscroll-behavior:contain;padding:2px 2px 6px}
.talk .turn{max-width:min(40rem,92%);padding:8px 12px;border-radius:10px;border:1px solid var(--rule);
  overflow-wrap:anywhere;line-height:1.45;font-size:.9rem;white-space:pre-wrap;display:grid;gap:4px}
.talk .turn .who{font-size:.76rem;font-weight:500;white-space:normal}
.talk .turn.person{justify-self:end;background:var(--teal);border-color:var(--teal);color:var(--paper)}
.talk .turn.agent{justify-self:start;background:var(--paper)}
.talk .turn.agent .who{color:var(--teal)}
.talk .turn.note{justify-self:center;border:0;margin:0;padding:0 4px;color:var(--ink-3);font-size:.8rem;
  text-align:center}
.talk .said{display:grid;justify-items:end;gap:4px}
.talk .receipt{font-size:.78rem;color:var(--ink-2);text-align:right;max-width:min(40rem,92%)}
.talk .receipt.good{color:var(--good)}.talk .receipt.wait{color:var(--brass)}
.talk .receipt.bad{color:var(--critical)}.talk .receipt.quiet{color:var(--ink-3);font-style:italic}
.talk .turn.person.bad{background:var(--paper);color:var(--ink);border-color:var(--critical)}
.talk .acts{display:flex;flex-wrap:wrap;gap:6px;justify-content:flex-end}
.talk .acts button,.talk .steer button,.talk .box button.cut{font:inherit;font-size:.82rem;min-height:36px;
  padding:4px 12px;border-radius:8px;border:1px solid var(--rule);background:var(--paper);color:var(--ink);
  cursor:pointer}
.talk button.cut,.talk .acts button[data-talk-cut]{border-color:var(--brass);color:var(--brass)}
.talk .acts button[data-talk-again]{border-color:var(--teal);color:var(--teal)}
.talk .turn.question{white-space:normal;color:var(--ink)}
.talk .turn.question .ans{display:grid;gap:6px;margin-top:4px}
.talk .turn.question textarea{font:inherit;font-size:.86rem;width:100%;padding:6px 8px;border-radius:8px;
  border:1px solid var(--rule);background:var(--paper);color:var(--ink)}
.talk .turn.question .buttons button{min-height:36px}
.talk .turn.question.done{opacity:1;background:var(--paper);border-color:var(--rule)}
.talk .turn .small{font-size:.8rem;color:var(--ink-2)}
.talk .steer{display:grid;gap:6px;padding:10px 12px;border:1px solid var(--rule);border-radius:10px;
  background:var(--ground)}
.talk .steer p{margin:0;font-size:.84rem}
.talk .steer .one{display:flex;flex-wrap:wrap;align-items:center;gap:4px 10px;font-size:.82rem;color:var(--ink-2)}
.talk .steer .one button{flex:none;min-width:88px}
.talk .steer button[data-talk-steer="stop"]{border-color:var(--critical);color:var(--critical)}
.talk .steer input{font:inherit;font-size:.84rem;padding:6px 8px;border-radius:8px;border:1px solid var(--rule);
  background:var(--paper);color:var(--ink);min-width:0}
.talk .box{display:grid;gap:6px}
.talk .box label{font-size:.82rem;color:var(--ink-2)}
.talk .box textarea{font:inherit;font-size:.9rem;width:100%;padding:8px 10px;border-radius:8px;
  border:1px solid var(--rule);background:var(--paper);color:var(--ink);resize:vertical}
.talk .box .row{display:flex;flex-wrap:wrap;align-items:center;gap:6px 10px;font-size:.8rem;color:var(--ink-3)}
.talk .box .row button.go{min-height:40px}
.talk .box .why-none{font-size:.8rem;color:var(--ink-2)}
.talk .fault{color:var(--critical);font-size:.84rem;margin:0}
.talk .fault:empty{display:none}
"""

SCRIPT = r"""
(function(){
  const talk = document.querySelector('section.talk[data-talk]');
  if (!talk) return;
  const fairway = talk.dataset.fairway, slice = talk.dataset.slice || '';
  const log = talk.querySelector('[data-talk-log]'), state = talk.querySelector('[data-talk-state]');
  const box = talk.querySelector('textarea[data-talk-text]'), fault = talk.querySelector('.fault');
  let shown = 0;
  const post = async (where, body) => {
    fault.textContent = '';
    const answer = await fetch(where, {method: 'POST', headers: {'Content-Type': 'application/json'},
                                       body: JSON.stringify({fairway, slice, ...body})});
    if (!answer.ok) { fault.textContent = await answer.text(); return false; }
    refresh();
    return true;
  };
  // Not while a person is in it: a focused control, or anything typed into it, keeps the region as it is.
  const busy = region => region && [...region.querySelectorAll('input, textarea, select')]
    .some(one => one === document.activeElement || (one.value || '').trim());
  const swap = (region, html, said) => {
    if (!region || region.dataset.said === said || busy(region)) return;
    const atFoot = region.scrollTop + region.clientHeight >= region.scrollHeight - 24, top = region.scrollTop;
    const open = new Set([...region.querySelectorAll('details[open]')].map(one => one.id));
    region.innerHTML = html;
    region.dataset.said = said;
    region.querySelectorAll('details').forEach(one => { if (open.has(one.id)) one.open = true; });
    region.scrollTop = atFoot ? region.scrollHeight : top;
  };
  const mark = how => talk.querySelectorAll('[data-talk-how]').forEach(one => {
    one.hidden = one.dataset.talkHow !== (how === 'protocol' ? 'protocol' : how === 'print' ? 'print' : 'unknown');
  });
  const seen = heard => {
    if (document.hidden || heard <= shown) return;
    shown = heard;
    fetch('/talk/seen', {method: 'POST', headers: {'Content-Type': 'application/json'},
                         body: JSON.stringify({fairway, slice, heard})}).catch(() => {});
  };
  let timer = null;
  const refresh = async () => {
    clearTimeout(timer);
    let found;
    try { found = await (await fetch(talk.dataset.poll)).json(); }
    catch (fault) { timer = setTimeout(refresh, 8000); return; }
    swap(log, found.log, found.log_said);
    swap(state, found.state, found.state_said);
    mark(found.how);
    seen(found.heard);
    document.dispatchEvent(new CustomEvent('talk:found', {detail: found}));
    timer = setTimeout(refresh, document.hidden ? 8000 : 3000);
  };
  log.scrollTop = log.scrollHeight;
  mark(talk.dataset.how);
  seen(Number(talk.dataset.heard || 0));
  document.addEventListener('visibilitychange', () => { if (!document.hidden) refresh(); });
  talk.addEventListener('click', async event => {
    const send = event.target.closest('[data-talk-send]');
    if (send) {
      event.preventDefault();
      const text = box.value.trim();
      if (!text) { box.focus(); return; }
      send.disabled = true;
      if (await post('/talk/say', {text, mode: send.dataset.talkSend})) box.value = '';
      send.disabled = false;
      return;
    }
    const steer = event.target.closest('[data-talk-steer]');
    if (steer) {
      const why = state.querySelector('[data-talk-why]');
      steer.disabled = true;
      const said = await post('/talk/steer', {kind: steer.dataset.talkSteer, why: why ? why.value.trim() : ''});
      if (said && why) why.value = '';
      steer.disabled = false;
      return;
    }
    if (event.target.closest('[data-talk-earlier]')) {
      const url = new URL(talk.dataset.poll, location.href);
      url.searchParams.set('limit', String(Number(url.searchParams.get('limit') || 200) + 200));
      talk.dataset.poll = url.pathname + url.search;
      log.dataset.said = '';
      refresh();
      return;
    }
    const withdraw = event.target.closest('[data-talk-withdraw]');
    if (withdraw) {
      withdraw.disabled = true;
      post('/talk/steer', {kind: 'withdraw', of: withdraw.dataset.talkWithdraw});
      return;
    }
    const cut = event.target.closest('[data-talk-cut]');
    if (cut) { cut.disabled = true; post('/talk/interrupt', {id: cut.dataset.talkCut}); return; }
    const again = event.target.closest('[data-talk-again]');
    if (again) { again.disabled = true; post('/talk/again', {id: again.dataset.talkAgain}); return; }
    const pick = event.target.closest('[data-ask-pick]');
    const asked = event.target.closest('[data-ask]');
    if (asked && (pick || event.target.closest('[data-ask-send]'))) {
      const typed = asked.querySelector('textarea');
      const text = pick ? pick.dataset.askPick : (typed ? typed.value.trim() : '');
      if (!text) return;
      if (await post('/talk/say', {text, of: asked.dataset.ask}) && typed) typed.value = '';
    }
  });
  timer = setTimeout(refresh, 3000);
})();
"""


#: How many turns a window draws at first; "Show earlier" draws as many again.
SHOWN = 200


def signature(drawn: str) -> str:
    return hashlib.sha1(drawn.encode("utf-8")).hexdigest()[:16]


def answered_by(by: str) -> str:
    if by == "person":
        return "you"
    if by.startswith("captain:"):
        return "its captain"
    return {"rule": "the captain's rule", "skipper": "the skipper"}.get(by, by or "someone")


def said_html(one: dict[str, Any], name: str, how: str, extra: str = "") -> str:
    """A person's message, its receipt beneath it, what can still be done with it, and the reply."""
    acts = ""
    if one["state"] == "queued" and not one["steer"]:
        cut = (f'<button type="button" data-talk-cut="{esc(one["id"])}">Interrupt now</button>'
               if how == "protocol" else "")
        acts = (f'<span class="acts">{cut}<button type="button" data-talk-withdraw="{esc(one["id"])}">Withdraw'
                f"</button></span>")
    elif one["state"] == "not delivered" and one["text"] and not one["steer"] and one["who"].startswith("You"):
        acts = f'<span class="acts"><button type="button" data-talk-again="{esc(one["id"])}">Send again</button></span>'
    line = esc(one["line"]) + (f" · {esc(extra)}" if extra else "")
    reply = (f'<div class="turn agent"><b class="who">{esc(name)}</b><span>{esc(one["reply"])}</span></div>'
             if one["reply"] else "")
    bad = " bad" if one["tone"] == "bad" else ""
    return (f'<div class="said" id="m-{esc(one["id"])}"><div class="turn person{bad}"><b class="who">'
            f'{esc(one["who"])}</b><span>{esc(one["text"])}</span></div>'
            f'<span class="receipt {esc(one["tone"])}">{line}</span>{acts}</div>{reply}')


def ask_html(one: dict[str, Any], name: str, asks_you: bool, mine: dict[str, dict[str, Any]]) -> str:
    """What the agent asked, as a card: answered, answering, or waiting on a person with a way to answer."""
    kind = "permission" if one["what"] == "permission" else "question"
    head = f'<b class="who">{esc(name)} asks</b>' if kind == "question" else f'<b class="who">{esc(name)} wants to</b>'
    done = f'<div class="turn {kind} done" id="ask-{esc(one["id"])}">{head}<span>{esc(one["text"])}</span>'
    if one["answer"]:
        return f'{done}<span class="chose">Answered by {esc(answered_by(one["by"]))}: {esc(one["answer"])}</span></div>'
    if one["yours"]:
        sent = mine.get(one["yours"], {})
        return (f'{done}<span class="chose">Your answer: {esc(sent.get("text", ""))}</span>'
                f'<span class="small">{esc(sent.get("line", ""))}</span></div>')
    captains = one.get("asker") == "captain"  # put to a person whatever the run: no skipper answers a captain
    if kind == "permission":
        under = '<span class="small">Its captain rules on this; nothing here waits on you.</span>'
    elif not asks_you and not captains:
        under = ('<span class="small">This fleet is cruising, so it answers product questions itself — the '
                 "stage's recommendation or the skipper — and nothing waits on you.</span>")
    else:
        picks = "".join(f'<button type="button" data-ask-pick="{esc(option)}">{esc(option)}</button>'
                        for option in one["options"])
        why = "only a person decides what its captain asks" if captains else "this run is not cruising, so a " \
            "person answers its product questions"
        under = (f'<span class="small">Waiting on you: {why}.</span>'
                 f'<span class="ans">{f"<span class=buttons>{picks}</span>" if picks else ""}'
                 f'<textarea rows="2" aria-label="Your answer to {esc(name)}"></textarea>'
                 f'<span class="buttons"><button type="button" class="allow" data-ask-send>Answer</button></span>'
                 f"</span>")
    return (f'<div class="turn {kind}" id="ask-{esc(one["id"])}" data-ask="{esc(one["id"])}">{head}'
            f"<span>{esc(one['text'])}</span>{under}</div>")


def log_html(folded: dict[str, Any], name: str, asks_you: bool, extra: list[dict[str, Any]] | None = None,
             routed: dict[str, str] | None = None, limit: int = SHOWN) -> str:
    """The newest `limit` turns, oldest first, with a way to the earlier ones; `extra` are turns from
    elsewhere (a captain's own words), `routed` a line beside a message saying where its captain sent it."""
    every = sorted(folded["turns"] + list(extra or []), key=lambda one: one["t"])
    mine = {one["id"]: one for one in every if one["kind"] == "said"}
    earlier = max(0, len(every) - limit)
    drawn = (f'<p class="turn note"><button type="button" data-talk-earlier>Show {min(earlier, SHOWN)} earlier'
             f"</button> of {earlier} not shown</p>") if earlier else ""
    for one in every[earlier:]:
        if one["kind"] == "said":
            drawn += said_html(one, name, folded["how"], (routed or {}).get(one["id"], ""))
        elif one["kind"] == "ask":
            drawn += ask_html(one, name, asks_you, mine)
        elif one["kind"] == "agent":
            drawn += (f'<div class="turn agent"><b class="who">{esc(one["who"])}</b><span>{esc(one["text"])}</span>'
                      f"</div>")
        else:
            drawn += f'<p class="turn note">{esc(one["text"])}</p>'
    return drawn or '<p class="turn note">Nothing said yet.</p>'


def steer_html(folded: dict[str, Any]) -> str:
    """Pause, Resume and Stop, each with what it does, for what holds the slice now."""
    if folded["merged"]:
        return "<p>This slice has merged: what it does is on trunk. To change it now, send feedback on the board.</p>"
    halt, by = folded["halted"], folded["by"]
    who = "you" if by == "person" else f"its {by.removeprefix('captain:')} captain" if by.startswith("captain:") \
        else by or "its captain"
    why = f": {folded['why']}" if folded["why"] else ""
    reason = ('<input data-talk-why placeholder="Why, if you want to say (optional)" '
              'aria-label="Why you are pausing or stopping it">')
    resume = '<span class="one"><button type="button" data-talk-steer="resume">Resume</button>{}</span>'
    stop = ('<span class="one"><button type="button" data-talk-steer="stop">Stop</button>Ends the session now; the '
            "slice goes back to the queue with why. Its commits stay on its branch, uncommitted edits in its berth. "
            "A stop you make holds it until you resume it, and it starts again in a fresh session.</span>")
    if halt == "paused":
        return (f"<p><b>Paused by {esc(who)}{esc(why)}.</b> Its session is kept and its slot given back.</p>"
                + resume.format("Carries on in the session it paused in.") + reason + stop)
    if halt == "stopped":
        return (f"<p><b>Stopped by {esc(who)}{esc(why)}.</b> Its session has ended, and it stays out of the queue "
                f"until a person resumes it.</p>"
                + resume.format("Puts it back in the queue; it starts in a fresh session."))
    return ('<span class="one"><button type="button" data-talk-steer="pause">Pause</button>The turn under way '
            "finishes, its session is kept and its slot is given back. Resume carries on in the same session.</span>"
            + reason + stop)


def box_html(name: str, slice_id: str) -> str:
    """The box: Send after the turn under way and, where its session can take one, Interrupt now."""
    if not slice_id:
        return (f'<div class="box"><label for="talk-text">Say something to the {esc(name)} captain. It works out '
                f'which of its slices it is for.</label><textarea id="talk-text" rows="3" data-talk-text></textarea>'
                f'<span class="row"><button type="button" class="go" data-talk-send="wait">Send</button></span></div>')
    return (f'<div class="box"><label for="talk-text">Say something to {esc(name)}</label>'
            f'<textarea id="talk-text" rows="3" data-talk-text></textarea><span class="row">'
            f'<button type="button" class="go" data-talk-send="wait">Send</button><span>after its current turn</span>'
            f'<span data-talk-how="protocol" hidden><button type="button" class="cut" data-talk-send="interrupt">'
            f"Interrupt</button> cancels the turn and delivers at once</span>"
            f'<span class="why-none" data-talk-how="print" hidden>No Interrupt: this slice runs in print mode, where a '
            f"session cannot be spoken to while it runs, so a message goes in when it next starts.</span>"
            f'<span class="why-none" data-talk-how="unknown" hidden>No Interrupt yet: it is offered once its session '
            f"is open. Until then a message goes in when the slice starts.</span></span></div>")


def where_of(root: Path, fairway: str, slice_id: str) -> str:
    """Where the slice is now — `working`, `waiting` (parked), `queued`, `todo`, `done` — off the board's read."""
    return next((str(row.get("state", "")) for row in read(root).rows
                 if row.get("slice") == slice_id and row.get("fairway") == fairway), "") if slice_id else ""


def payload(root: Path, fairway: str, slice_id: str, extra: list[dict[str, Any]] | None = None,
            routed: dict[str, str] | None = None, said: int = 0, limit: int = SHOWN) -> dict[str, Any]:
    """What the window's poll is given: the turns and the controls drawn, each with its signature, how the
    slice is reached, and how many lines speaking to a person it now shows."""
    folded = turns(home(root, fairway, slice_id))
    folded = {**folded, "turns": placed_for(folded["turns"], where_of(root, fairway, slice_id))}
    name = slice_id or f"Captain · {fairway}"
    log = log_html(folded, name, person_answers(root), extra, routed, limit)
    state = steer_html(folded) if slice_id else ""
    return {"log": log, "log_said": signature(log), "state": state, "state_said": signature(state),
            "how": folded["how"], "heard": folded["heard"] + said}


def pane(root: Path, fairway: str, slice_id: str, poll: str, extra: list[dict[str, Any]] | None = None,
         routed: dict[str, str] | None = None, said: int = 0) -> str:
    """The conversation, whole, for a window: its turns, its controls and its box."""
    try:
        found = payload(root, fairway, slice_id, extra, routed, said)
    except ValueError as fault:  # a stream or a slice named in the address that no conversation can have
        return f'<section class="talk card"><h2>No conversation here</h2><p class="empty">{esc(fault)}</p></section>'
    name = slice_id or fairway
    title = f"Conversation with {slice_id}" if slice_id else f"Conversation with the {fairway} captain"
    state = (f'<div class="steer" data-talk-state data-said="{found["state_said"]}">{found["state"]}</div>'
             if slice_id else '<div data-talk-state hidden></div>')
    return (f'<section class="talk card" data-talk data-fairway="{esc(fairway)}" data-slice="{esc(slice_id)}" '
            f'data-poll="{esc(poll)}" data-how="{esc(found["how"])}" data-heard="{found["heard"]}">'
            f'<h2>{esc(title)}</h2><div class="talk-log turns" data-talk-log role="log" aria-live="polite" '
            f'data-said="{found["log_said"]}">{found["log"]}</div>{box_html(name, slice_id)}'
            f'<p class="fault" role="alert"></p>{state}</section>')


def dumps(found: dict[str, Any]) -> str:
    return json.dumps(found, ensure_ascii=False)

"""The Feedback card on the Voyage tab: what using the app showed a person, where it goes, and what it became.

Three things in one card, because they are one loop. A capability waiting for its demo is accepted here, or
not yet, with the reason. Anything a person says — from this card, from Try it, from a slice's card — is
written under `docs/feedback/` (`feedback.py`), and the board starts the triage session that proposes a
route for it. Each proposal then waits here for Confirm, a different route, or Drop, and below them the list
of every item and what it turned into.

**The box is not repainted.** The card polls `/feedback.json` and swaps its list when what it shows has
changed; the box a person is typing in sits outside that list, so a poll never takes their words away.
"""
from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

from .feedback import HOLDS, ROUTES, Item, capture, confirm, drop, items
from .page_shell import esc

#: What the card's buttons and the box ask for.
VERBS = ("send", "confirm", "drop", "triage", "accept")
#: How each context line is said on its chip.
CHIPS = {"slice": "Slice", "capability": "Capability", "page": "Page", "signed-in-as": "Signed in as",
         "trunk": "Trunk"}
#: How many handed-on items the list keeps showing.
SHOWN = 20

STYLE = """
#feedback .head{display:flex;flex-wrap:wrap;gap:8px 14px;align-items:center;justify-content:space-between}
#feedback .head h2{margin:0}
#feedback h3{font-size:.78rem;letter-spacing:.06em;text-transform:uppercase;color:var(--ink-3);margin:16px 0 6px}
#feedback .cap{display:flex;flex-wrap:wrap;gap:8px 14px;align-items:center;justify-content:space-between;
  border-left:3px solid var(--teal);padding:4px 0 4px 12px;margin:8px 0}
#feedback .prop{border:1px solid var(--rule);border-radius:8px;padding:10px 12px;margin:10px 0;display:grid;gap:6px}
#feedback .prop q{color:var(--ink-2);font-style:italic}
#feedback .prop pre{white-space:pre-wrap;font-family:inherit;font-size:.86rem;margin:0;color:var(--ink-2)}
#feedback .route{font-size:.72rem;font-weight:600;padding:2px 8px;border-radius:999px;margin-right:8px;
  background:var(--brass-soft);color:var(--brass)}
#feedback .route.defect{background:transparent;border:1px solid #b4432f;color:#b4432f}
#feedback .route.scope,#feedback .route.planned{background:var(--teal-soft);color:var(--teal)}
#feedback .warn{color:#b4432f;font-size:.86rem;margin:0}
#feedback .row{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
#feedback table{border-collapse:collapse;font-size:.86rem;width:100%}
#feedback th,#feedback td{text-align:left;padding:5px 10px 5px 0;vertical-align:top;
  border-bottom:1px solid var(--rule-2)}
#feedback th{font-size:.7rem;letter-spacing:.06em;text-transform:uppercase;color:var(--ink-3);font-weight:600}
#feedback .num{font-family:var(--mono);color:var(--ink-3)}
#feedback-box{border:1px solid var(--teal);border-radius:8px;padding:12px;margin:10px 0;display:grid;gap:8px}
#feedback-box[hidden]{display:none}
#feedback-box textarea{width:100%;box-sizing:border-box}
#feedback-box .chips{display:flex;flex-wrap:wrap;gap:6px}
#feedback-box .chip{font-size:.78rem;border:1px solid var(--rule);border-radius:999px;padding:2px 4px 2px 10px}
#feedback-box .chip button{border:0;background:none;cursor:pointer;color:var(--ink-3);padding:0 4px}
#feedback-box input{font:inherit;font-size:.86rem;padding:3px 6px;min-width:0;flex:1}
"""

SCRIPT = """
// Feedback: the box opens from any button carrying data-feedback (its context, as JSON), sends to
// /feedback, and the card's list repaints from /feedback.json — never the box, which may hold words.
(function(){
  const list = () => document.getElementById('feedback-list');
  const box = () => document.getElementById('feedback-box');
  if (!list()) return;
  let context = {}, verdict = '';
  const post = async body => {
    const answer = await fetch('/feedback', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify(body)});
    const said = await answer.text();
    if (!answer.ok) { alert(said); return false; }
    setTimeout(poll, 300);
    return true;
  };
  const chips = () => {
    const names = %CHIPS%;
    box().querySelector('.chips').innerHTML = Object.entries(context).filter(([k, v]) => names[k] && v)
      .map(([k, v]) => `<span class="chip">${names[k]} · `
        + `${String(v).replace(/[&<>"]/g, c => '&#' + c.charCodeAt(0) + ';')}`
        + `<button type="button" data-unchip="${k}" aria-label="Remove">×</button></span>`).join('');
  };
  const poll = async () => {
    let found;
    try { found = await (await fetch('/feedback.json')).json(); }
    catch (fault) { setTimeout(poll, 10000); return; }
    const now = list();
    if (now && now.dataset.said !== found.said) now.outerHTML = found.html;
    setTimeout(poll, found.triaging ? 3000 : 10000);
  };
  setTimeout(poll, 3000);
  document.addEventListener('click', async event => {
    const at = event.target.closest('button');
    if (!at) return;
    const data = at.dataset;
    if (data.feedback !== undefined) {
      context = JSON.parse(data.feedback || '{}'); verdict = data.verdict || '';
      box().hidden = false; box().querySelector('h3').textContent = data.ask || 'What did using it show?';
      chips(); box().scrollIntoView({block: 'nearest'}); box().querySelector('textarea').focus();
    } else if (data.unchip) { delete context[data.unchip]; chips(); }
    else if (data.fbCancel !== undefined) { box().hidden = true; }
    else if (data.fbSend !== undefined) {
      const words = box().querySelector('textarea').value.trim();
      const page = box().querySelector('input[name=page]').value.trim();
      if (page) context.page = page;
      at.disabled = true;
      if (await post({verb: 'send', words, context, verdict})) {
        box().querySelector('textarea').value = ''; box().querySelector('input[name=page]').value = '';
        box().hidden = true;
      }
      at.disabled = false;
    } else if (data.fb) {
      const routed = at.closest('.prop') && at.closest('.prop').querySelector('select');
      at.disabled = true;
      await post({verb: data.fb, number: data.number || '', hold: data.hold || '',
                  route: data.fb === 'confirm' && routed ? routed.value : '',
                  capability: data.capability || '', fairway: data.fairway || ''});
      at.disabled = false;
    }
  });
})();
""".replace("%CHIPS%", json.dumps(CHIPS))


def opener(face: str, context: dict[str, str], primary: bool = False, ask: str = "", verdict: str = "") -> str:
    """A button that opens the box with this context already on it."""
    shown = {key: value for key, value in context.items() if value}
    extra = (f' data-ask="{esc(ask)}"' if ask else "") + (f' data-verdict="{esc(verdict)}"' if verdict else "")
    return (f'<button type="button" class="{"go" if primary else "install"}" '
            f'data-feedback="{esc(json.dumps(shown))}"{extra}>{esc(face)}</button>')


def act_button(verb: str, face: str, primary: bool = False, **data: str) -> str:
    extra = "".join(f' data-{name}="{esc(value)}"' for name, value in data.items())
    kind = "go" if primary else "install"
    return f'<button type="button" class="{kind}" data-fb="{verb}"{extra}>{esc(face)}</button>'


def box_html() -> str:
    return ('<div id="feedback-box" hidden><h3>What did using it show?</h3><div class="chips"></div>'
            '<textarea rows="4" placeholder="In your own words. Two things in one message are split into two.">'
            "</textarea>"
            '<div class="row"><input name="page" placeholder="The page you were on (optional): paste its address">'
            '</div><div class="row"><button type="button" class="go" data-fb-send>Send</button>'
            '<button type="button" class="install" data-fb-cancel>Cancel</button></div></div>')


def capabilities_html(fleet: dict) -> str:
    """Each capability waiting for a person's demo, with its verdict to give."""
    due = fleet.get("demo_due_in") or {}
    if not due:
        return ""
    rows = "".join(
        f'<div class="cap"><span><b>{esc(name)}</b> · ready for you to see</span><span class="row">'
        + act_button("accept", "Accept", True, capability=name, fairway=fairway)
        + opener("Not yet: say why", {"from": "capability", "capability": name, "fairway": fairway},
                 ask=f"What does the {name} capability still need?", verdict="not-yet")
        + "</span></div>" for name, fairway in sorted(due.items()))
    return f"<h3>Ready for your demo</h3>{rows}"


def proposal_html(item: Item, rows: list[dict[str, str]]) -> str:
    route = item.fields.get("route", "")
    on = item.fields.get("slice", "")
    flight = item.fields.get("in-flight", "")
    state = next((one.get("state", "") for one in rows if one.get("slice") == (flight or on)), "")
    menu = "".join(f'<option value="{key}"{" selected" if key == route else ""}>{esc(face)}</option>'
                   for key, face in ROUTES.items())
    if flight and route == "change" and state not in ("done", "todo", ""):
        warn = (f'<p class="warn">{esc(flight)} is in flight. Confirming parks it at its next boundary with this '
                "change as the reason; holding leaves it alone until it has merged.</p>")
        buttons = (act_button("confirm", f"Confirm and park {flight}", True, number=item.number, hold=HOLDS[0])
                   + act_button("confirm", f"Hold until {flight} merges", number=item.number, hold=HOLDS[1]))
    else:
        warn, buttons = "", act_button("confirm", "Confirm", True, number=item.number)
    becomes = item.fields.get("becomes", "")
    return (f'<div class="prop"><div><span class="route {esc(route)}">{esc(ROUTES.get(route, route))}</span>'
            f'<b>{esc(" · ".join(one for one in (on, item.title) if one))}</b> '
            f'<span class="num">#{item.number}</span></div>'
            f"<q>{esc(item.said)}</q>"
            + (f"<pre>{esc(item.proposed)}</pre>" if item.proposed else "")
            + (f"<div>Becomes: {esc(becomes)}</div>" if becomes else "") + warn
            + f'<div class="row">{buttons}<label>or route it as <select>{menu}</select></label>'
            + act_button("drop", "Drop", number=item.number) + "</div></div>")


def ledger_html(found: list[Item]) -> str:
    done = [one for one in found if one.state in ("confirmed", "dropped")][:SHOWN]
    if not done:
        return ""
    lines = "".join(
        f'<tr><td class="num">{one.number}</td><td>{esc(one.title)}</td>'
        f'<td>{esc(ROUTES.get(one.route, "—") if one.state == "confirmed" else "Dropped")}</td>'
        f'<td>{esc(one.fields.get("became", ""))}</td><td><code>{esc(one.path.name)}</code></td></tr>'
        for one in done)
    return (f'<h3>Every item, and what it turned into</h3><div style="overflow-x:auto"><table><tr><th>#</th>'
            f"<th>What you said</th><th>Route</th><th>Became</th><th>Record</th></tr>{lines}</table></div>")


def list_html(root: Path, rows: list[dict[str, str]], fleet: dict, triaging: bool) -> str:
    found = items(root)
    waiting = [one for one in found if one.state == "triaging"]
    proposed = [one for one in found if one.state == "proposed"]
    if waiting:
        reading = (f'<p class="empty">Reading what you said: {len(waiting)} item(s). A headless session is '
                   "proposing where each goes; nothing moves until you confirm.</p>" if triaging else
                   f'<div class="row"><p class="empty">{len(waiting)} item(s) not read yet.</p>'
                   + act_button("triage", "Triage now") + "</div>")
    else:
        reading = ""
    props = "".join(proposal_html(one, rows) for one in proposed)
    body = (capabilities_html(fleet) + reading
            + (f"<h3>Where the board proposes each goes</h3>{props}" if props else "") + ledger_html(found))
    said = json.dumps([[one.number, one.state, one.fields.get("route")] for one in found]
                      + [triaging, sorted((fleet.get("demo_due_in") or {}).items())])
    empty = ('<p class="empty">Nothing said yet. After using the app, say what it showed: a fault, something '
             "you wanted different, something missing. The board proposes where it goes.</p>")
    return f'<div id="feedback-list" data-said="{esc(said)}">{body or empty}</div>'


def card(root: Path, rows: list[dict[str, str]], fleet: dict, triaging: bool, trunk: str = "") -> str:
    head = opener("What did using it show?", {"from": "voyage", "trunk": trunk[:7]}, primary=True)
    return (f'<div class="card" id="feedback"><div class="head"><h2>Feedback</h2><div class="row">{head}'
            f"</div></div>{box_html()}{list_html(root, rows, fleet, triaging)}</div>")


def payload(root: Path, rows: list[dict[str, str]], fleet: dict, triaging: bool) -> str:
    html = list_html(root, rows, fleet, triaging)
    said = html.split('data-said="', 1)[1].split('"', 1)[0]
    return json.dumps({"said": said, "html": html, "triaging": triaging})


def act(root: Path, held: dict, rows: list[dict[str, str]], fleet: dict, start: Callable[[], bool]) -> str:
    """One press on the card. `start` begins the triage session when the board is free, and says if it did."""
    from .deck import tell

    verb = str(held.get("verb", ""))
    if verb not in VERBS:
        raise ValueError(f"the Feedback card has no {verb!r}; it can {', '.join(VERBS)}")
    if verb == "accept":
        capability, fairway = str(held.get("capability", "")), str(held.get("fairway", ""))
        if capability not in (fleet.get("demo_due_in") or {}):
            raise ValueError(f"{capability or 'that capability'} is not waiting for a demo")
        tell(root, fairway, f"Demo verdict for the {capability} capability: accepted.")
        return f"told {fairway}: {capability} accepted"
    if verb == "send":
        context = held.get("context") if isinstance(held.get("context"), dict) else {}
        item = capture(root, str(held.get("words", "")), context)
        said = f"feedback {item.number} written"
        if held.get("verdict") == "not-yet" and context.get("capability") and context.get("fairway"):
            tell(root, str(context["fairway"]), f"Demo verdict for the {context['capability']} capability: not "
                                                 f"accepted yet (behaviour). {item.said} The record is "
                                                 f"{item.path.relative_to(root).as_posix()}.")
            said += "; the captain is told it is not accepted yet"
        return said + ("; reading it now" if start() else "; Triage now reads it when the board is free")
    if verb == "triage":
        if not [one for one in items(root) if one.state == "triaging"]:
            raise ValueError("nothing waiting to be read under docs/feedback")
        if not start():
            raise ValueError("this board is already running something; Triage now once it has finished")
        return "reading your feedback"
    number = str(held.get("number", ""))
    if verb == "drop":
        return drop(root, number)
    return confirm(root, number, rows, str(held.get("route", "")), str(held.get("hold", "")))

"""The board's first page: a conversation that draws a product, the brief counting itself up, and the thing to play.

Markup, style and script for `brief_session.py`, which holds the conversation. Three columns of one page: the
turns and a box to type in, the brief as the start page will read it — the check's five lines, or *nothing
yet* — and the prototype, embedded from the sketch's own folder. The header carries the four steps the plan
draws, with the one the session says it is at marked.

It is a tab beside the start page and never in front of it: a person with a document, or with nothing, takes
*Start from a PRD* as they do today. Its routes are its own and hand straight back to the session, so the
bridge's one job here is two lines. Files are served from the workspace and confined to it: the prototype's
page and the surface pages' stylesheets load from there, and nothing else does.
"""
from __future__ import annotations

# budget: 400 — the first page's two faces, the listing and a sketch, their routes, the files a sketch serves,
# and the brief read as a document; the conversation itself is brief_session.py's.
import json
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote

from .brief_session import BRIEF, BROUGHT, PROTOTYPE, for_slug, sketches, slug_of, started, workspace
from .errors import Busy
from .page_shell import document, esc
from .spec_page import page as read_page
from .turn_cards import SCRIPT as DRAW
from .turn_cards import STYLE as CARDS

STEPS = ("Describe", "Walk the states", "Check", "Hand over")
TYPES = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8", ".js": "text/javascript",
         ".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
         ".webp": "image/webp", ".json": "application/json; charset=utf-8", ".md": "text/plain; charset=utf-8",
         ".txt": "text/plain; charset=utf-8"}

STYLE = """
#sketch{display:grid;grid-template-columns:minmax(0,1.3fr) minmax(0,1fr);gap:18px;margin-top:18px}
@media (max-width:860px){#sketch{grid-template-columns:minmax(0,1fr)}}
#sketch .card{margin-top:0;min-width:0}
#sketch nav.steps{display:flex;flex-wrap:wrap;gap:6px;margin-top:14px}
#sketch nav.steps span{font-size:.82rem;padding:5px 12px;border-radius:8px;background:var(--rule-2);
  color:var(--ink-2)}
#sketch nav.steps span.now{background:var(--teal);color:#fff;font-weight:500}
#sketch .log{max-height:min(32rem,60vh);min-height:8rem;overflow:auto;display:grid;gap:8px;align-content:start;
  padding:2px 2px 10px}
#sketch .turn{max-width:min(46rem,92%);padding:8px 12px;border-radius:10px;border:1px solid var(--rule);
  white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.45;font-size:.9rem}
#sketch .turn.person{justify-self:end;background:var(--teal);border-color:var(--teal);color:#fff}
#sketch .turn.sketch{justify-self:start;background:var(--paper)}
#sketch .turn.read,#sketch .turn.wrote{justify-self:start;border:0;padding:0 4px;color:var(--ink-3);font-size:.78rem;
  font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
#sketch .turn.error{justify-self:start;border-color:var(--brass);color:var(--brass)}
#sketch .empty,#sketch .none{color:var(--ink-3);font-size:.88rem;margin:0}
#sketch .check{list-style:none;margin:0;padding:0;display:grid;gap:4px;font-size:.84rem;
  font-family:ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--ink-2)}
#sketch iframe{width:100%;height:36rem;border:1px solid var(--rule);border-radius:8px;background:#fff}
#sketch .head{display:flex;align-items:baseline;gap:10px;justify-content:space-between}
#sketch .head h2{margin:0;white-space:nowrap}
#sketch .head .on{flex:1 1 auto;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
  font-size:.8rem;color:var(--ink-3)}
#sketch .head button{font:inherit;font-size:.8rem;background:none;border:0;color:var(--ink-3);cursor:pointer;
  white-space:nowrap}
#sketches .doc{display:grid;gap:6px;margin-top:16px}
#sketches .doc>label,#sketches h3{font-size:.85rem;font-weight:500;color:var(--ink-2);margin:0}
#sketches textarea{width:100%;box-sizing:border-box;min-height:6rem;font:inherit;font-size:.9rem;padding:8px 10px;
  border:1px solid var(--rule);border-radius:8px;background:var(--paper);color:var(--ink);resize:vertical}
#sketches label.file{display:flex;align-items:center;gap:10px;font-size:.84rem;color:var(--ink-3);cursor:pointer}
#sketches label.file input{position:absolute;width:1px;height:1px;opacity:0}
#sketches .pick,#sketches ul.had a{display:inline-block;font-size:.84rem;padding:6px 12px;border-radius:8px;
  border:1px solid var(--rule);background:var(--paper);color:var(--ink-2);text-decoration:none}
#sketches ul.had a{color:var(--teal)}
#sketches label.file:focus-within .pick{outline:2px solid var(--teal);outline-offset:1px}
#sketches h3{margin-top:18px}
#sketches ul.had{list-style:none;margin:6px 0 0;padding:0;display:flex;flex-wrap:wrap;gap:6px}
#sketches .said{color:var(--brass);font-size:.88rem;margin:8px 0 0}
#sketch .check li{padding-left:18px;position:relative}
#sketch .check li::before{content:"";position:absolute;left:0;top:.45em;width:9px;height:9px;border-radius:50%;
  background:var(--good)}
#sketch .check li.amber::before{background:var(--warn)}
#sketch .check li.refused::before{background:var(--brass)}
#sketch .check li.detail{padding-left:30px}#sketch .check li.detail::before{display:none}
#sketch .legend{color:var(--ink-3);font-size:.78rem;margin:8px 0 0}
#sketch a.hand-over{display:inline-block;margin-top:12px;font-size:.9rem;padding:8px 14px;border-radius:8px;
  border:1px solid var(--teal);background:var(--teal);color:#fff;text-decoration:none}
"""

SCRIPT = """
{
  const page = document.getElementById('sketch');
  if (page) {
    const slug = page.dataset.sketch, log = page.querySelector('.log'), input = page.querySelector('input');
    const go = page.querySelector('button.go'), empty = page.querySelector('.empty');
    const check = page.querySelector('.check'), none = page.querySelector('.none');
    const frame = page.querySelector('iframe'), undrawn = page.querySelector('.undrawn');
    const steps = page.querySelectorAll('nav.steps span');
    let at = 0, busy = false, timer = null, drawn = 0;
    const post = (where, body) => fetch(where, {method: 'POST', headers: {'Content-Type': 'application/json'},
                                                 body: JSON.stringify({sketch: slug, ...body})});
    const reply = (id, body) => post('/brief/answer', {id, ...body});
    const draw = turn => { if (drawTurn(log, turn, reply)) drawn += 1; };
    const hand = page.querySelector('a.hand-over');
    const colour = line => {
      if (line.startsWith('  ')) return 'detail';
      if (line.startsWith('the draft will have to assume: nothing')) return '';
      if (line.startsWith('the draft will have to assume')) return 'amber';
      if (line.startsWith('requirements document: none')) return 'amber';
      if (line.startsWith('runs for: not said')) return 'amber';
      if (line.startsWith('runs for:')) return line.endsWith('(proposed)') ? 'amber' : '';
      return /^(requirements document|surfaces|look|people):/.test(line) ? '' : 'refused';
    };
    const stop = page.querySelector('button.stop'), on = page.querySelector('.head .on');
    const paint = said => {
      input.disabled = busy; go.disabled = busy;
      go.textContent = busy ? (said.thinking ? 'Thinking…' : 'Drawing…') : 'Say';
      stop.hidden = !busy;
      if (said.agent) on.textContent = 'on ' + said.agent + (said.model ? ' · ' + said.model : '');
      steps.forEach((one, index) => one.classList.toggle('now', index + 1 === said.step));
      check.replaceChildren(...said.check.map(line => {
        const li = document.createElement('li'); li.textContent = line; li.className = colour(line); return li; }));
      none.hidden = said.check.length > 0;
      const written = said.check.length > 0 && !said.check[0].startsWith('requirements document: none')
        && colour(said.check[0]) !== 'refused';
      hand.hidden = !written; hand.classList.toggle('ready', !!said.ready);
      const open = log.querySelectorAll('.turn.permission:not(.done), .turn.question:not(.done)').length;
      const ready = {count: 1, text: 'The brief is ready to hand over', href: '#hand-over'};
      if (window.waiting) waiting.set(open ? {count: open, text: 'The brief asks you something', href: '#brief-log'}
                                      : said.ready ? ready : null);
    };
    const poll = async () => {
      let said;
      try { said = await (await fetch('/brief.json?sketch=' + encodeURIComponent(slug) + '&since=' + at)).json(); }
      catch (fault) { return; }
      const stuck = log.scrollTop + log.clientHeight >= log.scrollHeight - 24;
      const before = drawn;
      said.turns.forEach(draw);
      at = said.at; busy = said.busy;
      drawWaiting(log, busy, said.thinking, said.doing, said.for);
      if (said.turns.length || busy) { empty.hidden = true; if (stuck) log.scrollTop = log.scrollHeight; }
      paint(said);
      if (frame && drawn !== before) {
        frame.hidden = false; frame.src = frame.dataset.src + '?v=' + Date.now();
        if (undrawn) undrawn.hidden = true;
      }
      clearTimeout(timer);
      // Polled while idle too, slowly: a turn started from another window is still this conversation's.
      timer = setTimeout(poll, busy ? 900 : 4000);
    };
    const ask = async text => {
      if (!text.trim() || busy) return;
      const answer = await post('/brief/ask', {message: text});
      if (answer.status === 409) { busy = true; paint({step: 0, check: []}); poll(); return; }  // another window's turn
      if (!answer.ok) { draw({role: 'sketch', kind: 'error', text: await answer.text()}); return; }
      input.value = ''; busy = true; drawWaiting(log, true, false); paint({step: 0, check: []}); poll();
    };
    page.querySelector('form.ask').addEventListener('submit', event => { event.preventDefault(); ask(input.value); });
    stop.addEventListener('click', () => post('/brief/cancel', {}));
    page.querySelector('[data-clear]').addEventListener('click', async () => {
      await post('/brief/reset', {});
      log.querySelectorAll('.turn').forEach(one => one.remove());
      empty.hidden = false; at = 0; busy = false; poll();
    });
    poll();
  }
}
"""


def chosen(query: str) -> str | None:
    """Which sketch the address names: by its slug, or by the name a person just typed for a new one."""
    asked = parse_qs(query)
    if slug := (asked.get("sketch") or [""])[0].strip():
        return slug
    if name := (asked.get("name") or [""])[0].strip():
        return slug_of(name)
    return None


def listing() -> str:
    """The page with no sketch: the ones this machine has, a field for a new one's name, and a document a
    person already has, pasted or chosen, which the session reads first."""
    had = "".join(f'<li><a href="/brief?sketch={quote(one)}">{esc(one)}</a></li>' for one in sketches())
    kept = f'<h3>Pick up where you left off</h3><ul class="had">{had}</ul>' if had else ""
    return (f'<div id="sketches" class="card"><h2>Start from an idea</h2>'
            f'<p>Say what it is, in your words, and it is drawn as a thing you can tap through. What you decide '
            f'while playing becomes the brief a project starts from. Nothing here is required: a person with '
            f'a document, or with nothing, starts a project from the next tab as before.</p>'
            f'<form class="ask" method="get" action="/brief"><input name="name" placeholder="Club boat bookings" '
            f'autocomplete="off" aria-label="The product\'s name">'
            f'<button class="go" type="submit">Start</button></form>'
            f'<div class="doc"><label for="said">Say what it is, in your words</label>'
            f'<textarea id="said" name="said" placeholder="Who uses it, and what they do with it. A document you '
            f'already have can go here too: it is read first, and what it leaves open is asked."></textarea>'
            f'<label class="file"><input type="file" accept=".md,.txt,text/*"><span class="pick">Or choose a '
            f'document you already have</span><span class="name"></span></label></div>'
            f'<p class="said" hidden></p>'
            f"{kept}</div>")


BEGIN = """
{
  const card = document.getElementById('sketches');
  if (card) {
    const form = card.querySelector('form'), text = card.querySelector('textarea');
    const file = card.querySelector('input[type=file]');
    const said = card.querySelector('.said');
    let brought = false;  // a chosen file is a document to review; typed words are the first thing said
    file.addEventListener('change', () => {
      const one = file.files && file.files[0];
      if (!one) return;
      one.text().then(read => {
        text.value = read; brought = true; card.querySelector('.name').textContent = one.name;
      });
    });
    form.addEventListener('submit', async event => {
      if (!text.value.trim()) return;  // a name alone: the plain form, which needs no script
      event.preventDefault();
      const body = {name: form.name.value, [brought ? 'document' : 'said']: text.value};
      const answer = await fetch('/brief/new', {method: 'POST', headers: {'Content-Type': 'application/json'},
                                                 body: JSON.stringify(body)});
      if (!answer.ok) { said.textContent = await answer.text(); said.hidden = false; return; }
      location.href = '/brief?sketch=' + encodeURIComponent(await answer.text());
    });
  }
}
"""


def sketch_page(slug: str) -> str:
    """One sketch: the steps, the conversation, the brief so far, and the prototype where there is one."""
    held = for_slug(slug)
    held.resume()  # after a restart: the kept session loading while the page is read
    said = held.said()
    now = said["step"]
    steps = "".join(f'<span class="{"now" if number == now else ""}">{number} {esc(name)}</span>'
                    for number, name in enumerate(STEPS, 1))
    home = workspace(slug)
    played = f"/brief/files/{quote(slug)}/{PROTOTYPE}/index.html"
    has_prototype = (home / PROTOTYPE / "index.html").is_file()
    frame = (f'<iframe title="The prototype" src="{played}" data-src="{played}"></iframe>' if has_prototype
             else f'<iframe title="The prototype" hidden data-src="{played}"></iframe>'
                  f'<p class="none undrawn">Nothing drawn yet. Say what the product is.</p>')
    return (f'<div id="sketch" data-sketch="{esc(slug)}">'
            f'<div><nav class="steps" aria-label="Steps">{steps}</nav>'
            f'<div class="card" style="margin-top:14px"><div class="head"><h2>{esc(slug)}</h2>'
            f'<span class="on">{esc("on " + said["agent"]) if said["agent"] else ""}</span>'
            f'<button type="button" data-clear>New conversation</button></div>'
            f'<div class="log turns" id="brief-log" role="log" aria-live="polite"></div>'
            f'<p class="empty">Say what the product is: who uses it, and what they do with it.</p>'
            f'<form class="ask"><input placeholder="Members book one of the club boats for a morning…" '
            f'autocomplete="off" aria-label="Say something"><button class="go" type="submit">Say</button>'
            f'<button class="stop" type="button" hidden>Stop</button></form>'
            f'</div></div>'
            f'<div><div class="card"><h2>The brief, as the start page will read it</h2>'
            f'<ul class="check"></ul><p class="none">Nothing written yet.</p>'
            f'<p class="legend">Green: the builder can start from it without asking. Amber: what the draft will '
            f'decide for you, and say it did.</p>'
            f'<a class="hand-over" id="hand-over" hidden href="/generate?brief={quote(str(home / BRIEF))}">'
            f'Hand over: start a project from this brief</a>'
            f'<p class="read" style="margin-top:8px"><a class="quiet-link" href="/brief/read?sketch={quote(slug)}">'
            f'Read the brief as a document</a> · '
            f'<a class="quiet-link" href="/brief/read?sketch={quote(slug)}&amp;file=people">the people</a> · '
            f'<a class="quiet-link" href="/brief/read?sketch={quote(slug)}&amp;file=domain">the facts</a></p>'
            f'<p class="empty" style="margin-top:8px">Folder: <code>{esc(home / BRIEF)}</code></p></div>'
            f'<div class="card" style="margin-top:14px"><h2>The prototype</h2>{frame}</div></div></div>')


#: The brief's documents a person may read on the board, by the name the address carries.
READABLE = {"prd": "prd.md", "people": "people.md", "domain": "domain.md"}


def reading(slug: str, name: str) -> str:
    """One of the brief's documents in reading form, the way a drafted specification is read on the voyage:
    headings, lists, bold and code rendered, nothing followed, nothing run. A missing one is a refusal."""
    if name not in READABLE:
        raise ValueError(f"{name} is not a document of the brief; prd, people or domain")
    home = workspace(slug_of(slug))
    document = home / BRIEF / READABLE[name]
    if not document.is_file():
        raise ValueError(f"{READABLE[name]} is not written yet in this sketch")
    return read_page(f"{slug}/brief/{READABLE[name]}", document.read_text(encoding="utf-8", errors="replace"),
                     back=f"/brief?sketch={quote(slug)}")


def page(query: str) -> str:
    slug = chosen(query)
    body = sketch_page(slug) if slug else listing()
    return document("Start from an idea", "A prototype to play with, and the brief it leaves behind",
                    f"<style>{STYLE}{CARDS}</style>{body}", DRAW + SCRIPT + BEGIN, now="/brief")


def served(where: str) -> tuple[Path, str] | None:
    """The file a `/brief/files/<slug>/<path>` address names, inside that sketch's workspace, and its type."""
    _, _, rest = where.partition("/brief/files/")
    slug, _, inside = rest.partition("/")
    if not slug or not inside:
        return None
    home = workspace(slug).resolve()
    path = (home / inside).resolve()
    if not path.is_relative_to(home) or ".claude" in path.relative_to(home).parts or not path.is_file():
        return None
    return path, TYPES.get(path.suffix.lower(), "application/octet-stream")


def route_get(bridge: Any, where: str, query: str) -> bool:
    """Answer a GET of this page's, or say it was not one."""
    if where == "/brief/read":
        asked = parse_qs(query)
        slug, name = (asked.get("sketch") or [""])[0], (asked.get("file") or ["prd"])[0]
        try:
            bridge.send(200, reading(slug, name))
        except ValueError as refused:
            bridge.send(404, str(refused), "text/plain; charset=utf-8")
        return True
    if where == "/brief":
        try:
            bridge.send(200, page(query))
        except ValueError as refused:
            bridge.send(400, f'<div class="card"><p>{esc(refused)}</p></div>')
    elif where == "/brief.json":
        asked = parse_qs(query)
        slug = (asked.get("sketch") or [""])[0]
        try:
            since = int((asked.get("since") or ["0"])[0])
            bridge.send(200, json.dumps(for_slug(slug).said(since)), "application/json; charset=utf-8")
        except ValueError as refused:
            bridge.send(400, str(refused), "text/plain; charset=utf-8")
    elif where.startswith("/brief/files/"):
        found = served(where)
        if found is None:
            # Styled, because the frame shows it: a prototype is reloaded as soon as the agent wrote anything,
            # and the first reload lands before the first drawing exists.
            bridge.send(404, '<!doctype html><html><body style="margin:0;padding:16px;background:#fcfcfb;'
                             'color:#7a8891;font:14px system-ui,sans-serif">Nothing drawn yet.</body></html>',
                        "text/html; charset=utf-8")
        else:
            bridge.send(200, found[0].read_bytes(), found[1])
    else:
        return False
    return True


def route_post(bridge: Any, where: str, held: dict) -> bool:
    """Answer a POST of this page's — a turn, or a new conversation, begun with what the person typed or with
    a document they chose — or say it was not one."""
    if where not in ("/brief/ask", "/brief/reset", "/brief/new", "/brief/answer", "/brief/cancel"):
        return False
    try:
        if where == "/brief/new":
            slug = slug_of(str(held.get("name") or ""))
            document, said = str(held.get("document") or ""), str(held.get("said") or "")
            started(slug, document)
            if document.strip():
                for_slug(slug).ask(BROUGHT)  # a brought document is the first thing the person said
            elif said.strip():
                for_slug(slug).ask(said)
            bridge.send(200, slug, "text/plain; charset=utf-8")
            return True
        sketch = for_slug(str(held.get("sketch") or ""))
        if where == "/brief/answer":
            # A card's answer: an option, a question's words, or a decline, which is no answer at all.
            given = None if held.get("decline") else held.get("option") or held.get("answer")
            if not sketch.answer(str(held.get("id") or ""), None if given is None else str(given)):
                bridge.send(400, "nothing is waiting on that answer", "text/plain; charset=utf-8")
                return True
            said = "answered"
        elif where == "/brief/cancel":
            said = sketch.cancel()
        else:
            said = sketch.ask(str(held.get("message") or "")) if where == "/brief/ask" else sketch.reset()
        bridge.send(200, said, "text/plain; charset=utf-8")
    except Busy as wait:
        bridge.send(409, str(wait), "text/plain; charset=utf-8")  # a turn under way: the page waits
    except ValueError as refused:
        bridge.send(400, str(refused), "text/plain; charset=utf-8")
    return True

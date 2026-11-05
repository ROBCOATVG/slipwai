"""The board's first page: a conversation that draws a product, the brief counting itself up, and the thing to play.

Markup, style and script for `brief_session.py`, which holds the conversation. Three columns of one page: the
turns and a box to type in, the brief as the start page will read it — the check's five lines, or *nothing
yet* — and the prototype, embedded from the sketch's own folder. The header carries the four steps the plan
draws, with the one the session says it is at marked.

It is a tab beside the start page and never in front of it: a person with a document, or with nothing, takes
*Start a project* as they do today. Its routes are its own and hand straight back to the session, so the
bridge's one job here is two lines. Files are served from the workspace and confined to it: the prototype's
page and the surface pages' stylesheets load from there, and nothing else does.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote

from .brief_session import BRIEF, PROTOTYPE, for_slug, sketches, slug_of, workspace
from .page_shell import document, esc

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
#sketch nav.steps span{font-size:.82rem;padding:5px 12px;border-radius:999px;background:var(--rule-2);
  color:var(--ink-2)}
#sketch nav.steps span.now{background:var(--teal);color:#fff;font-weight:600}
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
#sketch .head h2{margin:0}
#sketch .head button{font:inherit;font-size:.8rem;background:none;border:0;color:var(--ink-3);cursor:pointer}
#sketches ul{margin:8px 0 0;padding-left:1.2rem}
"""

SCRIPT = """
{
  const page = document.getElementById('sketch');
  if (page) {
    const slug = page.dataset.sketch, log = page.querySelector('.log'), input = page.querySelector('input');
    const go = page.querySelector('button.go'), empty = page.querySelector('.empty');
    const check = page.querySelector('.check'), none = page.querySelector('.none');
    const frame = page.querySelector('iframe');
    const steps = page.querySelectorAll('nav.steps span');
    let at = 0, busy = false, timer = null, drawn = 0;
    const draw = turn => {
      const one = document.createElement('div');
      one.className = 'turn ' + (turn.kind === 'text' ? turn.role : turn.kind);
      one.textContent = turn.text;
      log.appendChild(one);
      if (turn.kind === 'wrote') drawn += 1;
    };
    const paint = said => {
      input.disabled = busy; go.disabled = busy; go.textContent = busy ? 'Drawing…' : 'Say';
      steps.forEach((one, index) => one.classList.toggle('now', index + 1 === said.step));
      check.replaceChildren(...said.check.map(line => {
        const li = document.createElement('li'); li.textContent = line; return li; }));
      none.hidden = said.check.length > 0;
    };
    const poll = async () => {
      let said;
      try { said = await (await fetch('/brief.json?sketch=' + encodeURIComponent(slug) + '&since=' + at)).json(); }
      catch (fault) { return; }
      const stuck = log.scrollTop + log.clientHeight >= log.scrollHeight - 24;
      const before = drawn;
      said.turns.forEach(draw);
      at = said.at; busy = said.busy;
      if (said.turns.length) { empty.hidden = true; if (stuck) log.scrollTop = log.scrollHeight; }
      paint(said);
      if (frame && !busy && drawn !== before) frame.src = frame.dataset.src + '?v=' + Date.now();
      clearTimeout(timer);
      if (busy) timer = setTimeout(poll, 900);
    };
    const ask = async text => {
      if (!text.trim() || busy) return;
      const answer = await fetch('/brief/ask', {method: 'POST', headers: {'Content-Type': 'application/json'},
                                                 body: JSON.stringify({sketch: slug, message: text})});
      if (!answer.ok) { draw({role: 'sketch', kind: 'error', text: await answer.text()}); return; }
      input.value = ''; busy = true; paint({step: 0, check: []}); poll();
    };
    page.querySelector('form.ask').addEventListener('submit', event => { event.preventDefault(); ask(input.value); });
    page.querySelector('[data-clear]').addEventListener('click', async () => {
      await fetch('/brief/reset', {method: 'POST', headers: {'Content-Type': 'application/json'},
                                   body: JSON.stringify({sketch: slug})});
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
    """The page with no sketch: the ones this machine has, and a field for a new one's name."""
    had = "".join(f'<li><a href="/brief?sketch={quote(one)}">{esc(one)}</a></li>' for one in sketches())
    return (f'<div id="sketches" class="card"><h2>Describe a product</h2>'
            f'<p>Say what it is, in your words, and it is drawn as a thing you can tap through. What you decide '
            f'while playing becomes the brief a project starts from. Nothing here is required: a person with '
            f'a document, or with nothing, starts a project from the next tab as before.</p>'
            f'<form class="ask" method="get" action="/brief"><input name="name" placeholder="Club boat bookings" '
            f'autocomplete="off" aria-label="The product\'s name">'
            f'<button class="go" type="submit">Start</button></form>'
            f"{'<ul>' + had + '</ul>' if had else ''}</div>")


def sketch_page(slug: str) -> str:
    """One sketch: the steps, the conversation, the brief so far, and the prototype where there is one."""
    said = for_slug(slug).said()
    now = said["step"]
    steps = "".join(f'<span class="{"now" if number == now else ""}">{number} {esc(name)}</span>'
                    for number, name in enumerate(STEPS, 1))
    home = workspace(slug)
    played = f"/brief/files/{quote(slug)}/{PROTOTYPE}/index.html"
    has_prototype = (home / PROTOTYPE / "index.html").is_file()
    frame = (f'<iframe title="The prototype" src="{played}" data-src="{played}"></iframe>' if has_prototype
             else f'<iframe title="The prototype" hidden data-src="{played}"></iframe>'
                  f'<p class="none">Nothing drawn yet. Say what the product is.</p>')
    return (f'<div id="sketch" data-sketch="{esc(slug)}">'
            f'<div><nav class="steps" aria-label="Steps">{steps}</nav>'
            f'<div class="card" style="margin-top:14px"><div class="head"><h2>{esc(slug)}</h2>'
            f'<button type="button" data-clear>New conversation</button></div>'
            f'<div class="log" role="log" aria-live="polite"></div>'
            f'<p class="empty">Say what the product is: who uses it, and what they do with it.</p>'
            f'<form class="ask"><input placeholder="Members book one of the club boats for a morning…" '
            f'autocomplete="off" aria-label="Say something"><button class="go" type="submit">Say</button></form>'
            f'</div></div>'
            f'<div><div class="card"><h2>The brief, as the start page will read it</h2>'
            f'<ul class="check"></ul><p class="none">Nothing written yet.</p>'
            f'<p class="empty" style="margin-top:8px">Folder: <code>{esc(home / BRIEF)}</code></p></div>'
            f'<div class="card" style="margin-top:14px"><h2>The prototype</h2>{frame}</div></div></div>')


def page(query: str) -> str:
    slug = chosen(query)
    body = sketch_page(slug) if slug else listing()
    return document("Describe a product", "A prototype to play with, and the brief it leaves behind",
                    f"<style>{STYLE}</style>{body}", SCRIPT, now="/brief")


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
            bridge.send(404, "no such file in this sketch", "text/plain; charset=utf-8")
        else:
            bridge.send(200, found[0].read_bytes(), found[1])
    else:
        return False
    return True


def route_post(bridge: Any, where: str, held: dict) -> bool:
    """Answer a POST of this page's — a turn, or a new conversation — or say it was not one."""
    if where not in ("/brief/ask", "/brief/reset"):
        return False
    try:
        sketch = for_slug(str(held.get("sketch") or ""))
        said = sketch.ask(str(held.get("message") or "")) if where == "/brief/ask" else sketch.reset()
        bridge.send(200, said, "text/plain; charset=utf-8")
    except ValueError as refused:
        bridge.send(400, str(refused), "text/plain; charset=utf-8")
    return True

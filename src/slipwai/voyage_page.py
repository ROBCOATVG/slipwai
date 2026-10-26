"""The Voyage tab: where this project stands — the passage, the model, the screens built so far, the work.

The Board is the operations view: streams, speed, the inbox. This is the "where are we" view, and it is a
tab rather than a card for that reason — one link each way, and the page a generate lands on, because that
is the question a person has at that moment. Nothing on it is editable: a column somebody could drag a card
between would be a status field by another name, and the one action here, telling a stream, is the board's.
"""
from __future__ import annotations

import json
from pathlib import Path

from .bridge_page import SCRIPT as BOARD_SCRIPT
from .bridge_page import fitting_card, live_cards, live_sub
from .console_page import console_card
from .decision_log import SCRIPT as DECISIONS_SCRIPT
from .decision_log import STYLE as DECISIONS_STYLE
from .feedback_card import SCRIPT as FEEDBACK_SCRIPT
from .feedback_card import STYLE as FEEDBACK_STYLE
from .feedback_card import opener
from .live_page import STRIP_SCRIPT
from .live_page import STYLE as LIVE_STYLE
from .page_shell import document, esc
from .passage import Stage, current, surface_pages
from .settings_card import project_tabs
from .try_card import SCRIPT as TRY_SCRIPT
from .try_card import STYLE as TRY_STYLE
from .voyage import COLUMNS, SPEC, SPEC_ROUTE, viewer_config

# budget: 790 — the bands of one window: where the project stands, what to expect of the stage it is on,
# who answers at each stop of the run, the model, the screens built so far, and the work. A module per band
# would be copies of the poll that repaints them all — and the poll is now the reason as much as the bands
# are: it repaints the strip, and reloads the window when the signature says the page is built out of
# different files than the ones it was drawn from. Both halves have to agree on what a band is, so both are here.
# and a red card that opens on what its slice waits for, with a box that answers that slice and no other
# and the strip's amber attention beside its red stop
# and a slice card that is its number, its title and its stage until it is opened
# and the Try it card, placed here and drawn by `try_card.py`
# and the Now strip and a slice's live caption, drawn by `live_page.py`
# and the tabs the bands below the strip sit in, and the Feedback card in one of them (`feedback_card.py`)
# and the decision log's tab, drawn by `decision_log.py`

TITLES = {"todo": "To do", "queued": "Queued", "working": "Working", "waiting": "Waiting on you", "done": "Done"}
#: The model's controls, in the order they sit on the bar: what each does, its face, and its tooltip.
MODEL_CONTROLS = (("left", "←", "Nudge left"), ("right", "→", "Nudge right"), ("up", "↑", "Nudge up"),
                  ("down", "↓", "Nudge down"), ("out", "−", "Zoom out"), ("in", "+", "Zoom in"),
                  ("reset", "1:1", "Actual size"), ("fit", "Fit", "Fit the whole model"),
                  ("lightbox", "⤢", "Open full screen"))
#: What each stage's dot says: a tick, a dot, or its number.
DOTS = {"done": "✓", "working": "●", "attention": "!", "waiting": "■", "skipped": "·"}

STYLE = """
.passage{display:grid;grid-template-columns:repeat(var(--stages,8),minmax(0,1fr));position:relative;padding-top:6px}
/* Below a certain width a nine-across strip is nine words broken into letters. Two rows of dots is still
   a strip; the rule behind them is not, so it goes. */
@media (max-width:860px){.passage{grid-template-columns:repeat(3,minmax(0,1fr));gap:14px 0}
  .passage::before{display:none}}
.passage::before{content:"";position:absolute;left:6%;right:6%;top:20px;height:3px;background:var(--rule);border-radius:2px}
.stage{display:grid;gap:6px;justify-items:center;text-align:center;padding:0 6px;position:relative;min-width:0}
.stage .dot{width:30px;height:30px;border-radius:50%;border:3px solid var(--rule);background:var(--paper);display:grid;
  place-items:center;font-size:.72rem;color:var(--ink-3);position:relative}
.stage.done .dot{background:var(--teal);border-color:var(--teal);color:#fff}
.stage.working .dot{border-color:var(--brass);color:var(--brass);background:var(--brass-soft)}
.stage.working .dot::after{content:"";position:absolute;inset:-7px;border-radius:50%;border:2px solid var(--brass);
  opacity:.5;animation:pulse 1.6s ease-out infinite}
.stage.waiting .dot{border-color:#b4432f;background:#b4432f;color:#fff}
.stage.attention .dot{border-color:#c77d14;color:#c77d14;background:var(--brass-soft)}
.stage.attention .dot::after{content:"";position:absolute;inset:-7px;border-radius:50%;border:2px solid #c77d14;
  opacity:.5;animation:pulse 1.6s ease-out infinite}
@keyframes pulse{from{transform:scale(.85);opacity:.6}to{transform:scale(1.25);opacity:0}}
@media (prefers-reduced-motion:reduce){.stage.working .dot::after,.stage.attention .dot::after{animation:none}}
.stage b{font-size:.84rem;line-height:1.2}.stage.working b{color:var(--brass)}.stage.waiting b{color:#b4432f}
.stage.attention b{color:#c77d14}
.stage small{font-size:.74rem;color:var(--ink-3);line-height:1.3}
.stage .ev{font-family:ui-monospace,Menlo,monospace;font-size:.68rem;color:var(--ink-3);word-break:break-all}
.stage.skipped{opacity:.4}.stage.todo .dot{opacity:.75}
.next{border-top:1px solid var(--rule-2);padding-top:12px;display:grid;gap:8px}
a.quiet{font:inherit;padding:7px 14px;border-radius:7px;border:1px solid var(--teal);background:transparent;
  color:var(--teal);text-decoration:none;align-self:center}
a.quiet:hover{background:var(--teal-soft)}
.expect .now{border-left:3px solid var(--brass);padding-left:12px;margin:0 0 10px}
.expect .now .who{display:block;font-size:.78rem;letter-spacing:.06em;text-transform:uppercase;
  color:var(--brass);margin-bottom:3px}
.expect .now p{margin:0;font-size:.9rem;color:var(--ink-2)}
.expect ol{margin:8px 0 0;padding:0 0 0 18px;display:grid;gap:7px;font-size:.86rem;color:var(--ink-2)}
.expect ol b.who{color:var(--ink);font-weight:600}
.expect ol li.gone{opacity:.45}
.columns{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:12px}
.col h3{font-size:.78rem;letter-spacing:.06em;text-transform:uppercase;color:var(--ink-3);margin:0 0 8px;
  padding-bottom:6px;border-bottom:2px solid var(--rule)}
.col.queued h3{border-color:var(--brass-soft)}
.col.done h3{border-color:var(--teal)}.col.working h3{border-color:var(--brass)}.col.waiting h3{border-color:#b4432f}
.slice{border:1px solid var(--rule);border-radius:8px;padding:8px 10px;margin-bottom:8px;display:grid;gap:3px;
  background:var(--paper)}
.slice b{font-size:.86rem}.slice .fw{font-size:.72rem;color:var(--ink-3);font-family:ui-monospace,Menlo,monospace}
.slice .why{font-size:.78rem;color:var(--ink-2)}
details.slice summary{display:flex;flex-wrap:wrap;align-items:center;gap:4px 8px;cursor:pointer;
  list-style:none}
.slice .chip{font-size:.7rem;padding:1px 7px;border-radius:999px;border:1px solid var(--rule);color:var(--ink-2);
  white-space:nowrap}
.slice.working .chip{border-color:var(--brass);color:var(--brass)}
.slice.waiting .chip{border-color:#b4432f;color:#b4432f}
details.slice .facts{display:grid;grid-template-columns:auto 1fr;gap:2px 10px;margin:6px 0 0;font-size:.78rem}
details.slice .facts dt{color:var(--ink-3)}details.slice .facts dd{margin:0;color:var(--ink-2);overflow-wrap:anywhere}
details.slice summary::-webkit-details-marker{display:none}
details.slice[open]{grid-column:1 / -1}
details.slice .park{font-size:.8rem;color:var(--ink-2);margin:6px 0 0;white-space:pre-wrap}
details.slice .asked{font-size:.8rem;margin:4px 0;padding-left:18px;display:grid;gap:4px}
details.slice textarea{width:100%;box-sizing:border-box;font:inherit;font-size:.84rem;margin-top:6px}
details.slice button{justify-self:start;margin-top:4px}
.slice.queued{border-style:dashed;border-color:var(--brass)}
.slice.waiting{border-color:#b4432f}.slice.working{border-color:var(--brass)}.slice.done{border-color:var(--teal-soft)}
.mocks{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px}
.mock{display:grid;gap:4px;text-decoration:none;color:inherit;border:1px solid var(--rule);border-radius:8px;
  padding:8px;background:var(--paper)}
.mock:hover{border-color:var(--teal)}
.mocks .board{grid-column:1 / -1;max-width:720px}.mocks .board iframe{aspect-ratio:16/9}
.mock iframe{width:100%;aspect-ratio:4/3;border:0;border-radius:4px;background:#fff;pointer-events:none;
  transform-origin:0 0}
.mock b{font-size:.84rem}.mock .fw{font-size:.72rem;color:var(--ink-3);font-family:ui-monospace,Menlo,monospace}
.shots{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:8px}
.shot{display:grid;gap:4px;text-decoration:none;color:inherit}
.shot img{width:100%;aspect-ratio:4/3;object-fit:contain;object-position:top;border-radius:4px;background:#fff;
  border:1px solid var(--rule)}
.compare{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:16px;align-items:start}
.compare h3{font-size:.78rem;letter-spacing:.06em;text-transform:uppercase;color:var(--ink-3);margin:0 0 8px}
.viewer{border:1px solid var(--rule);border-radius:8px;overflow:hidden;background:#fff}
.viewer .bar{display:flex;gap:8px;align-items:center;padding:6px 10px;border-bottom:1px solid #e3e3e3;
  background:#f7f7f7;color:#555;font-size:.78rem}
.viewer .canvas{height:520px !important;width:auto !important;overflow:hidden !important;position:relative;
  background:#fff;cursor:grab}
.viewer .canvas:active{cursor:grabbing}
.viewer .sp{flex:1}
.viewer .model-dial{display:flex;gap:4px}
.viewer .model-dial button{font:inherit;font-size:.78rem;min-width:28px;padding:2px 7px;border:1px solid #d0d0d0;
  border-radius:4px;background:#fff;color:#444;cursor:pointer}
.viewer .model-dial button:hover{border-color:#0f6b6b;color:#0f6b6b}
.viewer .hint{font-size:.74rem;color:#666;padding:6px 10px;margin:0;border-top:1px solid #e3e3e3;background:#fafafa}
.tabs{display:flex;flex-wrap:wrap;gap:4px;margin:18px 0 0;border-bottom:1px solid var(--rule)}
.tabs button{font:inherit;font-size:.88rem;background:none;border:1px solid transparent;border-bottom:0;
  border-radius:8px 8px 0 0;padding:7px 14px;margin-bottom:-1px;color:var(--ink-2);cursor:pointer}
.tabs button[aria-selected="true"]{background:var(--paper);border-color:var(--rule);color:var(--ink);font-weight:600}
.tabs .count{font-size:.72rem;padding:0 6px;border-radius:999px;margin-left:6px;background:var(--brass-soft);
  color:var(--brass)}
.tab[hidden]{display:none}
@media (max-width:900px){.passage{grid-template-columns:repeat(4,minmax(0,1fr));row-gap:18px}
  .passage::before{display:none}.columns{grid-template-columns:repeat(2,minmax(0,1fr))}
  .compare{grid-template-columns:1fr}}
@media (max-width:520px){.columns{grid-template-columns:1fr}.passage{grid-template-columns:repeat(2,minmax(0,1fr))}}
"""

SCRIPT = BOARD_SCRIPT + """
// The bands below the strip are tabs: one shown at a time, the choice kept in the address and in this
// browser, and a link to anything inside another tab — the strip's "Waiting on you" — opens that tab first.
(function(){
  const tabs = [...document.querySelectorAll('.tabs [data-tab]')];
  if (!tabs.length) return;
  const show = (name, keep) => {
    if (!tabs.some(one => one.dataset.tab === name)) name = tabs[0].dataset.tab;
    tabs.forEach(one => one.setAttribute('aria-selected', String(one.dataset.tab === name)));
    document.querySelectorAll('section.tab').forEach(one => { one.hidden = one.dataset.tab !== name; });
    if (keep) {
      try { localStorage.setItem('voyage-tab', name); } catch (fault) {}
      history.replaceState(null, '', location.pathname + location.search + '#tab-' + name);
    }
    document.dispatchEvent(new CustomEvent('voyage:tab', {detail: name}));
  };
  const into = id => {
    const node = id && document.getElementById(id);
    const panel = node && node.closest('section.tab');
    if (panel) { show(panel.dataset.tab, true); node.scrollIntoView({block: 'start'}); }
    return Boolean(panel);
  };
  let first = (location.hash.match(/^#tab-([a-z]+)$/) || [])[1];
  if (!first && !into(location.hash.slice(1))) { try { first = localStorage.getItem('voyage-tab'); } catch (fault) {} }
  if (first || !location.hash) show(first || '', false);
  document.addEventListener('click', event => {
    const tab = event.target.closest('.tabs [data-tab]');
    if (tab) { show(tab.dataset.tab, true); return; }
    const link = event.target.closest('a[href^="#"]');
    if (link && into(link.getAttribute('href').slice(1))) event.preventDefault();
    // A Feedback button on a slice's card opens the box, which lives on the feedback tab.
    const opener = event.target.closest('[data-feedback]');
    const box = document.getElementById('feedback-box');
    const home = box && box.closest('section.tab');
    if (opener && home && !home.contains(opener)) show(home.dataset.tab, true);
  }, true);
})();
// The strip, kept current while the board's child or the fleet is moving: the stages are re-read on the
// server and only their state and words change here, so the page never flickers.
(function(){
  const strip = document.querySelector('.passage');
  if (!strip) return;
  const paint = (found) => {
    for (const stage of found.stages) {
      const node = strip.querySelector('[data-stage="' + stage.key + '"]');
      if (!node) continue;
      node.className = 'stage ' + stage.state;
      node.querySelector('.dot').textContent = stage.dot;
      node.querySelector('small').textContent = stage.detail;
    }
    const now = document.getElementById('now');
    if (now && found.now) now.textContent = found.now;
    const launch = document.getElementById('launch');
    if (launch) launch.hidden = !found.launchable;
    const cast = document.getElementById('cast-off');
    if (cast) cast.hidden = !found.castable;
    const stop = document.getElementById('stop');
    if (stop) { stop.hidden = !found.stoppable; stop.disabled = false; }
    const draw = document.getElementById('draw');
    if (draw) { draw.hidden = !found.drawable; draw.disabled = false; }
    const model = document.getElementById('model');
    if (model) { model.hidden = !found.modelable; model.disabled = false; }
  };
  // Two things change on this page and only one of them is the strip. The cards — the storyboard, the
  // model, the work, the button that opens the specification — are rendered once, out of files that may
  // not exist yet, and a window opened during the draft watched the specification land and showed nothing
  // of it. So the poll carries a signature of what the page was built from, and a difference is a reload:
  // what changes there is which cards exist, which is rare, and a repaint of it would be the server
  // rendering the page twice.
  let shape = strip.closest('.card').dataset.shape;
  const poll = async () => {
    let found;
    // Slower when nothing is moving, and never stopped: the stages that move this project on are run in
    // the agent, by a person, and the board is not told. A poll that gave up the moment nothing of its
    // own was running is what made this page stale in the first place.
    try { found = await (await fetch('/voyage.json')).json(); }
    catch (fault) { setTimeout(poll, 8000); return; }
    // Not while somebody is typing an answer into a card: the reload would throw the words away.
    const typing = [...document.querySelectorAll('details.slice textarea, #feedback-box textarea')]
      .some(box => box.value.trim());
    if (found.shape !== shape && !typing) { location.reload(); return; }
    paint(found);
    setTimeout(poll, found.moving ? 2500 : 8000);
  };
  setTimeout(poll, 2500);
  document.addEventListener('click', event => {
    if (event.target.id === 'cast-off') { event.target.disabled = true; send('/cast-off', {}); }
    if (event.target.id === 'draw') { event.target.disabled = true; send('/draw', {}); }
    if (event.target.id === 'model') { event.target.disabled = true; send('/model', {}); }
    if (event.target.id === 'intake-go') { event.target.disabled = true; send('/intake', {}); }
    const answer = event.target.dataset && event.target.dataset.answer;
    if (answer) {
      const box = document.getElementById(event.target.dataset.box);
      if (box && box.value.trim()) {
        event.target.disabled = true;
        send('/tell', {fairway: answer, slice: event.target.dataset.slice, message: box.value.trim()});
      }
    }
    const story = event.target.dataset && event.target.dataset.storyboard;
    if (story) {
      const why = document.getElementById('why-' + story);
      const buttons = [...document.querySelectorAll('[data-storyboard]')]
        .filter(one => one.dataset.storyboard === story);
      buttons.forEach(one => { one.disabled = true; });
      fetch('/storyboard', {method:'POST', headers:{'Content-Type':'application/json'},
                            body: JSON.stringify({feature: story, verdict: event.target.dataset.verdict,
                                                  reason: why ? why.value : ''})})
        .then(async answer => {
          if (answer.ok) location.reload();
          else { buttons.forEach(one => { one.disabled = false; }); alert(await answer.text()); }
        })
        .catch(() => buttons.forEach(one => { one.disabled = false; }));
    }
    // No confirm(): a dialog blocks every later event in this window, and stopping is asked rather than
    // done — a captain finishes its stage, so there is nothing here to be sorry about afterwards.
    if (event.target.id === 'stop') { event.target.disabled = true; send('/stop', {}); }
    const dial = event.target.dataset && event.target.dataset.dial;
    if (dial) {
      event.target.disabled = true;
      send(dial === 'cruise' ? '/wheel' : '/dial',
           dial === 'cruise' ? {stop: event.target.dataset.key, value: event.target.dataset.value}
                             : {panel: dial, key: event.target.dataset.key,
                                value: event.target.dataset.value});
    }
  });
  // A menu rather than a dial, where a setting has twenty-two rows: the same send, on the value chosen.
  document.addEventListener('change', event => {
    const where = event.target.dataset && event.target.dataset.dial;
    if (where && event.target.tagName === 'SELECT') {
      send('/dial', {panel: where, key: event.target.dataset.key, value: event.target.value});
    }
  });
})();
"""


#: Runs after draw.io's viewer has loaded: the model drawn into the canvas by a viewer the page holds,
#: rather than one the script makes for itself, because the controls need the graph it holds. Panning is
#: turned on with the left button — the viewer's own default is off, since a page that embeds a diagram
#: usually scrolls — the wheel zooms, and each button is one call on the graph.
MODEL_SCRIPT = """
(function(){
  const box = document.getElementById('model-canvas');
  if (!box || typeof GraphViewer === 'undefined') return;
  const config = JSON.parse(box.dataset.model);
  const xml = config.xml; delete config.xml;
  box.textContent = '';
  let viewer;
  try { viewer = new GraphViewer(box, mxUtils.parseXml(xml).documentElement, config); }
  catch (fault) { box.textContent = 'the draw.io viewer could not draw the model: ' + fault; return; }
  const g = viewer.graph;
  box.viewer = viewer;  // for whoever wants to drive it from the console
  // The viewer sizes its container to the picture; this canvas keeps its own size and shows a window on
  // it, which is what panning and zooming are for. Panning moves the picture, never a scrollbar.
  box.style.width = ''; box.style.height = ''; box.style.overflow = 'hidden';
  g.useScrollbarsForPanning = false;
  // A timeline is wider than it is tall by a long way, and fitted to the canvas's width it is a thin line
  // nobody can read: fit the lanes to the height instead, and start at the left, where the model starts.
  g.fit(12, false, 0, true, true, false);
  g.view.setTranslate(12 / g.view.scale, g.view.translate.y);
  g.setPanning(true);
  g.panningHandler.useLeftButtonForPanning = true;
  g.panningHandler.ignoreCell = true;
  mxEvent.addMouseWheelListener(function(evt, up){
    if (!box.contains(evt.target)) return;
    if (up) g.zoomIn(); else g.zoomOut();
    mxEvent.consume(evt);
  }, box);
  const nudge = (dx, dy) => {
    const t = g.view.translate, s = g.view.scale;
    g.view.setTranslate(t.x + dx / s, t.y + dy / s);
  };
  const step = 160;
  const act = {
    left: () => nudge(step, 0), right: () => nudge(-step, 0), up: () => nudge(0, step), down: () => nudge(0, -step),
    in: () => g.zoomIn(), out: () => g.zoomOut(),
    reset: () => { g.zoomTo(1); g.view.setTranslate(12, 12); },
    fit: () => { g.minFitScale = 0.01; g.fit(12); }, lightbox: () => viewer.showLightbox(),
  };
  document.querySelectorAll('[data-model-do]').forEach(button => {
    button.addEventListener('click', () => { const run = act[button.dataset.modelDo]; if (run) run(); });
  });
  box.addEventListener('keydown', evt => {
    const keys = {ArrowLeft:'left', ArrowRight:'right', ArrowUp:'up', ArrowDown:'down',
                  '+':'in', '=':'in', '-':'out', '0':'reset', f:'fit'};
    const key = keys[evt.key];
    if (key) { act[key](); evt.preventDefault(); }
  });
  box.tabIndex = 0;
  // Drawn while its tab was hidden, the canvas had no size to fit to: fit it again the first time it shows.
  let fitted = box.offsetWidth > 0;
  document.addEventListener('voyage:tab', () => {
    if (fitted || !box.offsetWidth) return;
    fitted = true;
    g.fit(12, false, 0, true, true, false);
    g.view.setTranslate(12 / g.view.scale, g.view.translate.y);
  });
})();
"""


def stage_html(stage: Stage, index: int) -> str:
    """One stage of the strip. A stage waiting on a person is a link to the thing that is waiting: the
    inbox for the fleet's stages, the receipt for the board's own child.

    A skipped stage shows no evidence, and that is the whole of what evidence is: the file that proves the
    stage done. A stage this profile has not got is never going to be done, so the path under it was a file
    the project will never have — `docs/event-model/model.yaml` under a faint Event model on the standard
    profile, which reads as a thing to go and make rather than a column that is there to be ignored.
    """
    dot = DOTS.get(stage.state, "") or str(index + 1)
    title = esc(stage.title)
    if stage.state in ("waiting", "attention"):
        where = ("#waiting" if stage.key in ("slices", "accepted")
                 else "#mockups" if stage.key == "storyboard" else "#fitting")
        title = f'<a href="{where}">{title}</a>'
    shown = "" if stage.state == "skipped" else stage.evidence
    return (f'<div class="stage {esc(stage.state)}" data-stage="{esc(stage.key)}" role="listitem">'
            f'<div class="dot">{esc(dot)}</div><b>{title}</b><small>{esc(stage.detail)}</small>'
            f'<span class="ev">{esc(shown)}</span></div>')


def stage_payload(found: list[Stage]) -> list[dict[str, str]]:
    """What the poll repaints: the stage, its state, its dot and its words."""
    return [{"key": one.key, "state": one.state, "detail": one.detail,
             "dot": DOTS.get(one.state, "") or str(index + 1)} for index, one in enumerate(found)]


def said(line: str) -> str:
    """One expectation, with the half that matters in bold.

    `**…**` and not markup, because the sentence is written in `passage.py`, where a stage knows what to
    expect of itself and nothing knows it is going to be read in a browser.
    """
    parts = esc(line).split("**")
    return "".join(f"<b>{part}</b>" if index % 2 else part for index, part in enumerate(parts))


def expect_card(found: list[Stage]) -> str:
    """What the stage this project is on will do, and whether it will stop for a person.

    The strip above says where the work is. This says whether what it is doing is normal, which is a
    different question and the one somebody asks at the twenty-minute mark: a stage that waits for a person
    by design looks exactly like a stage that has hung, and until this nothing on the page said which it
    was. The stage somebody is on is given its own space; the rest are the whole voyage in order, so the
    answer to "and then what" is one click from the answer to "what now".

    A skipped stage is left out. The strip keeps its faint column, which says something worth saying — that
    this project is on the standard profile — but there is nothing to expect of a stage that is not going to
    happen, and a line here about one would be the page mentioning a non-event twice.
    """
    now = current(found)
    rows = "".join(
        f'<li class="{"" if one.state in ("working", "attention", "waiting", "todo") else "gone"}">'
        f"<b class=\"who\">{esc(one.title)}</b> \u2014 {said(one.expect)}</li>"
        for one in found if one.expect and one.state != "skipped")
    here = (f'<div class="now"><span class="who">Now \u00b7 {esc(now.title)}</span>'
            f"<p>{said(now.expect)}</p></div>" if now and now.expect else "")
    # The whole voyage behind a click: above the tabs, eight paragraphs pushed them off the screen.
    return ('<div class="card expect"><h2>What to expect</h2>'
            f"{here}<details><summary>Every stage, in order</summary><ol>{rows}</ol></details></div>")


def passage_card(name: str, found: list[Stage], launchable: bool, model_next: bool, castable: bool = False,
                 stoppable: bool = False, feature: str = "", drawable: bool = False, shape: str = "",
                 modelable: bool = False) -> str:
    strip = "".join(stage_html(one, index) for index, one in enumerate(found))
    wide = f"--stages:{max(1, len(found))}"
    said = now_said(found)
    # On the event profile the step after the specification is a conversation, not a button: the chart is
    # drawn from the model, so there is nothing to launch until somebody has modelled.
    # A fleet that is not running after the split is the one silence the tree cannot explain — a launch
    # whose captains never lit, a machine restarted — so the button to cast off again is here, and said.
    button = ('<span class="chip">Model it next: the event-modeling skill, in the agent, with a person</span>'
              if model_next else
              f'<button class="go" id="launch"{"" if launchable else " hidden"}>Continue the build</button>'
              f'<button class="go" id="cast-off"{"" if castable else " hidden"}>Cast off the fleet</button>')
    # Beside them whatever else the strip says, because the one thing a person wants at the moment they
    # want it is the way to make it stop. Not styled as the primary action: stopping is the exception.
    button += (f'<button class="install" id="stop"{"" if stoppable else " hidden"}>Stop the fleet</button>')
    # The stage between a specification and a model had no button at all, and its line said to go and type
    # a command in the agent — on the page a person had just run two headless sessions from. This runs the
    # half of it nobody has to be present for; the half they do is the storyboard, below.
    button += (f'<button class="go" id="draw"{"" if drawable else " hidden"}>Draw the surfaces</button>')
    # Approving starts the model once and locks the verdict, so a model step that failed had no way back but
    # the agent. Always in the page and shown by the poll, as Draw is, so the page's shape does not move.
    button += (f'<button class="go" id="model"{"" if modelable else " hidden"}>Model again</button>')
    # And the thing to do *before* pressing the primary one. Continue the build is a person's word that the
    # specification is good to build from, and a page that asks for that word while giving no way to read
    # the file is asking somebody to agree to something they have not opened. Quiet, beside it, and in its
    # own tab, so reading it does not cost the page the run is watched on.
    if feature:
        button += (f'<a class="quiet" href="{esc(SPEC_ROUTE)}{esc(feature)}" target="_blank" rel="noopener">'
                   f"Open specs/{esc(feature)}/{esc(SPEC)}</a>")
    return (f'<div class="card" id="passage" data-shape="{esc(shape)}"><h2>{esc(name)}</h2>'
            f'<div class="passage" role="list" style="{esc(wide)}">{strip}</div>'
            f'<div class="next"><p id="now">{esc(said)}</p><div class="ask">{button}</div></div></div>')


def model_card(xml: str, note: str, viewer_fault: str) -> str:
    if not xml:
        return f'<div class="card"><h2>The model</h2><p class="empty">{esc(note)}</p></div>'
    # The controls are the board's, not the viewer's toolbar: the viewer's offers zoom in, out and fit, and a
    # timeline that grows sideways forever wants to be dragged, wheeled and nudged as well.
    dial = "".join(f'<button type="button" data-model-do="{what}" title="{esc(hint)}">{esc(label)}</button>'
                   for what, label, hint in MODEL_CONTROLS)
    bar = ('<div class="bar"><b>model.drawio</b><span>· read-only · each slice\'s caption is stroked by where it '
           f'stands</span><span class="sp"></span><span class="model-dial">{dial}</span></div>')
    # The viewer is given the canvas once its script has loaded; until then, and on a machine the script
    # never reaches, the words inside it are what a person sees.
    body = (f'<p class="empty">{esc(viewer_fault)}</p>' if viewer_fault else
            f'<div class="canvas" id="model-canvas" data-model="{esc(viewer_config(xml))}"><p class="empty">Drawing '
            f"the model with draw.io's viewer — fetched once from viewer.diagrams.net the first time, kept after. "
            f'Where that never arrives, docs/event-model/model.drawio opens in draw.io.</p></div>'
            f'<p class="hint">Drag to pan, wheel to zoom, arrows nudge; ⤢ opens it full screen.</p>')
    warn = f'<p class="empty">{esc(note)}</p>' if note else ""
    return f'<div class="card"><h2>The model</h2>{warn}<div class="viewer">{bar}{body}</div></div>'


def slice_html(row: dict[str, str]) -> str:
    """One slice: its number and title, and a chip saying how far it has got. The rest behind a click.

    A card that carried its stream, its clearance word, its reason and its park was a wall of text times
    twenty-three, and the one thing a person scans the columns for — which slice, and how far along — was
    lost in it. Closed, a card is the slice and its stage; opened in place, it is everything the board knows
    about it, and for a slice waiting on a person, the box to answer it.
    """
    name = f'{row["slice"]} · {row["title"]}' if row.get("title") else row["slice"]
    chip = chip_of(row)
    shown = f'<span class="chip">{esc(chip)}</span>' if chip else ""
    answer = answer_html(row) if row["state"] == "waiting" and row.get("fairway") else ""
    cap = f'<span class="live-cap">{esc(row["live"])}</span>' if row.get("live") else ""
    said = opener("Feedback", {"from": "slice", "feature": row.get("feature", ""), "fairway": row.get("fairway", ""),
                               "slice": row["slice"]}, ask=f"What did {row['slice']} show you?")
    return (f'<details class="slice {esc(row["state"])}"><summary><b>{esc(name)}</b>{shown}{cap}</summary>'
            f'{facts_html(row)}{answer}<div class="ask">{said}</div></details>')


def chip_of(row: dict[str, str]) -> str:
    """The word on a closed card: its stage at work, `Queued` and its stage while it waits for a slot, and
    `Waiting on you` where a person holds it. Nothing on a slice still to do or done — the column says it."""
    stage = row.get("chip") or row.get("stage") or ""
    if row["state"] == "waiting":
        return "Waiting on you"
    if row.get("paused"):
        return f"Paused · lifts {row['paused']}"
    if row["state"] == "queued":
        return f"Queued · {stage}" if stage else "Queued"
    return stage if row["state"] == "working" else ""


def facts_html(row: dict[str, str]) -> str:
    """What an opened card says: only the facts there are, each on its own line."""
    when, _, said = row.get("commit", "").partition(" ")
    facts = (("Stream", row.get("fairway", "")), ("Stage", row.get("chip", "")),
             ("Clearance", row.get("clearance", "")), ("On its branch", row.get("artifacts", "").replace(",", ", ")),
             ("Last line", row.get("last", "")), ("Last commit", f"{when[:16]} {said}".strip() if said else ""),
             ("Why", "" if row["state"] == "waiting" else row.get("why", "")))
    lines = "".join(f"<dt>{esc(label)}</dt><dd>{esc(value)}</dd>" for label, value in facts if value)
    return f'<dl class="facts">{lines}</dl>' if lines else ""


def answer_html(row: dict[str, str]) -> str:
    """What a slice waiting on a person waits for, and a box to answer it, inside its opened card.

    The answer box was a stream's, further down, and a stream with three slices parked on three questions
    got one box. Opened, the card says the park and each open question, and what is typed goes to that slice
    — a `told` naming it, which clears its park and no sibling's, and which the captain records as the
    answer to its questions when it carries the slice on.
    """
    asked = "".join(f"<li>{esc(one)}</li>" for one in row.get("asked", "").splitlines() if one.strip())
    questions = f'<ol class="asked">{asked}</ol>' if asked else ""
    park = row.get("park") or row.get("why", "")
    box = f'answer-{row["slice"]}'
    target = row["slice"] if row.get("aim") else f'the {row["fairway"]} stream'
    return (f'<p class="park">{esc(park)}</p>{questions}'
            f'<textarea id="{esc(box)}" rows="4" placeholder="Your answer, or what {esc(row["slice"])} needs to '
            f'know"></textarea>'
            f'<button type="button" data-answer="{esc(row["fairway"])}" data-slice="{esc(row.get("aim", ""))}" '
            f'data-box="{esc(box)}">Send to {esc(target)}</button>')


def shot_html(shot: dict[str, str]) -> str:
    """One photograph, linked at its own size. The address is the file, so opening it is the picture."""
    label = shot["title"] or shot["name"]
    return (f'<a class="shot" href="{esc(shot["href"])}" target="_blank" rel="noopener">'
            f'<img src="{esc(shot["href"])}" alt="{esc(label)}" loading="lazy">'
            f"<b>{esc(label)}</b></a>")


def intended_html(mocks: list[dict[str, str]]) -> str:
    """The mock-ups of one feature, the storyboard where there is one — it is how the rest are reached."""
    boards = [row for row in mocks if row["name"] == "storyboard.html"]
    tiles = "".join(
        f'<a class="mock" href="{esc(row["href"])}" target="_blank" rel="noopener">'
        f'<iframe src="{esc(row["href"])}" loading="lazy" tabindex="-1" title="{esc(row["title"])}"></iframe>'
        f"<b>{esc(row['title'])}</b></a>"
        for row in (boards or mocks))
    return f"<div><h3>Intended</h3><div class=\"mocks\">{tiles}</div></div>"


def built_group(shots: list[dict[str, str]]) -> str:
    """One slice's photographs, under its name and the standing the columns already use."""
    one = shots[0]
    name = f'{one["slice"]} · {one["title"]}' if one["title"] else one["slice"]
    images = "".join(shot_html(shot) for shot in shots)
    return (f'<div class="slice {esc(one["state"])}"><b>{esc(name)}</b>'
            f'<span class="fw">{esc(TITLES[one["state"]])}</span><div class="shots">{images}</div></div>')


def screens_card(shots: list[dict[str, str]], mocks: list[dict[str, str]], app: str) -> str:
    """What has been rendered, beside the mock-up it was drawn from.

    Nothing where the design review has not photographed a screen yet: an empty band would be a promise
    that pictures are coming. The running app is a link, where the project records one, and not a frame —
    the picture is the record, and the link is how a person opens the thing itself.
    """
    if not shots:
        return ""
    features: list[str] = []
    for shot in shots:
        if shot["feature"] not in features:
            features.append(shot["feature"])
    blocks = ""
    for feature in features:
        mine = [shot for shot in shots if shot["feature"] == feature]
        groups: list[list[dict[str, str]]] = []
        for shot in mine:
            if groups and groups[-1][0]["slice"] == shot["slice"]:
                groups[-1].append(shot)
            else:
                groups.append([shot])
        built = f"<div><h3>Built</h3>{''.join(built_group(group) for group in groups)}</div>"
        intended = [row for row in mocks if row["feature"] == feature]
        blocks += f'<div class="compare">{intended_html(intended)}{built}</div>' if intended else built
    link = (f'<a class="quiet" href="{esc(app)}" target="_blank" rel="noopener">Open the running app</a>'
            if app else "")
    return f'<div class="card" id="built"><h2>Built screens · {len(shots)}</h2>{link}{blocks}</div>'


def verdict_form(root: Path, feature: str) -> str:
    """Approve marks every drawn state approved. Disapprove parks them, and has to say why.

    Only where there is a page per surface to mark: a storyboard with the surfaces drawn inside it has no state
    a verdict can name, and buttons for one were buttons the server refused. That feature is told what is
    missing and what draws it, instead.
    """
    home = root / "specs" / feature / "mockups"
    if not surface_pages(home):
        return ('<p class="empty">This storyboard has no page per surface, so there is nothing to approve: '
                "each surface is drawn as its own page, which the storyboard links. Draw the surfaces draws it "
                "again.</p>")
    path = home / "mock-states.md"
    note = "Nothing on this storyboard is approved yet."
    text = path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""
    parked = next((line.split("parked:", 1)[1].strip()
                   for line in text.splitlines() if "\u2014 parked:" in line), "")
    if parked:
        note = (f"Disapproved: {parked}. It is being drawn again from that, and the new drawing waits on a "
                f"verdict of its own.")
    elif "\u2014 approved" in text:
        note = "Approved."
    # Either verdict locks both. A refusal (a disapproval with no reason) turns them back on in the page.
    held = " disabled" if parked or "\u2014 approved" in text else ""
    return (f'<form class="verdict" onsubmit="return false"><p class="empty">{esc(note)} '
            f"Approving marks every drawn state approved. Disapproving draws it again from your reason.</p>"
            f'<div class="ask"><input id="why-{esc(feature)}" type="text" maxlength="240" '
            f'placeholder="Why, if you disapprove"{held}>'
            f'<button type="button" class="go" data-storyboard="{esc(feature)}" data-verdict="approved"{held}>'
            f'Approve storyboard</button>'
            f'<button type="button" class="install" data-storyboard="{esc(feature)}" data-verdict="parked"{held}>'
            f"Disapprove</button></div></form>")


def mockups_card(found: list[dict[str, str]], root: Path | None = None) -> str:
    """The storyboard the mock-up stage wrote, where it wrote one — every mock-up is reached from it, which
    is what it is for — else the wireframes themselves, shown small. Nothing where the stage has not run."""
    if not found:
        return ""
    features: list[str] = []
    for row in found:
        if row["feature"] not in features:
            features.append(row["feature"])
    forms = "".join(verdict_form(root, feature) for feature in features) if root is not None else ""
    boards = [row for row in found if row["name"] == "storyboard.html"]
    if boards:
        tiles = "".join(
            f'<a class="mock board" href="{esc(row["href"])}" target="_blank" rel="noopener">'
            f'<iframe src="{esc(row["href"])}" loading="lazy" tabindex="-1" title="{esc(row["title"])}"></iframe>'
            f'<b>{esc(row["title"])}</b><span class="fw">{esc(row["feature"])} · '
            f'{sum(1 for one in found if one["feature"] == row["feature"]) - 1} mock-ups, from the storyboard'
            "</span></a>"
            for row in boards)
        return (f'<div class="card" id="mockups"><h2>Storyboard</h2><div class="mocks">{tiles}</div>'
                f"{forms}</div>")
    tiles = "".join(
        f'<a class="mock" href="{esc(row["href"])}" target="_blank" rel="noopener">'
        f'<iframe src="{esc(row["href"])}" loading="lazy" tabindex="-1" title="{esc(row["title"])}"></iframe>'
        f'<b>{esc(row["title"])}</b><span class="fw">{esc(row["feature"])} · {esc(row["name"])}</span></a>'
        for row in found)
    return (f'<div class="card" id="mockups"><h2>Mockups · {len(found)}</h2><div class="mocks">{tiles}</div>'
            f"{forms}</div>")


def intake_card(found: list) -> str:
    """Ideas handed to `/sail` that are not yet specified or killed, and the button that moves the earliest."""
    pending = [one for one in found if one.state not in ("specified", "kill")]
    if not pending:
        return ""
    rows = "".join(f"<p><b>{esc(one.slug)}</b> — {esc(one.state)}. {esc(one.detail)}</p>" for one in pending)
    return (f'<div class="card" id="intake"><h2>Next features</h2>{rows}'
            f'<div class="ask"><button class="go" id="intake-go">Continue the next feature</button></div></div>')


def feedback_points_card(points: list[dict]) -> str:
    """The next three feedback points: the observables a person is asked to look at first, by what delaying
    their judgement would cost, each with the decisions it would let them test. From the project's own
    `clearance.py --feedback`, so the number here is the number a captain's split would argue with."""
    if not points:
        return ""
    items = []
    for row in points:
        sources = (row.get("uncertainty") or {}).get("sources") or []
        said = "; ".join(str(one).split(" — ", 1)[0] for one in sources[:3])
        reach = (row.get("blast_radius") or {}).get("score", 0)
        cost = (row.get("cost_to_surface") or {}).get("score", 0)
        actor = f" for {esc(str(row['actor']))}" if row.get("actor") else ""
        score = row.get("score") or 0
        items.append(f'<li><span class="sid">{esc(str(row.get("slice", "")))}</span>'
                     f'<b>{esc(str(row.get("pattern", "")))}{actor}</b> · score {esc(f"{score:g}")}'
                     f' · {esc(str(reach))} unmerged slice{"s" if reach != 1 else ""} build on its marks · '
                     f'{esc(f"{cost:g}")} to surface'
                     + (f'<div class="empty">would test {esc(said)}</div>' if said else "") + "</li>")
    return ('<div class="card" id="feedback-points"><h2>Next feedback points</h2><p class="empty">What a person '
            "could judge next, by what delaying the judgement would cost. From `clearance.py --feedback`; the split "
            f'proposes its order from the same ranking.</p><ul class="new">{"".join(items)}</ul></div>')


def work_card(rows: list[dict[str, str]], fault: str) -> str:
    if fault:
        return f'<div class="card"><h2>The work</h2><p class="empty">{esc(fault)}</p></div>'
    if not rows:
        return ('<div class="card"><h2>The work</h2><p class="empty">No slices yet: the chart and the split are '
                "where they come from.</p></div>")
    columns = ""
    for state in COLUMNS:
        held = [row for row in rows if row["state"] == state]
        cards = "".join(slice_html(row) for row in held) or '<p class="empty">none</p>'
        columns += f'<div class="col {esc(state)}"><h3>{esc(TITLES[state])} · {len(held)}</h3>{cards}</div>'
    return f'<div class="card"><h2>The work</h2><div class="columns">{columns}</div></div>'


def page(root: Path, found: list[Stage], rows: list[dict[str, str]], fault: str, xml: str, note: str,
         viewer_fault: str, made: dict | None, launchable: bool, fleet: dict | None = None,
         config: dict | None = None, mocks: list[dict[str, str]] | None = None, castable: bool = False,
         stoppable: bool = False, feature: str = "", drawable: bool = False, shape: str = "",
         ideas: list | None = None, shots: list[dict[str, str]] | None = None, app: str = "",
         modelable: bool = False, trying: str = "", strip: str = "", feedback: str = "",
         decisions: tuple[str, int] = ("", 0), points: list[dict] | None = None, adopting: str = "",
         dates: str = "") -> str:
    now = current(found)
    # An adopted repository walks its own steps until its first specification, and the strip a generated
    # project has would name a stage it is not on: the adoption's card stands where the strip does.
    sub = ("adopting" if adopting else f"now: {now.title.lower()}" if now else "complete") \
        + (f" · {live_sub(fleet)}" if fleet else "")
    model_next = any(one.key == "model" and one.state == "todo" for one in found)
    landed = fitting_card(made, "Adopted" if adopting else "Made") if made else ""
    # The live cards, with their controls, under the model: how the work is going belongs on the page that
    # says what the work is.
    live = live_cards(fleet, config or {}, True, project_tabs(root, True)) if fleet else ""
    # Past it, the strategy's checkpoint stands above the strip, never in its place.
    where = adopting or dates + passage_card(root.resolve().name, found, launchable, model_next, castable, stoppable,
                                     feature, drawable, shape, modelable)
    taken = {shot["feature"] for shot in (shots or [])}
    # A feature's mock-ups move next to its screenshots. One that has no screenshot yet stays where it was.
    left = [row for row in (mocks or []) if row["feature"] not in taken]
    # The count on the tab is what waits on a person: a park that lifts by itself is paused, not waiting.
    waiting = len([row for row in (fleet or {}).get("inbox") or [] if row.get("paused") != "yes"])
    tabs = [("work", "Work", f"{strip}{feedback_points_card(points or [])}{work_card(rows, fault)}"),
            ("try", "Try it & feedback" if trying else "Feedback", f"{trying}{feedback}"),
            ("screens", "Screens", screens_card(shots or [], mocks or [], "" if trying else app)
             + mockups_card(left, root)),
            ("model", "Model", model_card(xml, note, viewer_fault) if xml or note or viewer_fault else ""),
            ("fleet", "Fleet" + (f'<span class="count">{waiting} waiting</span>' if waiting else ""), live),
            ("decisions", f'Decisions<span class="count" data-decisions-unread{"" if decisions[1] else " hidden"}>'
                          f"{decisions[1]} unread</span>", decisions[0]),
            ("next", "Next features", intake_card(ideas or []))]
    body = (f"<style>{STYLE}{TRY_STYLE if trying else ''}{FEEDBACK_STYLE if feedback else ''}"
            f"{DECISIONS_STYLE if decisions[0] else ''}{LIVE_STYLE}</style>"
            f"{where}{landed}{'' if adopting else expect_card(found)}{tabs_html(tabs)}{console_card()}")
    script = SCRIPT + (TRY_SCRIPT if trying else "") + (FEEDBACK_SCRIPT if feedback else "") \
        + (STRIP_SCRIPT if strip else "") + (DECISIONS_SCRIPT if decisions[0] else "") \
        + ("" if viewer_fault or not xml else "\n")
    # Named for the project rather than "Voyage": this is a window of its own now, and what a person
    # picks it out by — in the dock, in a window switcher, across two runs open at once — is its title.
    page_html = document(f"Voyage \u00b7 {root.resolve().name}", sub, body, script, now="/voyage")
    if xml and not viewer_fault:
        page_html = page_html.replace(
            "</body>", f'<script src="/drawio-viewer.js"></script><script>{MODEL_SCRIPT}</script></body>', 1)
    return page_html


def tabs_html(tabs: list[tuple[str, str, str]]) -> str:
    """The bands below the strip, one tab each, leaving out a band with nothing in it. The first is shown
    until the page's script says which one this person had open."""
    kept = [(key, face, body) for key, face, body in tabs if body.strip()]
    if not kept:
        return ""
    bar = "".join(f'<button type="button" role="tab" data-tab="{key}" aria-selected="{str(n == 0).lower()}">'
                  f"{face}</button>" for n, (key, face, _) in enumerate(kept))
    panels = "".join(f'<section class="tab" data-tab="{key}" role="tabpanel"{" hidden" if n else ""}>{body}</section>'
                     for n, (key, _, body) in enumerate(kept))
    return f'<nav class="tabs" role="tablist">{bar}</nav>{panels}'


def now_said(found: list[Stage]) -> str:
    """The one sentence about where the project is and what moves it, as the strip, the poll and the
    landing all say it."""
    now = current(found)
    said = (f"Now: {now.title.lower()} — {now.detail}. Next: {now.next}." if now
            else "Every stage is done: the voyage is complete.")
    spec = next((one for one in found if one.key == "specification" and "waiting:" in one.detail), None)
    if spec and (now is None or now.key != "specification"):
        said += f" {spec.detail[spec.detail.index('waiting:'):]}."
    return said


def payload(found: list[Stage], launchable: bool, moving: bool, castable: bool = False,
            stoppable: bool = False, drawable: bool = False, shape: str = "", modelable: bool = False) -> str:
    return json.dumps({"stages": stage_payload(found), "launchable": launchable, "moving": moving,
                       "castable": castable, "stoppable": stoppable, "drawable": drawable, "modelable": modelable,
                       "shape": shape, "now": now_said(found)})

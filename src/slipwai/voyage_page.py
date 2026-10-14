"""The Voyage tab: where this project stands, as three bands — the passage, the model, the work.

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
from .page_shell import document, esc
from .passage import Stage, current
from .voyage import COLUMNS, viewer_config

TITLES = {"todo": "To do", "working": "Working", "waiting": "Waiting on you", "done": "Done"}
#: The model's controls, in the order they sit on the bar: what each does, its face, and its tooltip.
MODEL_CONTROLS = (("left", "←", "Nudge left"), ("right", "→", "Nudge right"), ("up", "↑", "Nudge up"),
                  ("down", "↓", "Nudge down"), ("out", "−", "Zoom out"), ("in", "+", "Zoom in"),
                  ("reset", "1:1", "Actual size"), ("fit", "Fit", "Fit the whole model"),
                  ("lightbox", "⤢", "Open full screen"))
#: What each stage's dot says: a tick, a dot, or its number.
DOTS = {"done": "✓", "working": "●", "waiting": "!", "skipped": "·"}

STYLE = """
.passage{display:grid;grid-template-columns:repeat(8,minmax(0,1fr));position:relative;padding-top:6px}
.passage::before{content:"";position:absolute;left:6%;right:6%;top:20px;height:3px;background:var(--rule);border-radius:2px}
.stage{display:grid;gap:6px;justify-items:center;text-align:center;padding:0 6px;position:relative;min-width:0}
.stage .dot{width:30px;height:30px;border-radius:50%;border:3px solid var(--rule);background:var(--paper);display:grid;
  place-items:center;font-size:.72rem;color:var(--ink-3);position:relative}
.stage.done .dot{background:var(--teal);border-color:var(--teal);color:#fff}
.stage.working .dot{border-color:var(--brass);color:var(--brass);background:var(--brass-soft)}
.stage.working .dot::after{content:"";position:absolute;inset:-7px;border-radius:50%;border:2px solid var(--brass);
  opacity:.5;animation:pulse 1.6s ease-out infinite}
.stage.waiting .dot{border-color:#b4432f;color:#b4432f}
@keyframes pulse{from{transform:scale(.85);opacity:.6}to{transform:scale(1.25);opacity:0}}
@media (prefers-reduced-motion:reduce){.stage.working .dot::after{animation:none}}
.stage b{font-size:.84rem;line-height:1.2}.stage.working b{color:var(--brass)}.stage.waiting b{color:#b4432f}
.stage small{font-size:.74rem;color:var(--ink-3);line-height:1.3}
.stage .ev{font-family:ui-monospace,Menlo,monospace;font-size:.68rem;color:var(--ink-3);word-break:break-all}
.stage.skipped{opacity:.4}.stage.todo .dot{opacity:.75}
.next{border-top:1px solid var(--rule-2);padding-top:12px;display:grid;gap:8px}
.columns{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}
.col h3{font-size:.78rem;letter-spacing:.06em;text-transform:uppercase;color:var(--ink-3);margin:0 0 8px;
  padding-bottom:6px;border-bottom:2px solid var(--rule)}
.col.done h3{border-color:var(--teal)}.col.working h3{border-color:var(--brass)}.col.waiting h3{border-color:#b4432f}
.slice{border:1px solid var(--rule);border-radius:8px;padding:8px 10px;margin-bottom:8px;display:grid;gap:3px;
  background:var(--paper)}
.slice b{font-size:.86rem}.slice .fw{font-size:.72rem;color:var(--ink-3);font-family:ui-monospace,Menlo,monospace}
.slice .why{font-size:.78rem;color:var(--ink-2)}
.slice.waiting{border-color:#b4432f}.slice.working{border-color:var(--brass)}.slice.done{border-color:var(--teal-soft)}
.mocks{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px}
.mock{display:grid;gap:4px;text-decoration:none;color:inherit;border:1px solid var(--rule);border-radius:8px;
  padding:8px;background:var(--paper)}
.mock:hover{border-color:var(--teal)}
.mocks .board{grid-column:1 / -1;max-width:720px}.mocks .board iframe{aspect-ratio:16/9}
.mock iframe{width:100%;aspect-ratio:4/3;border:0;border-radius:4px;background:#fff;pointer-events:none;
  transform-origin:0 0}
.mock b{font-size:.84rem}.mock .fw{font-size:.72rem;color:var(--ink-3);font-family:ui-monospace,Menlo,monospace}
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
@media (max-width:900px){.passage{grid-template-columns:repeat(4,minmax(0,1fr));row-gap:18px}
  .passage::before{display:none}.columns{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media (max-width:520px){.columns{grid-template-columns:1fr}.passage{grid-template-columns:repeat(2,minmax(0,1fr))}}
"""

SCRIPT = BOARD_SCRIPT + """
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
  };
  const poll = async () => {
    let found;
    try { found = await (await fetch('/voyage.json')).json(); } catch (fault) { return; }
    paint(found);
    if (found.moving) setTimeout(poll, 2500);
  };
  setTimeout(poll, 2500);
  document.addEventListener('click', event => {
    if (event.target.id === 'cast-off') { event.target.disabled = true; send('/cast-off', {}); }
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
})();
"""


def stage_html(stage: Stage, index: int) -> str:
    """One stage of the strip. A stage waiting on a person is a link to the thing that is waiting: the
    inbox for the fleet's stages, the receipt for the board's own child."""
    dot = DOTS.get(stage.state, "") or str(index + 1)
    title = esc(stage.title)
    if stage.state == "waiting":
        where = "#waiting" if stage.key in ("slices", "accepted") else "#fitting"
        title = f'<a href="{where}">{title}</a>'
    return (f'<div class="stage {esc(stage.state)}" data-stage="{esc(stage.key)}" role="listitem">'
            f'<div class="dot">{esc(dot)}</div><b>{title}</b><small>{esc(stage.detail)}</small>'
            f'<span class="ev">{esc(stage.evidence)}</span></div>')


def stage_payload(found: list[Stage]) -> list[dict[str, str]]:
    """What the poll repaints: the stage, its state, its dot and its words."""
    return [{"key": one.key, "state": one.state, "detail": one.detail,
             "dot": DOTS.get(one.state, "") or str(index + 1)} for index, one in enumerate(found)]


def passage_card(name: str, found: list[Stage], launchable: bool, model_next: bool, castable: bool = False) -> str:
    strip = "".join(stage_html(one, index) for index, one in enumerate(found))
    said = now_said(found)
    # On the event profile the step after the specification is a conversation, not a button: the chart is
    # drawn from the model, so there is nothing to launch until somebody has modelled.
    # A fleet that is not running after the split is the one silence the tree cannot explain — a launch
    # whose captains never lit, a machine restarted — so the button to cast off again is here, and said.
    button = ('<span class="chip">Model it next: the event-modeling skill, in the agent, with a person</span>'
              if model_next else
              f'<button class="go" id="launch"{"" if launchable else " hidden"}>Continue the build</button>'
              f'<button class="go" id="cast-off"{"" if castable else " hidden"}>Cast off the fleet</button>')
    return (f'<div class="card" id="passage"><h2>{esc(name)}</h2>'
            f'<div class="passage" role="list">{strip}</div>'
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
    fairway = f'<span class="fw">{esc(row["fairway"])} · {esc(row["clearance"])}</span>' if row.get("fairway") else \
        f'<span class="fw">{esc(row["clearance"])}</span>'
    name = f'{row["slice"]} · {row["title"]}' if row.get("title") else row["slice"]
    return (f'<div class="slice {esc(row["state"])}"><b>{esc(name)}</b>{fairway}'
            f'<span class="why">{esc(row.get("why", ""))}</span></div>')


def mockups_card(found: list[dict[str, str]]) -> str:
    """The storyboard the mock-up stage wrote, where it wrote one — every mock-up is reached from it, which
    is what it is for — else the wireframes themselves, shown small. Nothing where the stage has not run."""
    if not found:
        return ""
    boards = [row for row in found if row["name"] == "storyboard.html"]
    if boards:
        tiles = "".join(
            f'<a class="mock board" href="{esc(row["href"])}" target="_blank" rel="noopener">'
            f'<iframe src="{esc(row["href"])}" loading="lazy" tabindex="-1" title="{esc(row["title"])}"></iframe>'
            f'<b>{esc(row["title"])}</b><span class="fw">{esc(row["feature"])} · '
            f'{sum(1 for one in found if one["feature"] == row["feature"]) - 1} mock-ups, from the storyboard'
            "</span></a>"
            for row in boards)
        return f'<div class="card"><h2>Storyboard</h2><div class="mocks">{tiles}</div></div>'
    tiles = "".join(
        f'<a class="mock" href="{esc(row["href"])}" target="_blank" rel="noopener">'
        f'<iframe src="{esc(row["href"])}" loading="lazy" tabindex="-1" title="{esc(row["title"])}"></iframe>'
        f'<b>{esc(row["title"])}</b><span class="fw">{esc(row["feature"])} · {esc(row["name"])}</span></a>'
        for row in found)
    return f'<div class="card"><h2>Mockups · {len(found)}</h2><div class="mocks">{tiles}</div></div>'


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
         config: dict | None = None, mocks: list[dict[str, str]] | None = None, castable: bool = False) -> str:
    now = current(found)
    sub = (f"now: {now.title.lower()}" if now else "complete") + (f" · {live_sub(fleet)}" if fleet else "")
    model_next = now is not None and now.key == "model" and now.state == "todo"
    landed = fitting_card(made) if made else ""
    # The live cards, with their controls, under the model: how the work is going belongs on the page that
    # says what the work is.
    live = live_cards(fleet, config or {}, True) if fleet else ""
    body = (f"<style>{STYLE}</style>{passage_card(root.resolve().name, found, launchable, model_next, castable)}"
            f"{landed}"
            f"{model_card(xml, note, viewer_fault)}{mockups_card(mocks or [])}{work_card(rows, fault)}{live}")
    script = SCRIPT + ("" if viewer_fault or not xml else "\n")
    page_html = document("Voyage", sub, body, script, now="/voyage")
    if xml and not viewer_fault:
        page_html = page_html.replace(
            "</body>", f'<script src="/drawio-viewer.js"></script><script>{MODEL_SCRIPT}</script></body>', 1)
    return page_html


def now_said(found: list[Stage]) -> str:
    """The one sentence about where the project is and what moves it, as the strip, the poll and the
    landing all say it."""
    now = current(found)
    return (f"Now: {now.title.lower()} — {now.detail}. Next: {now.next}." if now
            else "Every stage is done: the voyage is complete.")


def payload(found: list[Stage], launchable: bool, moving: bool, castable: bool = False) -> str:
    return json.dumps({"stages": stage_payload(found), "launchable": launchable, "moving": moving,
                       "castable": castable, "now": now_said(found)})

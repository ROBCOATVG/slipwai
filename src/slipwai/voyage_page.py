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
from .bridge_page import fitting_card
from .page_shell import document, esc
from .passage import Stage, current
from .voyage import COLUMNS, viewer_config

TITLES = {"todo": "To do", "working": "Working", "waiting": "Waiting on you", "done": "Done"}
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
.viewer{border:1px solid var(--rule);border-radius:8px;overflow:hidden;background:#fff}
.viewer .bar{display:flex;gap:8px;align-items:center;padding:6px 10px;border-bottom:1px solid #e3e3e3;
  background:#f7f7f7;color:#555;font-size:.78rem}
.viewer .mxgraph{min-height:240px}
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
  };
  const poll = async () => {
    let found;
    try { found = await (await fetch('/voyage.json')).json(); } catch (fault) { return; }
    paint(found);
    if (found.moving) setTimeout(poll, 2500);
  };
  setTimeout(poll, 2500);
})();
"""


def stage_html(stage: Stage, index: int) -> str:
    dot = DOTS.get(stage.state, "") or str(index + 1)
    return (f'<div class="stage {esc(stage.state)}" data-stage="{esc(stage.key)}" role="listitem">'
            f'<div class="dot">{esc(dot)}</div><b>{esc(stage.title)}</b><small>{esc(stage.detail)}</small>'
            f'<span class="ev">{esc(stage.evidence)}</span></div>')


def stage_payload(found: list[Stage]) -> list[dict[str, str]]:
    """What the poll repaints: the stage, its state, its dot and its words."""
    return [{"key": one.key, "state": one.state, "detail": one.detail,
             "dot": DOTS.get(one.state, "") or str(index + 1)} for index, one in enumerate(found)]


def passage_card(name: str, found: list[Stage], launchable: bool, model_next: bool) -> str:
    now = current(found)
    strip = "".join(stage_html(one, index) for index, one in enumerate(found))
    said = (f"Now: {now.title.lower()} — {now.detail}. Next: {now.next}." if now
            else "Every stage is done: the voyage is complete.")
    # On the event profile the step after the specification is a conversation, not a button: the chart is
    # drawn from the model, so there is nothing to launch until somebody has modelled.
    button = ('<span class="chip">Model it next: the event-modeling skill, in the agent, with a person</span>'
              if model_next else
              f'<button class="go" id="launch"{"" if launchable else " hidden"}>Continue the build</button>')
    return (f'<div class="card" id="passage"><h2>{esc(name)}</h2>'
            f'<div class="passage" role="list">{strip}</div>'
            f'<div class="next"><p id="now">{esc(said)}</p><div class="ask">{button}</div></div></div>')


def model_card(xml: str, note: str, viewer_fault: str) -> str:
    if not xml:
        return f'<div class="card"><h2>The model</h2><p class="empty">{esc(note)}</p></div>'
    bar = ('<div class="bar"><b>model.drawio</b><span>· read-only · each slice\'s caption is stroked by where it '
           "stands</span></div>")
    # The viewer replaces the div's contents once its script has loaded; until then, and on a machine the
    # script never reaches, the words inside it are what a person sees.
    body = (f'<p class="empty">{esc(viewer_fault)}</p>' if viewer_fault else
            f'<div class="mxgraph" data-mxgraph="{esc(viewer_config(xml))}"><p class="empty">Drawing the model with '
            f"draw.io's viewer — fetched once from viewer.diagrams.net the first time, kept after. Where that never "
            f'arrives, docs/event-model/model.drawio opens in draw.io.</p></div>')
    warn = f'<p class="empty">{esc(note)}</p>' if note else ""
    return f'<div class="card"><h2>The model</h2>{warn}<div class="viewer">{bar}{body}</div></div>'


def slice_html(row: dict[str, str]) -> str:
    fairway = f'<span class="fw">{esc(row["fairway"])} · {esc(row["clearance"])}</span>' if row.get("fairway") else \
        f'<span class="fw">{esc(row["clearance"])}</span>'
    return (f'<div class="slice {esc(row["state"])}"><b>{esc(row["slice"])}</b>{fairway}'
            f'<span class="why">{esc(row.get("why", ""))}</span></div>')


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
         viewer_fault: str, made: dict | None, launchable: bool) -> str:
    now = current(found)
    sub = f"now: {now.title.lower()}" if now else "complete"
    model_next = now is not None and now.key == "model" and now.state == "todo"
    landed = fitting_card(made) if made else ""
    body = (f"<style>{STYLE}</style>{passage_card(root.name, found, launchable, model_next)}{landed}"
            f"{model_card(xml, note, viewer_fault)}{work_card(rows, fault)}")
    script = SCRIPT + ("" if viewer_fault or not xml else "\n")
    page_html = document("Voyage", sub, body, script, now="/voyage")
    if xml and not viewer_fault:
        page_html = page_html.replace("</body>", '<script src="/drawio-viewer.js"></script></body>', 1)
    return page_html


def payload(found: list[Stage], launchable: bool, moving: bool) -> str:
    now = current(found)
    return json.dumps({"stages": stage_payload(found), "launchable": launchable, "moving": moving,
                       "now": (f"Now: {now.title.lower()} — {now.detail}. Next: {now.next}." if now
                               else "Every stage is done: the voyage is complete.")})

"""The timeline card on the Fleet tab: the voyage as a track, drawn at the scale a person picks.

`timeline.py` folds the logs into lanes of spans and a list of marks; this draws them. The bars are
percentages of the whole voyage, so the dropdown changes only how wide the track is drawn, and the names
column stays put while the track scrolls. The published copy draws the whole voyage with nothing to press.
"""
from __future__ import annotations

from datetime import UTC, timedelta

from .fleet_record import clock_of
from .page_shell import esc
from .timeline import instant

STYLE = """
.tl-head{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}
.tl-head h2{margin:0}
.tl-head label{font-size:.85rem;color:var(--ink-2);display:flex;align-items:center;gap:8px}
.tl-head select{font:inherit;padding:5px 8px;border:1px solid var(--rule);border-radius:7px;background:var(--paper);
  color:var(--ink)}
.tl{display:flex;margin-top:10px}
.tl-names{width:130px;flex:none}
.tl-names .spacer{height:22px;border-bottom:1px solid var(--rule)}
.tl-names .lname{height:30px;line-height:30px;font-size:.8rem;color:var(--ink-2);text-align:right;padding-right:8px;
  border-bottom:1px solid var(--rule-2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tl-scroll{flex:1;min-width:0;overflow-x:auto;overflow-y:hidden}
.tl-track{position:relative;min-width:100%}
.tl-axis{position:relative;height:22px;border-bottom:1px solid var(--rule)}
.tl-tick{position:absolute;top:0;transform:translateX(-50%);font-size:.72rem;color:var(--ink-3);
  font-family:var(--mono);white-space:nowrap}
.tl-rows{position:relative}
.tl-lane{position:relative;height:30px;border-bottom:1px solid var(--rule-2)}
.tl-bar{position:absolute;top:7px;height:16px;border-radius:3px;min-width:2px}
.tl-bar.run{background:var(--teal)}
.tl-bar.park{background:var(--brass);height:6px;top:12px}
.tl-bar.pause{background:#d6e6f8;border:1px dashed #1d4f8f;box-sizing:border-box}
:root:has(#t-dark:checked) .tl-bar.pause{background:#1b2f4a}
@media (prefers-color-scheme:dark){:root:has(#t-auto:checked) .tl-bar.pause{background:#1b2f4a}}
.tl-lbl{position:absolute;font-size:.7rem;white-space:nowrap;font-family:var(--mono);pointer-events:none}
.tl-lbl.in{top:9px;color:#fff;padding-left:4px;overflow:hidden;max-width:100%}
.tl-lbl.pause{color:#1d4f8f}
.dense .tl-lbl.in{display:none}
.tl-grid{position:absolute;top:0;bottom:0;width:1px;background:var(--rule-2)}
.tl-future{position:absolute;top:0;bottom:0;background:rgba(23,33,41,.05)}
.tl-mark{position:absolute;top:0;bottom:0;width:2px}
.tl-mark.limit{background:var(--critical)}.tl-mark.now{background:var(--ink)}
.tl-mark.reset{background:#1d4f8f;opacity:.8}.tl-mark.person{width:0;top:-8px;bottom:auto;color:var(--brass)}
.tl-mark .tl-lbl{top:-18px;left:4px}
.tl-mark.limit .tl-lbl{color:var(--critical)}.tl-mark.reset .tl-lbl{color:#1d4f8f}.tl-mark.now .tl-lbl{color:var(--ink)}
.tl-legend{display:flex;gap:16px;flex-wrap:wrap;margin-top:8px;font-size:.8rem;color:var(--ink-2)}
.tl-legend span{display:inline-flex;align-items:center;gap:6px}
.tl-legend i{width:12px;height:12px;border-radius:3px;display:inline-block}
"""

SCRIPT = """
// The timeline: the bars are positions in the whole voyage, so the scale is only how wide it is drawn.
// The names stay put; the track scrolls; the ticks are redrawn for the hours across the window.
const track = document.querySelector('.tl-track');
const scale = document.getElementById('tl-scale');
if (track && scale) {
  const from = Date.parse(track.dataset.from), to = Date.parse(track.dataset.to);
  const axis = track.querySelector('.tl-axis');
  const rows = track.querySelector('.tl-rows');
  const KEY = 'slipwai-timeline-scale';
  const draw = () => {
    const span = Math.max(1, (to - from) / 3.6e6);
    const hours = scale.value === 'all' ? span : Number(scale.value);
    track.style.width = Math.max(100, span / hours * 100) + '%';
    track.classList.toggle('dense', hours >= 24);
    const step = hours <= 8 ? 1 : hours <= 24 ? 2 : 4;
    axis.textContent = '';
    rows.querySelectorAll('.tl-grid').forEach(one => one.remove());
    const start = new Date(from); start.setMinutes(0, 0, 0);
    for (let at = start.getTime(); at <= to; at += 3.6e6) {
      const when = new Date(at);
      if (when.getHours() % step) continue;
      const left = (at - from) / (to - from) * 100;
      if (left < 0) continue;
      const label = when.getHours() === 0
        ? when.toLocaleDateString(undefined, {day: 'numeric', month: 'short'}) + ' 00:00'
        : String(when.getHours()).padStart(2, '0') + ':00';
      const tick = document.createElement('span');
      tick.className = 'tl-tick'; tick.style.left = left + '%'; tick.textContent = label;
      axis.appendChild(tick);
      const grid = document.createElement('div');
      grid.className = 'tl-grid'; grid.style.left = left + '%';
      rows.prepend(grid);
    }
    const mark = track.querySelector('.tl-mark.now');
    const scroller = track.parentElement;
    if (mark && scroller) scroller.scrollLeft = Math.max(0, mark.offsetLeft - scroller.clientWidth * 0.6);
  };
  try { const held = localStorage.getItem(KEY); if (held) scale.value = held; } catch (fault) { /* no storage */ }
  scale.addEventListener('change', () => {
    try { localStorage.setItem(KEY, scale.value); } catch (fault) { /* no storage */ }
    draw();
  });
  draw();
}
"""


def percent(stamp: str, begin: str, end: str) -> float:
    """Where an instant falls in the window, 0 to 100."""
    at, opened, closed = instant(stamp), instant(begin), instant(end)
    if at is None or opened is None or closed is None or closed <= opened:
        return 0.0
    return max(0.0, min(100.0, (at - opened).total_seconds() / (closed - opened).total_seconds() * 100))


def ticks(begin: str, end: str) -> str:
    """Hour ticks across the whole window, thinned as the window grows; the page redraws them per scale."""
    opened, closed = instant(begin), instant(end)
    if opened is None or closed is None or closed <= opened:
        return ""
    hours = (closed - opened).total_seconds() / 3600
    step = 1 if hours <= 8 else 2 if hours <= 24 else 4
    found = []
    at = opened.astimezone().replace(minute=0, second=0, microsecond=0)
    while at <= closed.astimezone():
        if at.hour % step == 0 and at >= opened.astimezone():
            label = at.strftime("%-d %b 00:00") if at.hour == 0 else at.strftime("%H:00")
            left = percent(at.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), begin, end)
            found.append(f'<span class="tl-tick" style="left:{left:.3f}%">{esc(label)}</span>')
        at = at.replace(hour=(at.hour + 1) % 24) if at.hour < 23 else (at + timedelta(hours=1))
    return "".join(found)


def timeline_card(found: dict, controls: bool) -> str:
    """The voyage as a track: one lane per slot per stream, the parks on a person under them, and the marks.

    The bars are percentages of the whole voyage, so the only thing the scale changes is the width of the
    track. The published copy draws it at the whole voyage; the served page adds the dropdown.
    """
    data = found.get("timeline") or {}
    lanes = data.get("lanes") or []
    if not lanes:
        return ""
    begin, end, at_now = str(data.get("from", "")), str(data.get("to", "")), str(data.get("now", ""))
    names = "".join(f'<div class="lname" title="{esc(lane["name"])}">{esc(lane["name"])}</div>' for lane in lanes)
    rows = f'<div class="tl-future" style="left:{percent(at_now, begin, end):.3f}%;right:0"></div>'
    for lane in lanes:
        bars = ""
        for span in lane["spans"]:
            left, right = percent(span["from"], begin, end), percent(span["to"], begin, end)
            width = max(0.05, right - left)
            kind = span["kind"]
            if kind == "run":
                title = f"{span['slice']} {span['from'][11:16]}–{span['to'][11:16]}"
                label = f'<span class="tl-lbl in">{esc(span["slice"])}</span>'
            elif kind == "pause":
                lifts = clock_of(str(span.get("until") or "")) or span["to"][11:16]
                title = f"{span['slice'] or lane['fairway']} paused until {lifts}: {span.get('why', '')}"
                label = f'<span class="tl-lbl in pause">paused · lifts {esc(lifts)}</span>'
            else:
                title = f"{span['slice'] or lane['fairway']} parked ({span.get('cause')}): {span.get('why', '')}"
                label = ""
            bars += (f'<div class="tl-bar {esc(kind)}" style="left:{left:.3f}%;width:{width:.3f}%" '
                     f'title="{esc(title)}">{label}</div>')
        rows += f'<div class="tl-lane">{bars}</div>'
    for mark in data.get("marks") or []:
        left = percent(mark["t"], begin, end)
        label = mark["label"] + (" " + (clock_of(mark["t"]) or "") if mark["kind"] != "person" else "")
        rows += (f'<div class="tl-mark {esc(mark["kind"])}" style="left:{left:.3f}%">'
                 f'<span class="tl-lbl">{"▲" if mark["kind"] == "person" else esc(label)}</span></div>')
    chooser = ('<label>Scale <select id="tl-scale" aria-label="Hours across the window">'
               '<option value="4">4 hours across</option><option value="8" selected>8 hours across</option>'
               '<option value="24">24 hours across</option><option value="all">The whole voyage</option>'
               '</select></label>') if controls else ""
    legend = ('<div class="tl-legend"><span><i style="background:var(--teal)"></i>a session working</span>'
              '<span><i style="background:var(--brass)"></i>parked on you</span>'
              '<span><i style="background:#d6e6f8;border:1px dashed #1d4f8f"></i>paused, with a time</span>'
              '<span><i style="background:var(--critical)"></i>the harness refused the run</span>'
              '<span style="color:var(--brass)">▲ you cleared a park</span></div>')
    return (f'<div class="card" id="timeline"><div class="tl-head"><h2>Timeline</h2>{chooser}</div>'
            f'<p class="empty" style="margin:6px 0 0">From the first line to now, one bar per session in its slot. '
            f"Scroll sideways; the names stay put.</p>"
            f'<div class="tl"><div class="tl-names"><div class="spacer"></div>{names}</div>'
            f'<div class="tl-scroll"><div class="tl-track" data-from="{esc(begin)}" data-to="{esc(end)}">'
            f'<div class="tl-axis">{ticks(begin, end)}</div><div class="tl-rows">{rows}</div></div></div></div>'
            f"{legend}</div>")

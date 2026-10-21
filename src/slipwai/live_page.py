"""What the slices are doing now, drawn: the Now strip on the Voyage tab and a window per slice.

`activity.py` folds each slice's activity log; this draws it. The strip is one row per working slice — its
stage, who is on it, the last thing it said, how long it has been quiet, and a warning where a person would
step in — and the window is one slice at length: a lane per sub-agent over the last hour, the feed in plain
words, and what the slice has cost so far in time.

Both repaint themselves from the board, the strip from `/now.json` and the window from `/slice.json`, with
the HTML drawn here and swapped whole: a page that redrew from data would be a second renderer to keep in
step with this one.
"""
from __future__ import annotations

import html
import json
from pathlib import Path
from urllib.parse import quote

from .activity import fold, lines_of, minutes, now_stamp, stamp, task_of
from .page_shell import document, esc

#: How much of the past a window's lanes span.
SPAN = 60 * 60

STYLE = """
#now .rows{display:grid;grid-template-columns:70px minmax(120px,.8fr) minmax(200px,1.4fr) minmax(180px,1.2fr) 80px;
  font-size:.86rem;overflow-x:auto}
#now .rows>div{padding:8px 10px;border-top:1px solid var(--rule-2);display:flex;flex-direction:column;gap:2px;
  min-width:0}
#now .rows>.h{font-size:.7rem;letter-spacing:.06em;text-transform:uppercase;color:var(--ink-3);border-top:0;
  padding-top:0}
#now .sid{font-family:var(--mono);font-weight:500}
#now .sub,.lane-name .sub{color:var(--ink-3);font-size:.78rem}
.role{font-family:var(--mono);font-size:.72rem;padding:1px 6px;border-radius:4px;background:var(--brass-soft);
  color:var(--brass);width:fit-content}
.role.main{background:var(--teal-soft);color:var(--teal)}
.warn{display:inline-block;font-size:.72rem;padding:1px 8px;border-radius:999px;width:fit-content;margin-top:2px}
.warn.amber{background:var(--brass-soft);color:var(--brass)}
.warn.red{background:transparent;border:1px solid #b4432f;color:#b4432f}
.ago{font-family:var(--mono);font-size:.78rem;color:var(--ink-3);font-variant-numeric:tabular-nums}
.live-dot{display:inline-flex;align-items:center;gap:6px;font-size:.72rem;font-weight:500;color:var(--teal)}
.live-dot::before{content:"";width:7px;height:7px;border-radius:50%;background:var(--teal);
  animation:blink 1.6s ease-in-out infinite}
@keyframes blink{50%{opacity:.25}}
@media (prefers-reduced-motion:reduce){.live-dot::before{animation:none}}
.slice .live-cap{font-size:.78rem;color:var(--ink-2);border-left:2px solid var(--teal);padding-left:7px}
@media (max-width:760px){#now .rows{grid-template-columns:60px 1fr;}#now .rows>.h:nth-child(n+3),
  #now .rows>.said,#now .rows>.quiet{display:none}}
"""

WINDOW_STYLE = """
.lanes{display:grid;grid-template-columns:170px minmax(0,1fr);gap:6px 10px;font-size:.78rem}
.lane-name{display:flex;flex-direction:column;justify-content:center;min-width:0}
.lane-name b{font-weight:500;font-size:.8rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.track{position:relative;height:28px;border-radius:4px;background:repeating-linear-gradient(90deg,transparent 0,
  transparent calc(10% - 1px),var(--rule-2) calc(10% - 1px),var(--rule-2) 10%)}
.seg{position:absolute;top:4px;bottom:4px;border-radius:4px;background:var(--teal-soft);color:var(--ink);
  font-size:.7rem;display:flex;align-items:center;padding:0 6px;white-space:nowrap;overflow:hidden;min-width:3px}
.seg.sub{background:var(--brass-soft)}
.seg.open{box-shadow:inset -3px 0 0 var(--teal)}
.axis{display:flex;justify-content:space-between;font-family:var(--mono);font-size:.68rem;color:var(--ink-3)}
.feed{font-family:var(--mono);font-size:.78rem;list-style:none;margin:0;padding:0;display:grid;gap:3px;
  max-height:520px;overflow:auto}
.feed li{display:grid;grid-template-columns:62px 64px minmax(0,1fr);gap:8px}
.feed .t{color:var(--ink-3)}.feed .k{color:var(--brass)}.feed .k.said{color:var(--teal)}
.feed .k.failed{color:#b4432f}.feed .k.stage{color:var(--ink);font-weight:500}
.two{display:grid;grid-template-columns:minmax(0,1.4fr) minmax(0,1fr);gap:16px;align-items:start}
@media (max-width:860px){.two{grid-template-columns:1fr}}
.facts-list{margin:0;padding-left:18px;display:grid;gap:6px;font-size:.88rem}
"""

STRIP_SCRIPT = """
// The Now strip: repainted from /now.json every few seconds, swapped whole when what it says has changed.
(function(){
  if (!document.getElementById('now')) return;
  const poll = async () => {
    let found;
    try { found = await (await fetch('/now.json')).json(); } catch (fault) { setTimeout(poll, 8000); return; }
    const card = document.getElementById('now');
    if (card && card.dataset.said !== found.said) card.outerHTML = found.html;
    setTimeout(poll, 4000);
  };
  setTimeout(poll, 4000);
})();
"""

WINDOW_SCRIPT = """
(function(){
  const where = new URLSearchParams(location.search);
  const poll = async () => {
    let found;
    try { found = await (await fetch('/slice.json?fairway=' + encodeURIComponent(where.get('fairway') || '') +
                                      '&slice=' + encodeURIComponent(where.get('slice') || ''))).json(); }
    catch (fault) { setTimeout(poll, 8000); return; }
    const body = document.getElementById('slice-live');
    if (body && body.dataset.said !== found.said) body.outerHTML = found.html;
    setTimeout(poll, 3000);
  };
  setTimeout(poll, 3000);
})();
"""


def window_address(fairway: str, slice_id: str) -> str:
    return f"/slice?fairway={quote(fairway, safe='')}&slice={quote(slice_id, safe='')}"


def who_html(found: dict) -> str:
    current = found["current"]
    if found["waiting"]:
        return (f'<span class="role main">session</span><span>waiting on {esc(found["waiting"])}</span>')
    if current:
        took = minutes(now_stamp() - current["started"])
        model = f" · {current['model']}" if current["model"] else ""
        role = current["role"].removeprefix("sail-").removesuffix("-shipwright") or "sub-agent"
        words = " ".join(part for part in (current["task"], current["what"]) if part)
        return (f'<span class="role">{esc(role)}</span><span class="sub">{esc(model.lstrip(" ·"))}'
                f'{" · " if model else ""}{esc(took)}</span><span>{esc(words)}</span>')
    return f'<span class="role main">session</span><span>{esc(found["last"])}</span>'


def strip_html(rows: list[dict[str, str]], folds: dict[str, dict]) -> str:
    """The Now strip: every working slice, the one a person should look at first at the top."""
    working = [row for row in rows if row.get("state") == "working"]
    if not working:
        return ""

    def order(row: dict[str, str]) -> tuple:
        found = folds.get(f"{row.get('fairway')}/{row['slice']}")
        warned = bool(found and found["warnings"])
        return (not warned, -(found["quiet"] if found else 0))

    cells = ""
    for row in sorted(working, key=order):
        found = folds.get(f"{row.get('fairway')}/{row['slice']}")
        link = (f'<a class="sid" href="{esc(window_address(row.get("fairway", ""), row["slice"]))}" '
                f'target="_blank" rel="noopener">{esc(row["slice"])}</a>')
        stage = row.get("chip") or row.get("stage") or ""
        if found is None:
            cells += (f'<div>{link}</div><div><span>{esc(stage)}</span></div>'
                      '<div><span class="sub">no activity log yet: its session predates it, or its harness '
                      'writes none</span></div><div class="said"></div><div class="quiet"></div>')
            continue
        warnings = "".join(f'<span class="warn {esc(one["level"])}">{esc(one["said"])}</span>'
                           for one in found["warnings"])
        said = f"“{found['said']}”" if found["said"] else ""
        cells += (f'<div>{link}</div><div><span>{esc(stage)}</span></div>'
                  f'<div>{who_html(found)}{warnings}</div>'
                  f'<div class="said"><span>{esc(said)}</span></div>'
                  f'<div class="quiet"><span class="ago">{esc(minutes(found["quiet"]))}</span></div>')
    said = json.dumps([[row["slice"], row.get("chip")] for row in working]
                      + [[key, one["last_t"], one["said"], [w["said"] for w in one["warnings"]],
                          one["current"]["agent"] if one["current"] else ""] for key, one in sorted(folds.items())])
    head = ('<div class="h">Slice</div><div class="h">Stage</div><div class="h">Who is on it</div>'
            '<div class="h">Last thing it said</div><div class="h">Quiet for</div>')
    return (f'<div class="card" id="now" data-said="{esc(said)}"><h2>Now <span class="live-dot">'
            f'live · {len(working)} working</span></h2><div class="rows">{head}{cells}</div></div>')


def lanes_html(found: dict, lines: list[dict], now: float) -> str:
    """A lane for the session and one per sub-agent, over the last hour."""
    start = now - SPAN

    def segment(began: float, ended: float, label: str, kind: str, open_: bool) -> str:
        left = max(0.0, (began - start) / SPAN * 100)
        right = min(100.0, ((ended or now) - start) / SPAN * 100)
        if right <= 0 or right <= left:
            return ""
        return (f'<div class="seg {kind}{" open" if open_ else ""}" style="left:{left:.2f}%;'
                f'width:{max(right - left, 0.4):.2f}%" title="{esc(label)}">{esc(label)}</div>')

    session_marks = "".join(
        segment(stamp_of(one) - 20, stamp_of(one) + 20, "", "", False)
        for one in lines if one.get("agent") in (None, "", "session") and stamp_of(one) > start)
    rows = (f'<div class="lane-name"><b>Session</b><span class="sub">the slice’s own</span></div>'
            f'<div class="track">{session_marks}</div>')
    for agent in found["agents"]:
        if (agent["ended"] or now) < start:
            continue
        name = agent["task"] or agent["role"]
        rows += (f'<div class="lane-name"><b>{esc(name)}</b><span class="sub">'
                 f'{esc(agent["role"].removeprefix("sail-"))}{" · " + esc(agent["model"]) if agent["model"] else ""}'
                 f'</span></div><div class="track">'
                 f'{segment(agent["started"], agent["ended"], agent["what"], "sub", not agent["ended"])}</div>')
    ticks = "".join(f"<span>{minutes(SPAN - step * SPAN / 6)} ago</span>" for step in range(6)) + "<span>now</span>"
    return f'<div class="lanes"><div></div><div class="axis">{ticks}</div>{rows}</div>'


def stamp_of(one: dict) -> float:
    return stamp(str(one.get("t", "")))


def feed_html(lines: list[dict], slice_id: str) -> str:
    shown = [one for one in lines if one["kind"] in ("said", "start", "done", "ran", "failed", "wait", "stage")][-120:]
    items = ""
    for one in reversed(shown):
        what = str(one.get("what", ""))
        if one["kind"] in ("start", "done"):
            task, words = task_of(what, slice_id)
            who = str(one.get("role", "")).removeprefix("sail-")
            what = " ".join(part for part in (who, task, words) if part)
            if one["kind"] == "done" and one.get("commit"):
                what += f" · commit {one['commit']}"
        items += (f'<li><span class="t">{esc(str(one["t"])[11:19])}</span>'
                  f'<span class="k {esc(one["kind"])}">{esc(one["kind"])}</span><span>{esc(what)}</span></li>')
    return f'<ul class="feed">{items}</ul>' if items else '<p class="empty">Nothing in its activity log yet.</p>'


def summary_html(found: dict) -> str:
    agents = found["agents"]
    done = [one for one in agents if one["ended"]]
    facts = [f"<b>Sub-agents:</b> {len(agents)} seen, {len(done)} done, {len(found['running'])} running"
             + (f"; a finished one took {minutes(found['usual'])} at the median" if done else "")]
    commits = [one["commit"] for one in done if one["commit"]]
    if commits:
        facts.append(f"<b>Commits handed back:</b> {len(commits)}, the newest {esc(commits[-1])}")
    if found["said"]:
        facts.append(f"<b>Last said:</b> {esc(found['said'])}")
    facts.append(f"<b>Quiet for:</b> {esc(minutes(found['quiet']))}")
    facts += [f'<span class="warn {esc(one["level"])}">{esc(one["said"])}</span>' for one in found["warnings"]]
    return '<ul class="facts-list">' + "".join(f"<li>{one}</li>" for one in facts) + "</ul>"


def window_body(root: Path, fairway: str, slice_id: str) -> str:
    lines = lines_of(root, fairway, slice_id)
    now = now_stamp()
    found = fold(lines, slice_id, now)
    said = json.dumps([found["last_t"], len(lines), [w["said"] for w in found["warnings"]]])
    if not lines:
        inner = ('<p class="empty">No activity log for this slice yet. One is written by the hooks of a session '
                 "the captain started after the project's slipwai was upgraded.</p>")
    else:
        inner = (f'<div class="card"><h2>Who did what, the last hour</h2>{lanes_html(found, lines, now)}</div>'
                 f'<div class="two"><div class="card"><h2>Feed</h2>{feed_html(lines, slice_id)}</div>'
                 f'<div class="card"><h2>So far</h2>{summary_html(found)}</div></div>')
    return f'<div id="slice-live" data-said="{esc(said)}">{inner}</div>'


def window(root: Path, fairway: str, slice_id: str) -> str:
    body = f"<style>{STYLE}{WINDOW_STYLE}</style>{window_body(root, fairway, slice_id)}"
    return document(f"{slice_id} · {root.resolve().name}", f"live · {fairway}", body, WINDOW_SCRIPT, now="/voyage")


def said_in(drawn: str) -> str:
    """The `data-said` a drawn card carries, as the poll compares it."""
    if 'data-said="' not in drawn:
        return ""
    return html.unescape(drawn.split('data-said="', 1)[1].split('"', 1)[0])


def window_payload(root: Path, fairway: str, slice_id: str) -> str:
    drawn = window_body(root, fairway, slice_id)
    return json.dumps({"said": said_in(drawn), "html": drawn})


def strip_payload(rows: list[dict[str, str]], folds: dict[str, dict]) -> str:
    drawn = strip_html(rows, folds)
    return json.dumps({"said": said_in(drawn), "html": drawn})

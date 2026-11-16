"""What the slices are doing now, drawn: the Needs a look strip on the Voyage tab and a window per slice.

`activity.py` folds each slice's activity log; this draws it. The strip was a row per working slice, and a
slice's card says where it is and what it is doing now, so the strip says only what is wrong: a slice stuck
on one task, going in circles or gone quiet, a merge the harbour refused, and a red trunk — one line when
nothing is. The window is one slice at length: a lane per sub-agent over the last hour, the feed in plain
words, and what the slice has cost so far in time.

Both repaint themselves from the board, the strip as a band of `/live.json` and the window from
`/slice.json`, with the HTML drawn here and swapped whole: a page that redrew from data would be a second
renderer to keep in step with this one.
"""
from __future__ import annotations

import html
import json
from pathlib import Path
from urllib.parse import quote

from .activity import fold, lines_of, minutes, now_stamp, stamp, task_of
from .example_map_page import STYLE as MAP_STYLE
from .example_map_page import map_panel
from .page_shell import document, esc

#: How much of the past a window's lanes span.
SPAN = 60 * 60

STYLE = """
#look{display:grid;gap:8px}
#look .head{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:baseline;gap:4px 12px}
#look .head h2{margin:0}#look .head span,#look small{font-size:.8rem;color:var(--ink-2)}
#look.calm{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:baseline;gap:4px 12px}
#look .look{display:flex;flex-wrap:wrap;align-items:center;gap:6px 12px;padding:8px 12px;border-radius:6px;
  border:1px solid var(--warn)}
#look .look.red{border-color:var(--critical)}#look .look.trunk{background:var(--critical-soft)}
#look .look b{flex:0 0 140px;font-size:.86rem}#look .look.trunk b{color:var(--critical)}
#look .look .says{flex:1 1 260px;font-size:.86rem}#look .look .did{flex:1 1 100%;font-size:.8rem;color:var(--ink-2)}
#look .look a{font-size:.84rem;padding:6px 12px;border-radius:6px;border:1px solid var(--teal);color:var(--teal);
  text-decoration:none;white-space:nowrap}
#look .look a:hover{background:var(--teal-soft)}
.role{font-family:var(--mono);font-size:.72rem;padding:1px 6px;border-radius:4px;background:var(--brass-soft);
  color:var(--brass);width:fit-content}
.role.main{background:var(--teal-soft);color:var(--teal)}
.warn{display:inline-block;font-size:.72rem;padding:1px 8px;border-radius:999px;width:fit-content;margin-top:2px}
.warn.amber{background:var(--brass-soft);color:var(--brass)}
.warn.red{background:transparent;border:1px solid var(--critical);color:var(--critical)}
.ago{font-family:var(--mono);font-size:.78rem;color:var(--ink-3);font-variant-numeric:tabular-nums}
.slice .live-cap{font-size:.78rem;color:var(--ink-2);border-left:2px solid var(--teal);padding-left:7px}
.lane-name .sub{color:var(--ink-3);font-size:.78rem}
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
/* A bar a few seconds wide shows one letter of its label. Hovered, it widens to say the whole thing over
   its neighbours, which is what a person reaching for it wants to read. */
.seg:hover{min-width:max-content;overflow:visible;z-index:2;box-shadow:0 1px 6px rgba(23,33,41,.3)}
.seg.open{box-shadow:inset -3px 0 0 var(--teal)}
.axis{display:flex;justify-content:space-between;font-family:var(--mono);font-size:.68rem;color:var(--ink-3)}
.feed{font-family:var(--mono);font-size:.78rem;list-style:none;margin:0;padding:0;display:grid;gap:3px;
  max-height:520px;overflow:auto}
.feed li{display:grid;grid-template-columns:62px 64px minmax(0,1fr);gap:8px}
.feed .t{color:var(--ink-3)}.feed .k{color:var(--brass)}.feed .k.said{color:var(--teal)}
.feed .k.failed{color:var(--critical)}.feed .k.stage{color:var(--ink);font-weight:500}
.two{display:grid;grid-template-columns:minmax(0,1.4fr) minmax(0,1fr);gap:16px;align-items:start}
@media (max-width:860px){.two{grid-template-columns:1fr}}
.facts-list{margin:0;padding-left:18px;display:grid;gap:6px;font-size:.88rem}
"""

WINDOW_SCRIPT = """
(function(){
  const where = new URLSearchParams(location.search);
  // The tab is kept in the address, so a reload or a link opens the one a person was on.
  const show = tab => {
    document.querySelectorAll('[data-panel]').forEach(one => { one.hidden = one.dataset.panel !== tab; });
    document.querySelectorAll('[data-tab]').forEach(one => {
      if (one.dataset.tab === tab) one.setAttribute('aria-current', 'page'); else one.removeAttribute('aria-current');
    });
  };
  show(where.get('tab') === 'map' ? 'map' : 'where');
  document.addEventListener('click', event => {
    const tab = event.target.closest('[data-tab]');
    if (tab) { event.preventDefault(); show(tab.dataset.tab); history.replaceState(null, '', tab.href); return; }
    const card = event.target.closest('button.ex');
    if (card) card.setAttribute('aria-expanded', card.getAttribute('aria-expanded') === 'true' ? 'false' : 'true');
  });
  const poll = async () => {
    let found;
    try { found = await (await fetch('/slice.json?fairway=' + encodeURIComponent(where.get('fairway') || '') +
                                      '&slice=' + encodeURIComponent(where.get('slice') || ''))).json(); }
    catch (fault) { setTimeout(poll, 8000); return; }
    const body = document.getElementById('slice-live');
    if (body && body.dataset.said !== found.said) body.outerHTML = found.html;
    // The map is swapped only when the file said something new, with the examples a person opened opened
    // again and the row of rules scrolled back to where they had it.
    const map = document.getElementById('slice-map');
    if (map && found.map_html && map.dataset.said !== found.map_said) {
      const open = [...map.querySelectorAll('button.ex[aria-expanded="true"]')].map(one => one.dataset.ex);
      const row = map.querySelector('.map-row');
      const left = row ? row.scrollLeft : 0;
      const held = document.createElement('div');
      held.innerHTML = found.map_html;
      const fresh = held.firstElementChild;
      fresh.querySelectorAll('button.ex').forEach(one => {
        if (open.includes(one.dataset.ex)) one.setAttribute('aria-expanded', 'true');
      });
      map.replaceWith(fresh);
      const again = fresh.querySelector('.map-row');
      if (again) again.scrollLeft = left;
    }
    setTimeout(poll, 3000);
  };
  setTimeout(poll, 3000);
})();
"""


def window_address(fairway: str, slice_id: str) -> str:
    return f"/slice?fairway={quote(fairway, safe='')}&slice={quote(slice_id, safe='')}"


#: The warnings `activity.fold` raises that are a person's to look at: a task taking far longer than its
#: siblings, the same failure round and round, and a session gone silent.
LOOKED = {"long": "Stuck on one task", "circles": "Going in circles", "quiet": "Gone quiet"}
#: What a slice has to be for the strip to count it: in flight, whether at work, queued or held.
IN_FLIGHT = ("working", "queued", "waiting")


def looks(rows: list[dict[str, str]], folds: dict[str, dict], trunk: dict[str, str]) -> list[dict[str, str]]:
    """What needs a look, worst first: a red trunk, then each slice with a warning or a refused merge.

    `did` is where what its captain already did about it goes, once captains decide things; empty until then,
    and nothing is drawn for it while it is.
    """
    found: list[dict[str, str]] = []
    if trunk.get("state") == "red":
        since = minutes(now_stamp() - stamp(trunk.get("t", ""))) if trunk.get("t") else ""
        why = trunk.get("why") or trunk.get("job") or ""
        found.append({"name": "Trunk is red", "level": "red trunk", "href": "#tab-fleet", "verb": "See the fleet",
                      "says": f"Trunk's CI failed{' ' + since + ' ago' if since else ''}"
                              f"{': ' + why if why else ''}. Merges are held until it is green.", "did": ""})
    for row in rows:
        warned = [one for one in (folds.get(f"{row.get('fairway')}/{row['slice']}") or {}).get("warnings", [])
                  if one["kind"] in LOOKED]
        refused = row.get("refused", "") if row.get("stage") == "Merge refused" else ""
        if not warned and not refused:
            continue
        said = [f"{LOOKED[one['kind']]}: {one['said']}" for one in warned]
        said += [f"Merge refused: {refused}"] if refused else []
        stage = row.get("stage") or ""
        found.append({"name": f"{row['slice']} · {stage}" if stage else row["slice"], "says": "; ".join(said),
                      "level": "red" if refused or any(one["level"] == "red" for one in warned) else "amber",
                      "href": f"#card-{row['slice']}", "verb": "Open its card", "did": "", "slice": row["slice"]})
    return sorted(found, key=lambda one: ("trunk" not in one["level"], one["level"] != "red"))


def look_html(rows: list[dict[str, str]], folds: dict[str, dict], trunk: dict[str, str]) -> str:
    """Needs a look: only what is wrong, each row linking to where to look, and one line when nothing is.
    Nothing at all where no slice is in flight and trunk is not red: there is nothing yet to look at."""
    working = len([row for row in rows if row.get("state") == "working"])
    found = looks(rows, folds, trunk)
    if not found:
        if not any(row.get("state") in IN_FLIGHT for row in rows):
            return ""
        green = "Trunk green" if trunk.get("state") == "green" else ""
        return (f'<div class="card calm" id="look"><span><b>{working} working</b> · nothing needs a look</span>'
                f"<small>{green}</small></div>")
    flagged = len({one["slice"] for one in found if one.get("slice")})
    items = "".join(
        f'<div class="look {esc(one["level"])}"><b>{esc(one["name"])}</b><span class="says">{esc(one["says"])}'
        f'</span><a href="{esc(one["href"])}">{esc(one["verb"])}</a>'
        + (f'<span class="did">{esc(one["did"])}</span>' if one["did"] else "") + "</div>" for one in found)
    return (f'<div class="card" id="look"><div class="head"><h2>Needs a look · {len(found)}</h2>'
            f"<span>{working} working · {max(0, working - flagged)} fine</span></div>{items}</div>")


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
        # A sub-agent with no task of its own is named by its role, once: the role again underneath would be
        # the same words twice, so the line under it then says only the model.
        role = agent["role"].removeprefix("sail-")
        name = agent["task"] or role
        under = " · ".join(part for part in ((role if agent["task"] else ""), agent["model"]) if part)
        rows += (f'<div class="lane-name"><b>{esc(name)}</b><span class="sub">{esc(under)}</span></div>'
                 f'<div class="track">'
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


def window_tabs(fairway: str, slice_id: str) -> str:
    """Where it is, and its example map: links, so each is an address a person can keep or reload."""
    here = esc(window_address(fairway, slice_id))
    return (f'<nav class="tabs" aria-label="This slice"><a href="{here}&amp;tab=where" data-tab="where" '
            f'aria-current="page">Where it is</a><a href="{here}&amp;tab=map" data-tab="map">Example map</a></nav>')


def window(root: Path, fairway: str, slice_id: str) -> str:
    body = (f"<style>{STYLE}{WINDOW_STYLE}{MAP_STYLE}</style>{window_tabs(fairway, slice_id)}"
            f'<section data-panel="where">{window_body(root, fairway, slice_id)}</section>'
            f'<section data-panel="map" hidden>{map_panel(root, slice_id)}</section>')
    return document(f"{slice_id} · {root.resolve().name}", f"live · {fairway}", body, WINDOW_SCRIPT, now="/slice")


def said_in(drawn: str) -> str:
    """The `data-said` a drawn card carries, as the poll compares it."""
    if 'data-said="' not in drawn:
        return ""
    return html.unescape(drawn.split('data-said="', 1)[1].split('"', 1)[0])


def window_payload(root: Path, fairway: str, slice_id: str) -> str:
    drawn, mapped = window_body(root, fairway, slice_id), map_panel(root, slice_id)
    return json.dumps({"said": said_in(drawn), "html": drawn, "map_said": said_in(mapped), "map_html": mapped})

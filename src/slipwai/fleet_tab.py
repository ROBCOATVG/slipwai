"""The Voyage's Fleet tab: the machinery, and nothing a slice already says.

The tab carried the fleet's whole board — a headline over *Waiting on you*, every park in one line, a row per
stream naming its slices, the lanes, the feed — and each of those said again something the Work tab said
first, sometimes differently. What only this tab can say is how the machine is running: how many session
slots are in use and which slice takes the next, the tokens spent against the day's budget, whether trunk
is green, and a row per process — the harbourmaster and each captain — with its state and its last line.
The settings and Stop stay with it, because they are the controls of that machine.

The published copy (`bridge_page.read_only`) still draws the whole board: it has no Work tab to say the rest.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from .bridge_page import STATES, log_link
from .fleet_page import headline, plural, when
from .page_shell import esc

STYLE = """
#machinery .head{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:baseline;gap:4px 12px}
#machinery .head h2{margin:0}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px;margin:12px 0}
.tile{border:1px solid var(--rule);border-radius:8px;padding:10px 12px;display:grid;gap:4px;background:var(--paper)}
.tile span{font-size:.78rem;color:var(--ink-2)}.tile b{font-size:1.2rem;font-weight:600}
.tile.red{border-color:var(--critical)}.tile.red b{color:var(--critical)}.tile.green b{color:var(--teal)}
.tile .bar{height:6px;border-radius:3px;background:var(--rule-2);overflow:hidden;display:block}
.tile .bar i{display:block;height:100%;background:var(--teal)}.tile .bar i.over{background:var(--critical)}
.procs-list{display:grid;font-size:.86rem;overflow-x:auto}
.proc-row{display:grid;grid-template-columns:minmax(150px,.9fr) minmax(110px,.6fr) minmax(0,2fr) auto;gap:10px;
  align-items:center;min-height:44px;border-top:1px solid var(--rule-2);padding:4px 0}
.proc-row .said{color:var(--ink-2);overflow-wrap:anywhere}.proc-row .running{color:var(--teal)}
.proc-row .stalled,.proc-row .exited{color:var(--critical)}
#machinery .acts{display:flex;flex-wrap:wrap;gap:10px;padding-top:12px;margin-top:8px;border-top:1px solid var(--rule)}
@media (max-width:640px){.proc-row{grid-template-columns:1fr 1fr}.proc-row .said{grid-column:1 / -1}}
"""


def sessions_tile(fleet: dict[str, Any], rows: list[dict[str, str]]) -> str:
    """The slots in use, and which slice takes the next one free: the first queued that is not paused."""
    counts = fleet.get("counts") or {}
    busy, slots = int(counts.get("running") or 0), counts.get("slots")
    nxt = next((row["slice"] for row in rows if row.get("state") == "queued" and not row.get("paused")), "")
    if isinstance(slots, int):
        free = max(0, slots - busy)
        under = (f"{plural(free, 'slot')} free" if free else "every slot in use") + (
            f" · {nxt} takes {'it' if free == 1 else 'the next'}" if nxt else "")
        big = f"{busy} of {slots}"
    else:
        big, under = str(busy), (f"no limit set · {nxt} is next" if nxt else "no limit set on how many run")
    return f'<div class="tile"><span>Sessions</span><b>{esc(big)}</b><span>{esc(under)}</span></div>'


def tokens_tile(fleet: dict[str, Any]) -> str:
    """Today's tokens against the day's budget, in thousands, as the harbour counts them."""
    bunker = fleet.get("bunker") or {}
    today, allowed = bunker.get("today"), bunker.get("allowed")
    spent = f"{today:,}k" if isinstance(today, int) else "none recorded"
    if isinstance(allowed, int | float) and not isinstance(allowed, bool) and allowed > 0:
        share, spent = (today or 0) / allowed, f"{today or 0:,}k"
        bar = (f'<span class="bar"><i class="{"over" if share > 1 else ""}" '
               f'style="width:{min(100, round(100 * share))}%"></i></span>')
        return (f'<div class="tile"><span>Tokens today</span><b>{esc(spent)} of {esc(f"{allowed:,}")}k</b>'
                f"{bar}</div>")
    return (f'<div class="tile"><span>Tokens today</span><b>{esc(spent)}</b><span>no budget a day is set'
            f"</span></div>")


def trunk_tile(trunk: dict[str, str], now: datetime | None = None) -> str:
    """Trunk's own CI as the harbour last heard it, and what a red trunk holds."""
    if trunk.get("state") == "red":
        since = when(trunk.get("t", ""), now)
        why = trunk.get("why") or trunk.get("job") or "its CI failed"
        return (f'<div class="tile red"><span>Trunk</span><b>Red{" since " + esc(since) if since else ""}</b>'
                f"<span>Merges are held until it is green: {esc(why)}</span></div>")
    if trunk.get("state") == "green":
        since = when(trunk.get("t", ""), now)
        return (f'<div class="tile green"><span>Trunk</span><b>Green</b><span>'
                f'{"since " + esc(since) if since else "its CI passed"}</span></div>')
    return ('<div class="tile"><span>Trunk</span><b>Not heard yet</b><span>The harbour writes a line when trunk\'s '
            "CI first reports</span></div>")


def process_rows(fleet: dict[str, Any], controls: bool, now: datetime | None = None) -> str:
    """A row per process: who it is, its state — with its stream's, where that is the news — and its last line."""
    berths = {str(row.get("fairway")): str(row.get("state")) for row in fleet.get("berths") or []}
    streams = fleet.get("streams") or {}
    harbour = [(at, kind) for at, who, kind in fleet.get("feed") or [] if who == "harbour"]
    rows = ""
    for one in fleet.get("processes") or []:
        fairway = str(one.get("fairway") or "")
        name = f"Captain · {fairway}" if fairway else "Harbourmaster"
        state = {"running": "running", "exited": "exited", "not lit": "not lit"}.get(str(one["state"]), "")
        stream = STATES.get(berths.get(fairway, ""), "")
        tone = "stalled" if stream == "stalled" else state.replace(" ", "-")
        if stream and stream not in ("running", state) and one["state"] == "running":
            state = f"running · {stream}"
        lines = list(streams.get(fairway) or []) if fairway else harbour
        last = f"{when(str(lines[-1][0]), now) or ''} {lines[-1][1]}".strip() if lines else "nothing said yet"
        if one["state"] != "running" and one.get("starts_when"):
            last = f"{one.get('why') or 'not running'} · starts again when {one['starts_when']}"
        link = log_link(fairway) if fairway and controls else ""
        rows += (f'<div class="proc-row"><b>{esc(name)}</b><span class="{esc(tone)}">{esc(state)}</span>'
                 f'<span class="said">{esc(last)}</span><span>{link}</span></div>')
    return f'<div class="procs-list">{rows}</div>' if rows else '<p class="empty">No process has started yet.</p>'


def fleet_tab(fleet: dict[str, Any], rows: list[dict[str, str]], trunk: dict[str, str], stoppable: bool,
              controls: bool = True, now: datetime | None = None) -> str:
    """The machinery card: the three tiles, a row per process, and Stop. Not the headline the published copy
    opens on, which counts what waits on a person by its own rule: the strip above the tabs says that."""
    fault = (fleet.get("unreadable") or {}).get("clearance", "")
    unread = f'<p class="empty">Clearance could not be read: {esc(fault)}</p>' if fault else ""
    stop = (f'<div class="acts"><button type="button" class="install" data-fleet-stop'
            f'{"" if stoppable else " hidden"}>Stop the fleet</button></div>' if controls else "")
    return (f'<div class="card" id="machinery"><div class="head"><h2>Fleet</h2><span class="empty">The machinery: '
            f"the harbourmaster and each captain's process.</span></div>{unread}"
            f'<div class="tiles">{sessions_tile(fleet, rows)}{tokens_tile(fleet)}{trunk_tile(trunk, now)}</div>'
            f"{process_rows(fleet, controls, now)}{stop}</div>")


def fleet_sub(fleet: dict[str, Any]) -> str:
    """The short line under the window's title: the fleet in a word and its slots. Not what waits on you —
    that is the strip's, and a second count here was a fourth place to disagree."""
    colour, sentence, _ = headline(fleet)
    word = {"teal": "working", "brass": "stopped", "blue": "paused", "red": "stalled", "grey": "quiet"}[colour]
    counts = fleet.get("counts") or {}
    slots = counts.get("slots")
    used = (f"{counts.get('running', 0)} of {slots} slots" if isinstance(slots, int)
            else f"{counts.get('running', 0)} running")
    return f"{'built' if sentence.startswith('Built:') else word} · {used}"

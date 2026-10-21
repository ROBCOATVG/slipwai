"""One captain's window: everything its fairway has done, with the harbour's answers beside it, and its output.

The Streams card answers *is anything stuck*, and its drawer shows the last sixty lines of one deck log. The
question after that is *what has this one been doing, and what happened to what it asked for* — and half of
that answer is in the harbour log, where a merge request's grant or refusal is written with the time it took.
So this window reads both, in one timeline grouped by slice, and beside it the captain process's own output,
which until now only a terminal could show.

It is a window of its own, like the Voyage, because a person keeps it open beside the run. It is a fold of
files on disk like every other page on the board: the poll asks for the lines after the ones it has and the
output after the byte it has, and nothing is kept anywhere but the files.
"""
from __future__ import annotations

import json
from pathlib import Path

from .bridge_page import STATES
from .deck import feature_of, output, timeline
from .page_shell import document, esc
from .seats import parameter

STYLE = """
.who-facts{display:flex;flex-wrap:wrap;gap:4px 18px;font-size:.86rem;color:var(--ink-2)}
.who-facts b{font-weight:500;color:var(--ink)}
.panes{display:grid;grid-template-columns:minmax(0,1fr) 290px;gap:18px;align-items:start}
@media (max-width:860px){.panes{grid-template-columns:minmax(0,1fr)}}
.panes>*{min-width:0}
.pick{display:flex;flex-wrap:wrap;gap:2px;border-bottom:1px solid var(--rule);margin:-4px 0 12px}
.pick button{font:inherit;font-size:.88rem;border:0;background:none;color:var(--ink-2);padding:7px 12px;
  border-bottom:2px solid transparent;margin-bottom:-1px;cursor:pointer;white-space:nowrap}
.pick button[aria-selected="true"]{color:var(--ink);border-bottom-color:var(--teal);font-weight:500}
.pick small{font-family:var(--mono);color:var(--ink-3);margin-left:6px}
@media (max-width:1100px){.pick small{display:none}}
.filters{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin-bottom:10px}
.filters .lbl{font-size:.72rem;color:var(--ink-3);text-transform:uppercase;letter-spacing:.05em}
.f{font:inherit;font-size:.8rem;border:1px solid var(--rule);background:var(--paper);color:var(--ink-2);
  border-radius:999px;padding:2px 10px;cursor:pointer}
.f[aria-pressed="true"]{background:var(--ink);border-color:var(--ink);color:var(--paper)}
.filters input{flex:1 1 160px;min-width:0;font:inherit;font-size:.84rem;padding:4px 10px;border:1px solid var(--rule);
  border-radius:7px;background:var(--paper);color:var(--ink)}
.tl{max-height:70vh;overflow:auto}
.slicehead{display:flex;gap:10px;align-items:baseline;margin:14px 0 2px;padding-bottom:3px;
  border-bottom:1px solid var(--rule-2);font-size:.8rem;color:var(--ink-3)}
.slicehead:first-child{margin-top:0}.slicehead b{font-family:var(--mono);font-size:.9rem;color:var(--ink)}
.row{display:grid;grid-template-columns:70px 66px minmax(0,1fr);gap:0 10px;padding:5px 4px;border-radius:6px}
.row:hover{background:var(--rule-2)}
.row .t{font-family:var(--mono);font-size:.78rem;color:var(--ink-3);font-variant-numeric:tabular-nums}
.who{font-size:.68rem;text-transform:uppercase;letter-spacing:.05em;padding:2px 6px;border-radius:4px;
  text-align:center;align-self:start;background:var(--rule-2);color:var(--ink-2)}
.who.captain{background:var(--teal-soft);color:var(--teal)}
.who.person{background:var(--brass-soft);color:var(--brass)}
.what{min-width:0;overflow-wrap:anywhere}
.what .k{font-family:var(--mono);font-size:.74rem;color:var(--ink-3);margin-right:6px}
.row.quiet{opacity:.65}
.row.flag{background:var(--brass-soft)}
.rawbtn{font:inherit;font-size:.74rem;border:0;background:none;color:var(--ink-3);padding:0 0 0 6px;
  cursor:pointer;text-decoration:underline dotted}
.raw{display:none;grid-column:3;margin-top:5px;background:var(--rule-2);border-radius:6px;padding:7px 10px;
  font-family:var(--mono);font-size:.76rem;white-space:pre-wrap;overflow-wrap:anywhere;color:var(--ink-2)}
.row.open .raw{display:block}
.spent{display:flex;flex-wrap:wrap;gap:2px 12px;font-size:.78rem;color:var(--ink-2);margin-top:3px;
  font-variant-numeric:tabular-nums}
.bar{display:flex;height:7px;border-radius:4px;overflow:hidden;background:var(--rule-2);margin-top:4px;
  max-width:340px}
.bar i{display:block;height:100%}.bar .q{background:var(--brass)}.bar .l{background:var(--ink-3)}
.bar .g{background:var(--teal)}
pre.out{margin:0;max-height:70vh;overflow:auto;background:var(--rule-2);border-radius:8px;padding:12px 14px;
  font-family:var(--mono);font-size:.78rem;line-height:1.55;white-space:pre-wrap;overflow-wrap:anywhere}
.rail h3{font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;color:var(--ink-3);font-weight:500;
  margin:0 0 8px}
.rail .card{margin-top:0}.rail .card+.card{margin-top:14px}
.needs{list-style:none;margin:0;padding:0;display:grid;gap:8px;font-size:.84rem}
.needs li{border:1px solid var(--rule);border-radius:8px;padding:7px 9px;overflow-wrap:anywhere}
.needs .clip{display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:5;overflow:hidden;margin-top:4px}
.live{font-size:.82rem;color:var(--ink-3)}
.head{display:flex;flex-wrap:wrap;gap:8px 16px;align-items:center;justify-content:space-between}
.kv{display:grid;grid-template-columns:auto 1fr;gap:3px 10px;margin:0;font-size:.84rem;
  font-variant-numeric:tabular-nums}
.kv dt{color:var(--ink-3)}.kv dd{margin:0;text-align:right}
"""

SCRIPT = r"""
const DATA = JSON.parse(document.getElementById('captain-data').textContent);
const FAIRWAY = DATA.fairway;
const shown = {slice: 'all', beats: false, harbour: false, q: ''};
let lines = DATA.lines, at = DATA.at, follow = true;
const esc = s => String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const clock = t => (t || '').slice(11, 19);
function spent(t) {
  if (!('gate_s' in t || 'waited_s' in t)) {
    return t.attempt ? `<div class="spent"><span>attempt ${t.attempt}</span></div>` : '';
  }
  const q = t.waited_s || 0, l = t.lock_s || 0, g = t.gate_s || 0, all = q + l + g || 1;
  const pct = v => (100 * v / all).toFixed(1) + '%';
  const said = [t.attempt ? `attempt ${t.attempt}` : '', 'waited_s' in t ? `queued ${q}s` : '',
                'lock_s' in t ? `merge ref ${l}s` : '', 'gate_s' in t ? `gate ${g}s` : ''].filter(Boolean);
  return `<div class="spent">${said.map(s => `<span>${s}</span>`).join('')}</div>`
    + `<div class="bar" aria-hidden="true"><i class="q" style="width:${pct(q)}"></i>`
    + `<i class="l" style="width:${pct(l)}"></i><i class="g" style="width:${pct(g)}"></i></div>`;
}
function chips() {
  const slices = [...new Set(lines.map(l => l.slice).filter(Boolean))];
  document.getElementById('slices').innerHTML = ['all', ...slices].map(s =>
    `<button class="f" data-slice="${esc(s)}" aria-pressed="${shown.slice === s}">`
    + `${s === 'all' ? 'All' : esc(s)}</button>`).join('');
}
function paint() {
  const box = document.getElementById('timeline');
  const atEnd = box.scrollHeight - box.scrollTop - box.clientHeight < 40;
  const q = shown.q.toLowerCase();
  const kept = lines.map((l, i) => [l, i]).filter(([l]) =>
    (shown.slice === 'all' || l.slice === shown.slice) && (shown.beats || l.kind !== 'heartbeat')
    && (!shown.harbour || l.who === 'harbour')
    && (!q || (l.what + ' ' + l.kind + ' ' + JSON.stringify(l.line)).toLowerCase().includes(q)));
  let html = '', group = null;
  for (const [l, i] of kept) {
    if (l.slice !== group) {
      group = l.slice;
      html += `<div class="slicehead"><b>${esc(group || 'before any slice')}</b>`
        + `<span>${esc(l.t.slice(0, 10))}</span></div>`;
    }
    const flag = ['parked', 'park', 'refused', 'question', 'fix-trunk'].includes(l.kind);
    html += `<div class="row${l.kind === 'heartbeat' ? ' quiet' : ''}${flag ? ' flag' : ''}" data-i="${i}">`
      + `<span class="t">${clock(l.t)}</span><span class="who ${l.who}">${l.who === 'person' ? 'you' : l.who}</span>`
      + `<span class="what"><span class="k">${esc(l.kind)}</span>${esc(l.what)}<button class="rawbtn">raw</button>`
      + `${spent(l.timing)}</span><span class="raw">${esc(JSON.stringify(l.line))}</span></div>`;
  }
  box.innerHTML = html || '<p class="empty">No line matches.</p>';
  if (atEnd) box.scrollTop = box.scrollHeight;
}
function addOutput(text) {
  if (!text) return;
  const out = document.getElementById('output');
  const atEnd = out.scrollHeight - out.scrollTop - out.clientHeight < 40;
  if (out.dataset.empty) { out.textContent = ''; delete out.dataset.empty; }
  out.textContent += text;
  if (atEnd) out.scrollTop = out.scrollHeight;
}
async function poll() {
  if (!follow) return;
  try {
    const asked = `/captain.json?fairway=${encodeURIComponent(FAIRWAY)}&lines=${lines.length}&out=${at}`;
    const now = await (await fetch(asked)).json();
    if (now.lines.length) { lines = lines.concat(now.lines); chips(); paint(); }
    addOutput(now.out); at = now.at;
    document.getElementById('state').innerHTML = now.state;
    document.getElementById('rail').innerHTML = now.rail;
  } catch (fault) { /* the board went away; the next tick asks again */ }
}
document.addEventListener('click', event => {
  const tab = event.target.closest('[data-pane]');
  if (tab) {
    document.querySelectorAll('[data-pane]').forEach(one => one.setAttribute('aria-selected', one === tab));
    document.querySelectorAll('[data-shows]').forEach(one => { one.hidden = one.dataset.shows !== tab.dataset.pane; });
    const out = document.getElementById('output'); out.scrollTop = out.scrollHeight;
  }
  const slice = event.target.closest('[data-slice]');
  if (slice) { shown.slice = slice.dataset.slice; chips(); paint(); }
  const toggle = event.target.closest('[data-toggle]');
  if (toggle) {
    shown[toggle.dataset.toggle] = !shown[toggle.dataset.toggle];
    toggle.setAttribute('aria-pressed', shown[toggle.dataset.toggle]); paint();
  }
  if (event.target.classList.contains('rawbtn')) event.target.closest('.row').classList.toggle('open');
  if (event.target.id === 'follow') {
    follow = !follow; event.target.setAttribute('aria-pressed', follow);
    event.target.textContent = follow ? 'Following' : 'Paused';
    if (follow) poll();
  }
  if (event.target.id === 'tell-go') {
    const box = document.getElementById('tell');
    if (!box.value.trim()) return;
    fetch('/tell', {method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({fairway: FAIRWAY, message: box.value.trim()})})
      .then(answer => { if (answer.ok) { box.value = ''; poll(); } else answer.text().then(said => alert(said)); });
  }
});
document.getElementById('q').addEventListener('input', event => { shown.q = event.target.value; paint(); });
chips(); paint(); addOutput(DATA.out);
document.getElementById('timeline').scrollTop = 1e9;
setInterval(poll, 2500);
"""


def number(query: str, name: str, otherwise: int) -> int:
    """A whole number out of the poll's query, or `otherwise` where it is missing or is not one."""
    try:
        return int(parameter(query, name))
    except ValueError:
        return otherwise


def state_html(row: dict | None) -> str:
    """The header line: what the captain is on, as the Streams card says it."""
    if not row:
        return '<span class="chip">not started</span>'
    state = STATES.get(str(row["state"]), str(row["state"]))
    tokens = f"{row['tokens']}k" if isinstance(row["tokens"], int) else row["tokens"]
    return (f'<span class="chip {esc(STATES.get(str(row["state"]), ""))}" data-state="{esc(state)}">{esc(state)}'
            f'</span> <span class="who-facts"><span>Slice <b class="mono">{esc(row["slice"])}</b></span>'
            f'<span>Last line <b>{esc(row["last"])}</b></span><span>Tokens <b>{esc(tokens)}</b></span>'
            f'<span>Merged <b>{esc(row["merged"])}</b></span></span>')


def last_merge(lines: list[dict]) -> str:
    """Where the most recent merge answer's time went, or nothing where no answer carried timings."""
    timed = [one for one in lines if one["who"] == "harbour" and one["timing"]]
    if not timed:
        return ""
    one = timed[-1]
    rows = "".join(f"<dt>{esc(label)}</dt><dd>{esc(one['timing'][name])}{'' if name == 'attempt' else 's'}</dd>"
                   for name, label in (("waited_s", "Queued"), ("lock_s", "Merge ref"), ("gate_s", "Gate"),
                                       ("attempt", "Attempt")) if name in one["timing"])
    return (f'<div class="card"><h3>Last merge · {esc(one["slice"])}</h3>'
            f'<p class="empty" style="margin:0 0 6px">{esc(one["kind"])} at {esc(one["t"][11:19])}</p>'
            f'<dl class="kv">{rows}</dl></div>')


def rail_html(fairway: str, lines: list[dict], waiting: list[dict]) -> str:
    """What is waiting on a person from this captain, its last merge's time, and the box to answer it."""
    decided = {str(one["line"].get("id")) for one in lines if one["kind"] == "decision"}
    asked = [one for one in lines if one["kind"] == "question" and str(one["line"].get("id")) not in decided]
    needs = [f"<li title=\"{esc(row['what'])}\">"
             f"<span class=\"chip\" data-state=\"waiting on you\">{esc(row['kind'])}</span> "
             f"<span class=\"clip\">{esc(row['what'])}{' · ' + esc(row['waited']) if row.get('waited') else ''}"
             f"</span></li>"
             for row in waiting if row["fairway"] == fairway]
    needs += [f"<li><span class=\"chip\" data-state=\"waiting on you\">question</span> "
              f"<b class=\"mono\">{esc(one['line'].get('id'))}</b>"
              f"<span class=\"clip\">{esc(one['line'].get('what', ''))}</span></li>"
              for one in asked]
    listed = f'<ul class="needs">{"".join(needs)}</ul>' if needs else '<p class="empty">Nothing.</p>'
    return (f'<div class="card"><h3>Needs you</h3>{listed}</div>{last_merge(lines)}'
            f'<div class="card"><h3>Tell this captain</h3><div class="ask" style="margin-top:0">'
            f'<input id="tell" placeholder="Read at its next boundary" aria-label="Message to {esc(fairway)}">'
            f'<button class="go" id="tell-go">Send</button></div></div>')


def found_parts(root: Path, fairway: str, board: dict) -> tuple[dict | None, list[dict], str]:
    """This captain's row on the board, its timeline, and the fault where a log could not be read."""
    row = next((one for one in board["berths"] if one["fairway"] == fairway), None)
    lines, fault = timeline(root, fairway)
    return row, lines, fault


def page(root: Path, fairway: str, board: dict) -> tuple[int, str]:
    """The window, or a 404 that names the captains this board does have."""
    feature = feature_of(root, fairway)
    if not feature:
        known = ", ".join(str(one["fairway"]) for one in board["berths"]) or "none yet"
        return 404, document(f"No captain called {fairway}", "captain log",
                             f'<div class="card"><p>No fairway here has a deck log called '
                             f'<code>{esc(fairway)}</code>. Captains with a log: {esc(known)}.</p></div>',
                             now="/captain")
    row, lines, fault = found_parts(root, fairway, board)
    out, at = output(root, fairway)
    data = json.dumps({"fairway": fairway, "lines": lines, "out": out, "at": at}, ensure_ascii=False)
    embedded = data.replace("</", "<\\/")  # a line that says `</script>` must not end the block it is in
    broken = f'<div class="card"><h2>Part of this log cannot be read</h2><p class="empty">{esc(fault)}</p></div>'
    body = f"""<style>{STYLE}</style>
<script type="application/json" id="captain-data">{embedded}</script>
{broken if fault else ""}
<div class="card"><div class="head">
<div id="state">{state_html(row)}</div>
<span class="live">New lines every few seconds
<button class="f" id="follow" aria-pressed="true">Following</button></span>
</div></div>
<div class="panes" style="margin-top:18px">
<div class="card" style="margin-top:0">
<div class="pick" role="tablist">
<button role="tab" data-pane="timeline" aria-selected="true">Timeline<small>deck + harbour</small></button>
<button role="tab" data-pane="output" aria-selected="false">Captain output
<small>captain-{esc(fairway)}.out</small></button>
</div>
<section data-shows="timeline">
<div class="filters"><span class="lbl">Slice</span><span id="slices" style="display:contents"></span>
<span class="lbl" style="margin-left:8px">Show</span>
<button class="f" data-toggle="beats" aria-pressed="false">Heartbeats</button>
<button class="f" data-toggle="harbour" aria-pressed="false">Harbour answers only</button>
<input id="q" type="search" placeholder="Filter lines, e.g. merge or D-ORD" aria-label="Filter lines"></div>
<div class="tl" id="timeline"></div>
</section>
<section data-shows="output" hidden>
<p class="empty" style="margin:0 0 10px">What the captain process printed: its own lines and each turn's
closing message, from <code>.slipwai/running/captain-{esc(fairway)}.out</code>.</p>
<pre class="out" id="output" data-empty="1">Nothing printed yet. A captain that `make cruise` started writes here.</pre>
</section>
</div>
<aside class="rail" id="rail">{rail_html(fairway, lines, board["inbox"])}</aside>
</div>"""
    return 200, document(fairway, f"captain log · {feature}", body, SCRIPT, now="/captain")


def payload(root: Path, fairway: str, board: dict, after_lines: int, after_out: int) -> str:
    """What the window's poll is given: the lines after the ones it has, the output after its byte, and the
    header and rail drawn afresh, because a park or an answer changes both."""
    row, lines, _ = found_parts(root, fairway, board)
    out, at = output(root, fairway, after_out)
    return json.dumps({"lines": lines[max(0, after_lines):], "out": out, "at": at, "state": state_html(row),
                       "rail": rail_html(fairway, lines, board["inbox"])}, ensure_ascii=False)

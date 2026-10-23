"""The bridge's page: the board as HTML, in the words a person uses rather than the method's.

The nautical names are the method's — they make a dozen scattered ideas into one picture, and that is worth
having in a plan and in a log. They are not the dashboard's. Somebody looking at this page wants to know
what is running, what is waiting on them, and how fast it is going; `boilers` and `fanout` cost them a
glossary to find out.

So every label here is plain, and `PLAIN` is the one table that says which is which. The mockup
(`docs/mockups/ledger-bridge.html`) decided this and the rule is its, not this module's.

**The look is not here.** The tokens, the type, the three-state theme and the document around them are
`page_shell`, because the board is one page whatever started it and a second stylesheet would be a second
look. What is here is the board's own markup, written from `fleet.board`.

**Nothing here reaches the network and nothing is cached.** The page is a render of `fleet.board`, which is
a fold of the logs, so a reload is a re-fold. That is the same rule the board has and for the same reason.
"""
# budget: 380 — the waiting card now groups parks, questions and notes by what a person has to do, and
# each group carries its own heading, count and the rows under it, so the page is a little longer than one
# that listed them flat.
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import quote

from .console_page import SCRIPT as CONSOLE_SCRIPT
from .fleet import NOTHING, inbox_detail  # noqa: F401 - NOTHING is read by name by the pages built on this
from .fleet_page import SCRIPT as FLEET_SCRIPT
from .fleet_page import STYLE as FLEET_STYLE
from .fleet_page import headline_card, parks_table, waiting_card
from .fleet_page import live_sub as fleet_sub

# PLAIN, STYLE and THEME are read by name here — and `PLAIN` by the suite, which is where the board's
# plain-words table was until the settings box needed it too.
from .page_shell import PLAIN, STYLE, THEME, document, esc  # noqa: F401
from .settings_card import settings
from .timeline_page import SCRIPT as TIMELINE_SCRIPT
from .timeline_page import STYLE as TIMELINE_STYLE
from .timeline_page import timeline_card

#: What each state means in a word a reader does not have to be told. `stalled` stays `stalled`: it is the
#: one that has to be noticed, and a gentler word for it would be the dashboard hiding something.
STATES = {"working": "running", "stalled": "stalled", "parked": "waiting on you", "paused": "paused",
          "finished": "done", "idle": "idle", "unknown": "clearance unavailable", "not started": "not started"}

SCRIPT = """
// The toggle works without this. What this adds is remembering it: the page reloads after every control,
// and a theme that reset on every send would be a theme nobody bothers to set.
const THEME_KEY = 'slipwai-bridge-theme';
const held = localStorage.getItem(THEME_KEY);
if (held) { const box = document.getElementById(held); if (box) box.checked = true; }
for (const box of document.querySelectorAll('.theme input')) {
  box.addEventListener('change', () => localStorage.setItem(THEME_KEY, box.id));
}

async function send(path, body){
  const answer = await fetch(path, {method:'POST', headers:{'Content-Type':'application/json'},
                                    body: JSON.stringify(body)});
  if (answer.ok) location.reload();
  else alert(await answer.text());
}
// The one thing on this board that changes without a reload: `./init`, running in the project the board
// has just landed in. It is a child of the server and nobody is watching its terminal, so the page asks for
// what it has said since the line it already has, and the clock on the chip ticks between asks — a card
// that said "running" and nothing else for the two minutes Spec Kit takes is a card a person reloads.
// Every log on this page opens on its newest line, including the ones inside a drawer that was not open
// when the page loaded. `toggle` does not bubble, so it is listened for on the way down.
const bottom = one => { one.scrollTop = one.scrollHeight; };
document.querySelectorAll('[data-tail]').forEach(bottom);
document.addEventListener('toggle', event => {
  if (event.target.matches('details.log')) event.target.querySelectorAll('[data-tail]').forEach(bottom);
}, true);

const fitting = document.getElementById('fitting');
if (fitting) {
  const tail = document.getElementById('fitting-said');
  const chip = fitting.querySelector('[data-state]');
  const clock = s => Math.floor(s / 60) + ':' + String(Math.floor(s % 60)).padStart(2, '0');
  let at = Number(tail.dataset.at || 0);
  let seconds = Number(chip.dataset.seconds || 0);
  let running = chip.dataset.state === 'running';
  const paint = () => { chip.textContent = chip.dataset.state + ' · ' + clock(seconds); };
  setInterval(() => { if (running) { seconds += 1; paint(); } }, 1000);
  const poll = async () => {
    let said;
    try { said = await (await fetch('/init.json?since=' + at)).json(); }
    catch (fault) { return; }   // the board was closed, or the server went away: stop asking
    at = said.at;
    seconds = said.seconds;
    if (said.lines.length) {
      tail.textContent += said.lines.join('\\n') + '\\n';
      tail.scrollTop = tail.scrollHeight;   // the last line, which is the one being waited on
    }
    if (said.done) {
      running = false;
      chip.dataset.state = said.code ? 'stopped' : 'done';
      chip.className = said.code ? 'chip stalled' : 'chip';
    }
    const launch = document.getElementById('launch');
    if (launch) launch.hidden = !said.launchable;
    paint();
    if (running) setTimeout(poll, 700);
  };
  poll();
}

document.addEventListener('click', event => {
  const dial = event.target.closest('[data-ring]');
  if (dial) send('/ring', {position: dial.dataset.ring});
  const say = event.target.closest('[data-tell]');
  if (say) {
    const box = document.getElementById(say.dataset.box || 'tell-' + say.dataset.tell);
    if (box && box.value.trim()) send('/tell', {fairway: say.dataset.tell, message: box.value.trim()});
  }
  const read = event.target.closest('[data-read]');
  if (read) send('/read', {fairway: read.dataset.read, decisions: read.dataset.stamps.split(',')});
  const seen = event.target.closest('[data-dismiss]');
  if (seen) send('/dismiss', {fairway: seen.dataset.dismiss, told: seen.dataset.told});
  if (event.target.id === 'launch') {
    event.target.disabled = true;
    send('/launch', {});
  }
  if (event.target.id === 'attach-go') {
    const box = document.getElementById('attach');
    if (box && box.value.trim()) send('/attach', {root: box.value.trim()});
  }
  if (event.target.id === 'apply') {
    const pairs = [...document.querySelectorAll('[data-number]')]
      .map(one => one.dataset.number + '=' + one.value);
    send('/set', {pairs});
  }
});
""" + FLEET_SCRIPT + TIMELINE_SCRIPT + CONSOLE_SCRIPT


def stream_log(fairway: str, lines: list) -> str:
    """One stream's own log, folded open by clicking its row.

    A `<details>`, not a route: the published copy is one file with nothing to press, and a link that
    worked on the served page and 404'd on the published one would be the two copies disagreeing. A
    checkbox and a CSS rule is also what `page.ts` settled on, for the same reason.
    """
    if not lines:
        return '<p class="empty">Nothing in this stream\'s log yet.</p>'
    rows = "".join(f'<li><span class="when">{esc(when)}</span> {esc(what)}</li>' for when, what in lines)
    return (f'<details class="log"><summary>{esc(len(lines))} lines from {esc(fairway)}\'s captain'
            f'</summary><ol class="lines" data-tail>{rows}</ol></details>')


def queued_note(row: dict) -> str:
    """The slices a stream has claimed and no session is on, said beside the ones at work — they are waiting
    for a slot, which is different from being worked and different from being stuck."""
    queued = str(row.get("queued") or "")
    return f' <small>· queued {esc(queued)}</small>' if queued and queued != "—" else ""


def log_link(fairway: str) -> str:
    """The way into one captain's own window. Not on the published copy, which has no route behind it."""
    return (f'<a class="quiet-link" href="/captain?fairway={quote(fairway)}" target="_blank" rel="noopener">'
            f'Open log \u2197</a>')


def berth_rows(rows: list[dict], streams: dict, controls: bool = True) -> str:
    if not rows:
        return '<p class="empty">No stream has written a line yet.</p>'
    head = ("<tr><th>Stream</th><th>Feature</th><th>Piece of work</th><th>State</th>"
            "<th>Waiting</th><th>Last line</th><th>Tokens</th><th>Merged</th><th></th></tr>")
    body = ""
    for row in rows:
        name = str(row["fairway"])
        state = STATES.get(str(row["state"]), str(row["state"]))
        body += (
            f"<tr><td><b>{esc(name)}</b></td><td>{esc(row['feature'])}</td>"
            f"<td class=\"mono\">{esc(row['slice'])}{queued_note(row)}</td>"
            f"<td><span class=\"chip {esc(STATES.get(str(row['state']), ''))}\" "
            f"data-state=\"{esc(state)}\">{esc(state)}</span></td>"
            f"<td>{esc(row.get('waiting', 0))}</td><td>{esc(row['last'])}</td>"
            f"<td>{esc(row['tokens'])}</td><td>{esc(row['merged'])}</td>"
            f"<td>{log_link(name) if controls else ''}</td></tr>"
            f"<tr class=\"drawer\"><td colspan=\"9\">"
            f"{stream_log(name, streams.get(name) or [])}</td></tr>")
    return f"<table>{head}{body}</table>"


#: What a person has to do with each kind of waiting row, in the order they should be looked at. A park or a
#: question needs an answer; unread decisions need reading; a told is only a note, and Done clears it.
WAIT_GROUPS = (
    ("answer", "Needs an answer", ("question", "parked"), "Silence keeps the stream parked."),
    ("read", "Read and mark read", ("decisions",), "A stream over its decision ceiling is waiting on these."),
    ("note", "Notes", ("told",), "Nothing here blocks a stream; Done clears one."),
)


def headline(detail: str, limit: int = 140) -> str:
    """The first sentence of what is waiting, cut at a word, so the row says what it is before it is opened."""
    first = detail.split(". ", 1)[0].strip()
    if len(first) <= limit:
        return first
    return first[:limit].rsplit(" ", 1)[0] + "…"


def inbox_rows(rows: list[dict], controls: bool, streams: dict | None = None) -> str:
    """Each thing waiting on a person, grouped by what they have to do with it and opened by clicking it:
    what the stream has been saying, and a box to answer it from here. The answer becomes a `told` in the
    stream's deck log, which its captain reads at the next boundary — the one way a park is lifted without a
    terminal."""
    if not rows:
        return '<p class="empty">Nothing is waiting on you.</p>'
    groups = []
    for key, title, kinds, hint in WAIT_GROUPS:
        mine = [(index, row) for index, row in enumerate(rows) if row["kind"] in kinds]
        if not mine:
            continue
        said = "".join(inbox_row(index, row, controls, streams, key) for index, row in mine)
        groups.append(f'<div class="wait-group {key}"><h3>{esc(title)} <span class="count">{len(mine)}</span> '
                      f'<small>{esc(hint)}</small></h3>{said}</div>')
    counts = " · ".join(f"{len([r for r in rows if r['kind'] in kinds])} {title.lower()}"
                        for _, title, kinds, _ in WAIT_GROUPS if any(r["kind"] in kinds for r in rows))
    return f'<p class="wait-sum">{esc(counts)}</p>' + "".join(groups)


def inbox_row(index: int, row: dict, controls: bool, streams: dict | None, group: str) -> str:
    if row["kind"] == "decisions":
        return unread_decisions(row, controls)
    name, detail = str(row["fairway"]), inbox_detail(row)
    # A park brings its own slice's lines, without heartbeats; anything else shows the stream's tail.
    lines = row["lines"] if "lines" in row else (streams or {}).get(name) or []
    log = "".join(f'<li><span class="when">{esc(when)}</span> {esc(what)}</li>' for when, what in lines[-20:])
    # A note needs no answer, only to be seen: Done writes its `read` receipt and it leaves the list.
    done = (f'<button data-dismiss="{esc(name)}" data-told="{esc(row["t"])}">Done</button>'
            if row["kind"] == "told" else "")
    box = (f'<div class="ask"><input id="tell-wait-{index}" placeholder="Answer {esc(name)}…">'
           f'<button class="go" data-tell="{esc(name)}" data-box="tell-wait-{index}">Send</button>{done}</div>'
           if controls else "")
    full = f'<p class="why">{esc(detail)}</p>' if headline(detail) != detail else ""
    return (f'<details class="log"><summary><b>{esc(headline(detail))}</b> '
            f'<span class="tag">{esc(name)}</span> <span class="mono">{esc(row["t"])}</span></summary>'
            f'{full}<ol class="lines" data-tail>{log or "<li>nothing said yet</li>"}</ol>{box}</details>')


def unread_decisions(row: dict, controls: bool) -> str:
    """The decisions a stream took that nobody has read, each with Mark read, and one for all of them.

    Pressing it writes the `read` receipt the decision ceiling counts — the receipt a fairway parked over the
    ceiling is waiting for, which until this had to be written by hand. The decision is shown in full above
    its button, so the press is a person saying they read this one rather than a way past the ceiling.
    """
    name = str(row["fairway"])
    items = []
    for one in row["decisions"]:
        button = (f' <button class="go" data-read="{esc(name)}" data-stamps="{esc(one["t"])}">Mark read</button>'
                  if controls else "")
        items.append(f'<li><span class="when">{esc(one["t"])}</span> <b>{esc(one["id"])}</b> '
                     f'{esc(one["what"])}{button}</li>')
    every = ",".join(str(one["t"]) for one in row["decisions"])
    all_read = (f'<div class="ask"><button class="go" data-read="{esc(name)}" data-stamps="{esc(every)}">'
                f'I have read all {len(row["decisions"])}</button></div>' if controls else "")
    # The log reads them whole — question, options, why — which these one-line ids never could.
    log = '<p><a href="#decisions">Read them in the decision log</a>, each with its question and why.</p>'
    return (f'<details class="log"><summary><b>{esc(row["what"])}</b> '
            f'<span class="tag">{esc(name)}</span> <span class="mono">{esc(row["t"])}</span></summary>'
            f'{log if controls else ""}<ol class="lines">{"".join(items)}</ol>{all_read}</details>')


def answer_boxes(rows: list[dict]) -> str:
    """One box per stream that has written a line. An answer typed here becomes a `told` in its deck log,
    which is the whole point: a person answers from one seat instead of finding the right terminal."""
    streams = sorted({str(row["fairway"]) for row in rows})
    if not streams:
        return ""
    boxes = "".join(
        f'<div class="ask"><input id="tell-{esc(one)}" placeholder="Tell {esc(one)} something…">'
        f'<button class="go" data-tell="{esc(one)}">Send</button></div>' for one in streams)
    return f'<div class="card"><h2>Say something to a stream</h2>{boxes}</div>'


#: The two things a person does *before* there is anything to watch, each with the verb that does it. They
#: are on the board because the board is where somebody who typed one word arrives, and a board that could
#: only show an empty harbour would be a page telling them to go back to the terminal.
def clock(seconds: float) -> str:
    """How long it has been going, as a person reads a clock: `0:07`, `2:41`."""
    whole = int(seconds)
    return f"{whole // 60}:{whole % 60:02d}"


def fitting_card(made: dict) -> str:
    """What the board made and what `./init` is saying in it — the receipt the board lands with.

    It is on the board rather than left on the interview page because the board is where landing *is*: the
    page a person is looking at is now this project's, and the sentence saying which project that is belongs
    on it. `data-at` is how many lines are already here, so the poll asks for what came after them and the
    page never shows a line twice.
    """
    said = "\n".join(made["lines"])
    state = "running" if not made["done"] else ("stopped" if made.get("code") else "done")
    seconds = float(made.get("seconds") or 0)
    # The chip carries the state and the clock, and the script keeps both moving between polls: a card that
    # said "running" and nothing else, for the two minutes Spec Kit takes, is a card a person reloads.
    chip = (f'<span class="chip {esc(state)}" data-state="{esc(state)}" data-seconds="{esc(seconds)}">'
            f'{esc(state)} · {esc(clock(seconds))}</span>')
    # The button is on the card whether or not it can be pressed yet, hidden until the poll says the draft
    # has ended well; a specification a person has read is what pressing it means.
    launch = f'<button class="go" id="launch"{"" if made.get("launchable") else " hidden"}>Continue the build</button>'
    return (f'<div class="card" id="fitting"><h2>Made {esc(Path(str(made["where"])).name)}</h2>'
            f'<p class="empty">{esc(made["where"])} — {chip}</p>'
            f'<pre class="said" id="fitting-said" data-tail data-at="{esc(made["at"])}">'
            f'{esc(said)}\n</pre><div class="ask">{launch}</div></div>')


def live_sub(found: dict) -> str:
    """The one line over the live cards: the fleet's state in a word, and what is waiting on a person."""
    return fleet_sub(found)


def live_cards(found: dict, config: dict, controls: bool = True,
               more: list[tuple[str, str, str]] | None = None) -> str:
    """Everything folded from the logs, with its controls: the headline with the processes under it, what
    waits on a person grouped by what it waits on, each park in one line, the answer boxes, the streams,
    the speed, the fine tune and the feed. The Voyage tab carries these beside the stages and the model;
    the published copy carries them alone, with nothing to press."""
    berths, waiting, pressure = found["berths"], found["inbox"], found["pressure"]
    # Every line the fold carries, not the last fifteen: the list is a tail now, so what used to be cut to
    # keep the page short is scrolled instead, and the newest is the one it opens on.
    feed = "".join(f"<li>{esc(w)}  {esc(who)}  {esc(kind)}</li>" for w, who, kind in found["feed"])
    clearance_fault = (found.get("unreadable") or {}).get("clearance", "")
    unavailable = (f'<div class="card"><h2>Waiting counts unavailable</h2>'
                   f'<p class="empty">{esc(clearance_fault)}</p></div>') if clearance_fault else ""
    # A park is drawn by its group above; what is listed one by one here is a message, a question, and
    # the decisions nobody has read.
    others = [row for row in waiting if row["kind"] != "parked"]
    listed = inbox_rows(others, controls, found.get("streams")) if others else ""
    return f"""<style>{FLEET_STYLE}{TIMELINE_STYLE}</style>{unavailable}
{headline_card(found, controls)}
{waiting_card(found, controls, listed)}
{parks_table(found)}
{timeline_card(found, controls)}
{answer_boxes(berths) if controls else ""}
<div class="card"><h2>Streams</h2>{berth_rows(berths, found.get("streams") or {}, controls)}</div>
{settings(pressure, config, controls, more)}
<div class="card"><h2>Last lines</h2><ul class="feed" data-tail>{feed or "<li>nothing yet</li>"}</ul></div>"""


def page(found: dict, config: dict, controls: bool = True, title: str = "Bridge",
         made: dict | None = None, root: str = "") -> str:
    """The live cards as a page of their own — the published copy, which has no other tab to reach and
    nothing to press. `made` and `root` are kept for the callers that still pass them; the served board
    is `landing_page.landing` and the live cards are on the Voyage tab."""
    del made, root
    return document(title, live_sub(found), live_cards(found, config, controls), SCRIPT if controls else "",
                    now="/" if controls else "")


def read_only(found: dict, config: dict, title: str = "Bridge") -> str:
    """The published copy: the same page with nothing to press, which is what Pages serves."""
    return page(found, config, controls=False, title=title)


def payload(found: dict) -> str:
    """The board as JSON, for anything that would rather read it than look at it."""
    return json.dumps(found, indent=2, ensure_ascii=False, default=str)

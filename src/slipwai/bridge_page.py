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
from __future__ import annotations

import json
from pathlib import Path

from .assets import this_command
from .fleet import NOTHING, inbox_detail
from .page_shell import STYLE, THEME, document, esc  # noqa: F401 — STYLE and THEME are read by name here
from .telegraph import MEANS, POSITIONS

#: The method's word, and the word on the page. The page never shows the left-hand column.
PLAIN = {
    "boilers": "Captains at once",
    "fanout": "Delegates per captain",
    "bunker_per_slice": "Budget per slice (k tokens)",
    "bunker_per_day": "Budget per day (k tokens)",
    "stage_scale": "Stage budgets ×",
    "bar": "Stop a merge at or above",
    "decision_ceiling": "Unread decisions allowed",
    "wait_bound": "Longest wait (minutes)",
    "attempts": "Retries per piece of work",
    "browsers": "Browser test runs at once",
    "fairway": "Stream",
    "berth": "Workspace",
    "slice": "Piece of work",
    "capability": "Capability",
}
#: How a position reads on the dial. Sentence case, as the mockup has it.
DIAL = {name: name.replace("-", " ").capitalize() for name in POSITIONS}
#: What each state means in a word a reader does not have to be told. `stalled` stays `stalled`: it is the
#: one that has to be noticed, and a gentler word for it would be the dashboard hiding something.
STATES = {"working": "running", "stalled": "stalled", "parked": "waiting on you",
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
    const box = document.getElementById('tell-' + say.dataset.tell);
    if (box && box.value.trim()) send('/tell', {fairway: say.dataset.tell, message: box.value.trim()});
  }
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
"""


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


def berth_rows(rows: list[dict], streams: dict) -> str:
    if not rows:
        return '<p class="empty">No stream has written a line yet.</p>'
    head = ("<tr><th>Stream</th><th>Feature</th><th>Piece of work</th><th>State</th>"
            "<th>Waiting</th><th>Last line</th><th>Tokens</th><th>Merged</th></tr>")
    body = ""
    for row in rows:
        name = str(row["fairway"])
        state = STATES.get(str(row["state"]), str(row["state"]))
        body += (
            f"<tr><td><b>{esc(name)}</b></td><td>{esc(row['feature'])}</td>"
            f"<td class=\"mono\">{esc(row['slice'])}</td>"
            f"<td><span class=\"chip {esc(STATES.get(str(row['state']), ''))}\" "
            f"data-state=\"{esc(state)}\">{esc(state)}</span></td>"
            f"<td>{esc(row.get('waiting', 0))}</td><td>{esc(row['last'])}</td>"
            f"<td>{esc(row['tokens'])}</td><td>{esc(row['merged'])}</td></tr>"
            f"<tr class=\"drawer\"><td colspan=\"8\">"
            f"{stream_log(name, streams.get(name) or [])}</td></tr>")
    return f"<table>{head}{body}</table>"


def inbox_rows(rows: list[dict], controls: bool) -> str:
    if not rows:
        return '<p class="empty">Nothing is waiting on you.</p>'
    said = []
    for row in rows:
        detail = inbox_detail(row)
        said.append(f"<tr><td><b>{esc(row['fairway'])}</b></td><td>{esc(row['kind'])}</td>"
                    f"<td>{esc(detail)}</td><td class=\"mono\">{esc(row['t'])}</td></tr>")
    return f"<table>{''.join(said)}</table>"


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
STARTING = (
    ("Start a new project", "generate", "/generate",
     "The interview, asked here: the delivery foundation, the language, what the first service owns, and "
     "where it goes to production."),
    ("Adopt a repository you already have", "adopt", "/adopt",
     "The method installed around code that exists, with what it found and what it would write shown "
     "before anything is written."),
)


def starting_points(command: str | None = None) -> str:
    """What can be started from here, whether or not there is a project in this directory.

    Both the page and the verb, because both are true: the link is where somebody who arrived by typing one
    word goes next, and the command is what they type the second time, from a script or from habit.
    """
    command = this_command() if command is None else command
    rows = "".join(f'<dt><a href="{esc(where)}"><b>{esc(title)}</b></a>'
                   f'<div class="empty">{esc(why)}</div></dt>'
                   f"<dd><code>{esc(command)} {esc(verb)}</code></dd>" for title, verb, where, why in STARTING)
    return f'<div class="card"><h2>Start something</h2><dl>{rows}</dl></div>'


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


def looking(root: str) -> str:
    """Which directory this board is a view of, and the box that points it at another one.

    The board has always been a view of one directory, decided by where it was started and changed only by
    stopping it and starting it again with `--root`. That was the terminal deciding something for a page
    that has a person sitting in front of it: nothing here is cached, every request re-folds the logs at
    `root`, so moving the board is a sentence rather than a restart. A generate moves it by itself, to the
    project it just made; this is the same move, made on purpose.
    """
    return ('<div class="card" id="looking"><h2>Looking at</h2>'
            f'<div class="ask"><input id="attach" value="{esc(root)}">'
            '<button class="go" id="attach-go">Attach</button></div>'
            '<div class="why">any project with a <code>.slipwai/</code> in it — its streams, its inbox and '
            'its telegraph are what this page then shows</div></div>')


def dial(position: str, controls: bool) -> str:
    buttons = []
    for name in POSITIONS:
        if name == position:
            buttons.append(f'<span class="now">{esc(DIAL[name])}</span>')
        elif controls:
            buttons.append(f'<button data-ring="{esc(name)}">{esc(DIAL[name])}</button>')
        else:
            buttons.append(f"<span>{esc(DIAL[name])}</span>")
    return f'<div class="dial">{"".join(buttons)}</div>'


def tune(config: dict, controls: bool) -> str:
    """The fine-tune panel, in plain words. Writes `harbour.json` through the same code the verb uses."""
    rows = []
    for name in MEANS:
        value = config.get(name, NOTHING)
        cell = (f'<input data-number="{esc(name)}" value="{esc(value)}">' if controls else esc(value))
        rows.append(f"<dt>{esc(PLAIN.get(name, name))}</dt><dd>{cell}</dd>")
    apply = '<div class="ask"><button class="go" id="apply">Apply</button></div>' if controls else ""
    return f'<div class="card"><h2>Fine tune</h2><dl>{"".join(rows)}</dl>{apply}</div>'


def page(found: dict, config: dict, controls: bool = True, title: str = "Bridge",
         made: dict | None = None, root: str = "") -> str:
    """The whole page. `controls` off is the read-only copy, which is the same page with nothing to press."""
    berths = found["berths"]
    waiting = found["inbox"]
    pressure = found["pressure"]
    bunker = found["bunker"]
    spent = bunker["spent"]
    stalled = [row for row in berths if row["state"] == "stalled"]
    sub = (f"{len(waiting)} waiting on you · {len(berths)} stream(s)"
           + (f" · {len(stalled)} stalled" if stalled else "")
           + f" · {spent if spent is not None else NOTHING}/{bunker['allowed']}k today")
    banked = f'<p class="empty">{esc(pressure["banked"])}</p>' if pressure["banked"] else ""
    # Every line the fold carries, not the last fifteen: the list is a tail now, so what used to be cut to
    # keep the page short is scrolled instead, and the newest is the one it opens on.
    feed = "".join(f"<li>{esc(w)}  {esc(who)}  {esc(kind)}</li>" for w, who, kind in found["feed"])
    # What can be started leads where there is no fleet to lead with, and is the tab bar's business where
    # there is: a harbour with ten streams running is not a page about making an eleventh project, and a
    # card saying twice what the tabs already say is a page repeating itself. The published copy has it
    # nowhere — it is a file on somebody's Pages site, and nothing can be started from there.
    start = starting_points() if controls and not berths else ""
    clearance_fault = (found.get("unreadable") or {}).get("clearance", "")
    unavailable = (f'<div class="card"><h2>Waiting counts unavailable</h2>'
                   f'<p class="empty">{esc(clearance_fault)}</p></div>') if clearance_fault else ""
    landed = fitting_card(made) if made and controls else ""
    # The published copy is a file on somebody's Pages site and is a view of nothing it could move to.
    at = looking(root) if controls and root else ""
    body = f"""{landed}{at}{start}{unavailable}
<div class="card"><h2>Waiting on you</h2>{inbox_rows(waiting, controls)}</div>
{answer_boxes(berths) if controls else ""}
<div class="card"><h2>Streams</h2>{berth_rows(berths, found.get("streams") or {})}</div>
<div class="card"><h2>Speed</h2>{dial(str(pressure["position"]), controls)}{banked}</div>
{tune(config, controls)}
<div class="card"><h2>Last lines</h2><ul class="feed" data-tail>{feed or "<li>nothing yet</li>"}</ul></div>"""
    # The published copy is one file and has no other tab to reach, so it gets no bar.
    return document(title, sub, body, SCRIPT if controls else "", now="/" if controls else "")


def read_only(found: dict, config: dict, title: str = "Bridge") -> str:
    """The published copy: the same page with nothing to press, which is what Pages serves."""
    return page(found, config, controls=False, title=title)


def payload(found: dict) -> str:
    """The board as JSON, for anything that would rather read it than look at it."""
    return json.dumps(found, indent=2, ensure_ascii=False, default=str)

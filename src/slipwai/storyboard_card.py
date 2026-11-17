"""The storyboard on the Voyage's Screens tab: the drawing, what it found, a verdict, and a conversation about it.

The surfaces stage ran eight minutes headless on the first real run and nobody looking at the Screens tab
could tell; the card appeared when it was done. It had reviewed seven pages and written eighty-four findings
and a list of questions, and the person's two moves were to approve all forty-nine states or redraw them
all. So the tab now says a stage is drawing while it draws — a card in the storyboard's place with what it
is doing and for how long, and a mark on the tab — and once it is drawn the findings are under it, Blockers
first, each a way into a conversation with the session that drew it.

**Talking never approves.** The conversation resumes the stage's kept session, which already holds the
research and the review; it may change a page when asked, and a page it changes loses its verdict
(`drawn.withdraw`). Approve and Disapprove are the only verdicts there are, and stay buttons.
"""
from __future__ import annotations

# budget: 380 — the storyboard's card, its verdict, what the drawing found and the conversation about it are
# one band of one tab, drawn by one script; split, each half would read the stage's live state its own way.
from pathlib import Path
from typing import Any

from . import stage_talk
from .drawn import decided_states, withdrawn
from .init_run import outside_session, resumed
from .page_shell import esc
from .passage import surface_pages
from .review_reading import RESEARCH, REVIEW, reading
from .stage_session import kept_stage
from .upstream import advancing, stopped

#: The stages whose result has a tab of its own, by the step the board's run is on and the command it runs.
WATCHED = {"surfaces": "mockups", "model": "model"}
SAYS = {"surfaces": ("Storyboard", "Being drawn: the research, the surfaces and the storyboard. The storyboard "
                                   "appears here when the drawing ends, and is listed under Waiting on you."),
        "model": ("The model", "Being modelled from the approved storyboard. The model appears here when the "
                               "stage ends.")}

STYLE = """
.stage-running h2{display:flex;gap:10px;align-items:center}
.stage-running .doing{font-family:var(--mono);font-size:.8rem;color:var(--ink-2);margin:6px 0 0;overflow-wrap:anywhere}
.tabs .count.running{background:var(--teal-soft);color:var(--teal);animation:breathe 1.7s ease-in-out infinite}
details.findings{margin-top:12px;border-top:1px solid var(--rule-2);padding-top:10px}
details.findings summary{cursor:pointer;font-size:.9rem}
details.findings h3{font-size:.82rem;font-weight:500;color:var(--ink-3);margin:12px 0 6px}
details.findings ul{margin:0;padding-left:18px;display:grid;gap:6px;font-size:.86rem}
details.findings .where{font-size:.74rem;color:var(--ink-3);margin-right:6px}
details.findings li button{margin-left:8px;font-size:.76rem;padding:2px 8px}
.verdict-gone{color:var(--brass)}
#storyboard-talk .log{max-height:min(28rem,55vh);min-height:3rem;overflow:auto;display:grid;gap:8px;
  align-content:start;padding:2px 2px 10px}
#storyboard-talk .turn{max-width:min(46rem,92%);padding:8px 12px;border-radius:10px;border:1px solid var(--rule);
  white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.45;font-size:.9rem}
#storyboard-talk .turn.person{justify-self:end;background:var(--teal);border-color:var(--teal);color:#fff}
#storyboard-talk .turn.person.queued{background:var(--paper);color:var(--teal);border-style:dashed}
#storyboard-talk .turn.person.queued::after{content:" · queued: said when its turn ends";font-size:.76rem}
#storyboard-talk .turn.agent{justify-self:start;background:var(--paper)}
#storyboard-talk .turn.error{justify-self:start;border-color:var(--brass);color:var(--brass)}
p.held{border-left:3px solid var(--brass);padding-left:10px;color:var(--ink-2);font-size:.88rem}
"""

SCRIPT = """
// The stages whose result has a tab: while one runs, its tab label is marked and a card in its result's place
// says what it is doing and for how long. Polled from the stage's own state; the page's shape reloads it
// when the stage starts and ends, so the card that replaces this one arrives by itself.
(function(){
  const clock = s => Math.floor(s / 60) + ':' + String(Math.floor(s % 60)).padStart(2, '0');
  document.querySelectorAll('[data-stage-watch]').forEach(card => {
    const command = card.dataset.stageWatch, chip = card.querySelector('[data-clock]');
    let seconds = Number(chip.dataset.seconds || 0), running = true;
    setInterval(() => { if (running) { seconds += 1; chip.textContent = 'running · ' + clock(seconds); } }, 1000);
    const poll = async () => {
      let said;
      try { said = await (await fetch('/stage/talk.json?command=' + command + '&since=999999')).json(); }
      catch (fault) { setTimeout(poll, 8000); return; }
      running = said.running; seconds = said.seconds || seconds;
      if (said.doing) card.querySelector('[data-doing]').textContent = said.doing;
      if (!running) chip.textContent = 'ended · putting it on the page';
      document.querySelectorAll('[data-stage-marker="' + command + '"]').forEach(one => { one.hidden = !running; });
      setTimeout(poll, running ? 2000 : 6000);
    };
    poll();
  });
})();
// The conversation with the session that drew the storyboard: the turns live, what it is doing and for how
// long, Stop, and Carry on where the board waits on the person's word. What the person types while the
// stage runs is queued, shown as queued, and said when its turn ends. Everything drawn as text, never markup.
(function(){
  const card = document.getElementById('storyboard-talk');
  const fitting = document.getElementById('fitting');
  if (!card && !fitting) return;
  const command = card ? card.dataset.command : '';
  const post = (where, body) => fetch(where, {method: 'POST', headers: {'Content-Type': 'application/json'},
                                               body: JSON.stringify(body)});
  // The stage card says why the board is not moving on by itself, with its Carry on, as this card does.
  let fittingHeld = null, fittingCarry = null;
  if (fitting) {
    fittingHeld = document.createElement('p'); fittingHeld.className = 'held'; fittingHeld.hidden = true;
    fittingCarry = document.createElement('button'); fittingCarry.type = 'button'; fittingCarry.className = 'install';
    fittingCarry.textContent = 'Carry on'; fittingCarry.hidden = true;
    // The card's own row of buttons, a child of the card: the reply form inside it is an `.ask` as well.
    const row = fitting.querySelector(':scope > .ask');
    if (row) { fitting.insertBefore(fittingHeld, row); row.appendChild(fittingCarry); }
    else { fitting.append(fittingHeld, fittingCarry); }
  }
  const log = card && card.querySelector('.log'), input = card && card.querySelector('input');
  const go = card && card.querySelector('button.go'), stop = card && card.querySelector('button.stop');
  const held = card && card.querySelector('p.held'), carry = card && card.querySelector('[data-carry-on]');
  let at = 0, busy = false, timer = null, wrote = false;
  const reply = (id, body) => post('/stage/answer', {id, ...body});
  const draw = turn => {
    if (turn.role === 'person') {
      const one = document.createElement('div');
      one.className = 'turn person' + (turn.queued ? ' queued' : ''); one.dataset.talk = turn.id || '';
      one.textContent = turn.text; log.appendChild(one); return;
    }
    // True where a call that changed a file has finished: the storyboard's frames are drawn again after the turn.
    if (drawTurn(log, turn, reply)) wrote = true;  // the console's, which every Voyage window carries
  };
  const frames = () => document.querySelectorAll('#mockups iframe').forEach(one => { one.src = one.src; });
  const poll = async () => {
    let said;
    try { said = await (await fetch('/stage/talk.json?command=' + command + '&since=' + at)).json(); }
    catch (fault) { clearTimeout(timer); timer = setTimeout(poll, 8000); return; }
    for (const [words, button] of [[held, carry], [fittingHeld, fittingCarry]]) {
      if (!words) continue;
      words.textContent = said.held || ''; words.hidden = !said.held; button.hidden = !said.carry;
    }
    if (log) {
      const end = log.scrollTop + log.clientHeight >= log.scrollHeight - 24;
      said.turns.forEach(draw);
      at = said.at;
      log.querySelectorAll('.turn.person.queued').forEach(one => {
        if (!said.queued_ids.includes(one.dataset.talk)) one.classList.remove('queued'); });
      const was = busy; busy = said.busy;
      drawWaiting(log, busy, said.thinking, said.doing, said.for);
      if (said.turns.length && end) log.scrollTop = log.scrollHeight;
      if (was && !busy && wrote) { frames(); wrote = false; }
      go.textContent = busy || said.running ? 'Queue it' : 'Say';
      stop.hidden = !busy;
    }
    clearTimeout(timer);
    timer = setTimeout(poll, busy || (said && said.running) ? 900 : 4000);
  };
  if (card) {
    card.querySelector('form').addEventListener('submit', async event => {
      event.preventDefault();
      const text = input.value.trim();
      if (!text) return;
      const answer = await post('/stage/say', {command, message: text});
      if (!answer.ok) { draw({role: 'agent', kind: 'error', text: await answer.text()}); return; }
      input.value = ''; input.defaultValue = ''; poll();
      log.scrollTop = log.scrollHeight;
    });
    stop.addEventListener('click', () => post('/stage/cancel', {}));
    // A finding or a question opens the conversation on it, its words in the box and nothing sent.
    document.addEventListener('click', event => {
      const about = event.target.closest('[data-talk-about]');
      if (!about) return;
      input.value = about.dataset.talkAbout;
      card.scrollIntoView({block: 'start'}); input.focus();
    });
  }
  document.addEventListener('click', async event => {
    if (!event.target.closest('[data-carry-on]') && event.target !== fittingCarry) return;
    event.target.disabled = true;
    await post('/stage/carry-on', {});
    event.target.disabled = false; poll();
  });
  poll();
})();
"""


def live(board: Any) -> dict[str, Any]:
    """Which stage with a tab of its own is running now — `surfaces`, `model` or nothing — for how long, what
    it is doing, and whether the storyboard has a session a conversation can carry on. A turn of
    conversation is not the stage running: it is the person, talking."""
    fitting = board.fitting
    said = fitting.said(max(fitting.said()["at"] - 1, 0)) if fitting is not None else None
    stage = getattr(fitting, "stage", None)
    running, seconds, doing = "", 0.0, ""
    if said is not None and not said["done"]:
        if not said.get("talking") and said["step"] in WATCHED:
            running, seconds = said["step"], float(said["seconds"])
            doing = (stage.doing() if stage is not None else "") or (said["lines"] or [""])[-1]
    elif (outside := outside_session(board.root)) is not None and outside["step"] in WATCHED:
        running, seconds, doing = outside["step"], float(outside["seconds"]), outside["lines"][0]
    mine = stage is not None and stage.command == "mockups"
    return {"running": running, "seconds": seconds, "doing": doing,
            "talk": mine or stage_talk.kept(board.root, "mockups")}


def payload(board: Any, command: str, since: int) -> dict[str, Any]:
    """`/stage/talk.json`: the conversation with `command`'s stage after `since`, and its live state."""
    root = board.root
    turns = stage_talk.turns(root, command) if command else []
    shown = turns[since:] if since else turns[-stage_talk.SHOWN:]
    fitting = board.fitting
    stage: Any = getattr(fitting, "stage", None)
    said = fitting.said(10 ** 9) if fitting is not None else {}
    # A turn of this stage's conversation under way: the person's, so what it is doing is said in the log.
    busy = bool(stage is not None and stage.command == command and not said.get("done", True)
                and said.get("talking"))
    now = live(board)
    why, _ = stopped(root)
    return {"turns": shown, "at": len(turns), "busy": busy, "running": WATCHED.get(now["running"]) == command,
            "seconds": now["seconds"], "doing": (stage.doing() if busy else now["doing"]) if command else "",
            "for": int(said.get("seconds") or 0) if busy else 0,
            "thinking": bool(busy and stage.agent is not None and stage.agent.thinking),
            "queued_ids": [one.get("id") for one in stage_talk.undelivered(root, command)] if command else [],
            "held": why, "carry": bool(advancing(root) and stage_talk.held(root))}


def talking_to(board: Any, command: str) -> str:
    """The run something said to `command`'s stage goes through — the one the board holds where it is that
    stage's, else that stage's kept session carried on, where nothing else is running — or why there is none.
    With no command, the stage of the board's own run, or the one kept from before a restart."""
    fitting = board.fitting
    command = command or ("" if fitting is not None else kept_stage(board.root))
    if not command or getattr(getattr(fitting, "stage", None), "command", "") == command:
        return ""
    if fitting is not None and not fitting.said()["done"]:
        return f"the {fitting.said()['step'] or 'board'} stage is running; say this to it once it has ended"
    if not stage_talk.kept(board.root, command):
        return f"no session of the {command} stage is kept here, so there is nothing to say that to"
    board.fitting = resumed(board.root, command, fitting.said()["lines"] if fitting is not None else None)
    return ""


def placeholder(step: str, now: dict[str, Any]) -> str:
    """The card in a running stage's result's place: what it is doing, and for how long."""
    title, words = SAYS[step]
    seconds = int(now.get("seconds") or 0)
    return (f'<div class="card stage-running" id="{esc(step)}-running" data-stage-watch="{esc(WATCHED[step])}">'
            f'<h2>{esc(title)} <span class="chip running" data-clock data-seconds="{seconds}">running · '
            f'{seconds // 60}:{seconds % 60:02d}</span></h2><p class="empty">{esc(words)}</p>'
            f'<p class="doing" data-doing>{esc(now.get("doing") or "")}</p></div>')


def marker(step: str, now: dict[str, Any] | None) -> str:
    """The mark on a tab's label while its stage runs."""
    running = bool(now and now.get("running") == step)
    word = "drawing" if step == "surfaces" else "modelling"
    return (f'<span class="count running" data-stage-marker="{esc(WATCHED[step])}"{"" if running else " hidden"}>'
            f"{word}</span>")


def talk_card() -> str:
    """The conversation with the session that drew the storyboard, its turns drawn by the script above."""
    return ('<div class="card" id="storyboard-talk" data-command="mockups"><h2>Talk about the storyboard</h2>'
            '<p class="empty">Ask about a finding, ask to see or change a state, or answer one of its questions: '
            "the session that drew it answers, and writes down what you decide. Talking never approves anything "
            "— Approve and Disapprove are the verdicts — and a page changed here waits on yours again.</p>"
            '<p class="held" hidden></p><div class="log turns" role="log" aria-live="polite"></div>'
            '<form class="ask"><input placeholder="Ask about it, or say what to change…" autocomplete="off" '
            'aria-label="Say something about the storyboard"><button class="go" type="submit">Say</button>'
            '<button class="stop" type="button" hidden>Stop</button>'
            '<button type="button" class="install" data-carry-on hidden>Carry on</button></form></div>')


def findings_html(root: Path, feature: str, base: str) -> str:
    """What the drawing found, collapsed: the review's counts, its Blockers first, then the open questions, each
    a way into the conversation. Where a file's shape is not found, a link to it and nothing else."""
    found = reading(root, feature)
    if not found.review and not found.research:
        return ""
    link = {name: f'<a href="{esc(base)}/{name}" target="_blank" rel="noopener">{name}</a>' for name in (REVIEW,
                                                                                                    RESEARCH)}
    unread = [link[name] for name, read, there in ((REVIEW, found.review_read, found.review),
                                                    (RESEARCH, found.research_read, found.research))
              if there and not read]
    words = {"blocker": "Blocker", "should": "Should-address", "nice": "Nice-to-have"}
    sums = [f"{found.counts[key]} {word}" for key, word in words.items() if found.counts.get(key)]
    if found.review_read and found.review and not sums:
        sums.append("no findings")
    if found.research_read and found.questions:
        sums.append(f"{len(found.questions)} open question{'' if len(found.questions) == 1 else 's'}")
    blockers = "".join(f'<li><span class="where">{esc(one.where)}</span>{esc(one.text)}<button type="button" '
                       f'class="install" data-talk-about="{esc(about(one.where, one.text))}">Ask about this'
                       "</button></li>" for one in found.blockers if found.review_read)
    asked = "".join(f'<li>{esc(one)}<button type="button" class="install" data-talk-about="'
                    f'{esc(f"Answering “{one}”: ")}">Answer this</button></li>'
                    for one in (found.questions if found.research_read else []))
    files = " · ".join(link[name] for name, there in ((REVIEW, found.review), (RESEARCH, found.research)) if there)
    body = ((f"<h3>Blockers</h3><ul>{blockers}</ul>" if blockers else "")
            + (f"<h3>Open questions only you can answer</h3><ul>{asked}</ul>" if asked else "")
            + (f'<p class="empty">Not read here, so open it: {" · ".join(unread)}</p>' if unread else "")
            + f'<p class="empty">{files}</p>')
    return (f'<details class="findings" id="findings-{esc(feature)}"><summary>What the drawing found · '
            f'{esc(" · ".join(sums) or "see the files")}</summary>{body}</details>')


def about(where: str, text: str) -> str:
    return f"About the Blocker{f' on {where}' if where else ''}: “{text}” — "


def verdict_form(root: Path, feature: str) -> str:
    """Approve marks every drawn state approved. Disapprove parks them, and has to say why.

    Only where there is a page per surface to mark: a storyboard with the surfaces drawn inside it has no state
    a verdict can name, and buttons for one were buttons the server refused. That feature is told what is
    missing and what draws it, instead. A verdict a conversation withdrew by changing a page is said by surface,
    and the buttons are back: the storyboard waits on a verdict again.
    """
    home = root / "specs" / feature / "mockups"
    if not surface_pages(home):
        return ('<p class="empty">This storyboard has no page per surface, so there is nothing to approve: '
                "each surface is drawn as its own page, which the storyboard links. Draw the storyboard draws it "
                "again.</p>")
    path = home / "mock-states.md"
    note = "Nothing on this storyboard is approved yet."
    text = path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""
    parked = next((line.split("parked:", 1)[1].strip()
                   for line in text.splitlines() if "— parked:" in line), "")
    gone = withdrawn(root, feature)
    if gone:
        note = ("Changed in the conversation since your verdict, so not approved: " + "; ".join(gone)
                + ". Approve or disapprove the storyboard again.")
    elif parked:
        note = (f"Disapproved: {parked}. It is being drawn again from that, and the new drawing waits on a "
                f"verdict of its own.")
    elif "— approved" in text:
        note = "Approved."
    # Where the pages say who chose each state, the note says how many a person decided and how many the
    # tool put in: the person approving knows which states they have already seen.
    who = [one for page in surface_pages(home) for _, one in decided_states(page)[1]]
    if any(who):
        proposed = sum(one.lower() == "proposed" for one in who)
        note += (f" {len(who)} states: {sum(bool(one) for one in who) - proposed} decided by a person, "
                 f"{proposed} proposed.")
    # Either verdict locks both. A refusal (a disapproval with no reason) turns them back on in the page.
    held = " disabled" if (parked or "— approved" in text) and not gone else ""
    return (f'<form class="verdict" onsubmit="return false"><p class="empty{" verdict-gone" if gone else ""}">'
            f"{esc(note)} Approving marks every drawn state approved. Disapproving draws it again from your "
            f'reason.</p><div class="ask"><input id="why-{esc(feature)}" type="text" maxlength="240" '
            f'placeholder="Why, if you disapprove"{held}>'
            f'<button type="button" class="go" data-storyboard="{esc(feature)}" data-verdict="approved"{held}>'
            f'Approve storyboard</button>'
            f'<button type="button" class="install" data-storyboard="{esc(feature)}" data-verdict="parked"{held}>'
            f"Disapprove</button></div></form>")


def mockups_card(found: list[dict[str, str]], root: Path | None = None) -> str:
    """The storyboard the mock-up stage wrote, where it wrote one — every mock-up is reached from it, which
    is what it is for — else the wireframes themselves, shown small; under each feature's verdict, what the
    drawing found. Nothing where the stage has not run."""
    if not found:
        return ""
    features: list[str] = []
    for row in found:
        if row["feature"] not in features:
            features.append(row["feature"])
    base = {row["feature"]: row["href"].rsplit("/", 1)[0] for row in found}
    forms = "".join(verdict_form(root, feature) + findings_html(root, feature, base[feature])
                    for feature in features) if root is not None else ""
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


def screens_band(root: Path, found: list[dict[str, str]], now: dict[str, Any] | None) -> str:
    """The storyboard's part of the Screens tab: a card saying it is being drawn while it is, the storyboard
    once it is, and the conversation with the session that drew it wherever that session is kept."""
    now = now or {}
    drawing = placeholder("surfaces", now) if now.get("running") == "surfaces" else mockups_card(found, root)
    return drawing + (talk_card() if now.get("talk") else "")

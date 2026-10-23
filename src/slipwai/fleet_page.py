"""The Fleet tab: what is happening, what it needs from you, and when it moves again.

The tab used to open on *Waiting on you* as a list of parks, one per slice, each a paragraph. On the recap
voyage that was eleven paragraphs for three causes, and nothing on the page said which processes were alive
or why two captains had left within a second of being lit. A person restarted the fleet and could not tell
that nothing had happened.

So the tab opens on one sentence — what state the fleet is in and what changes it — with the processes
under it, then what is waiting on a person grouped by what it waits on, each group a checklist with the
ticks the harbourmaster has written and one button. The streams table and the last lines are still here,
further down, because they are what a reader goes to once the sentence has told them where to look.

Everything is a render of `fleet.board`, which is a fold of the logs. Nothing is kept here.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime

from .fleet_record import NOTHING, clock_of
from .page_shell import esc

#: The word on a group for its cause, in the words a person uses rather than the record's.
CAUSES = {"limit": "paused", "host": "on main", "question": "a question", "demo": "demo sent back",
          "gate": "gate not closed", "silence": "went quiet", "exit": "session ended", "ceiling": "to read",
          "trunk": "trunk is red", "budget": "budget spent", "other": "parked"}

STYLE = """
.headline{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:12px 24px;align-items:start}
.headline h2{font-size:1.05rem;margin:0;display:flex;gap:10px;align-items:flex-start;line-height:1.35}
.headline .dot{width:10px;height:10px;border-radius:50%;flex:none;margin-top:7px;background:var(--ink-3)}
.headline.teal .dot{background:var(--teal)}.headline.brass .dot{background:var(--brass)}
.headline.blue .dot{background:#1d4f8f}.headline.red .dot{background:var(--critical)}
.headline p{margin:8px 0 0;color:var(--ink-2);font-size:.9rem}
.headline .acts{display:flex;flex-direction:column;gap:8px;min-width:200px}
.procs{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px;margin-top:14px}
.proc{border:1px solid var(--rule-2);border-radius:8px;padding:10px 12px;background:var(--ground)}
.proc b{display:block;font-size:.86rem;margin-bottom:4px}
.proc .w{font-size:.8rem;color:var(--ink-2);margin-top:6px}
.counts{display:flex;gap:18px;flex-wrap:wrap;font-size:.85rem;color:var(--ink-2);margin-top:12px}
.counts b{color:var(--ink)}
.chip.paused{background:#d6e6f8;color:#1d4f8f}
:root:has(#t-dark:checked) .chip.paused{background:#1b2f4a;color:#9cc3ef}
@media (prefers-color-scheme:dark){:root:has(#t-auto:checked) .chip.paused{background:#1b2f4a;color:#9cc3ef}}
.group{border:1px solid var(--rule);border-radius:10px;padding:14px 16px;margin-top:12px;background:var(--paper)}
.group .head{display:flex;justify-content:space-between;gap:16px;align-items:flex-start;flex-wrap:wrap}
.group h3{font-size:.95rem;font-weight:600;margin:0}
.group .meta{color:var(--ink-3);font-size:.82rem;margin-top:4px}
.group .prog{height:6px;border-radius:3px;background:var(--rule-2);overflow:hidden;margin-top:10px}
.group .prog i{display:block;height:100%;background:var(--teal)}
.needs{list-style:none;padding:0;margin:10px 0 0}
.needs li{display:grid;grid-template-columns:20px minmax(0,1fr) auto;gap:10px;align-items:start;padding:7px 0;
  border-top:1px solid var(--rule-2);font-size:.9rem}
.needs .box{width:16px;height:16px;border:1.5px solid var(--ink-3);border-radius:4px;margin-top:2px}
.needs .box.on{background:var(--teal);border-color:var(--teal);position:relative}
.needs .box.on::after{content:"";position:absolute;left:4px;top:1px;width:5px;height:9px;border:solid #fff;
  border-width:0 2px 2px 0;transform:rotate(45deg)}
.needs .how{font-size:.78rem;color:var(--ink-3);text-align:right;white-space:nowrap}
.needs .how button{font:inherit;font-size:.78rem;padding:3px 10px;border-radius:6px;border:1px solid var(--rule);
  background:var(--paper);color:var(--ink-2);cursor:pointer}
.then{margin-top:10px;padding:8px 10px;border-radius:7px;background:var(--ground);font-size:.85rem;color:var(--ink-2)}
.then b{color:var(--ink)}
.quiet-button{font:inherit;padding:8px 14px;border-radius:7px;border:1px solid var(--rule);background:var(--paper);
  color:var(--ink-2);cursor:pointer;white-space:nowrap}
.quiet-button:hover{border-color:var(--teal);color:var(--ink)}
@media (max-width:720px){.headline{grid-template-columns:1fr}.needs li{grid-template-columns:20px 1fr}
  .needs .how{grid-column:2;text-align:left;white-space:normal}.tl-names{width:90px}}

"""

#: What the page's script does with the two controls this tab adds. One `told` per park in a group, then
#: one reload: the route that writes a `told` is the one the board already has, and a group is several parks.
SCRIPT = """
async function each(path, bodies){
  for (const body of bodies) {
    const answer = await fetch(path, {method:'POST', headers:{'Content-Type':'application/json'},
                                      body: JSON.stringify(body)});
    if (!answer.ok) { alert(await answer.text()); return; }
  }
  location.reload();
}
document.addEventListener('click', event => {
  const many = event.target.closest('[data-tell-each]');
  if (many) {
    const parks = JSON.parse(many.dataset.tellEach);
    each('/tell', parks.map(park => ({fairway: park.fairway, slice: park.slice, message: many.dataset.message})));
  }
  const tick = event.target.closest('[data-need]');
  if (tick) {
    const parks = JSON.parse(tick.dataset.parks);
    each('/need', parks.map(park => ({fairway: park.fairway, parked: park.t, need: Number(tick.dataset.need)})));
  }
});

"""


def when(stamp: str, now: datetime | None = None) -> str:
    """A log instant as a clock, with the day where it is not today: `17:40`, `17:40 yesterday`, `Mon 17:40`."""
    try:
        at = datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC).astimezone()
    except (ValueError, TypeError):
        return ""
    today = (now or datetime.now(UTC)).astimezone().date()
    days = (today - at.date()).days
    if days == 0:
        return at.strftime("%H:%M")
    if days == 1:
        return at.strftime("%H:%M") + " yesterday"
    if days == -1:
        return at.strftime("%H:%M") + " tomorrow"
    return at.strftime("%a %H:%M")


def in_how_long(until: str, now: datetime | None = None) -> str:
    """`in 3h 35m`, `in 12m`, or `` once it has passed."""
    try:
        at = datetime.strptime(until, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except (ValueError, TypeError):
        return ""
    left = int(((at - (now or datetime.now(UTC))).total_seconds() + 59) // 60)
    if left <= 0:
        return ""
    return f"in {left // 60}h {left % 60:02d}m" if left >= 60 else f"in {left}m"


def first_sentence(text: str, limit: int = 160) -> str:
    """The first sentence of a park's `why`, without the slice's own prefix, cut where a title ends."""
    said = text.strip()
    if ": " in said[:12]:
        said = said.split(": ", 1)[1]
    sentence = said.split(". ")[0].rstrip(".")
    return sentence if len(sentence) <= limit else sentence[:limit - 1].rstrip() + "…"


def needs_title(needs: list[dict[str, str]]) -> str:
    """A group's headline from its needs, where it has them: the first need, and how many more.

    A park's `why` is the paragraph a reader without the board sees, and recap's three host parks each ran
    to 900 characters before they said what they wanted. The needs are the ask itself, so the headline is
    the first of them — `context: catch-up on LB6, LB7, LB8, LB9, LB10 in docs/event-model/model.yaml and 4
    more` names the move where the paragraph's first sentence named the slice's rungs.
    """
    said = [str(need.get("what") or "").strip() for need in needs]
    said = [one for one in said if one]
    if not said:
        return ""
    first = first_sentence(said[0])
    rest = len(said) - 1
    return f"{first} and {rest} more" if rest else first


def plural(count: int, word: str) -> str:
    return f"{count} {word}" if count == 1 else f"{count} {word}s"


def headline(found: dict, now: datetime | None = None) -> tuple[str, str, str]:
    """(the colour, the one sentence, the sentence under it) about the whole fleet."""
    counts = found.get("counts") or {}
    groups = found.get("groups") or []
    inbox = found.get("inbox") or []
    berths = found.get("berths") or []
    running, paused = int(counts.get("running") or 0), int(counts.get("paused") or 0)
    on_you = [g for g in groups if g.get("paused") != "yes"]
    on_you += [row for row in inbox if row.get("kind") in ("told", "question") and row.get("grouped") != "yes"]
    limit = next((g for g in groups if g.get("cause") == "limit"), None)
    slots = counts.get("slots")
    stalled = [row["fairway"] for row in berths if row.get("state") == "stalled"]
    lifts = ""
    if limit is not None:
        lifts = clock_of(str(limit.get("until") or ""))
        wait = in_how_long(str(limit.get("until") or ""), now)
        lifts = f"{lifts}, {wait}" if wait else (f"{lifts}, which has passed; the harbourmaster lifts it on "
                                                  f"its next pass" if lifts else "")
    if not berths:
        return "grey", "Nothing has run yet.", "It writes its first line when you cast off."
    if stalled:
        return ("red", f"Stalled: {', '.join(stalled)} stopped writing without a word.",
                "A captain that is alive but silent looks just like one working hard. Open its log.")
    if running:
        said = f"{plural(running, 'slice')} working" + (f" in {slots} slots" if isinstance(slots, int) else "")
        extra = []
        if on_you:
            extra.append(f"{plural(len(on_you), 'thing')} waiting on you")
        if paused:
            extra.append(f"{plural(paused, 'slice')} paused until {lifts.split(',')[0]}" if lifts else
                         f"{plural(paused, 'slice')} paused")
        return "teal", said + ".", (" · ".join(extra) + "." if extra else "Nothing is waiting on you.")
    if on_you:
        held = sum(len(g.get("slices") or []) for g in groups if g.get("paused") != "yes")
        said = (f"Stopped. {plural(held, 'slice')} wait on you for {plural(len(on_you), 'thing')}." if held
                else f"Stopped. {plural(len(on_you), 'thing')} waiting on you.")
        under = (f"{plural(paused, 'slice')} more are paused until {lifts}." if paused and lifts else
                 "Nothing runs until one of them is answered.")
        return "brass", said, under
    if paused:
        since = when(str(limit.get("t") or ""), now) if limit else ""
        return ("blue", f"Paused. The harness refused the fleet at {since}; it resumes itself at {lifts}.",
                f"{plural(paused, 'slice')} paused, no attempt spent, nothing for you to do. The harbourmaster "
                f"lifts the pause when the time comes and relights the captains.")
    merged = int(counts.get("merged") or 0)
    return ("grey", "Nothing is running and nothing needs you.",
            f"{plural(merged, 'slice')} merged so far. The processes below say what would start things again.")


def live_sub(found: dict) -> str:
    """The short line in the page header: the state in a word, and the numbers that matter."""
    counts = found.get("counts") or {}
    colour, _sentence, _under = headline(found)
    word = {"teal": "working", "brass": "stopped", "blue": "paused", "red": "stalled", "grey": "quiet"}[colour]
    on_you = len([g for g in found.get("groups") or [] if g.get("paused") != "yes"])
    on_you += len([row for row in found.get("inbox") or []
                   if row.get("kind") in ("told", "question") and row.get("grouped") != "yes"])
    bits = [word, f"{on_you} waiting on you"]
    if counts.get("paused"):
        bits.append(f"{counts['paused']} paused")
    slots = counts.get("slots")
    bits.append(f"{counts.get('running', 0)} of {slots} slots" if isinstance(slots, int)
                else f"{counts.get('running', 0)} running")
    return " · ".join(bits)


def process_tiles(found: dict, now: datetime | None = None) -> str:
    rows = found.get("processes") or []
    if not rows:
        return ""
    tiles = []
    for row in rows:
        name = "Harbourmaster" if row["role"] == "harbourmaster" else f"{row['fairway']} captain"
        at = when(str(row.get("since") or ""), now)
        if row["state"] == "running":
            chip = f'<span class="chip running">running{" since " + at if at else ""}</span>'
        elif row["state"] == "exited":
            chip = f'<span class="chip">exited{" " + at if at else ""}</span>'
        else:
            chip = '<span class="chip">not lit</span>'
        said = row.get("why") or ""
        starts = row.get("starts_when") or ""
        text = esc(said) + (f"<br>Starts again when {esc(starts)}." if starts else "")
        tiles.append(f'<div class="proc"><b>{esc(name)}</b>{chip}<div class="w">{text}</div></div>')
    return f'<div class="procs">{"".join(tiles)}</div>'


def counts_line(found: dict) -> str:
    counts = found.get("counts") or {}
    slots = counts.get("slots")
    said = [f"<span><b>{esc(counts.get('running', 0))}</b> of {esc(slots)} slots in use" if isinstance(slots, int)
            else f"<span><b>{esc(counts.get('running', 0))}</b> running"]
    said += [f"<span><b>{esc(counts.get(key, 0))}</b> {label}" for key, label in
             (("queued", "waiting for a slot"), ("paused", "paused"), ("parked", "parked on you"),
              ("questions", "open questions"), ("merged", "merged"))]
    return f'<div class="counts">{"</span>".join(said)}</span></div>'


def headline_card(found: dict, controls: bool, now: datetime | None = None) -> str:
    colour, sentence, under = headline(found, now)
    limit = next((g for g in found.get("groups") or [] if g.get("cause") == "limit"), None)
    acts = ""
    if controls and limit is not None:
        parks = json.dumps(limit.get("parks") or [])
        acts = (f'<div class="acts"><button type="button" class="quiet-button" data-tell-each=\'{esc(parks)}\' '
                f'data-message="resume now">Try the {len(limit.get("slices") or [])} paused slices now anyway</button>'
                f'<span class="empty" style="text-align:center">Before then the harness will just say no again'
                f"</span></div>")
    return (f'<div class="card headline {esc(colour)}"><div><h2><span class="dot"></span><span>{esc(sentence)}'
            f"</span></h2><p>{esc(under)}</p>{process_tiles(found, now)}{counts_line(found)}</div>{acts}</div>")


def group_card(group: dict, controls: bool, now: datetime | None = None) -> str:
    """One thing waiting on a person: its cause, the slices on it, its needs with their ticks, and the
    button that answers it."""
    cause = str(group.get("cause") or "other")
    slices = group.get("slices") or []
    needs = group.get("needs") or []
    parks = json.dumps(group.get("parks") or [])
    title = needs_title(needs) or first_sentence(str(group.get("what") or "")) or CAUSES.get(cause, cause)
    met = sum(1 for need in needs if need.get("met") == "yes")
    meta = [f"holds {', '.join(slices)}" if len(slices) > 1 else slices[0] if slices else "",
            f"since {when(str(group.get('t') or ''), now)}"]
    if needs:
        meta.append(f"{met} of {len(needs)} done")
    buttons = ""
    if controls and group.get("source") != "told":
        # A hand-back's needs are met by trunk or ticked one by one; nothing a person says carries it on.
        label = "I have landed it, carry on" if cause == "host" else "Sorted, carry on"
        buttons = (f'<button type="button" class="go" data-tell-each=\'{esc(parks)}\' '
                   f'data-message="{esc(label.lower())}: {esc(title)}">{esc(label)}</button>')
    items = []
    for need in needs:
        index = str(need.get("index", ""))
        on = need.get("met") == "yes"
        how = esc(need.get("how") or "")
        if not on and need.get("by") == "person" and controls:
            how = f'<button type="button" data-need="{esc(index)}" data-parks=\'{esc(parks)}\'>Done</button>'
        elif not on and need.get("by") == "person":
            how = "only you can say"
        elif on:
            how = "done"
        else:
            how = f"ticks itself when {how}" if how else "ticks itself"
        items.append(f'<li><span class="box{" on" if on else ""}"></span><span>{esc(need.get("what", ""))}</span>'
                     f'<span class="how">{how}</span></li>')
    listed = f'<ul class="needs">{"".join(items)}</ul>' if items else ""
    bar = (f'<div class="prog"><i style="width:{int(100 * met / len(needs))}%"></i></div>' if needs else "")
    then = f'<div class="then"><b>Then, on its own:</b> {esc(group["then"])}</div>' if group.get("then") else ""
    # The drawer is the park's own slice's story — its lines, no heartbeats — and the park as the captain
    # wrote it, whole. The group's headline is the first sentence; this is the rest.
    log = "".join(f'<li><span class="when">{esc(at)}</span> {esc(what)}</li>' for at, what in group.get("lines") or [])
    whole = (f'<details class="log"><summary>{esc(slices[-1] if slices else "Its")}&#8217;s own lines, and the park '
             f'in full</summary><ol class="lines" data-tail>{log or "<li>nothing said yet</li>"}'
             f'</ol><p class="empty" style="white-space:pre-wrap">{esc(group.get("what") or "")}</p></details>')
    chip = "a slice needs this on trunk" if group.get("source") == "told" else CAUSES.get(cause, cause)
    return (f'<div class="group"><div class="head"><div><h3><span class="chip" data-state="waiting on you">'
            f'{esc(chip)}</span> {esc(title)}</h3><div class="meta">'
            f'{esc(" · ".join(bit for bit in meta if bit))}</div></div>{buttons}</div>{bar}{listed}{then}{whole}</div>')


def waiting_card(found: dict, controls: bool, rows_html: str, now: datetime | None = None) -> str:
    """What waits on a person: the groups first, then the messages, questions and decisions the board
    already listed one by one (`rows_html`), then a word on questions where none is open."""
    groups = [g for g in found.get("groups") or [] if g.get("paused") != "yes"]
    cards = "".join(group_card(group, controls, now) for group in groups)
    counts = found.get("counts") or {}
    questions = int(counts.get("questions") or 0)
    none = ('<p class="empty">No slice has stopped to ask you anything.</p>'
            if not questions and not groups and not rows_html.strip() else "")
    body = cards + rows_html + none or '<p class="empty">Nothing.</p>'
    return f'<div class="card" id="waiting"><h2>Waiting on you</h2>{body}</div>'


def parks_table(found: dict, now: datetime | None = None) -> str:
    rows = [row for row in found.get("inbox") or [] if row.get("kind") == "parked"]
    if not rows:
        return ""
    body = ""
    for row in rows:
        lifts = clock_of(str(row.get("until") or ""))
        then = row.get("then") or (f"lifts at {lifts}" if lifts else "")
        body += (f"<tr><td class=\"mono\">{esc(row.get('slice') or row['fairway'])}</td>"
                 f"<td>{esc(when(row['t'], now))}</td><td>{esc(CAUSES.get(str(row.get('cause')), 'parked'))}</td>"
                 f"<td>{esc(first_sentence(str(row.get('what') or '')))}</td><td>{esc(then or NOTHING)}</td></tr>")
    return (f'<div class="card"><h2>Each park, in one line</h2><table><tr><th>Slice</th><th>Parked</th>'
            f"<th>Cause</th><th>Why</th><th>Then</th></tr>{body}</table></div>")


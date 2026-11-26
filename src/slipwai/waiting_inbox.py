"""Waiting on you as an inbox: one compact row per thing, one button that finishes it, in the order attention goes.

manda's list held thirty-eight items, each a card of seven hundred pixels with its why, its numbered steps and
its checklist open, and three of them needed the person. The rest were edits a slice may not make itself,
hand-backs probably landed already, a park an earlier slipwai wrote, and decisions to read — all drawn alike,
so the person read the whole list as work to do by hand and could not find the three.

So each row is a title, one line of why, where it came from, and the button that finishes it; the card it was
is kept under *Details*, for the steps and the box to answer in. The sections are what a person does with them:
**Needs your judgement** (what only they can decide), **The mender tried these** (the trunk mender would
land them and has spent its attempts: *Have the mender try again*), **Needs your hands** (a thing on this
machine, or a need only a person can tick, with why it is theirs), and **Tidy up** (probably done, obsolete,
notes and decisions to read), each section finished in one press. Every button is a list of the board's own
POSTs, so this adds no new way to change anything but `/keep`, which confirms a chart question's
recommendation.

What the mender will do, or what lands with its slice's merge, is not here at all: it waits on nobody, so it
is its own card, **The mender will do these** (`mender_card`). manda's *Waiting on you* held seven things and
one needed the person (#172). Each row leads with the session's plain line, and the agent's own words are under
*Details*; a line written before there was a plain one says the wording is the agent's.
"""
from __future__ import annotations

import json
from typing import Any

from .bridge_page import inbox_rows
from .fleet_page import first_sentence, group_card, needs_title, when
from .page_shell import esc

#: Section key, its heading, what it is for, the bulk button's face, and whether its rows count as needing you.
SECTIONS = (
    ("judgement", "Needs your judgement", "Only you can answer these. Each says what is assumed meanwhile.", "", True),
    ("harness", "The mender tried these",
     "Edits a slice may not make itself. The trunk mender would make them, and has spent its attempts: each says "
     "what stopped it.", "Have the mender try all again", False),
    ("hands", "Needs your hands", "Something on this machine, or a need only a person can tick.", "", True),
    ("tidy", "Tidy up", "Nothing waits on these. Clear them so the real ones stand out.", "Clear all", False),
)

STYLE = """
.w-head{display:flex;flex-wrap:wrap;gap:8px;margin:4px 0 12px}
.w-count{display:inline-flex;gap:6px;align-items:baseline;padding:6px 12px;border-radius:999px;background:var(--rule-2);
  color:var(--ink-2);font-size:.86rem}
.w-count b{font-size:1rem;color:var(--ink)}
.w-count.you{background:var(--brass-soft);color:var(--brass)}.w-count.you b{color:var(--brass)}
.w-section{display:grid;gap:8px;margin:14px 0}
.w-section>header{display:flex;flex-wrap:wrap;gap:8px 14px;align-items:baseline;justify-content:space-between}
.w-section h3{margin:0;font-size:1rem}.w-section header p{margin:0;color:var(--ink-3);font-size:.84rem;flex:1 1 320px}
.w-row{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:6px 14px;padding:10px 12px;border-radius:10px;
  background:var(--paper);border:1px solid var(--rule)}
.w-text{display:grid;gap:2px;min-width:0}.w-text b{font-size:.95rem;overflow-wrap:anywhere}
.w-text span{color:var(--ink-2);font-size:.86rem}.w-text small{color:var(--ink-3);font-size:.78rem}
.w-act{display:flex;flex-wrap:wrap;gap:6px;align-items:center;justify-content:flex-end}
.w-say{display:flex;gap:6px;flex:1 1 320px;min-width:min(100%,320px)}
.w-say input{flex:1;min-width:0;font:inherit;padding:8px 10px;border:1px solid var(--rule);border-radius:8px;
  background:var(--paper);color:var(--ink)}
.w-row details{grid-column:1/-1}.w-row details>summary{cursor:pointer;color:var(--ink-3);font-size:.8rem}
@media (max-width:640px){.w-row{grid-template-columns:1fr}.w-act{justify-content:flex-start}}
"""

#: One handler for every button here: `data-w-post` is a list of [route, body], posted in order, then one reload.
SCRIPT = """
document.addEventListener('click', async event => {
  const open = event.target.closest('[data-w-open]');
  if (open) { const more = open.closest('.w-row').querySelector('details'); if (more) { more.open = true;
    more.scrollIntoView({block: 'nearest'}); } return; }
  const press = event.target.closest('[data-w-post]');
  if (!press) return;
  press.disabled = true;
  const scope = press.dataset.wBulk ? document.getElementById(press.dataset.wBulk) : null;
  const calls = scope ? [...scope.querySelectorAll('[data-w-post]:not([data-w-bulk])')]
                          .filter(one => one.dataset.wPrimary === 'yes').flatMap(one => JSON.parse(one.dataset.wPost))
                      : JSON.parse(press.dataset.wPost);
  for (const [path, body] of calls) {
    const answer = await fetch(path, {method: 'POST', headers: {'Content-Type': 'application/json'},
                                      body: JSON.stringify(body)});
    if (!answer.ok) { press.disabled = false; alert(await answer.text()); return; }
  }
  location.reload();
});
"""


def button(face: str, calls: list[tuple[str, dict]], primary: bool = True) -> str:
    """A button that posts `calls` in order; the primary one is what the section's bulk button presses for it."""
    shape = "go" if primary else "install"
    return (f'<button type="button" class="{shape}" data-w-primary="{"yes" if primary else ""}" '
            f"data-w-post='{esc(json.dumps(calls))}'>{esc(face)}</button>")


def answer_box(fairway: str, slice_id: str, of: str, question: str = "", primary: bool = True) -> str:
    """The box a question or a park is answered in, in the row itself: the bridge's own `data-tell` handler
    sends it (`/tell`), to the slice that asked, carrying what it answers. *Answer* used to open the row's
    Details, whose question was folded again inside, so a person pressed it and saw nothing happen."""
    box = "w-say-" + "".join(ch if ch.isalnum() else "-" for ch in f"{fairway}-{slice_id}-{of or question}")
    asks = f' data-question="{esc(question)}"' if question else ""
    return (f'<span class="w-say"><input id="{esc(box)}" placeholder="Type an answer…" aria-label="Type an answer">'
            f'<button type="button" class="{"go" if primary else "install"}" data-tell="{esc(fairway)}" '
            f'data-box="{esc(box)}"{asks} data-slice="{esc(slice_id)}" data-of="{esc(of)}">Send</button></span>')


def opener(face: str, primary: bool = True) -> str:
    return f'<button type="button" class="{"go" if primary else "install"}" data-w-open>{esc(face)}</button>'


def ticks(group: dict) -> list[tuple[str, dict]]:
    """Every unmet need of every park in a group, ticked: what *Mark done* and *Confirm* post."""
    return [("/need", {"fairway": park["fairway"], "parked": park["t"], "need": int(need.get("index", i))})
            for park in group.get("parks") or [] for i, need in enumerate(group.get("needs") or [])
            if need.get("met") != "yes"]


#: Said under a row whose needs carry no plain line: written before there was one, in the agent's words.
OWN_WORDS = "In the agent's own words: the session that raised it wrote no plain line."


def group_row(group: dict, controls: bool, answers: str = "") -> tuple[str, dict[str, Any]]:
    """Which section a park or hand-back goes in, and its row; `answers` is the box a hand-back is answered in."""
    needs = group.get("needs") or []
    action = group.get("action") or {}
    kind = str(action.get("kind") or "")
    parks = group.get("parks") or []
    title = first_sentence(needs_title(needs) or str(group.get("plain") or group.get("what") or ""), 110) or "A park"
    met = sum(1 for need in needs if need.get("met") == "yes")
    meta = " · ".join(bit for bit in (", ".join(dict.fromkeys(group.get("slices") or [])), f"since {when(group['t'])}",
                                      f"{met} of {len(needs)} done" if needs else "") if bit)
    unmet = [need for need in needs if need.get("met") != "yes"]
    # Why it is the person's, where a need says (`need_who`), before the steps' first sentence.
    whose = next((str(need["whose"]) for need in unmet if need.get("whose")), "")
    own = OWN_WORDS if unmet and not any(need.get("plain") for need in unmet) else ""
    row = {"title": title, "detail": first_sentence(whose or str(action.get("why") or ""), 160), "meta": meta,
           "more": group_card(group, controls) + answers, "buttons": "", "own": own}
    if group.get("obsolete"):
        row["buttons"] = button("Dismiss", [("/dismiss", {"fairway": park["fairway"], "told": park["t"]})
                                            for park in parks])
        return "tidy", row
    if group.get("probably"):
        row["buttons"] = button("Confirm it landed", ticks(group))
        return "tidy", row
    if group.get("acts") == "fleet":
        return "mender", row
    if group.get("source") == "told":
        if any(need.get("who") == "spent" for need in unmet):
            # Only where the mender would take it and has spent its attempts: anywhere else `mend-again` is a
            # line nothing reads, and the button did nothing on five of manda's seven cards (#172).
            row["buttons"] = (button("Have the mender try again",
                                     [("/mend-again", {"fairway": park["fairway"], "parked": park["t"]})
                                      for park in parks])
                              + button("Mark done", ticks(group), primary=False))
            return "harness", row
        row["buttons"] = opener("Show what to do") + button("Mark done", ticks(group), primary=False)
        return "hands", row
    if kind == "machine":
        row["buttons"] = opener("Show what to do")
        return "hands", row
    if kind in ("ceiling", "decisions"):
        row["buttons"] = opener("Read them")
        return "tidy", row
    newest = max(parks or [{}], key=lambda park: str(park.get("t", "")))
    row["buttons"] = answer_box(str(newest.get("fairway") or ""), str(newest.get("aim") or newest.get("slice") or ""),
                                str(newest.get("key") or ""))
    return "judgement", row


def inbox_row(row: dict, controls: bool, streams: dict | None) -> tuple[str, dict[str, Any]] | None:
    """A question, a note, the unread decisions or an unreadable log, as a row."""
    kind = row.get("kind")
    more = inbox_rows([row], controls, streams)
    text = str(row.get("asked") or row.get("what") or "")
    # A question's title is the question: what is taken meanwhile is said under it, not run on after it.
    said = first_sentence(text[:text.index("?") + 1] if kind == "question" and "?" in text else text, 110)
    meta = " · ".join(bit for bit in (str(row.get("slice") or row.get("fairway") or ""),
                                      f"since {when(str(row.get('t') or ''))}" if row.get("t") else "") if bit)
    found = {"title": said, "detail": "", "meta": meta, "more": more, "buttons": "", "own": ""}
    if kind == "question" and row.get("slice") != "chart":
        # Its plain line first, where the session wrote one; the question as asked stays under Details.
        found["title"] = first_sentence(str(row["plain"]), 160) if row.get("plain") else said
        found["own"] = "" if row.get("plain") else OWN_WORDS
    if kind == "question":
        if row.get("slice") == "chart":
            found["detail"] = "Nothing waits on this: the chart went ahead on the recommendation it names."
            found["buttons"] = (button("Keep the recommendation", [("/keep", {"fairway": row["fairway"],
                                                                             "id": str(row.get("id") or "")})])
                                + answer_box(str(row["fairway"]), "chart", str(row.get("key") or ""),
                                             str(row.get("id") or ""), primary=False))
            return "judgement", found
        found["buttons"] = answer_box(str(row["fairway"]), str(row.get("aim") or row.get("slice") or ""),
                                      str(row.get("key") or ""), str(row.get("id") or ""))
        return "judgement", found
    if kind == "unreadable":
        found["buttons"] = opener("Repair it")
        return "judgement", found
    if kind == "decisions":
        stamps = [str(one.get("t") if isinstance(one, dict) else one) for one in row.get("decisions") or []]
        found["title"] = f"{len(stamps)} decision(s) in {row.get('fairway')} to read"
        found["detail"] = ("The stream is over its limit of unread decisions and parks until they are read."
                           if row.get("blocking") == "yes" else "Nothing is held up by them yet.")
        found["buttons"] = button("Mark all read", [("/read", {"fairway": row["fairway"], "decisions": stamps})])
        if row.get("blocking") == "yes":
            found["buttons"] += button(f"Raise the limit to {len(stamps)}",
                                       [("/set", {"pairs": [f"decision_ceiling={len(stamps)}"]})], primary=False)
        return "tidy", found
    if kind == "told":
        found["buttons"] = button("Done", [("/dismiss", {"fairway": row["fairway"], "told": row["t"]})])
        return "tidy", found
    return None


def row_html(row: dict[str, Any], controls: bool) -> str:
    return (f'<div class="w-row"><div class="w-text"><b>{esc(row["title"])}</b>'
            + (f'<span>{esc(row["detail"])}</span>' if row["detail"] else "")
            + (f'<small>{esc(row["own"])}</small>' if row.get("own") else "")
            + (f'<small>{esc(row["meta"])}</small>' if row["meta"] else "")
            + f'</div><div class="w-act">{row["buttons"] if controls else ""}</div>'
            + f'<details><summary>Details</summary>{row["more"]}</details></div>')


def placed_rows(fleet: dict[str, Any], controls: bool = True) -> dict[str, list[dict[str, Any]]]:
    """Every row, by the section it goes in, and `mender` for what the fleet does itself."""
    placed: dict[str, list[dict[str, Any]]] = {key: [] for key, *_ in SECTIONS}
    placed["mender"] = []
    # A hand-back is answered as a park is, from the box its own row carried: kept under its group's Details.
    handed = {(one["fairway"], one["t"]): one for one in fleet.get("inbox") or []
              if one.get("kind") == "told" and one.get("needs")}
    for group in fleet.get("groups") or []:
        if group.get("paused") == "yes":
            continue
        mine = [handed[at] for park in group.get("parks") or [] if (at := (park["fairway"], park["t"])) in handed]
        where, row = group_row(group, controls, inbox_rows(mine, controls, fleet.get("streams")) if mine else "")
        placed[where].append(row)
    for one in fleet.get("inbox") or []:
        if one.get("kind") == "parked" or (one.get("kind") == "told" and one.get("needs")):
            continue  # drawn from its group above
        found = inbox_row(one, controls, fleet.get("streams"))
        if found:
            placed[found[0]].append(found[1])
    return placed


def mender_card(fleet: dict[str, Any], controls: bool = True) -> str:
    """What the fleet does itself — the mender lands it, or it lands with its slice's merge — as a card of its
    own beside *Waiting on you* rather than in it, since nothing in it waits on a person; `""` where empty."""
    rows = placed_rows(fleet, controls)["mender"]
    if not rows:
        return ""
    return (f'<div class="card" id="mender-will"><h2>The mender will do these · {len(rows)}</h2><p class="empty">'
            f"Edits a slice may not make itself. The trunk mender makes each on a branch of its own and lands it "
            f"through the full gate, or it lands with its slice's merge. Nothing here waits on you.</p>"
            + "".join(row_html(row, controls) for row in rows) + "</div>")


def inbox(fleet: dict[str, Any], controls: bool = True) -> str:
    """The whole list as sections of rows, with the three counts over it; `""` where nothing waits."""
    placed = placed_rows(fleet, controls)
    placed.pop("mender")
    if not any(placed.values()):
        return '<p class="empty">Nothing is waiting on you.</p>'
    you = sum(len(placed[key]) for key, *_, mine in SECTIONS if mine)
    counts = (f'<div class="w-head"><span class="w-count you"><b>{you}</b> need you</span>'
              f'<span class="w-count"><b>{len(placed["harness"])}</b> the mender tried</span>'
              f'<span class="w-count"><b>{len(placed["tidy"])}</b> to tidy</span></div>')
    said = counts
    for key, title, hint, bulk, _ in SECTIONS:
        rows = placed[key]
        if not rows:
            continue
        press = (f'<button type="button" class="install" data-w-bulk="w-{key}" data-w-post="[]">{esc(bulk)} '
                 f"{len(rows)}</button>" if bulk and controls and len(rows) > 1 else "")
        body = "".join(row_html(row, controls) for row in rows)
        said += (f'<section class="w-section" id="w-{key}"><header><h3>{esc(title)} · {len(rows)}</h3>'
                 f"<p>{esc(hint)}</p>{press}</header>{body}</section>")
    return said

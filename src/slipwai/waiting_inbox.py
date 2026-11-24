"""Waiting on you as an inbox: one compact row per thing, one button that finishes it, in the order attention goes.

manda's list held thirty-eight items, each a card of seven hundred pixels with its why, its numbered steps and
its checklist open, and three of them needed the person. The rest were edits a slice may not make itself,
hand-backs probably landed already, a park an earlier slipwai wrote, and decisions to read — all drawn alike,
so the person read the whole list as work to do by hand and could not find the three.

So each row is a title, one line of why, where it came from, and the button that finishes it; the card it was
is kept under *Details*, for the steps and the box to answer in. The sections are what a person does with them:
**Needs your judgement** (what only they can decide), **The harness can do these** (the trunk mender lands
them: *Land it*), **Needs your hands** (a thing on this machine, or a need only a person can tick), and
**Tidy up** (probably done, obsolete, notes and decisions to read), each section finished in one press. Every
button is a list of the board's own POSTs, so this adds no new way to change anything but `/keep`, which
confirms a chart question's recommendation.
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
    ("harness", "The harness can do these",
     "Edits a slice may not make itself. The trunk mender makes them on a branch of its own, runs the gates and "
     "lands them.", "Land all with the mender", False),
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


def opener(face: str, primary: bool = True) -> str:
    return f'<button type="button" class="{"go" if primary else "install"}" data-w-open>{esc(face)}</button>'


def ticks(group: dict) -> list[tuple[str, dict]]:
    """Every unmet need of every park in a group, ticked: what *Mark done* and *Confirm* post."""
    return [("/need", {"fairway": park["fairway"], "parked": park["t"], "need": int(need.get("index", i))})
            for park in group.get("parks") or [] for i, need in enumerate(group.get("needs") or [])
            if need.get("met") != "yes"]


def group_row(group: dict, controls: bool, answers: str = "") -> tuple[str, dict[str, Any]]:
    """Which section a park or hand-back goes in, and its row; `answers` is the box a hand-back is answered in."""
    needs = group.get("needs") or []
    action = group.get("action") or {}
    kind = str(action.get("kind") or "")
    parks = group.get("parks") or []
    title = first_sentence(needs_title(needs) or str(group.get("what") or ""), 110) or "A park"
    met = sum(1 for need in needs if need.get("met") == "yes")
    meta = " · ".join(bit for bit in (", ".join(dict.fromkeys(group.get("slices") or [])), f"since {when(group['t'])}",
                                      f"{met} of {len(needs)} done" if needs else "") if bit)
    row = {"title": title, "detail": first_sentence(str(action.get("why") or ""), 160), "meta": meta,
           "more": group_card(group, controls) + answers, "buttons": ""}
    unmet = [need for need in needs if need.get("met") != "yes"]
    if group.get("obsolete"):
        row["buttons"] = button("Dismiss", [("/dismiss", {"fairway": park["fairway"], "told": park["t"]})
                                            for park in parks])
        return "tidy", row
    if group.get("probably"):
        row["buttons"] = button("Confirm it landed", ticks(group))
        return "tidy", row
    if group.get("source") == "told":
        if any(need.get("by") != "person" for need in unmet):
            row["buttons"] = (button("Land it", [("/mend-again", {"fairway": park["fairway"], "parked": park["t"]})
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
    row["buttons"] = opener("Answer")
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
    found = {"title": said, "detail": "", "meta": meta, "more": more, "buttons": ""}
    if kind == "question":
        if row.get("slice") == "chart":
            found["detail"] = "Nothing waits on this: the chart went ahead on the recommendation it names."
            found["buttons"] = (button("Keep the recommendation", [("/keep", {"fairway": row["fairway"],
                                                                             "id": str(row.get("id") or "")})])
                                + opener("Change it…", primary=False))
            return "judgement", found
        found["buttons"] = opener("Answer")
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


def inbox(fleet: dict[str, Any], controls: bool = True) -> str:
    """The whole list as sections of rows, with the three counts over it; `""` where nothing waits."""
    placed: dict[str, list[dict[str, Any]]] = {key: [] for key, *_ in SECTIONS}
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
    if not any(placed.values()):
        return '<p class="empty">Nothing is waiting on you.</p>'
    you = sum(len(placed[key]) for key, *_, mine in SECTIONS if mine)
    counts = (f'<div class="w-head"><span class="w-count you"><b>{you}</b> need you</span>'
              f'<span class="w-count"><b>{len(placed["harness"])}</b> the harness can do</span>'
              f'<span class="w-count"><b>{len(placed["tidy"])}</b> to tidy</span></div>')
    said = counts
    for key, title, hint, bulk, _ in SECTIONS:
        rows = placed[key]
        if not rows:
            continue
        press = (f'<button type="button" class="install" data-w-bulk="w-{key}" data-w-post="[]">{esc(bulk)} '
                 f"{len(rows)}</button>" if bulk and controls and len(rows) > 1 else "")
        body = "".join(f'<div class="w-row"><div class="w-text"><b>{esc(row["title"])}</b>'
                       + (f'<span>{esc(row["detail"])}</span>' if row["detail"] else "")
                       + (f'<small>{esc(row["meta"])}</small>' if row["meta"] else "")
                       + f'</div><div class="w-act">{row["buttons"] if controls else ""}</div>'
                       + f'<details><summary>Details</summary>{row["more"]}</details></div>' for row in rows)
        said += (f'<section class="w-section" id="w-{key}"><header><h3>{esc(title)} · {len(rows)}</h3>'
                 f"<p>{esc(hint)}</p>{press}</header>{body}</section>")
    return said

"""One slice's card on the Voyage tab: closed, where it stands on the ladder; opened, how it got there.

The card said a chip and, behind a click, the board's own facts — a clearance word, a raw timestamp, the
names of the files on its branch. `Implementing · 11/15` read as nearly done with a demo, a review and a
merge still ahead of it, and the line under it was whatever command the agent ran a second ago. So closed, a
card in flight is the six steps with the one it is on, how long it has been on it, what comes after, and
the task in hand; opened, each step with when it began and how long it took, the last few things its log
says under the step it is on, and its conversation (`talk_card`): the last word, a quick send and the door to
its window. What a person is asked, and the box that answers it, are unchanged.

**Drawn whole and swapped whole.** The columns are a band of `/live.json`, repainted every few seconds, so
nothing here is kept in the page: a card is what its row says now. The poll puts back which cards were open.

**Compact** is the same slices a line each — the ones in flight, waiting first — for a person who wants the
whole fleet on one screen. A line opens its card, so the card stays the one place a slice is read at length.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .activity import caption, minutes, newest, now_stamp
from .example_map_page import card_html
from .feedback_card import opener
from .page_shell import esc
from .slice_rungs import AHEAD, COUNTED, instant
from .talk_card import card_html as talk_html
from .talk_card import fields as talk_fields
from .talk_card import held, held_html, marker_html
from .talk_marks import placed_html

#: The steps a chip word says no more than: `Implementing` on Build is Build.
PLAIN = {"Example mapping", "Starting", "Planning", "Implementing", "Demo", "Review", "Merging"}
IN_FLIGHT = ("working", "queued", "waiting")
SAID = {"done": "done", "now": "now"}

STYLE = """
.slice .rungs{display:flex;gap:3px;width:100%}
.slice .rung{flex:1;height:6px;border-radius:3px;background:var(--rule);overflow:hidden}
.slice .rung.done{background:var(--teal)}.slice .rung.now{background:var(--brass)}
.slice .rung.now.part{background:var(--brass-soft);box-shadow:inset 0 0 0 1px var(--brass)}
.slice .rung i{display:block;height:100%;background:var(--brass)}
.slice .where{display:flex;flex-wrap:wrap;justify-content:space-between;gap:2px 8px;width:100%;font-size:.74rem;
  color:var(--ink-3)}
.slice .where b{color:var(--brass);font-weight:500;font-size:.74rem}
.slice .for{font-size:.72rem;color:var(--ink-3);margin-left:auto;white-space:nowrap}
.slice .steps{list-style:none;margin:8px 0 0;padding:0;display:grid;gap:8px;font-size:.8rem}
.slice .steps li{display:grid;grid-template-columns:12px minmax(0,1fr) auto;gap:2px 8px;align-items:baseline}
.slice .steps li::before{content:"";width:8px;height:8px;border-radius:50%;border:2px solid var(--rule)}
.slice .steps li.done::before{background:var(--teal);border-color:var(--teal)}
.slice .steps li.now::before{background:var(--brass);border-color:var(--brass)}
.slice .steps li.now{background:var(--brass-soft);border-radius:6px;padding:8px;margin:0 -8px}
.slice .steps li.todo b{font-weight:500;color:var(--ink-2)}
.slice .steps .t{font-size:.74rem;color:var(--ink-3);white-space:nowrap}
.slice .steps small,.slice .steps .more{grid-column:2 / -1;color:var(--ink-2);font-size:.78rem}
.slice .steps li.todo small{color:var(--ink-3)}
.slice .steps .more{display:grid;gap:4px}
.slice .feed3{list-style:none;margin:0;padding:0;font-family:var(--mono);font-size:.72rem;display:grid;gap:2px}
.slice .feed3 li{display:block;overflow-wrap:anywhere}.slice .feed3 li::before{content:none}
.slice .span{font-size:.76rem;color:var(--ink-3);margin:8px 0 0;border-top:1px solid var(--rule-2);padding-top:8px}
.slice .film-ref{display:grid;gap:2px;font-size:.8rem;margin:8px 0 0;padding:8px;border:1px solid var(--rule);
  border-radius:6px}
.slice .film-ref .sub{color:var(--ink-3);font-size:.76rem}
#work .work-head{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;gap:8px 12px}
#work .work-head h2{margin:0}
.views{display:inline-flex;border:1px solid var(--rule);border-radius:7px;overflow:hidden}
.views button{font:inherit;font-size:.82rem;min-height:34px;padding:0 14px;border:0;background:transparent;
  color:var(--ink-2);cursor:pointer}
[data-view="cards"] .views [data-view-pick="cards"],[data-view="compact"] .views [data-view-pick="compact"]{
  background:var(--teal-soft);color:var(--ink);font-weight:500}
#work .compact{display:none;margin-top:10px;overflow-x:auto}
[data-view="compact"] #work .compact{display:block}[data-view="compact"] #work .columns{display:none}
#work .compact a{display:grid;grid-template-columns:minmax(150px,1.4fr) 132px minmax(0,2fr) minmax(90px,auto);
  gap:12px;align-items:center;min-height:44px;padding:0 4px;border-top:1px solid var(--rule-2);color:inherit;
  text-decoration:none;font-size:.86rem;min-width:620px}
#work .compact a:hover{background:var(--ground)}
#work .compact a b{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#work .compact .rungs{display:flex;gap:3px}#work .compact .rung{flex:1;height:6px;border-radius:3px;
  background:var(--rule);overflow:hidden}
#work .compact .rung.done{background:var(--teal)}#work .compact .rung.now{background:var(--brass)}
#work .compact .rung.now.part{background:var(--brass-soft);box-shadow:inset 0 0 0 1px var(--brass)}
#work .compact .rung i{display:block;height:100%;background:var(--brass)}
#work .compact .doing{color:var(--ink-2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#work .compact .state{font-size:.78rem;color:var(--ink-3);text-align:right;white-space:nowrap}
#work .compact a.waiting .state{color:var(--critical)}
"""

def lit(rows: list[dict[str, str]], folds: dict[str, dict], root: Path | None = None,
        films: list[dict] | None = None) -> list[dict[str, str]]:
    """The rows with what only the run's own files say: each working slice's caption and last few lines,
    and, for a slice a capability's film walks, its chapter there — and its conversation's last word."""
    found = []
    talking = talk_fields(root, rows) if root is not None else {}
    for row in rows:
        key, extra = f"{row.get('fairway')}/{row['slice']}", {}
        if row["slice"] in talking:
            extra["talk"] = talking[row["slice"]]
        if key in folds:
            extra["live"] = caption(folds[key], row.get("next", ""))
            if root is not None:
                extra["feed"] = json.dumps(newest(root, row.get("fairway", ""), row["slice"]))
        for film in films or []:
            marks = [one for one in film["chapters"] if one.get("slice") == row["slice"]]
            if marks and film.get("feature") in ("", row.get("feature", "")):
                names = list(dict.fromkeys(one.get("slice") for one in film["chapters"]))
                extra["film"] = json.dumps({"capability": film["title"], "id": film["id"], "at": marks[0]["at"],
                                            "chapter": names.index(row["slice"]) + 1, "of": len(names)})
        found.append({**row, **extra} if extra else row)
    return found


def ladder_of(row: dict[str, str]) -> list[dict]:
    try:
        found = json.loads(row.get("ladder") or "[]")
    except ValueError:
        return []
    return [one for one in found if isinstance(one, dict)] if isinstance(found, list) else []


def clock(at: float) -> str:
    """An instant as the hour and minute on this machine's clock, which is the one a person is reading."""
    if not at:
        return ""
    when = datetime.fromtimestamp(at)
    return when.strftime("%H:%M" if when.date() == datetime.now().date() else "%-d %b %H:%M")


def standing(row: dict[str, str], step: str) -> str:
    """The step the slice is on, with what counts it or what the chip says past the step's own name."""
    stage, tasks = row.get("stage", ""), row.get("tasks", "")
    done, _, of = tasks.partition("/")
    if stage in COUNTED and of:
        return f"{step} · {done} of {of} tasks"
    return step if stage in PLAIN or not stage or stage == step else f"{step} · {stage[:1].lower()}{stage[1:]}"


def cells_html(row: dict[str, str]) -> str:
    """The six segments alone: each step's state, and Build filled as far as its tasks are ticked."""
    steps = ladder_of(row)
    if not steps or row["state"] not in IN_FLIGHT:
        return ""
    done, _, of = row.get("tasks", "").partition("/")
    cells, said = "", []
    for one in steps:
        fill = ""
        if one["state"] == "now" and one["name"] == "Build" and done.isdigit() and of.isdigit() and int(of):
            fill = f'<i style="width:{min(100, round(100 * int(done) / int(of)))}%"></i>'
        cells += f'<span class="rung {esc(one["state"])}{" part" if fill else ""}">{fill}</span>'
        said.append(f'{one["name"]} {SAID.get(one["state"], "to come")}')
    return f'<span class="rungs" role="img" aria-label="{esc(", ".join(said))}">{cells}</span>'


def step_now(row: dict[str, str]) -> str:
    """The step the slice is on, with what counts it: `Build · 11 of 15 tasks`."""
    return standing(row, next((one["name"] for one in ladder_of(row) if one["state"] == "now"), ""))


def rungs_html(row: dict[str, str]) -> str:
    """The strip on a closed card: six segments, the one the slice is on, and what is still to come."""
    cells = cells_html(row)
    if not cells:
        return ""
    ahead = ", ".join(one["name"] for one in ladder_of(row) if one["state"] == "todo")
    then = f"<span>then {esc(ahead)}</span>" if ahead else ""
    return f'{cells}<span class="where"><b>{esc(step_now(row))}</b>{then}</span>'


#: The order Compact lists slices in: the ones a person holds up first.
FIRST = {"waiting": 0, "working": 1, "queued": 2}


def compact_html(rows: list[dict[str, str]]) -> str:
    """Every slice in flight in a line: its name, its six segments, what it is doing, and its time in the
    stage or its chip. Waiting first. A line is a link to the slice's card, which the page opens."""
    lines = ""
    for row in sorted((one for one in rows if one["state"] in IN_FLIGHT), key=lambda one: FIRST[one["state"]]):
        name = f'{row["slice"]} · {row["title"]}' if row.get("title") else row["slice"]
        doing = (str(row.get("park") or row.get("why") or "") if row["state"] == "waiting"
                 else " · ".join(part for part in (step_now(row), row.get("live", "")) if part))
        when = (in_stage(row) if row["state"] == "working" else "") or chip_of(row)
        lines += (f'<a class="{esc(row["state"])}" href="#card-{esc(row["slice"])}" data-open-card="'
                  f'{esc(row["slice"])}"><b>{esc(name)}</b>{cells_html(row) or "<span></span>"}'
                  f'<span class="doing">{esc(doing)}</span><span class="state">{esc(when)}</span></a>')
    return '<div class="compact">' + (lines or '<p class="empty">Nothing in flight.</p>') + "</div>"


def chip_of(row: dict[str, str]) -> str:
    """The word on a closed card: its stage at work, `Queued` and its stage while it waits for a slot, and
    `Waiting on you` where a person holds it. Nothing on a slice still to do or done — the column says it."""
    stage = row.get("chip") or row.get("stage") or ""
    if row["state"] == "waiting":
        return "Waiting on you"
    if row.get("paused"):
        return f"Paused · lifts {row['paused']}"
    if row["state"] == "queued":
        return f"Queued · {stage}" if stage else "Queued"
    return stage if row["state"] == "working" else ""


def in_stage(row: dict[str, str]) -> str:
    """How long the stage its berth has open has been open, or nothing between stages."""
    opened = instant(row.get("since", ""))
    return f"{minutes(now_stamp() - opened)} in stage" if opened else ""


def summary_html(row: dict[str, str]) -> str:
    name = f'{row["slice"]} · {row["title"]}' if row.get("title") else row["slice"]
    strip = rungs_html(row)
    # With the strip drawn the stage is under it, so the chip is only what the strip cannot say.
    chip = chip_of(row) if not strip or row["state"] != "working" else ""
    if strip and row["state"] == "queued" and not row.get("paused"):
        chip = "Queued"
    shown = f'<span class="chip">{esc(chip)}</span>' if chip else ""
    spent = in_stage(row) if row["state"] == "working" else ""
    spent = f'<span class="for">{esc(spent)}</span>' if spent else ""
    cap = f'<span class="live-cap">{esc(row["live"])}</span>' if row.get("live") else ""
    return f"<summary><b>{esc(name)}</b>{shown}{spent}{strip}{cap}{held_html(row)}{marker_html(row)}</summary>"


def now_html(row: dict[str, str]) -> str:
    """Under the step a working slice is on: what it is doing, the last few lines of its log, its window."""
    if row["state"] != "working":
        return ""
    try:
        lines = json.loads(row.get("feed") or "[]")
    except ValueError:
        lines = []
    feed = "".join(f'<li>{esc(str(one.get("t", ""))[11:16])} {esc(str(one.get("kind", "")))} '
                   f'{esc(str(one.get("what", "")))}</li>' for one in lines if isinstance(one, dict))
    doing = f'<span><b>Now:</b> {esc(row["live"])}</span>' if row.get("live") else ""
    # Its window is opened from the conversation's part of the card, below, with the quick send beside it.
    inner = doing + (f'<ul class="feed3">{feed}</ul>' if feed else "")
    return f'<div class="more">{inner}</div>' if inner else ""


def steps_html(row: dict[str, str]) -> str:
    """The opened card of a slice in flight: each step, when it began, how long it took, what it is."""
    steps = ladder_of(row)
    if not steps or row["state"] not in IN_FLIGHT:
        return ""
    items = ""
    for index, one in enumerate(steps):
        took = minutes(one.get("took") or 0) if one.get("took") else ""
        when = " · ".join(part for part in (clock(one.get("began") or 0),
                                            f"{took} so far" if took and one["state"] == "now" else took) if part)
        name = standing(row, one["name"]) if one["state"] == "now" else one["name"]
        under = now_html(row) if one["state"] == "now" else \
            f"<small>{esc(AHEAD[index])}</small>" if one["state"] == "todo" and index < len(AHEAD) else ""
        items += (f'<li class="{esc(one["state"])}"><b>{esc(name)}</b><span class="t">{esc(when)}</span>'
                  f"{under}{card_html(row) if index == 0 else ''}</li>")
    return f'<ol class="steps">{items}</ol>'


def span_html(row: dict[str, str]) -> str:
    """Its stream, and the work the slice has taken so far: its stages' own time, not the clock's, since a
    fleet stopped overnight has not been working on it."""
    parts = [f'Stream {row["fairway"]}'] if row.get("fairway") else []
    worked = sum(float(one.get("took") or 0) for one in ladder_of(row))
    if row["state"] in IN_FLIGHT and worked:
        parts.append(f"{minutes(worked)} of work on this slice so far")
    merged = instant(row.get("merged", ""))
    if row["state"] == "done" and merged:
        parts.append(f"merged {clock(merged)}")
    return f'<p class="span">{esc(" · ".join(parts))}</p>' if parts else ""


def facts_html(row: dict[str, str]) -> str:
    """What the steps do not say: why the harbour refused a merge, and why a slice not at work is not."""
    why = "" if row["state"] in ("waiting", "working", "done") else row.get("why", "")
    facts = (("Merge refused", row.get("refused", "")), ("Why", why))
    lines = "".join(f"<dt>{esc(label)}</dt><dd>{esc(value)}</dd>" for label, value in facts if value)
    return f'<dl class="facts">{lines}</dl>' if lines else ""


def film_html(row: dict[str, str]) -> str:
    """Where this slice is in its capability's film: the chapter, when it starts, and the link that plays it."""
    try:
        film = json.loads(row.get("film") or "{}")
    except ValueError:
        return ""
    if not isinstance(film, dict) or not film.get("capability"):
        return ""
    at = int(film.get("at") or 0)
    return (f'<div class="film-ref"><span>In the film of <b>{esc(str(film["capability"]))}</b></span>'
            f'<span class="sub">Chapter {esc(str(film.get("chapter", "")))} of {esc(str(film.get("of", "")))} · '
            f"starts at {at // 60}:{at % 60:02d}</span>"
            f'<a href="#{esc(str(film.get("id", "")))}" data-film-at="{at}">Watch from this chapter</a></div>')


def answer_html(row: dict[str, str]) -> str:
    """What a slice waiting on a person waits for, and a box to answer it, inside its opened card.

    The answer box was a stream's, further down, and a stream with three slices parked on three questions
    got one box. Opened, the card says the park and each open question, and what is typed goes to that slice's inbox
    — whatever the park's own fields name, the card is the slice's — where its captain takes a person's message
    as the answer to the park, clearing it and no sibling's. Once sent, the answer stands where the box was,
    with where it is and Change my answer (`talk_marks`).
    """
    asked = "".join(f"<li>{esc(one)}</li>" for one in row.get("asked", "").splitlines() if one.strip())
    questions = f'<ol class="asked">{asked}</ol>' if asked else ""
    park = row.get("park") or row.get("why", "")
    box = f'answer-{row["slice"]}'
    given = (held(row).get("answer") or None) if row.get("talk") else None
    return (f'<p class="park">{esc(park)}</p>{questions}{placed_html(given, box)}'
            f'<div class="ask"{" hidden" if given else ""}><textarea id="{esc(box)}" rows="4" placeholder="Your '
            f'answer, or what {esc(row["slice"])} needs to know"></textarea>'
            f'<button type="button" class="go" data-answer="{esc(row["fairway"])}" data-slice="{esc(row["slice"])}" '
            f'data-of="{esc(row.get("park_of", ""))}" data-box="{esc(box)}">Send to {esc(row["slice"])}</button></div>')


def slice_html(row: dict[str, str]) -> str:
    """One slice: closed, its name and where it stands; opened in place, how it got there and what it waits for."""
    answer = answer_html(row) if row["state"] == "waiting" and row.get("fairway") else ""
    said = opener("Feedback", {"from": "slice", "feature": row.get("feature", ""), "fairway": row.get("fairway", ""),
                               "slice": row["slice"]}, ask=f"What did {row['slice']} show you?")
    return (f'<details class="slice {esc(row["state"])}" id="card-{esc(row["slice"])}" '
            f'data-card="{esc(row["slice"])}">{summary_html(row)}'
            f"{answer}{steps_html(row)}{facts_html(row)}{talk_html(row)}{film_html(row)}{span_html(row)}"
            f"{card_html(row) if row['state'] == 'done' else ''}"
            f'<div class="ask">{said}</div></details>')

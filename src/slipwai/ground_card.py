"""`/ground` on the board: the rows of an adopted repository's map, asked one at a time, and each answer recorded.

`/ground` is the agent asking a person what the tree cannot say, one row of the convergence map at a time, with
the evidence and the rungs shown first and "I don't know" always an answer. A person who adopted from the board
was left at a checklist whose next step was "/ground, in the agent" — a different tool, opened by hand, for a
question set the board can put just as well: every rung's meaning is in `convergence.AXES`, and every row's
evidence is in the record.

So the voyage asks it. **One row at a time**, the first nobody has answered, as `/ground` does. **Each answer is
written where the record keeps it**: a rung a person is the fact for goes on the row with `confirmed` provenance
and their words as the evidence; an answer that is a fact under another key — the release path, a schema's home,
the release mode, why the work is happening — is written there, and the row follows when the record is
refreshed. **The tree still wins**: the structure and the constitution are read off the tree, so the question
there is only whether the reading is right, and `check-convergence` goes on failing a row the tree contradicts.
**"I don't know" leaves the row `unrecorded`** and marks it asked, so the checklist moves on without a guess
being written down — `/sail` asks again before a slice that touches it.

Every answer is followed by `adopt --refresh` and committed with the files it rewrote, and nothing else: what
`./init` wrote and the person's own changes stay theirs to commit.
"""
from __future__ import annotations

import datetime
import json
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from . import resurvey
from .convergence import AXES, BY_KEY, Axis, settled
from .errors import GenerationError
from .layout import layout_of
from .manifest import read_manifest
from .origin import HOMES, RELEASE_PATHS, adoption_of
from .page_shell import esc
from .uncommitted import refuse_foreign

#: A row a person has spoken for. `detected` is the tree's reading, not an answer.
SAID = ("confirmed", "overridden")
#: The answer that is always on offer, and the one that writes nothing but the asking.
UNKNOWN = "dont-know"
#: The answer to a row the tree reads: the reading is right. It records the person agreeing with it.
AS_READ = "as-read"
#: Rows the tree settles. Asked only as "is this reading right?" — what moves them is a change to the tree.
READ = {
    "structure": "the applications you confirmed, where they live, the layout they declare and their type checks",
    "constitution": "`.specify/memory/constitution.md` — `/speckit-constitution` ratifies it, after these rows",
}
#: Rows whose answer is a home: where the schema, or the infrastructure, is versioned.
HOMED = {"data": ("database", "schema", "the schema"),
         "infrastructure": ("infrastructure", "home", "the infrastructure")}
HOME_MEANS = {
    "here": "in this repository",
    "elsewhere": "in another repository — name it",
    "unmanaged": "nowhere: it is changed by hand",
    "none": "there is none",
}
MODES = {
    "open": "every change is visible to actors as soon as it is deployed",
    "keystone": "new behaviour is built unreachable, and one last change makes it reachable",
    "flagged": "new behaviour is behind a flag that is turned on when it is ready",
    "promoted": "a change reaches actors only when a release is promoted",
}


@dataclass(frozen=True)
class Asked:
    """One row put to a person: its axis, the row as recorded, and the choices on offer, each with its meaning."""

    axis: Axis
    row: dict
    choices: tuple[tuple[str, str], ...]
    #: What the answer is: a rung, a home, a release mode, a sentence, or only whether the reading is right.
    kind: str


def rows_of(document: dict) -> dict[str, dict]:
    return {str(row.get("axis")): row for row in document.get("convergence") or [] if isinstance(row, dict)}


def answered(row: dict | None) -> bool:
    """Spoken for by a person, or asked and answered "I don't know" — either way, not asked again here."""
    return row is not None and (row.get("provenance") in SAID or bool(row.get("asked")))


def asked(document: dict) -> Asked | None:
    """The first row nobody has answered, as the question it is; None once every row has been."""
    rows = rows_of(document)
    for axis in AXES:
        row = rows.get(axis.key)
        if answered(row):
            continue
        return question(axis, row or {})
    return None


def question(axis: Axis, row: dict) -> Asked:
    if axis.key in READ:
        return Asked(axis, row, ((AS_READ, f"that is right: `{row.get('rung')}`"),), "read")
    if axis.key in HOMED:
        return Asked(axis, row, tuple(HOME_MEANS.items()), "home")
    if axis.key == "release-mode":
        return Asked(axis, row, tuple(MODES.items()), "mode")
    if axis.key == "strategy":
        return Asked(axis, row, (), "why")
    # A rung a person is the fact for. The floor that only says "nobody has said" is not an answer to give.
    return Asked(axis, row, tuple((rung, axis.means[rung]) for rung in axis.rungs if rung != "unknown"), "rung")


def card(root: Path, fault: str = "") -> str:
    """The question card, or the line that says every row has been answered; nothing for a generated project."""
    try:
        document = read_manifest(root, "the board")
    except GenerationError:
        return ""
    if adoption_of(document) is None:
        return ""
    now = asked(document)
    done = sum(1 for axis in AXES if answered(rows_of(document).get(axis.key)))
    head = (f'<div class="card" id="ground"><h2>Ground the map · {done} of {len(AXES)}</h2>'
            + (f'<p class="said bad">{esc(fault)}</p>' if fault else ""))
    if now is None:
        return head + ('<p class="empty">Every row of the map has been answered. The rows a person did not know '
                       "stay `unrecorded`, and `/sail` asks about each before a slice that touches it.</p></div>")
    row = now.row
    at = ' class="at"'
    ladder = "".join(f'<li{at if rung == row.get("rung") else ""}><b>{esc(rung)}</b> — '
                     f"{esc(now.axis.means[rung])}</li>" for rung in now.axis.rungs)
    options = "".join(
        f'<label class="check"><input type="radio" name="answer" value="{esc(value)}"> '
        f"<span><b>{esc(value)}</b> — {esc(meaning)}</span></label>" for value, meaning in now.choices)
    options += (f'<label class="check"><input type="radio" name="answer" value="{UNKNOWN}"> '
                "<span><b>I don't know</b> — the row stays unrecorded, and is asked again before a slice "
                "that touches it</span></label>")
    words = ('<textarea name="evidence" rows="3" placeholder="Why the work is happening — the business trigger, '
             'in your words"></textarea>' if now.kind == "why" else
             '<input name="repository" placeholder="the repository, where it is elsewhere">'
             '<textarea name="evidence" rows="2" placeholder="In your words: what makes it so (optional)"></textarea>'
             if now.kind == "home" else
             '<textarea name="evidence" rows="2" placeholder="In your words: what makes it so (optional)">'
             "</textarea>")
    reading = (f'<p class="empty">Read from the tree: {esc(READ[now.axis.key])}. What moves it is a change to '
               "the tree, not an answer here.</p>" if now.kind == "read" else "")
    return (head + f'<h3>{esc(now.axis.title)}</h3>'
            f'<p>As recorded: <b>{esc(row.get("rung", "—"))}</b> ({esc(row.get("provenance", "unrecorded"))}) — '
            f'{esc(row.get("evidence", ""))}</p>{reading}<ol class="lines rungs">{ladder}</ol>'
            f'<form class="ask-page" id="ground-form"><input type="hidden" name="axis" value="{esc(now.axis.key)}">'
            f'<div class="checks">{options}</div>{words}</form>'
            '<div class="ask"><button class="go" id="ground-answer">Record the answer</button></div></div>')


def record(root: Path, answers: Mapping[str, str], today: str | None = None) -> list[str]:
    """Write one answer where the record keeps it, refresh what reads the record, and commit both.

    Returns the paths committed. Refuses, and writes nothing, where an answer is not one on offer or a file
    the refresh rewrites holds a change slipwai did not make.
    """
    document = read_manifest(root, "the board")
    if adoption_of(document) is None:
        raise GenerationError("this project was generated, not adopted, so it has no map to ground")
    axis = BY_KEY.get(str(answers.get("axis") or ""))
    if axis is None:
        raise GenerationError(f"there is no row of the map called {answers.get('axis')!r}")
    now = question(axis, rows_of(document).get(axis.key, {}))
    answer, words = str(answers.get("answer") or ""), str(answers.get("evidence") or "").strip()
    if now.kind == "why" and answer != UNKNOWN:
        answer = "why" if words else ""
    offered = {value for value, _ in now.choices} | ({"why"} if now.kind == "why" else set())
    if answer != UNKNOWN and answer not in offered:
        raise GenerationError("pick one of the answers on offer — I don't know is one of them")
    refuse_foreign(root, resurvey.writes(root, layout_of(document)), "grounding the map")
    when = today or datetime.date.today().isoformat()
    said = words or "said on the board"
    rows = document.setdefault("convergence", [])
    row = next((r for r in rows if isinstance(r, dict) and r.get("axis") == axis.key), None)
    if row is None:
        row = {"axis": axis.key, "rung": axis.rungs[0], "target": axis.target, "provenance": "unrecorded"}
        rows.append(row)
    row["asked"] = when
    if answer == UNKNOWN:
        row["evidence"] = f"asked on {when}: not known yet"
    elif now.kind == "rung":
        row.update(rung=answer, provenance="confirmed", evidence=said)
        if axis.key == "path-to-production":
            # The release path is the fact the gate caps this row by, and it knows four of the six rungs: the two
            # above a pipeline are a pipeline with more said about it.
            document["release"] = {**(document.get("release") or {}),
                                   "path": answer if answer in RELEASE_PATHS else "pipeline",
                                   "provenance": "confirmed", "evidence": [said]}
    elif now.kind == "home":
        key, field, _ = HOMED[axis.key]
        if answer not in HOMES:
            raise GenerationError(f"{answer!r} is not where a home can be")
        fact = {**(document.get(key) or {}), field: answer, "provenance": "confirmed"}
        repository = str(answers.get("repository") or "").strip()
        if answer == "elsewhere":
            if not repository:
                raise GenerationError("elsewhere is a named repository: say which one")
            fact["repository"] = repository
        document[key] = fact
        row.update(rung="settled" if settled(fact, field) else "recorded", provenance="confirmed", evidence=said)
    elif now.kind == "mode":
        document["releaseMode"] = answer
        row.update(rung="confirmed", provenance="confirmed", evidence=f"{answer}: {MODES[answer]}. {said}")
    elif now.kind == "why":
        # The trigger is the fact; the row is the strategy's, and the recommendation is re-made from it.
        document["why"] = words
    # A row the tree reads, agreed with, is only asked: `confirmed` would hold it at today's rung against the
    # tree, and the constitution `/speckit-constitution` ratifies next would still read `template`.
    (root / "project.json").write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    refreshed = resurvey.refresh(root, clean_checked=True)
    paths = sorted({"project.json", *refreshed.rewritten})
    subprocess.run(["git", "add", "--", *paths], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-q", "-m", f"Ground the map: {axis.title.lower()}"], cwd=root,
                   check=False, capture_output=True)
    return paths


#: The page half: the answer posted, and a refusal shown where the card was.
SCRIPT = """
document.addEventListener('click', async event => {
  if (event.target.id !== 'ground-answer') return;
  const form = document.getElementById('ground-form');
  const held = Object.fromEntries(new FormData(form).entries());
  event.target.disabled = true;
  const answer = await fetch('/adopt/ground', {method:'POST', headers:{'Content-Type':'application/json'},
                                              body: JSON.stringify(held)});
  // Recorded: the whole voyage is read again, because the checklist above moves with the row.
  if (answer.ok) { location.reload(); return; }
  document.getElementById('ground').outerHTML = await answer.text();
});
"""

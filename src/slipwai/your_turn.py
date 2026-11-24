"""The one next step, at the top of the Voyage: what to do, the button that does it, and what happens after.

The strip said where the work was and the line under it said, in one run-on sentence, what was waiting —
`Now: slices — stopped until you act: 1 park; 2 questions; 26 notes for you; 36 decision(s)…` — and a person
who had just approved a storyboard read that page and could not say what to press. Every stop in the run
is a stage waiting on a person by design, and each one looked like the run had hung.

So the stage the person is on is said as a step, in one shape at every pause: a heading that is a verb, the
line saying where it stands, the buttons, why a button is locked where one is, and the next two stages with
what each will do once this one is out of the way. Running is said as running, with nothing to press; a
stage that wants a person is said as *Your next step*; a step the board holds back is said as locked,
never as a button that is not there (`launch_lock`).
"""
from __future__ import annotations

import re
from html import escape as esc
from typing import Any

from .passage import Stage, current, meanwhile

#: The step a person takes at each stage, as a verb: (where it waits on them, where it has not started).
STEPS = {
    "init": ("Set the project up", "Set the project up"),
    "constitution": ("Read the drafted constitution", "Draft the constitution"),
    "specification": ("Read the specification", "Write the specification"),
    "storyboard": ("Give the storyboard its verdict", "Draw the storyboard"),
    "model": ("Model the feature again", "Model the feature"),
    "chart": ("Look at why the build stopped", "Continue the build"),
    "slices": ("Answer what the fleet is waiting on", "Cast off the fleet"),
    "accepted": ("Watch the demos and give a verdict", "Take each capability to its demo"),
}

STYLE = """
.turn{display:grid;gap:10px;padding:18px;border-radius:12px;border:1px solid var(--rule);background:var(--paper)}
.turn.you{border-color:var(--brass);background:var(--brass-soft)}
.turn.locked{border-color:var(--critical);background:var(--critical-soft)}
.turn .eyebrow{font-size:.78rem;font-weight:700;letter-spacing:.02em;color:var(--ink-3)}
.turn.you .eyebrow{color:var(--brass)}.turn.locked .eyebrow{color:var(--critical)}
.turn h3{margin:0;font-size:1.25rem;line-height:1.3}
.turn .line{margin:0;color:var(--ink-2)}
.turn .turn-then{margin:4px 0 0;padding:10px 0 0;border-top:1px solid var(--rule);list-style:none;display:grid;
  grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px}
.turn .turn-then li{display:grid;gap:2px;font-size:.86rem;color:var(--ink-2)}
.turn .turn-then b{font-size:.78rem;color:var(--ink-3)}
.turn .turn-then:empty{display:none}
.stage.current .dot{box-shadow:0 0 0 4px var(--brass-soft),0 0 0 6px var(--brass)}
.stage.elsewhere{opacity:.6}.stage.elsewhere .dot{border-style:dashed}
"""

#: Run by the strip's paint: the poll carries `turn` beside `now`.
SCRIPT = """
function paintTurn(found){
  const box = document.getElementById('turn'), turn = found.turn;
  if (!box || !turn) return;
  box.className = 'turn ' + turn.mode;
  box.querySelector('.eyebrow').textContent = turn.eyebrow;
  box.querySelector('h3').textContent = turn.heading;
  box.querySelector('.line').textContent = turn.line;
  const then = box.querySelector('.turn-then');
  then.replaceChildren(...turn.then.map(step => {
    const row = document.createElement('li'), when = document.createElement('b'), what = document.createElement('span');
    when.textContent = step.when; what.textContent = step.what;
    row.append(when, what); return row;
  }));
  for (const stage of found.stages) {
    const node = document.querySelector('.passage [data-stage="' + stage.key + '"]');
    if (!node) continue;
    node.classList.toggle('current', stage.key === turn.key);
    node.classList.toggle('elsewhere', !!stage.elsewhere);
  }
}
"""


def first_sentence(text: str) -> str:
    """The first sentence of a stage's expectation, without its bold marks."""
    plain = text.replace("**", "")
    return re.split(r"(?<=[.!?])\s", plain, maxsplit=1)[0]


def turn(found: list[Stage], held: str = "") -> dict[str, Any]:
    """The step: its mode (`you`, `running`, `locked`, `done`), its eyebrow, heading, and the two after it."""
    now = current(found)
    if now is None:
        return {"key": "", "mode": "done", "eyebrow": "Nothing waits on you",
                "heading": "Every stage is done", "line": "", "then": []}
    if held:
        mode, eyebrow, heading = "locked", "Your next step is locked", f"Unlock {STEPS[now.key][1]}"
    elif now.state == "working":
        mode, eyebrow, heading = "running", "Running · nothing for you to do yet", f"{now.title} is running"
    else:
        mode, eyebrow = "you", "Your next step"
        waiting = now.state in ("waiting", "attention")
        heading = STEPS.get(now.key, (now.title, now.title))[0 if waiting else 1]
    # An earlier feature's slices and acceptance still come next for this one, whatever state they are in.
    after = [one for one in found[found.index(now) + 1:]
             if one.elsewhere or one.state in ("todo", "waiting", "attention", "working")][:2]
    then = [{"when": f"Then · {STEPS.get(one.key, (one.title, one.title))[1]}", "what": first_sentence(one.expect)}
            for one in after if one.expect]
    detail = now.detail[:1].upper() + now.detail[1:]
    return {"key": now.key, "mode": mode, "eyebrow": eyebrow, "heading": heading,
            "line": f"{detail}.{meanwhile(found, now)}", "then": then}


def box(found: list[Stage], now_line: str, buttons: str, held_line: str, held: str = "") -> str:
    """The step as the page draws it once; the poll repaints it from `turn` (`paintTurn`)."""
    said = turn(found, held)
    then = "".join(f"<li><b>{esc(step['when'])}</b><span>{esc(step['what'])}</span></li>" for step in said["then"])
    return (f'<div class="turn {said["mode"]}" id="turn"><span class="eyebrow">{esc(said["eyebrow"])}</span>'
            f'<h3>{esc(said["heading"])}</h3><p class="line">{esc(said["line"])}</p>'
            f'<p id="now" hidden>{esc(now_line)}</p><div class="ask">{buttons}</div>'
            f'{held_line}<ol class="turn-then">{then}</ol></div>')


def classes(found: list[Stage]) -> dict[str, str]:
    """The strip's extra classes per stage: the one the person is on, and those an earlier feature owns."""
    now = current(found)
    return {one.key: " ".join(name for name, on in (("current", now is not None and one is now),
                                                     ("elsewhere", one.elsewhere)) if on)
            for one in found}

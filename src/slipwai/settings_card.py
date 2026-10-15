"""Everything a run is set to, in one box with a tab each.

Four settings surfaces and they were four places. Speed and Fine tune are the telegraph, two cards apart on
the board; who answers at each stop is a third card on the Voyage; and the two the ladder reads — how
`/sail` delegates, and which model runs what — were a command typed in an agent by somebody with the board
open in front of them. A person asking "what is this run set to" was asking four questions.

**The tabs are radio buttons and a stylesheet, not a script.** The published copy of this board is one HTML
file with no controls and therefore no JavaScript, and a box whose tabs only worked on the served copy
would be the two copies disagreeing — which is the rule the tab bar itself is held to. It is also what
makes each tab reachable by keyboard without anything here implementing that.

Which tabs there are is what the project has, not a fixed list: a harbour that is not a project has Speed
and Fine tune, and a tab offering to set a file that is not there would be a control that refuses every
press.
"""
from __future__ import annotations

from pathlib import Path

from .dials import MODELS, PANELS, Dial, Panel, held
from .dials import dials as dials_of
from .fleet import NOTHING
from .page_shell import PLAIN, esc
from .telegraph import MEANS, POSITIONS, SETTINGS
from .wheel import ASKS, STOPS, known, orders

#: The dial's positions as a person reads them, and the plain names of the numbers under them. `PLAIN` is
#: the board's, because the same names label the fine tune and the fold; this holds only the dial.
DIAL = {name: name.replace("-", " ").capitalize() for name in POSITIONS}

#: One tab: the key it is addressed by, what the tab says, and the panel under it.
STYLE = """
.settings{display:grid;gap:0}
.settings>input{position:absolute;width:1px;height:1px;opacity:0;pointer-events:none}
.settings .bar{display:flex;flex-wrap:wrap;gap:2px;border-bottom:1px solid var(--rule);margin:0 0 14px}
.settings .bar label{font-size:.84rem;padding:7px 12px;border-radius:7px 7px 0 0;cursor:pointer;
  color:var(--ink-3);border:1px solid transparent;border-bottom:0;margin-bottom:-1px;white-space:nowrap}
.settings .bar label:hover{color:var(--ink)}
.settings .panel{display:none}
.settings .panel>:first-child{margin-top:0}
.settings .panel .empty{margin:0 0 12px}
.settings .dials{display:grid;gap:12px}
.settings .row{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:6px 14px;align-items:center}
.settings .row small{grid-column:1 / -1;color:var(--ink-3);font-size:.76rem;margin-top:-4px}
.settings .row .dial{margin:0}
.settings .where{font-family:ui-monospace,Menlo,monospace;font-size:.74rem;color:var(--ink-3);
  margin:14px 0 0;padding-top:10px;border-top:1px solid var(--rule-2)}
.settings .dial .now.asks{background:var(--brass);border-color:var(--brass)}
/* Twenty-two stages is a table, not twenty-two dials: a hundred buttons in a tab is a wall. */
.settings .stages{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:7px 14px;align-items:center}
.settings .stages span{font-size:.86rem}
.settings .stages select{font:inherit;font-size:.82rem;padding:3px 6px;border-radius:6px;
  border:1px solid var(--rule);background:var(--paper);color:var(--ink)}
.settings .stages .fell{color:var(--ink-3)}
.settings .stages .key{font-family:ui-monospace,Menlo,monospace;font-style:normal;
  font-size:.74rem;color:var(--ink-3)}
@media (max-width:600px){.settings .row{grid-template-columns:1fr}}
"""


def rules(keys: list[str]) -> str:
    """The stylesheet that makes one checked radio show one panel. Generated, because the tabs are what
    the project has rather than a list written out here."""
    return "".join(
        f"#tab-{key}:checked~.bar label[for=tab-{key}]{{color:var(--teal);border-color:var(--rule);"
        f"background:var(--paper);font-weight:600}}"
        f"#tab-{key}:checked~.panels>[data-panel={key}]{{display:block}}" for key in keys)


def row(panel: str, one: Dial, values: tuple[str, ...], now: str, controls: bool, asks: str = "") -> str:
    """One setting, with its values as a dial: the one it is on said, the rest pressable.

    `asks` is the value that means a person is asked, where the setting has one. It is drawn amber, which
    is this board's one colour for a control that waits on somebody — the same amber the strip goes.
    """
    dial = "".join(
        f'<span class="now{" asks" if value == asks else ""}">{esc(one.says.get(value, value))}</span>'
        if value == now or not controls
        else f'<button data-dial="{esc(panel)}" data-key="{esc(one.key)}" data-value="{esc(value)}">'
             f"{esc(one.says.get(value, value))}</button>"
        for value in values if value == now or controls)
    return f'<div class="row"><b>{esc(one.title)}</b><div class="dial">{dial}</div></div>'


def panel(name: str, title: str, note: str, rows: str, where: str = "") -> str:
    """One tab's contents: what it is for, the settings, and the file they live in."""
    said = f'<p class="empty">{esc(note)}</p>' if note else ""
    at = f'<p class="where">{esc(where)}</p>' if where else ""
    del title
    return f'<div class="panel" data-panel="{esc(name)}">{said}{rows}{at}</div>'


def card(tabs: list[tuple[str, str, str]]) -> str:
    """The box. `tabs` is (key, what the tab says, the panel) in the order they sit, the first one open.

    Nothing where there is one tab: a box of tabs with a single tab is a card with a decoration on it, and
    a harbour that is not a project would otherwise get one over Speed alone.
    """
    if not tabs:
        return ""
    keys = [key for key, _, _ in tabs]
    boxes = "".join(f'<input type="radio" name="settings" id="tab-{esc(key)}"{" checked" if not index else ""}>'
                    for index, (key, _, _) in enumerate(tabs))
    bar = "".join(f'<label for="tab-{esc(key)}">{esc(said)}</label>' for key, said, _ in tabs)
    panels = "".join(one for _, _, one in tabs)
    return (f"<style>{STYLE}{rules(keys)}</style>"
            f'<div class="card"><h2>Settings</h2><div class="settings">{boxes}'
            f'<div class="bar" role="tablist">{bar}</div><div class="panels">{panels}</div></div></div>')


def choice(panel: str, key: str, title: str, now: str, values: tuple[str, ...], controls: bool) -> str:
    """One setting as a menu rather than a dial. Twenty-two stages with five roles each is a hundred and
    ten buttons, which is a wall; the same thing as rows of one menu is a table somebody can read.

    Both the words and the key, always. Three stages of the ladder carry no title at all and two share
    one — `plan` and `tasks-quartermaster` are both *Plan and tasks* — so a row labelled by its title is a
    blank row or one of an indistinguishable pair. The key is also what the file holds and what `--set`
    takes, which makes the row and the thing it writes the same name.
    """
    name = (f'{esc(title)} <i class="key">{esc(key)}</i>' if title else f'<i class="key">{esc(key)}</i>')
    if not controls:
        return f"<span>{name}</span><span class=\"fell\">{esc(now)}</span>"
    options = "".join(f'<option value="{esc(one)}"{" selected" if one == now else ""}>{esc(one)}</option>'
                      for one in values)
    return (f"<span>{name}</span>"
            f'<select data-dial="{esc(panel)}" data-key="{esc(key)}">{options}</select>')


def stops_tab(answers: dict[str, str], controls: bool) -> tuple[str, str, str] | None:
    """Who answers at each stop of the run — `.specify/cruise.json`, which `/cruise-settings` writes.

    Nothing where the project has none: a harbour, an adopted repository that has not been given one, a
    project generated before this was configurable. A tab offering to set a file that is not there would
    be a control that refuses every press.
    """
    if not answers:
        return None
    rows = "".join(row("cruise", Dial(name, title, says), known(name), answers.get(name, ""), controls,
                       ASKS) for name, title, says in STOPS)
    asked = [title.lower() for name, title, _ in STOPS if answers.get(name) == ASKS]
    note = (WHEEL + " " + (f"This run stops for you at: {', '.join(asked)}."
                           if asked else "Nothing here stops for you: this run answers every one itself."))
    return ("answers", "Who answers",
            panel("answers", "", note, f'<div class="dials">{rows}</div>', ".specify/cruise.json"))


def file_tab(root: Path, one: Panel, controls: bool) -> tuple[str, str, str] | None:
    """One of the two files the ladder reads, as its own tab. Nothing where the project has none."""
    now = held(root, one)
    if not now:
        return None
    found = dials_of(root, one)
    if one is MODELS:
        rows = "".join(choice(one.name, dial.key, dial.title, now.get(dial.key, now.get("default", "")),
                              values, controls) for dial, values in found)
        body = f'<div class="stages">{rows}</div>'
    else:
        body = '<div class="dials">' + "".join(
            row(one.name, dial, values, now.get(dial.key, ""), controls) for dial, values in found) + "</div>"
    return one.name, SHORT[one.name], panel(one.name, "", one.note, body, one.config)


#: What each project tab is called on the bar. Short, because five tabs have to sit on one line on a
#: laptop and the panel says the long version.
SHORT = {"sail": "Delegation", "models": "Models"}
#: Said once, over the stops. The second half is the half that makes it usable: a captain reads this at a
#: boundary, so a change here is about the next stop rather than the one being worked now.
WHEEL = ("Under /cruise the skipper answers and the hand demos. Each stop below can be set to park "
         "instead, which is what /sail does with it: the fleet stops and the question arrives under "
         "Waiting on you. A captain reads this at its next boundary, so a change applies to the next stop "
         "rather than to one already under way.")


def project_tabs(root: Path, controls: bool) -> list[tuple[str, str, str]]:
    """Every settings file this project actually has, in the order a person meets what they set."""
    found = [stops_tab(orders(root), controls)]
    found += [file_tab(root, one, controls) for one in PANELS]
    return [one for one in found if one is not None]


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


#: The three numbers somebody is actually choosing between when they ring: how much runs at once, and what
#: a day may cost. Every other number moves with them, and Fine tune below is where they all are.
HEADLINE = ("boilers", "fanout", "bunker_per_day")

#: Why the dial is one control and not nine, said once. The second sentence is the one people get wrong:
#: a slower run is also a stricter one, which is a judgement the telegraph's own table makes and not an
#: arithmetic that could be guessed from the position's name.
SPEED = ("The dial moves everything together: ringing a position sets every number under Fine tune as a "
         "group. Slower is not only cheaper \u2014 a slowed run also stops a merge at a lower severity and "
         "parks sooner on unread decisions, because a run somebody has slowed down is one where less gets "
         "deferred. A captain reads a new position at its next boundary, never mid-stage, so ringing it "
         "changes what happens next rather than what is happening now.")


def positions(now: str) -> str:
    """What each notch of the dial sets, read from the telegraph's own table.

    From `SETTINGS` rather than written out here, because a page that described the dial in its own words
    would be a second copy of the numbers and the first one to drift.
    """
    head = "".join(f"<th>{esc(PLAIN[name])}</th>" for name in HEADLINE)
    rows = ""
    for name in POSITIONS:
        held = SETTINGS[name]
        cells = "".join(f"<td>{esc(held.get(one, NOTHING))}</td>" for one in HEADLINE)
        here = ' <span class="chip running">now</span>' if name == now else ""
        rows += f"<tr><td><b>{esc(DIAL[name])}</b>{here}</td>{cells}</tr>"
    return f"<table><thead><tr><th>Position</th>{head}</tr></thead><tbody>{rows}</tbody></table>"


def tune(config: dict, controls: bool) -> str:
    """The fine-tune panel, in plain words. Writes `harbour.json` through the same code the verb uses."""
    rows = []
    for name in MEANS:
        value = config.get(name, NOTHING)
        cell = (f'<input data-number="{esc(name)}" value="{esc(value)}">' if controls else esc(value))
        rows.append(f"<dt>{esc(PLAIN.get(name, name))}</dt><dd>{cell}</dd>")
    apply = '<div class="ask"><button class="go" id="apply">Apply</button></div>' if controls else ""
    return panel("tune", "", TUNE, f'<dl>{"".join(rows)}</dl>{apply}', "harbour.json")


#: Why the numbers are here and the dial is the thing to reach for first.
TUNE = ("Every number the dial sets, one at a time. Ringing a position overwrites all of them together, so "
        "this is for the one number a position has wrong rather than for setting a run up.")


def speed(pressure: dict, controls: bool) -> str:
    """The dial, what it sets, and what it means — the first tab, because it is the one control here
    that moves everything else."""
    banked = f'<p class="empty">{esc(pressure["banked"])}</p>' if pressure["banked"] else ""
    return panel("speed", "", SPEED, f'{dial(str(pressure["position"]), controls)}{banked}'
                 f'{positions(str(pressure["position"]))}', "harbour.json")


def settings(pressure: dict, config: dict, controls: bool, more: list[tuple[str, str, str]] | None = None) -> str:
    """The settings box: the telegraph's two tabs, and whatever the project this board is looking at has
    beside them. The published copy passes none, which is why this takes them rather than reading them."""
    return card([("speed", "Speed", speed(pressure, controls)),
                 ("tune", "Fine tune", tune(config, controls))] + (more or []))

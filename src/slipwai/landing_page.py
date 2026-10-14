"""The Board tab as a landing: where the board is looking, where that project stands, and what can be started.

Everything live — the streams, the inbox, the speed, the last lines — is on the Voyage tab now, beside the
stages and the model, because a person reading how the work is going wants it in one place. What is left
here is what a person does *before* there is work to watch: point the board at a directory, start a project,
adopt a repository. A board started by a login service opens on this page, which is why it says plainly
what it is looking at and offers the two ways in rather than a table of streams that are not running.
"""
from __future__ import annotations

from .assets import this_command
from .page_shell import document, esc

#: What can be started from here: the page, the verb, and why.
STARTING = (
    ("Start a new project", "generate", "/generate",
     "The interview, asked here: the delivery foundation, the language, what the first service owns, and "
     "where it goes to production."),
    ("Adopt a repository you already have", "adopt", "/adopt",
     "The method installed around code that exists, with what it found and what it would write shown "
     "before anything is written."),
)

SCRIPT = """
async function send(path, body){
  const answer = await fetch(path, {method:'POST', headers:{'Content-Type':'application/json'},
                                    body: JSON.stringify(body)});
  if (answer.ok) location.reload();
  else alert(await answer.text());
}
document.addEventListener('click', event => {
  if (event.target.id === 'attach-go') {
    const box = document.getElementById('attach');
    if (box && box.value.trim()) send('/attach', {root: box.value.trim()});
  }
});
"""


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
            '<button class="go" id="attach-go">Look here</button></div>'
            '<p class="empty">A directory on this machine: a project, or a harbour of them. The board '
            "re-reads it on every request, so looking somewhere else is a sentence, not a restart.</p></div>")


def standing(name: str, now: str, project: bool) -> str:
    """Where the project the board is looking at stands, in one line, and the way to the page about it."""
    if not project:
        return ('<div class="card"><h2>No project here</h2><p class="empty">This directory has no '
                "project.json, so there is nothing to stand anywhere: look at a project, or start one below.</p></div>")
    return (f'<div class="card"><h2>{esc(name)}</h2><p class="empty">{esc(now)}</p>'
            '<div class="ask"><a class="go" href="/voyage">Open the voyage</a></div></div>')


def landing(root: str, name: str, now: str, project: bool) -> str:
    """The Board: looking at, where that stands, what can be started."""
    body = f"{looking(root)}{standing(name, now, project)}{starting_points()}"
    return document("Board", "start here", body, SCRIPT, now="/")

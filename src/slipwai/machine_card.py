"""*This machine*: the tools the board's routes need, found or not, on Settings and atop the start pages.

Each row of `prerequisites.TOOLS` says what this machine has of it. A row the machine has a good copy of
shows where and which version, and offers nothing. A row it lacks, or has only too old, offers *Install*
where `tool_install` has a way on this platform — for an old copy, a newer one for the board alone, the old
one left where it is — and the publisher's page where it has none.

The start pages carry one line, `lacking_line`, only where the route they begin needs something missing —
so a machine with everything sees those pages exactly as before.

**Nothing here waits for a tool.** The card and the line are drawn from what the machine has said so far
(`machine_probe`), marked while a tool is still out, and asked for again by the page until none is.

**On Windows, a terminal.** The tools the board installed are on its children's `PATH` and never the
system's, so the person's own terminal has none of them. The card offers *Open a terminal here* instead:
Git Bash, in the project this window shows, started with the board's `PATH`. **On a Mac**, where the app
is the way in, it offers *Add slipwai to my terminal*: one marked block in the shell's profile, taken out
again by *Remove* (`terminal_command`).
"""
from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode

from . import machine_probe, terminal_command, tool_install
from .machine_probe import BOUND, CHECKING, UNANSWERED
from .page_shell import esc
from .prerequisites import Found, lacking, needs
from .shell_environment import git_bash, login_environment

STYLE = """
#machine .tools{display:grid;gap:6px;margin:10px 0 0}
#machine .tool{padding:8px 10px;border:1px solid var(--rule);border-radius:8px}
#machine .tool b{font-weight:500}
#machine .tool .where{display:block;font-size:.8rem;color:var(--ink-3);overflow-wrap:anywhere}
#machine .tool.missing .where,#machine .tool.old .where,#machine .tool.unanswered .where{color:var(--brass)}
#machine .acts{display:flex;flex-wrap:wrap;gap:6px;margin-top:6px;font-size:.8rem;color:var(--ink-2)}
#machine .acts button{font:inherit;font-size:.78rem;padding:3px 10px;border-radius:8px;cursor:pointer;
  border:1px solid var(--rule);background:transparent;color:var(--ink-2)}
#machine .acts button:hover{border-color:var(--teal);color:var(--ink)}
#machine .doing{font-size:.8rem;color:var(--ink-2);white-space:pre-wrap;margin:6px 0 0;overflow-wrap:anywhere}
#machine .doing.failed{color:var(--critical)}
#machine .doing .now{display:block;margin-top:4px;color:var(--ink);font-weight:500}
#machine .doing progress{display:block;width:100%;max-width:340px;height:6px;margin-top:4px;accent-color:var(--teal)}
"""

SCRIPT = """
function bindMachine(scope) {
  scope.querySelectorAll('[data-tool]').forEach(one => {
    const doing = one.closest('.tool').querySelector('.doing');
    const asked = async () => (await fetch('/settings/tool.json?key=' + encodeURIComponent(one.dataset.tool))).json();
    // What has happened as lines, and under them what is happening now: the step in words, and a bar that
    // fills where the step can be counted and moves where it cannot. A failure stays on the page, in the
    // failure's colour, with the button back: reloading on every ending took the reason away with it.
    const show = state => {
      doing.hidden = !state.lines.length && !state.now;
      doing.classList.toggle('failed', !!state.failed);
      doing.textContent = state.lines.join('\\n');
      if (state.done) return;
      const now = document.createElement('span'); now.className = 'now'; now.textContent = state.now || 'Working…';
      const bar = document.createElement('progress');
      if (state.fraction !== null && state.fraction !== undefined) { bar.max = 1; bar.value = state.fraction; }
      doing.append(now, bar);
    };
    const poll = async () => {
      let state;
      try { state = await asked(); } catch (fault) { setTimeout(poll, 2000); return; }
      show(state);
      if (!state.done) { one.disabled = true; setTimeout(poll, 500); return; }
      if (state.failed) { one.disabled = false; return; }
      location.reload();
    };
    // An install begun before this page was loaded — a reload, a second window — is still this card's: it
    // is picked up where it is, and one that failed since still says why.
    asked().then(state => { if (!state.done) poll(); else if (state.failed) show(state); }).catch(() => {});
    one.addEventListener('click', async event => {
      event.preventDefault();
      one.disabled = true;
      doing.classList.remove('failed'); doing.textContent = 'Starting…'; doing.hidden = false;
      const answer = await fetch('/settings/tool', {method: 'POST', headers: {'Content-Type': 'application/json'},
                                                    body: JSON.stringify({key: one.dataset.tool})});
      const said = await answer.text();
      if (answer.status === 202) { doing.textContent = said; one.disabled = false; return; }
      // Refused because it is already being installed: that install is the one to follow, not a dead end.
      if (!answer.ok && (await asked()).done) { doing.textContent = said; one.disabled = false; return; }
      poll();
    });
  });
  scope.querySelectorAll('[data-command]').forEach(one => one.addEventListener('click', async () => {
    const said = one.parentElement.querySelector('.doing');
    const answer = await fetch('/settings/terminal-command', {method: 'POST',
      headers: {'Content-Type': 'application/json'}, body: JSON.stringify({action: one.dataset.command})});
    said.textContent = await answer.text(); said.hidden = false;
    if (answer.ok) setTimeout(() => location.reload(), 2500);
  }));
  scope.querySelectorAll('[data-terminal]').forEach(one => one.addEventListener('click', async () => {
    const said = one.parentElement.querySelector('.doing');
    const answer = await fetch('/settings/terminal', {method: 'POST', headers: {'Content-Type': 'application/json'},
                                                      body: '{}'});
    said.textContent = await answer.text(); said.hidden = false;
  }));
}
// The card is asked for after the page is up, and again until every tool has answered: each answers its
// version in its own time, and Settings waited for the slowest of them before it showed anything. A card
// that says what the last one said is left as it is, so a button on it is not taken from under a press.
let machineSaid = '';
async function fillMachine() {
  const machine = document.querySelector('[data-machine]');
  if (!machine) return;
  try {
    const html = await (await fetch('/settings/machine.html')).text();
    if (html !== machineSaid) {
      machineSaid = html; machine.outerHTML = html;
      bindMachine(document.getElementById('machine'));
    }
  } catch (fault) { /* asked again below */ }
  setTimeout(fillMachine, 1000);
}
fillMachine();
"""


def git_bash_window(path: str | None = None) -> Path | None:
    """Git Bash's own window, `git-bash.exe`, beside the first Git on the board's `PATH` that carries bash."""
    found = git_bash(login_environment().get("PATH", "") if path is None else path)
    window = found.parent.parent / "git-bash.exe" if found is not None else None
    return window if window is not None and window.is_file() else None


def terminal_row(window: Path | None) -> str:
    """The card's last row on Windows: the button, or what it waits for."""
    if window is None:
        return ('<p class="lacking-note">A project\'s scripts run in Git\'s bash. Install Git with bash above, and '
                'a terminal with the board\'s tools can be opened here.</p>')
    return ('<div class="acts"><button type="button" data-terminal>Open a terminal here</button><span>Git Bash, in '
            'the project this window shows, with the tools the board installed: <code>make</code>, '
            '<code>python3</code> and <code>slipwai</code> work there.</span><span class="doing" hidden></span></div>')


def command_row(state: str, file: Path | None) -> str:
    """The card's last row on a Mac: `slipwai` for the person's own terminal, asked for, or taken back."""
    where = f"~/{file.name}" if file is not None else "your shell's profile"
    if state == "absent":
        return (f'<div class="acts"><button type="button" data-command="add">Add slipwai to my terminal</button>'
                f'<span>The board and its agents have <code>slipwai</code>; this gives it to terminals you open '
                f'too, with one marked line in {esc(where)}. A <code>slipwai</code> you install later still '
                f'comes first.</span><span class="doing" hidden></span></div>')
    if state == "added":
        return (f'<div class="acts"><span><code>slipwai</code> is in your terminal, from {esc(where)}.</span>'
                f'<button type="button" data-command="remove">Remove</button><span class="doing" hidden></span>'
                f'</div>')
    if state == "unsupported":
        return (f'<p class="lacking-note">For <code>slipwai</code> in your own terminal, add this line to your '
                f'shell\'s profile: <code>{esc(terminal_command.LINE)}</code></p>')
    return ""


def open_terminal(root: Path, window: Path | None = None) -> str:
    """Git Bash opened in `root` with the board's `PATH`; a sentence saying what happened."""
    window = git_bash_window() if window is None else window
    if window is None:
        return "There is no Git with bash on this machine yet: install it above first."
    subprocess.Popen([str(window), f"--cd={root}"], env=login_environment(root=root),  # noqa: S603 — Git's own window
                     creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0))
    return f"Git Bash is open in {root}."


#: What a start page runs: its line is drawn before any tool has answered, and asked for again — at the
#: address the line itself carries, which names the route and the answers it was drawn for — until each has.
#: The form above it is drawn again when an answer changes, so the line is looked for afresh every time.
WATCH = """
let lackingSaid = null;
(async function watchLacking() {
  const line = document.querySelector('[data-lacking]');
  if (line) try {
    const answer = await fetch(line.dataset.lacking);
    const html = answer.ok ? await answer.text() : lackingSaid;
    if (html !== lackingSaid && line.isConnected) { lackingSaid = html; line.outerHTML = html; }
  } catch (fault) { /* asked again below */ }
  setTimeout(watchLacking, 1000);
})();
"""


def where_line(one: Found) -> str:
    if one.state == CHECKING:
        return "asking it for its version…"
    if one.state == UNANSWERED:
        return f"did not answer within {BOUND:g} seconds; reload this page to ask it again"
    if one.state == "found":
        return f"{one.version or 'found'} at {one.where}"
    if one.lacks:
        return f"{one.version} at {one.where}, which has no {one.lacks}: a project's scripts run in Git's bash"
    if one.state == "old":
        need = ".".join(str(part) for part in one.tool.minimum)
        return f"{one.version} at {one.where}, which is too old: it needs {need} or newer"
    return "not on this machine"


def acts(one: Found) -> str:
    """Install, for a tool the machine lacks or has only too old; the publisher's page where the board has
    no way. Nothing for a good copy, nor for one nobody has heard from: that is not a tool known missing."""
    if one.state in ("found", CHECKING, UNANSWERED):
        return ""
    how = tool_install.way(one.tool.key)
    if not how:
        return (f'<span class="acts">Install it from <a href="{esc(one.tool.page)}">{esc(one.tool.page)}</a>, '
                f'then reload this page.</span>')
    said = ("opens Apple's installer for the developer tools" if how == "apple"
            else "from its publisher, checked against their checksum, kept in ~/.slipwai/tools")
    if one.state == "old" and not one.lacks:
        said += "; used by the board ahead of yours, which is left as it is"
    label = (f"Install {one.tool.name} with {one.lacks}" if one.lacks
             else f"{'Install a newer' if one.state == 'old' else 'Install'} {one.tool.name}")
    return (f'<span class="acts"><button type="button" data-tool="{esc(one.tool.key)}">{esc(label)}'
            f'</button><span>{esc(said)}</span></span><span class="doing" hidden></span>')


#: What Settings shows until the card is ready: it is fetched from `/settings/machine.html` once the page is up.
PLACEHOLDER = ('<div id="machine" class="card" data-machine><h2>This machine</h2>'
               '<p class="empty">Looking at what this machine has…</p></div>')


def card(rows: list[Found] | None = None) -> str:
    """The card, for Settings: as the machine stands now, and marked to be asked for again (`data-machine`)
    while a tool has still to answer."""
    rows = machine_probe.MACHINE.read() if rows is None else rows
    again = " data-machine" if any(one.state == CHECKING for one in rows) else ""
    items = "".join(f'<div class="tool {esc(one.state)}"><b>{esc(one.tool.name)}</b>'
                    f'<span class="where">{esc(where_line(one))}</span>'
                    f'<span class="where">Needed because {esc(one.tool.why)}.</span>{acts(one)}</div>'
                    for one in rows)
    return (f'<div id="machine" class="card"{again}><h2>This machine</h2><p>What the board\'s routes need here. '
            f'The board installs a tool only where the machine has none, or only one too old, and never changes '
            f'one you installed.</p>'
            f'<div class="tools">{items}</div>{last_row()}</div>')


def last_row() -> str:
    """What follows the tools: a terminal on Windows, `slipwai` for the person's own terminal on a Mac."""
    if sys.platform == "win32":
        return terminal_row(git_bash_window())
    if sys.platform == "darwin":
        return command_row(terminal_command.state(), terminal_command.profile())
    return ""


def state_words(one: Found) -> str:
    if one.lacks:
        return f"no {one.lacks}"
    return "too old" if one.state == "old" else "not installed"


def lacking_line(route: str, answers: Mapping[str, str] | None = None, look=None, inline: bool = False) -> str:
    """The line atop a start page whose route needs something the machine lacks; `""` where it has it all.
    `inline` is the paragraph form, for a card that is re-rendered whole when an answer changes.

    Read off what the machine has said so far and never waited for (`machine_probe`). While a tool the
    route needs is still out the line says that instead, with the address its page asks again at and a
    reload for a page with no script; one that did not answer in its time is said to be that, and is not
    called missing. `look` is a machine described by the caller, asked there and then."""
    if look is None:
        keys = needs(route, answers)
        missing = [one for one in machine_probe.MACHINE.read() if one.tool.key in keys and one.state != "found"]
    else:
        missing = lacking(route, answers, look)
    if not missing:
        return ""
    again = ""
    if out := [one.tool.name for one in missing if one.state == CHECKING]:
        asks = {"route": route, **{key: str((answers or {}).get(key) or "") for key in ASKED_BY},
                "inline": "1" if inline else ""}
        again = f' data-lacking="/settings/lacking.html?{esc(urlencode({k: v for k, v in asks.items() if v}))}"'
        said = (f'Checking what this machine has of {esc(", ".join(out))}… <a href="">Reload</a> if this line '
                f'stays as it is.')
    else:
        silent = [one.tool.name for one in missing if one.state == UNANSWERED]
        named = ", ".join(f"{one.tool.name} ({state_words(one)})" for one in missing if one.state != UNANSWERED)
        said = (f'This machine needs something first: {esc(named)}. <a href="/settings#machine">Settings</a> says '
                f'what each is for and installs what is missing.') if named else ""
        if silent:
            said += (f'{" " if said else ""}{esc(", ".join(silent))} did not answer within {BOUND:g} seconds, so '
                     f'whether this machine has {"it" if len(silent) == 1 else "them"} is not known. '
                     f'<a href="">Reload</a> to ask again.')
    if inline:
        return f'<p class="lacking-note"{again}>{said}</p>'
    return f'<div class="card lacking"{again}><p>{said}</p></div>'


#: The answers that decide what a route needs (`prerequisites.needs`), carried in the address a line asks at.
ASKED_BY = ("language", "backend", "profile")


def route_get(bridge: Any, where: str, query: str) -> bool:
    if where == "/settings/machine.html":
        bridge.send(200, card(), "text/html; charset=utf-8")
        return True
    if where == "/settings/lacking.html":
        asked = {key: values[0] for key, values in parse_qs(query).items()}
        line = lacking_line(asked.get("route", ""), asked, inline=bool(asked.get("inline")))
        bridge.send(200, line, "text/html; charset=utf-8")
        return True
    if where != "/settings/tool.json":
        return False
    key = (parse_qs(query).get("key") or [""])[0]
    bridge.send(200, json.dumps(tool_install.state(key)), "application/json; charset=utf-8")
    return True


def route_post(bridge: Any, where: str, held: dict) -> bool:
    if where == "/settings/terminal-command" and sys.platform == "darwin":
        action = terminal_command.add if held.get("action") == "add" else terminal_command.remove
        bridge.send(200, action(), "text/plain; charset=utf-8")
        return True
    if where == "/settings/terminal" and sys.platform == "win32":
        bridge.send(200, open_terminal(bridge.root), "text/plain; charset=utf-8")
        return True
    if where != "/settings/tool":
        return False
    key = str(held.get("key") or "")
    begun = tool_install.begin(key)
    if isinstance(begun, tool_install.Opened):
        bridge.send(202, str(begun), "text/plain; charset=utf-8")
    elif isinstance(begun, str):
        bridge.send(400, begun, "text/plain; charset=utf-8")
    else:
        bridge.send(200, f"Installing {key}…", "text/plain; charset=utf-8")
    return True

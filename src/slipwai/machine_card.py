"""*This machine*: the tools the board's routes need, found or not, on Settings and atop the start pages.

Each row of `prerequisites.TOOLS` says what this machine has of it. A row the machine has a good copy of
shows where and which version, and offers nothing. A row it lacks, or has only too old, offers *Install*
where `tool_install` has a way on this platform — for an old copy, a newer one for the board alone, the old
one left where it is — and the publisher's page where it has none.

The start pages carry one line, `lacking_line`, only where the route they begin needs something missing —
so a machine with everything sees those pages exactly as before.

**On Windows, a terminal.** The tools the board installed are on its children's `PATH` and never the
system's, so the person's own terminal has none of them. The card offers *Open a terminal here* instead:
Git Bash, in the project this window shows, started with the board's `PATH`.
"""
from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

from . import tool_install
from .page_shell import esc
from .prerequisites import Found, everything, lacking
from .shell_environment import git_bash, login_environment

STYLE = """
#machine .tools{display:grid;gap:6px;margin:10px 0 0}
#machine .tool{padding:8px 10px;border:1px solid var(--rule);border-radius:8px}
#machine .tool b{font-weight:500}
#machine .tool .where{display:block;font-size:.8rem;color:var(--ink-3);overflow-wrap:anywhere}
#machine .tool.missing .where,#machine .tool.old .where{color:var(--brass)}
#machine .acts{display:flex;flex-wrap:wrap;gap:6px;margin-top:6px;font-size:.8rem;color:var(--ink-2)}
#machine .acts button{font:inherit;font-size:.78rem;padding:3px 10px;border-radius:8px;cursor:pointer;
  border:1px solid var(--rule);background:transparent;color:var(--ink-2)}
#machine .acts button:hover{border-color:var(--teal);color:var(--ink)}
#machine .doing{font-size:.8rem;color:var(--ink-2);white-space:pre-wrap;margin:6px 0 0}
"""

SCRIPT = """
document.querySelectorAll('[data-tool]').forEach(one => one.addEventListener('click', async event => {
  event.preventDefault();
  const doing = one.closest('.tool').querySelector('.doing');
  one.disabled = true;
  const answer = await fetch('/settings/tool', {method: 'POST', headers: {'Content-Type': 'application/json'},
                                                body: JSON.stringify({key: one.dataset.tool})});
  doing.textContent = await answer.text(); doing.hidden = false;
  if (!answer.ok || answer.status === 202) { one.disabled = false; return; }
  const poll = async () => {
    const state = await (await fetch('/settings/tool.json?key=' + encodeURIComponent(one.dataset.tool))).json();
    doing.textContent = state.lines.join('\\n');
    if (state.done) location.reload(); else setTimeout(poll, 800);
  };
  poll();
}));
document.querySelectorAll('[data-terminal]').forEach(one => one.addEventListener('click', async () => {
  const said = one.parentElement.querySelector('.doing');
  const answer = await fetch('/settings/terminal', {method: 'POST', headers: {'Content-Type': 'application/json'},
                                                    body: '{}'});
  said.textContent = await answer.text(); said.hidden = false;
}));
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


def open_terminal(root: Path, window: Path | None = None) -> str:
    """Git Bash opened in `root` with the board's `PATH`; a sentence saying what happened."""
    window = git_bash_window() if window is None else window
    if window is None:
        return "There is no Git with bash on this machine yet: install it above first."
    subprocess.Popen([str(window), f"--cd={root}"], env=login_environment(),  # noqa: S603 — Git's own window
                     creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0))
    return f"Git Bash is open in {root}."


def where_line(one: Found) -> str:
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
    no way. Nothing for a good copy."""
    if one.state == "found":
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


def card(rows: list[Found] | None = None) -> str:
    """The card, for Settings."""
    rows = everything() if rows is None else rows
    items = "".join(f'<div class="tool {esc(one.state)}"><b>{esc(one.tool.name)}</b>'
                    f'<span class="where">{esc(where_line(one))}</span>'
                    f'<span class="where">Needed because {esc(one.tool.why)}.</span>{acts(one)}</div>'
                    for one in rows)
    return (f'<div id="machine" class="card"><h2>This machine</h2><p>What the board\'s routes need here. The board '
            f'installs a tool only where the machine has none, or only one too old, and never changes one you '
            f'installed.</p>'
            f'<div class="tools">{items}</div>{terminal_row(git_bash_window()) if sys.platform == "win32" else ""}'
            f'</div>')


def state_words(one: Found) -> str:
    if one.lacks:
        return f"no {one.lacks}"
    return "too old" if one.state == "old" else "not installed"


def lacking_line(route: str, answers: Mapping[str, str] | None = None, look=None, inline: bool = False) -> str:
    """The line atop a start page whose route needs something the machine lacks; `""` where it has it all.
    `inline` is the paragraph form, for a card that is re-rendered whole when an answer changes."""
    missing = lacking(route, answers, look)
    if not missing:
        return ""
    named = ", ".join(f"{one.tool.name} ({state_words(one)})" for one in missing)
    said = (f'This machine needs something first: {esc(named)}. <a href="/settings#machine">Settings</a> says '
            f'what each is for and installs what is missing.')
    if inline:
        return f'<p class="lacking-note">{said}</p>'
    return f'<div class="card lacking"><p>{said}</p></div>'


def route_get(bridge: Any, where: str, query: str) -> bool:
    if where != "/settings/tool.json":
        return False
    key = (parse_qs(query).get("key") or [""])[0]
    bridge.send(200, json.dumps(tool_install.state(key)), "application/json; charset=utf-8")
    return True


def route_post(bridge: Any, where: str, held: dict) -> bool:
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

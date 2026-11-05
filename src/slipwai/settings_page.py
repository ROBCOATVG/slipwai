"""The settings page: what runs behind the board, picked from the agents this machine has.

One question first, *Runs on*: every harness the registry can launch as an Agent Client Protocol agent,
each with where it was found or what is missing, and *Auto* — the first found — as the default. Beside it,
the model, where the chosen agent has offered one: the board shows what the agent said at `session/new`
and never a name of its own. Saved to `~/.slipwai/board.json`; a project's own `./init` answer still wins
for its console. Nothing else moves here: the theme stays in the corner of every page.

Under each agent this machine can launch: *Make ready*, which does the handshake once ahead of the first
conversation (`agent_ready.py`) and shows what the agent said of itself; and a *Sign in* per way the agent
offers, or the one line to run where the way is a terminal's.
"""
from __future__ import annotations

from typing import Any
from urllib.parse import parse_qs

from . import agent_ready
from .board_settings import AUTO, Launch, Settings, chosen, launches, read, write
from .page_shell import document, esc

STYLE = """
#settings .agents{display:grid;gap:6px;margin:10px 0 0}
#settings .agent{display:grid;grid-template-columns:auto minmax(0,1fr);gap:10px;align-items:start;padding:8px 10px;
  border:1px solid var(--rule);border-radius:8px;cursor:pointer}
#settings .agent input{margin:4px 0 0;accent-color:var(--teal)}
#settings .agent b{font-weight:600}
#settings .agent .where{display:block;font-size:.8rem;color:var(--ink-3);overflow-wrap:anywhere}
#settings .agent.missing{color:var(--ink-3)}
#settings .agent.missing b{color:var(--ink-2)}
#settings .ready{display:block;font-size:.8rem;color:var(--ink-2);margin-top:4px}
#settings .ready.fault{color:var(--brass)}
#settings .acts{display:flex;flex-wrap:wrap;gap:6px;margin-top:6px}
#settings .acts button{font:inherit;font-size:.78rem;padding:3px 10px;border-radius:999px;cursor:pointer;
  border:1px solid var(--rule);background:transparent;color:var(--ink-2)}
#settings .acts button:hover{border-color:var(--teal);color:var(--ink)}
#settings .acts code{font-size:.78rem}
#settings .doing{font-size:.8rem;color:var(--ink-2);white-space:pre-wrap;margin:6px 0 0}
#settings .model{margin-top:16px;display:grid;gap:4px;max-width:460px}
#settings .model label{font-size:.85rem;color:var(--ink-2);font-weight:500}
#settings select{font:inherit;padding:8px 10px;border:1px solid var(--rule);border-radius:8px;background:var(--paper);
  color:var(--ink)}
#settings .now{margin:14px 0 0;font-size:.88rem}
#settings .said{color:var(--brass);font-size:.88rem;margin:8px 0 0}
#settings button.go{margin-top:14px}
"""

SCRIPT = """
{
  const card = document.getElementById('settings');
  if (card) {
    const form = card.querySelector('form'), said = card.querySelector('.said');
    form.addEventListener('submit', async event => {
      event.preventDefault();
      const body = {runs_on: form.runs_on.value, model: form.model ? form.model.value : ''};
      const answer = await fetch('/settings/save', {method: 'POST', headers: {'Content-Type': 'application/json'},
                                                    body: JSON.stringify(body)});
      said.textContent = await answer.text(); said.hidden = false;
      if (answer.ok) location.reload();
    });
    const post = body => fetch('/settings/ready', {method: 'POST', headers: {'Content-Type': 'application/json'},
                                                  body: JSON.stringify(body)});
    card.querySelectorAll('[data-ready]').forEach(one => one.addEventListener('click', async event => {
      event.preventDefault();
      const key = one.dataset.ready, doing = one.closest('.agent').querySelector('.doing');
      const answer = await post({key, method: one.dataset.method || ''});
      doing.textContent = await answer.text(); doing.hidden = false;
      if (!answer.ok) return;
      const poll = async () => {
        const state = await (await fetch('/settings/ready.json?key=' + encodeURIComponent(key))).json();
        doing.textContent = state.lines.join('\n');
        if (state.done) location.reload(); else setTimeout(poll, 800);
      };
      poll();
    }));
  }
}
"""


def ready_line(one: Launch, found: dict) -> str:
    """What making the agent ready found, in a sentence: the agent's own name and version, the handshake's
    time, and how it signs in — or what went wrong."""
    if not found:
        return '<span class="ready">Not made ready yet: the first conversation would fetch and start it.</span>'
    if found.get("fault"):
        return (f'<span class="ready fault">Could not be made ready on {esc(str(found.get("at")))}: '
                f'{esc(str(found["fault"]))}</span>')
    name = f"{found.get('agent', one.name)} {found.get('version', '')}".strip()
    methods = found.get("auth") or []
    signed = found.get("signed_in") or {}
    if not methods:
        how = "no sign-in needed"
    else:
        how = "sign-in: " + ", ".join(f"{m.get('name') or m.get('id')}" + (" (done)" if m.get("id") in signed else "")
                                      for m in methods)
    return (f'<span class="ready">Ready: {esc(name)} answered in {found.get("seconds")} s on '
            f'{esc(str(found.get("at")))}; {esc(how)}.</span>')


def acts(one: Launch, found: dict) -> str:
    """The row's buttons: Make ready, and a Sign in per method of the agent's kind; the line to run for one
    of the terminal kind."""
    if not one.able:
        return ""
    buttons = [f'<button type="button" data-ready="{esc(one.key)}">'
               f'{"Make ready again" if found and not found.get("fault") else "Make ready"}</button>']
    for method in found.get("auth") or []:
        if method.get("type", "agent") == "terminal":
            buttons.append(f'<span>{esc(str(method.get("name") or method.get("id")))}: run '
                           f'<code>{esc(agent_ready.sign_in_line(one, method))}</code> in a terminal</span>')
        else:
            buttons.append(f'<button type="button" data-ready="{esc(one.key)}" '
                           f'data-method="{esc(str(method.get("id")))}">'
                           f'Sign in: {esc(str(method.get("name") or method.get("id")))}</button>')
    return f'<span class="acts">{"".join(buttons)}</span><span class="doing" hidden></span>'


def agent_row(one: Launch, picked: str, found: dict | None = None) -> str:
    found = found or {}
    return (f'<label class="agent{"" if one.able else " missing"}"><input type="radio" name="runs_on" '
            f'value="{esc(one.key)}"{" checked" if picked == one.key else ""}>'
            f'<span><b>{esc(one.name)}</b><span class="where">{esc(one.said)}</span>'
            f'{ready_line(one, found) if one.able else ""}{acts(one, found)}</span></label>')


def model_field(settings: Settings, now: Launch | None) -> str:
    if now is None or not settings.offered.get(now.key):
        return ('<p class="legend">The model is the agent\'s to offer: once a session has begun on it, what it '
                'offered is shown here to pick from.</p>')
    options = settings.offered[now.key][0]
    set_to = settings.models.get(now.key) or options.get("current")
    rows = "".join(f'<option value="{esc(str(v.get("value")))}"{" selected" if v.get("value") == set_to else ""}>'
                   f'{esc(str(v.get("name")))}</option>' for v in options.get("values") or [])
    return (f'<div class="model"><label for="model">{esc(str(options.get("name") or "Model"))}, as '
            f'{esc(now.name)} offers it</label><select id="model" name="model">{rows}</select></div>')


def page(settings: Settings, found: list[Launch], now: Launch | None) -> str:
    auto = next((one for one in found if one.able), None)
    auto_said = f"the first found: {auto.name}" if auto else "nothing this machine can launch yet"
    rows = (f'<label class="agent"><input type="radio" name="runs_on" value="{AUTO}"'
            f'{" checked" if settings.runs_on == AUTO else ""}><span><b>Auto</b>'
            f'<span class="where">{esc(auto_said)}</span></span></label>')
    rows += "".join(agent_row(one, settings.runs_on, settings.ready.get(one.key)) for one in found)
    if now is None:
        state = ("Nothing this machine can launch as an agent. The board's conversations run as they did "
                 "before, on `claude` by name, where that is on the path.")
    elif not now.able:
        state = f"Set to {now.name}, which this machine cannot launch: {now.said}."
    else:
        state = f"The board's conversations run on {now.name}."
    body = (f'<div id="settings" class="card"><h2>Runs on</h2>'
            f'<p>Which coding agent the board\'s conversations are sessions of: the first page and the console. '
            f'A project\'s own answer to <code>./init</code> still wins for its console. Every row is a harness '
            f'the registry can launch over the Agent Client Protocol, as this machine finds it.</p>'
            f'<form class="ask-page"><div class="agents">{rows}</div>{model_field(settings, now)}'
            f'<button class="go" type="submit">Save</button></form>'
            f'<p class="now">{esc(state)}</p><p class="said" hidden></p></div>')
    return document("Settings", "What runs behind the board", f"<style>{STYLE}</style>{body}", SCRIPT, now="/settings")


def route_get(bridge: Any, where: str, query: str) -> bool:
    """Answer a GET of this page's — the page, or a make-ready run's lines — or say it was not one."""
    if where == "/settings/ready.json":
        import json  # noqa: PLC0415 — one route's answer

        key = (parse_qs(query).get("key") or [""])[0]
        bridge.send(200, json.dumps(agent_ready.state(key)), "application/json; charset=utf-8")
        return True
    if where != "/settings":
        return False
    settings = read()
    found = launches()
    bridge.send(200, page(settings, found, chosen(settings)))
    return True


def route_post(bridge: Any, where: str, held: dict) -> bool:
    """Answer a POST of this page's — the save, or make ready — or say it was not one."""
    if where == "/settings/ready":
        begun = agent_ready.begin(str(held.get("key") or ""), str(held.get("method") or ""))
        if isinstance(begun, str):
            bridge.send(400, begun, "text/plain; charset=utf-8")
        else:
            bridge.send(200, f"Making {begun.launch.name} ready…", "text/plain; charset=utf-8")
        return True
    if where != "/settings/save":
        return False
    settings = read()
    runs_on = str(held.get("runs_on") or AUTO)
    keys = {one.key for one in launches()}
    if runs_on != AUTO and runs_on not in keys:
        bridge.send(400, f"{runs_on} is not a harness the registry can launch", "text/plain; charset=utf-8")
        return True
    settings.runs_on = runs_on
    model = str(held.get("model") or "")
    if model and runs_on != AUTO:
        settings.models[runs_on] = model
    write(settings)
    bridge.send(200, "saved", "text/plain; charset=utf-8")
    return True


def from_query(query: str) -> dict[str, str]:
    """Nothing the address carries is a setting; kept so the route's shape matches the other pages'."""
    return {k: v[0] for k, v in parse_qs(query).items() if k in ()}

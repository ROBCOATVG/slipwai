"""The settings page: what runs behind the board, picked from the agents this machine has.

One question first, *Runs on*: every harness the registry can launch as an Agent Client Protocol agent,
each with where it was found or what is missing, and *Auto* — the first found — as the default. Beside it,
the model, where the chosen agent has offered one: the board shows what the agent said at `session/new`
and never a name of its own. Saved to `~/.slipwai/board.json`; a project's own `./init` answer still wins
for its console. Nothing else moves here: the theme stays in the corner of every page.
"""
from __future__ import annotations

from typing import Any
from urllib.parse import parse_qs

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
  }
}
"""


def agent_row(one: Launch, picked: str) -> str:
    where = esc(one.said if one.able else one.said)
    return (f'<label class="agent{"" if one.able else " missing"}"><input type="radio" name="runs_on" '
            f'value="{esc(one.key)}"{" checked" if picked == one.key else ""}>'
            f'<span><b>{esc(one.name)}</b><span class="where">{where}</span></span></label>')


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
    rows += "".join(agent_row(one, settings.runs_on) for one in found)
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
    """Answer a GET of this page's, or say it was not one."""
    if where != "/settings":
        return False
    del query
    settings = read()
    found = launches()
    bridge.send(200, page(settings, found, chosen(settings)))
    return True


def route_post(bridge: Any, where: str, held: dict) -> bool:
    """Answer a POST of this page's — the save — or say it was not one."""
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

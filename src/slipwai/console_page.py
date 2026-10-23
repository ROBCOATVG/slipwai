"""The console's dock: a transcript, a box to type in, and three questions to start from, on every tab.

Markup, style and script for `console.py`, which holds the conversation. The dock is written closed and empty and the
script fills it from `/console.json`, so a reload that happens to land mid-answer shows the whole exchange so
far rather than a blank panel over a session that is still running. It sits bottom-right on the page rather
than in a tab, because a question about what a fleet is doing is asked from wherever the person was looking.

It does not use the board's `send`, which reloads the page after every control: a conversation that
reloaded on every question would lose the scroll and the half-typed next one. It talks to its own three
routes and draws its own turns, with `textContent` throughout — what the agent said is data, and was read
out of a project's files on the way.
"""
from __future__ import annotations

from .page_shell import esc

STARTERS = ("What is waiting on me?", "Why is anything stalled or paused?", "What happened in the last hour?")

STYLE = """
#console{position:fixed;right:16px;bottom:16px;z-index:20;display:grid;justify-items:end;gap:10px;
  max-width:calc(100vw - 32px)}
#console .launch{font:inherit;font-size:.88rem;padding:8px 16px;border-radius:999px;cursor:pointer;
  border:1px solid var(--teal);background:var(--teal);color:#fff;box-shadow:0 4px 18px rgb(0 0 0 / 30%)}
#console .panel{width:min(30rem,calc(100vw - 32px));margin:0;box-shadow:0 8px 28px rgb(0 0 0 / 35%)}
#console .panel[hidden]{display:none}
#console .log{max-height:min(22rem,45vh);min-height:5rem;overflow:auto;display:grid;gap:8px;align-content:start;
  padding:2px 2px 10px}
#console .log:empty{min-height:0;padding:0}
#console .turn{max-width:min(46rem,92%);padding:8px 12px;border-radius:10px;border:1px solid var(--rule);
  white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.45;font-size:.9rem}
#console .turn.person{justify-self:end;background:var(--teal);border-color:var(--teal);color:#fff}
#console .turn.harbourmaster{justify-self:start;background:var(--paper)}
#console .turn.read{justify-self:start;border:0;padding:0 4px;color:var(--ink-3);font-size:.78rem;
  font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
#console .turn.error{justify-self:start;border-color:var(--brass);color:var(--brass)}
#console .empty{color:var(--ink-3);font-size:.88rem;margin:0}
#console .starters{display:flex;flex-wrap:wrap;gap:6px;margin:6px 0 0}
#console .starters button{font:inherit;font-size:.8rem;padding:4px 10px;border-radius:999px;cursor:pointer;
  border:1px solid var(--rule);background:transparent;color:var(--ink-2)}
#console .starters button:hover{border-color:var(--teal);color:var(--ink)}
#console .head{display:flex;align-items:baseline;gap:10px;justify-content:space-between}
#console .head h2{margin:0}
#console .head button{font:inherit;font-size:.8rem;background:none;border:0;color:var(--ink-3);cursor:pointer}
#console .note{color:var(--ink-3);font-size:.78rem;margin:2px 0 10px}
"""

SCRIPT = """
{
  const card = document.getElementById('console');
  if (card) {
    const log = card.querySelector('.log'), input = card.querySelector('input'), go = card.querySelector('button.go');
    const empty = card.querySelector('.empty');
    const panel = card.querySelector('.panel'), launch = card.querySelector('.launch');
    const KEY = 'slipwai-console-open';
    let at = 0, busy = false, timer = null;
    const show = open => {
      panel.hidden = !open; launch.setAttribute('aria-expanded', String(open));
      try { localStorage.setItem(KEY, open ? '1' : ''); } catch (fault) { /* a private window: not remembered */ }
      if (open) { log.scrollTop = log.scrollHeight; input.focus(); }
    };
    launch.addEventListener('click', () => show(panel.hidden));
    document.addEventListener('keydown', event => { if (event.key === 'Escape' && !panel.hidden) show(false); });
    let was = false;
    try { was = !!localStorage.getItem(KEY); } catch (fault) { /* nothing remembered */ }
    show(was);
    const draw = turn => {
      const one = document.createElement('div');
      one.className = 'turn ' + (turn.kind === 'text' ? turn.role : turn.kind);
      one.textContent = turn.text;
      log.appendChild(one);
    };
    const paint = () => { input.disabled = busy; go.disabled = busy;
      go.textContent = busy ? 'Answering…' : 'Ask'; };
    const poll = async () => {
      let said;
      try { said = await (await fetch('/console.json?since=' + at)).json(); }
      catch (fault) { return; }   // the board went away: stop asking
      const stuck = log.scrollTop + log.clientHeight >= log.scrollHeight - 24;
      said.turns.forEach(draw);
      at = said.at; busy = said.busy;
      if (said.turns.length) { empty.hidden = true; if (stuck) log.scrollTop = log.scrollHeight; }
      paint();
      clearTimeout(timer);
      if (busy) timer = setTimeout(poll, 700);
    };
    const ask = async text => {
      if (!text.trim() || busy) return;
      const answer = await fetch('/console/ask', {method: 'POST', headers: {'Content-Type': 'application/json'},
                                                   body: JSON.stringify({message: text})});
      if (!answer.ok) { draw({role: 'harbourmaster', kind: 'error', text: await answer.text()}); return; }
      input.value = ''; busy = true; paint(); poll();
    };
    card.querySelector('form').addEventListener('submit', event => { event.preventDefault(); ask(input.value); });
    card.querySelectorAll('[data-ask]').forEach(one => one.addEventListener('click', () => ask(one.dataset.ask)));
    card.querySelector('[data-clear]').addEventListener('click', async () => {
      await fetch('/console/reset', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: '{}'});
      log.querySelectorAll('.turn').forEach(one => one.remove());
      empty.hidden = false; at = 0; busy = false; paint(); poll();
    });
    poll();
  }
}
"""


def console_card() -> str:
    """The dock, closed: the script above fills it from the server's copy of the conversation."""
    starters = "".join(f'<button type="button" data-ask="{esc(one)}">{esc(one)}</button>' for one in STARTERS)
    return (f'<style>{STYLE}</style><div id="console">'
            f'<div class="card panel" hidden>'
            f'<div class="head"><h2>Ask the harbourmaster</h2>'
            f'<button type="button" data-clear>New conversation</button></div>'
            f'<p class="note">It reads this project\'s logs and answers from them. It cannot change anything — '
            f'what needs doing, you do from the board.</p>'
            f'<div class="log" role="log" aria-live="polite"></div>'
            f'<p class="empty">Nothing asked yet.</p>'
            f'<div class="starters">{starters}</div>'
            f'<form class="ask"><input placeholder="Why is ORD-02 waiting on me?" autocomplete="off" '
            f'aria-label="Ask the harbourmaster"><button class="go" type="submit">Ask</button></form></div>'
            f'<button type="button" class="launch" aria-expanded="false">Ask the harbourmaster</button></div>')

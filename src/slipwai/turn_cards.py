"""The cards an agent's turns become on a board page, shared by the first page and the console.

A conversation over the Agent Client Protocol says more than words: a tool call that changes as it runs, a
plan that ticks, a permission the board could not grant on its own, a question. Each is a kind of turn
(`board_agent.py`), and each is drawn the same way wherever the conversation is. One stylesheet, scoped to
`.turns`, and one script function, `drawTurn(log, turn, reply)`, which appends a turn to a log — or changes
one already there, for an update and an answer — and returns whether the turn changed a file, which is the
first page's cue to reload the prototype. `reply(id, body)` is the page's own route for a card's answer.
Everything is `textContent`: what the agent said is data.
"""
from __future__ import annotations

STYLE = """
.turns .turn.tool{justify-self:start;border:0;padding:2px 4px;font-size:.8rem;color:var(--ink-3);display:flex;gap:8px;
  align-items:baseline;white-space:nowrap;max-width:100%;width:100%}
.turns .turn.tool b{flex:none;min-width:5.2em}
.turns .turn.tool .title{min-width:0;overflow:hidden;text-overflow:ellipsis}
.turns .turn.tool .dot{width:8px;height:8px;border-radius:50%;background:var(--rule);flex:none;align-self:center}
.turns .turn.tool.in_progress .dot{background:var(--warn)}
.turns .turn.tool.completed .dot{background:var(--good)}
.turns .turn.tool.failed .dot{background:var(--critical)}
.turns .turn.tool b{font-weight:500;color:var(--ink-2);text-transform:capitalize}
.turns .turn.tool .path{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.76rem;flex:none}
.turns .turn.tool .path:empty{display:none}
.turns .turn.waiting{justify-self:start;border:0;padding:4px 4px;color:var(--ink-3);font-size:.84rem;font-style:italic;
  animation:breathe 1.7s ease-in-out infinite}
.turns .turn.plan{justify-self:start;background:var(--ground);font-size:.84rem}
.turns .turn.plan ol{margin:0;padding-left:1.2rem}
.turns .turn.plan li.completed{color:var(--ink-3);text-decoration:line-through}
.turns .turn.plan li.in_progress{font-weight:600}
.turns .turn.permission,.turns .turn.question{justify-self:stretch;max-width:none;border-color:var(--brass);
  background:var(--brass-soft);white-space:normal}
.turns .turn.permission .path{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.8rem;display:block;
  margin-top:4px;overflow-wrap:anywhere}
.turns .turn .buttons{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px}
.turns .turn .buttons button,.turns .turn input{font:inherit;font-size:.85rem;padding:6px 12px;border-radius:8px;
  border:1px solid var(--rule);background:var(--paper);color:var(--ink)}
.turns .turn .buttons button.allow{background:var(--teal);border-color:var(--teal);color:#fff}
.turns .turn input{width:100%;margin-top:8px}
.turns .turn.done{opacity:.55}
.turns .turn.done .buttons,.turns .turn.done input{display:none}
button.stop{font:inherit;padding:8px 14px;border-radius:8px;border:1px solid var(--brass);background:var(--paper);
  color:var(--brass);cursor:pointer}
.head .on{font-size:.8rem;color:var(--ink-3);margin-left:auto}
"""

SCRIPT = """
// The line at the foot of the log while the agent is busy: what it is doing now, in a word, breathing. It
// is the one turn that is never kept — the next real turn replaces it, and the end of the turn removes it.
function drawWaiting(log, busy, thinking) {
  let had = log.querySelector('.turn.waiting');
  if (!busy) { if (had) had.remove(); return; }
  if (!had) { had = document.createElement('div'); had.className = 'turn waiting'; }
  had.textContent = thinking ? 'Thinking…' : 'Working…';
  log.appendChild(had);
}
// What a tool call's kind is called on the page: a verb a person reads, not the protocol's word.
const VERBS = {read: 'Reading', edit: 'Writing', delete: 'Deleting', move: 'Moving', search: 'Searching',
               execute: 'Running', think: 'Thinking', fetch: 'Fetching', switch_mode: 'Switching', other: 'Working'};
const drawTurn = (log, turn, reply) => {
  const card = kind => {
    const one = document.createElement('div');
    one.className = 'turn ' + kind; one.dataset.ask = turn.ask.id;
    const words = document.createElement('div'); words.textContent = turn.text; one.appendChild(words);
    return one;
  };
  if (turn.kind === 'tool_update') {
    const had = log.querySelector('[data-tool="' + turn.tool.id + '"]');
    if (!had) return false;
    had.className = 'turn tool ' + turn.tool.status;
    if (turn.text) had.querySelector('.title').textContent = turn.text;
    return turn.tool.status === 'completed' && turn.tool.kind !== 'read' && turn.tool.kind !== 'search';
  }
  if (turn.kind === 'answered') {
    const had = log.querySelector('[data-ask="' + turn.ask.id + '"]');
    if (had) had.classList.add('done');
    return false;
  }
  let one;
  if (turn.kind === 'tool') {
    one = document.createElement('div');
    one.className = 'turn tool ' + turn.tool.status; one.dataset.tool = turn.tool.id;
    one.innerHTML = '<span class="dot"></span><b></b><span class="title"></span><span class="path"></span>';
    one.querySelector('b').textContent = VERBS[turn.tool.kind] || 'Working';
    // One line, cut: an `execute` call is titled with its whole command, and a command is not the person's.
    const title = one.querySelector('.title');
    title.textContent = turn.text.length > 90 ? turn.text.slice(0, 90) + '…' : turn.text; title.title = turn.text;
    const inside = turn.tool.path.match(/\\/(brief|prototype)\\/(.*)$/);
    one.querySelector('.path').textContent = inside ? inside[1] + '/' + inside[2] : '';
  } else if (turn.kind === 'plan') {
    one = log.querySelector('.turn.plan') || document.createElement('div');
    one.className = 'turn plan'; one.innerHTML = '<ol></ol>';
    turn.plan.forEach(entry => { const li = document.createElement('li'); li.className = entry.status;
                                 li.textContent = entry.content; one.querySelector('ol').appendChild(li); });
    if (one.parentNode) return false;
  } else if (turn.kind === 'permission') {
    one = card('permission');
    const path = document.createElement('span'); path.className = 'path'; path.textContent = turn.ask.path;
    one.appendChild(path);
    const buttons = document.createElement('div'); buttons.className = 'buttons';
    turn.ask.options.forEach(option => {
      const button = document.createElement('button'); button.type = 'button'; button.textContent = option.name;
      button.className = option.kind.startsWith('allow') ? 'allow' : '';
      button.addEventListener('click', () => reply(turn.ask.id, {option: option.id}));
      buttons.appendChild(button);
    });
    one.appendChild(buttons);
  } else if (turn.kind === 'question') {
    one = card('question');
    const input = document.createElement('input'); input.placeholder = 'Your answer'; one.appendChild(input);
    const buttons = document.createElement('div'); buttons.className = 'buttons';
    const say = document.createElement('button'); say.type = 'button'; say.className = 'allow';
    say.textContent = 'Answer'; say.addEventListener('click', () => reply(turn.ask.id, {answer: input.value}));
    const no = document.createElement('button'); no.type = 'button'; no.textContent = 'Decline';
    no.addEventListener('click', () => reply(turn.ask.id, {decline: true}));
    buttons.append(say, no); one.appendChild(buttons);
  } else {
    one = document.createElement('div');
    one.className = 'turn ' + (turn.kind === 'text' ? turn.role : turn.kind);
    one.textContent = turn.text;
  }
  log.appendChild(one);
  return turn.kind === 'wrote';
};
"""

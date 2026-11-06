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
.turns{grid-template-columns:minmax(0,1fr)}
.turns .turn.tool{justify-self:start;border:0;padding:2px 4px;font-size:.8rem;color:var(--ink-3);display:flex;gap:8px;
  align-items:baseline;white-space:nowrap;max-width:100%;width:100%;min-width:0}
.turns .turn.tool b{flex:none;min-width:5.2em}
.turns .turn.tool .title{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.turns .turn.tool b,.turns .turn.tool .path{white-space:nowrap}
.turns .turn.tool .note{color:var(--critical);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0}
.turns .turn.tool .dot{width:8px;height:8px;border-radius:50%;background:var(--rule);flex:none;align-self:center}
.turns .turn.tool.in_progress .dot{background:var(--warn)}
.turns .turn.tool.completed .dot{background:var(--good)}
.turns .turn.tool.failed .dot{background:var(--critical)}
.turns .turn.tool b{font-weight:500;color:var(--ink-2)}
.turns .turn.tool .path{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.76rem;flex:none}
.turns .turn.tool .path:empty{display:none}
.turns .turn ul{margin:4px 0 0;padding-left:1.2rem}
.turns .turn li{margin:2px 0}
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
// An agent's words carry a little markdown — bold, code, bullets — and a person reading raw asterisks is
// reading the wrong thing. Only those three, built as nodes rather than HTML, so what the agent said is data.
function words(one, text) {
  const run = (into, line) => {
    const parts = line.split(/(\\*\\*[^*]+\\*\\*|`[^`]+`)/);
    for (const part of parts) {
      if (!part) continue;
      let node;
      if (part.startsWith('**') && part.endsWith('**')) {
        node = document.createElement('b'); node.textContent = part.slice(2, -2);
      }
      else if (part.startsWith('`') && part.endsWith('`')) {
        node = document.createElement('code'); node.textContent = part.slice(1, -1);
      }
      else node = document.createTextNode(part);
      into.appendChild(node);
    }
  };
  let list = null;
  for (const line of text.split('\\n')) {
    const item = line.match(/^\\s*(?:[-*]|\\d+\\.)\\s+(.*)$/);
    if (item) {
      if (!list) { list = document.createElement('ul'); one.appendChild(list); }
      const li = document.createElement('li'); run(li, item[1]); list.appendChild(li);
      continue;
    }
    list = null;
    if (one.childNodes.length) one.appendChild(document.createTextNode('\\n'));
    run(one, line);
  }
}
// What a tool call's kind is called on the page: a verb a person reads, not the protocol's word.
const VERBS = {read: 'Reading', edit: 'Writing', delete: 'Deleting', move: 'Moving', search: 'Searching',
               execute: 'Running', think: 'Thinking', fetch: 'Fetching', switch_mode: 'Switching', other: 'Working'};
// An agent that titles a call with its tool's name says less than its kind does; these names say more.
const TOOLS = {shell: 'Running', bash: 'Running', skill: 'Loading the skill', read: 'Reading', write: 'Writing',
               edit: 'Writing', glob: 'Searching', grep: 'Searching', webfetch: 'Fetching', todowrite: 'Planning',
               task: 'Delegating', list: 'Listing'};
// One line for a tool call: a verb, what it is about, and the path where that is inside the sketch. The title
// is cut to a line with the whole of it on hover; a bare tool name as the title gives way to the call's input.
function toolLine(one, turn) {
  const named = turn.text.trim(), bare = /^[a-z_]+$/.test(named);
  one.querySelector('b').textContent = (bare && TOOLS[named]) || VERBS[turn.tool.kind] || 'Working';
  const said = (bare && turn.tool.what) || (bare ? '' : named) || turn.tool.what || '';
  const title = one.querySelector('.title');
  title.textContent = said.length > 90 ? said.slice(0, 90) + '…' : said; title.title = said;
  const inside = turn.tool.path.match(/\\/(brief|prototype)(?:\\/(.*))?$/);
  one.querySelector('.path').textContent = inside ? inside[1] + (inside[2] ? '/' + inside[2] : '') : '';
}
function drawTurn(log, turn, reply) {
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
    if (turn.text || turn.tool.what || turn.tool.path) toolLine(had, turn);
    if (turn.tool.status === 'failed' && turn.tool.note) {
      let note = had.querySelector('.note');
      if (!note) { note = document.createElement('span'); note.className = 'note'; had.appendChild(note); }
      note.textContent = turn.tool.note;
    }
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
    toolLine(one, turn);
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
    if (turn.kind === 'text') words(one, turn.text); else one.textContent = turn.text;
  }
  log.appendChild(one);
  return turn.kind === 'wrote';
}
"""

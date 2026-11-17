"""The storyboard card's look and its one script: a stage seen running where its result will appear, and the
conversation with the session that drew it. Strings only, drawn by `storyboard_card.py`; what an agent or a
file says reaches the page as `textContent`, never as markup.
"""
from __future__ import annotations

STYLE = """
.stage-running h2{display:flex;gap:10px;align-items:center}
.stage-running .doing{font-family:var(--mono);font-size:.8rem;color:var(--ink-2);margin:6px 0 0;overflow-wrap:anywhere}
.tabs .count.running{background:var(--teal-soft);color:var(--teal);animation:breathe 1.7s ease-in-out infinite}
details.findings{margin-top:12px;border-top:1px solid var(--rule-2);padding-top:10px}
details.findings summary{cursor:pointer;font-size:.9rem}
details.findings h3{font-size:.82rem;font-weight:500;color:var(--ink-3);margin:12px 0 6px}
details.findings ul{margin:0;padding-left:18px;display:grid;gap:6px;font-size:.86rem}
details.findings .where{font-size:.74rem;color:var(--ink-3);margin-right:6px}
details.findings li button{margin-left:8px;font-size:.76rem;padding:2px 8px}
.verdict-gone{color:var(--brass)}
#storyboard-talk .log{max-height:min(28rem,55vh);min-height:3rem;overflow:auto;display:grid;gap:8px;
  align-content:start;padding:2px 2px 10px}
#storyboard-talk .turn{max-width:min(46rem,92%);padding:8px 12px;border-radius:10px;border:1px solid var(--rule);
  white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.45;font-size:.9rem}
#storyboard-talk .turn.person{justify-self:end;background:var(--teal);border-color:var(--teal);color:#fff}
#storyboard-talk .turn.person.queued{background:var(--paper);color:var(--teal);border-style:dashed}
#storyboard-talk .turn.person.queued::after{content:" · queued: said when its turn ends";font-size:.76rem}
#storyboard-talk .turn.person.undelivered{background:var(--paper);color:var(--brass);border:1px dashed var(--brass)}
#storyboard-talk .turn.person.undelivered::after{content:" · not delivered: say it again";font-size:.76rem}
#storyboard-talk .turn.person button{margin-left:8px;font-size:.76rem;padding:2px 8px}
#storyboard-talk .turn.agent{justify-self:start;background:var(--paper)}
#storyboard-talk .turn.error{justify-self:start;border-color:var(--brass);color:var(--brass)}
p.held{border-left:3px solid var(--brass);padding-left:10px;color:var(--ink-2);font-size:.88rem}
"""

SCRIPT = """
// The stages whose result has a tab: while one runs, its tab label is marked and a card in its result's place
// says what it is doing and for how long. Polled from the stage's own state; the page's shape reloads it
// when the stage starts and ends, so the card that replaces this one arrives by itself.
(function(){
  const clock = s => Math.floor(s / 60) + ':' + String(Math.floor(s % 60)).padStart(2, '0');
  document.querySelectorAll('[data-stage-watch]').forEach(card => {
    const command = card.dataset.stageWatch, chip = card.querySelector('[data-clock]');
    let seconds = Number(chip.dataset.seconds || 0), running = true;
    setInterval(() => { if (running) { seconds += 1; chip.textContent = 'running · ' + clock(seconds); } }, 1000);
    const poll = async () => {
      let said;
      try { said = await (await fetch('/stage/talk.json?command=' + command + '&since=999999')).json(); }
      catch (fault) { setTimeout(poll, 8000); return; }
      running = said.running; seconds = said.seconds || seconds;
      if (said.doing) card.querySelector('[data-doing]').textContent = said.doing;
      // The page reloads with the result, except while somebody is typing: then it says so, not just "ended".
      const typing = [...document.querySelectorAll('input, textarea')].some(box => box.value.trim()
        && !/^(checkbox|radio|button|submit|hidden)$/.test(box.type) && box.value !== box.defaultValue);
      if (!running) chip.textContent = typing ? 'ended · send or clear what you are typing, and the page shows it'
                                              : 'ended · putting it on the page';
      document.querySelectorAll('[data-stage-marker="' + command + '"]').forEach(one => { one.hidden = !running; });
      setTimeout(poll, running ? 2000 : 6000);
    };
    poll();
  });
})();
// The conversation with the session that drew the storyboard: the turns live, what it is doing and for how
// long, Stop, and Carry on where the board waits on the person's word. What the person types while the
// stage runs is queued, shown as queued, and said when its turn ends. Everything drawn as text, never markup.
(function(){
  const card = document.getElementById('storyboard-talk');
  const fitting = document.getElementById('fitting');
  if (!card && !fitting) return;
  const command = card ? card.dataset.command : '';
  const post = (where, body) => fetch(where, {method: 'POST', headers: {'Content-Type': 'application/json'},
                                               body: JSON.stringify(body)});
  // The stage card says why the board is not moving on by itself, with its Carry on, as this card does.
  let fittingHeld = null, fittingCarry = null;
  if (fitting) {
    fittingHeld = document.createElement('p'); fittingHeld.className = 'held'; fittingHeld.hidden = true;
    fittingCarry = document.createElement('button'); fittingCarry.type = 'button'; fittingCarry.className = 'install';
    fittingCarry.textContent = 'Carry on'; fittingCarry.hidden = true;
    // The card's own row of buttons, a child of the card: the reply form inside it is an `.ask` as well.
    const row = fitting.querySelector(':scope > .ask');
    if (row) { fitting.insertBefore(fittingHeld, row); row.appendChild(fittingCarry); }
    else { fitting.append(fittingHeld, fittingCarry); }
  }
  const log = card && card.querySelector('.log'), input = card && card.querySelector('input');
  const go = card && card.querySelector('button.go'), stop = card && card.querySelector('button.stop');
  const held = card && card.querySelector('p.held'), carry = card && card.querySelector('[data-carry-on]');
  let at = 0, busy = false, timer = null, wrote = false, polling = false;
  const reply = (id, body) => post('/stage/answer', {id, ...body});
  const draw = turn => {
    if (turn.role === 'person') {
      const one = document.createElement('div');
      one.className = 'turn person' + (turn.queued ? ' queued' : ''); one.dataset.talk = turn.id || '';
      one.textContent = turn.text; log.appendChild(one); return;
    }
    // True where a call that changed a file has finished: the storyboard's frames are drawn again after the turn.
    if (drawTurn(log, turn, reply)) wrote = true;  // the console's, which every Voyage window carries
  };
  const frames = () => document.querySelectorAll('#mockups iframe').forEach(one => { one.src = one.src; });
  // Kept and not yet said: dashed and "queued" while a run of the stage will say it, and "not delivered" with
  // a Say it now where nothing will — after a Stop, or a restart. Never a promise the board will not keep.
  const mark = said => log.querySelectorAll('.turn.person[data-talk]').forEach(one => {
    const id = one.dataset.talk, stuck = said.undelivered.find(kept => kept.id === id);
    one.classList.toggle('queued', said.queued_ids.includes(id));
    one.classList.toggle('undelivered', Boolean(stuck));
    let now = one.querySelector('button');
    if (stuck && !now) {
      now = document.createElement('button'); now.type = 'button'; now.className = 'install';
      now.textContent = 'Say it now';
      now.addEventListener('click', async () => {
        now.disabled = true;
        const answer = await post('/stage/say', {command, message: stuck.text, resend: id});
        if (!answer.ok) draw({role: 'agent', kind: 'error', text: await answer.text()});
        poll();
      });
      one.appendChild(now);
    } else if (!stuck && now) now.remove();
  });
  const once = async () => {
    const said = await (await fetch('/stage/talk.json?command=' + command + '&since=' + at)).json();
    for (const [words, button] of [[held, carry], [fittingHeld, fittingCarry]]) {
      if (!words) continue;
      words.textContent = said.held || ''; words.hidden = !said.held; button.hidden = !said.carry;
    }
    if (log) {
      const end = log.scrollTop + log.clientHeight >= log.scrollHeight - 24;
      said.turns.forEach(draw);
      at = said.at;
      mark(said);
      const was = busy; busy = said.busy;
      drawWaiting(log, busy, said.thinking, said.doing, said.for);
      if (said.turns.length && end) log.scrollTop = log.scrollHeight;
      if (was && !busy && wrote) { frames(); wrote = false; }
      go.textContent = busy || said.running ? 'Queue it' : 'Say';
      stop.hidden = !busy;
    }
    return busy || said.running;
  };
  // One poll at a time: a send's poll and the timer's would otherwise both draw the same new turns.
  const poll = async () => {
    if (polling) return;
    polling = true;
    let quick = false, failed = false;
    try { quick = await once(); } catch (fault) { failed = true; } finally { polling = false; }
    clearTimeout(timer);
    timer = setTimeout(poll, failed ? 8000 : quick ? 900 : 4000);
  };
  if (card) {
    card.querySelector('form').addEventListener('submit', async event => {
      event.preventDefault();
      const text = input.value.trim();
      if (!text) return;
      const answer = await post('/stage/say', {command, message: text});
      if (!answer.ok) { draw({role: 'agent', kind: 'error', text: await answer.text()}); return; }
      input.value = ''; input.defaultValue = ''; poll();
      log.scrollTop = log.scrollHeight;
    });
    stop.addEventListener('click', () => post('/stage/cancel', {}));
    // A finding or a question opens the conversation on it, its words in the box and nothing sent.
    document.addEventListener('click', event => {
      const about = event.target.closest('[data-talk-about]');
      if (!about) return;
      input.value = about.dataset.talkAbout;
      card.scrollIntoView({block: 'start'}); input.focus();
    });
  }
  document.addEventListener('click', async event => {
    if (!event.target.closest('[data-carry-on]') && event.target !== fittingCarry) return;
    event.target.disabled = true;
    await post('/stage/carry-on', {});
    event.target.disabled = false; poll();
  });
  poll();
})();
"""

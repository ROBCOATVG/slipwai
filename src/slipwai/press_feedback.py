"""Every press on the board says it was heard, and what came of it, without stopping the page.

manda's owner typed an answer, pressed Send, and saw nothing: the answer had gone in under a second, and the
page then reloaded itself, which took thirty-eight seconds, during which the old page stood exactly as it was —
the text still in the box, the button still a button. A failure was worse: an `alert()`, which blocks every
later event in the window. Twenty-odd handlers each did their own POST and their own reload, so this is said
once, for all of them, around what they share:

- a press marks its button pressed — disabled, `aria-busy`, a working face — the moment it is made, and lets
  go after a while if the page did not move;
- every POST the page makes is said in a status line at the foot of the window: *Working…*, then the board's
  own answer (`answered S102-decide-1 · S102: sent`) and that the page is updating, or why it was refused;
- `alert()` says its words in that line instead, so nothing blocks the window.
"""
from __future__ import annotations

STYLE = """
.press-said{position:fixed;left:16px;bottom:16px;z-index:50;max-width:min(560px,calc(100vw - 32px));padding:10px 14px;
  border-radius:10px;background:var(--ink);color:var(--paper);font-size:.9rem;line-height:1.4;
  box-shadow:0 6px 24px rgba(0,0,0,.25)}
.press-said[hidden]{display:none}
.press-said.bad{background:var(--critical);color:#fff}
.press-said.good{background:var(--teal);color:#fff}
button.pressed,a.pressed{opacity:.7;cursor:progress}
button.pressed::after{content:" …"}
"""

SCRIPT = """
(() => {
  const line = document.createElement('div');
  line.className = 'press-said'; line.hidden = true;
  line.setAttribute('role', 'status'); line.setAttribute('aria-live', 'polite');
  let gone = 0;
  const say = (words, tone, last) => {
    if (!document.body.contains(line)) document.body.appendChild(line);
    line.textContent = words; line.className = 'press-said ' + (tone || ''); line.hidden = false;
    clearTimeout(gone);
    if (last) gone = setTimeout(() => { line.hidden = true; }, last);
  };
  window.boardSay = say;
  // A reload after a press keeps the old page painted until the new one arrives, which on a large project is
  // tens of seconds: the line says so, rather than the page sitting there as if nothing had been pressed.
  window.addEventListener('beforeunload', () => {
    if (!line.hidden) say(line.textContent.replace(/ Updating the page…$/, '') + ' Updating the page…', 'good');
  });
  window.alert = words => say(String(words), 'bad', 12000);
  // The press is remembered, and marked only when it sends something: a theme toggle is not a thing in flight.
  let pressedOn = null, at = 0;
  document.addEventListener('click', event => {
    pressedOn = event.target.closest('button, a'); at = Date.now();
  }, true);
  const mark = () => {
    const press = Date.now() - at < 2000 ? pressedOn : null;
    if (!press) return;
    press.classList.add('pressed'); press.setAttribute('aria-busy', 'true');
    setTimeout(() => { press.classList.remove('pressed'); press.removeAttribute('aria-busy'); }, 15000);
  };
  const fetched = window.fetch.bind(window);
  window.fetch = async (where, how) => {
    if (!how || String(how.method || 'GET').toUpperCase() !== 'POST') return fetched(where, how);
    mark();
    say('Working…');
    try {
      const answer = await fetched(where, how);
      const words = (await answer.clone().text()).trim();
      if (answer.ok) say(words && words.length < 300 && !words.startsWith('{') ? words : 'Done', 'good', 8000);
      else say(words || ('The board refused it (' + answer.status + ')'), 'bad', 12000);
      return answer;
    } catch (fault) {
      if (fault && fault.name === 'AbortError') throw fault;
      say('The board did not answer: ' + fault, 'bad', 12000);
      throw fault;
    }
  };
})();
"""

"""A prototype that does not run says so: on the page, and to the session that drew it.

A session draws `prototype/index.html`, says "tap through it on the right", and the person looks at a white
box: one name declared at the top of its script that a browser page may not declare (`function top`), and the
whole script is dropped without a word. Nothing in the conversation knew. Two things here, neither of which
needs anything but the browser the person is already looking through:

- every prototype page is served with one line added at the head of it, which tells the page that frames it
  what failed — a script that would not parse, one that threw, a rejection nobody caught, or a page that
  loaded and drew nothing. The line is added on the way out and never written to the sketch's folder, and it
  is one line so the prototype's own line numbers stay what they are;
- the names a page cannot declare are looked for in the file itself, so the fault is known before any browser
  has opened it, and is in what the page polls.

The page shows what failed under the prototype, with one button that says it to the session in the person's
own conversation. Nothing is said to the session unasked: a turn is the person's to spend.

Under the frame too, because a prototype drawn for a whole screen is hard to judge in a third of one: a link
that opens it in a window of its own, and a button that gives it the page's full width, which the browser
remembers for next time.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

#: Names a browser gives every page that a script's top level may not declare again; one such declaration
#: and the browser refuses the whole script.
TAKEN = ("top", "window", "document", "location")
CLASH = re.compile(rf"^(?:async\s+)?(function\*?|let|const|class)\s+({'|'.join(TAKEN)})\b", re.MULTILINE)

#: The one line a prototype page is served with. No newline in it: the page's own lines keep their numbers.
REPORTER = (
    "<script>(function(){var n=0,o=location.origin;function t(m,l){if(n++<3)try{parent.postMessage("
    "{slipwaiFault:{message:String(m).slice(0,300),line:l||0}},o)}catch(e){}}"
    "addEventListener('error',function(e){if(e.message)t(e.message,e.lineno)});"
    "addEventListener('unhandledrejection',function(e){var r=e.reason;"
    "t('Unhandled rejection: '+(r&&r.message||r),0)});"
    "addEventListener('load',function(){setTimeout(function(){var b=document.body;"
    "if(!n&&(!b||!b.innerText.trim()&&!b.querySelector('img,svg,canvas,video,input,button')))"
    "t('The page loaded and drew nothing',0)},600)})})();</script>")
HEAD = re.compile(rb"<head[^>]*>", re.IGNORECASE)

#: How a session is told, in the person's conversation and by their hand.
FIX = ("The prototype does not run in the browser: {message}{where}. Fix it, and check the page loads and draws "
       "before you say it is ready.")


def with_reporter(body: bytes) -> bytes:
    """A prototype page as it is served: the reporter straight after `<head>`, or first where there is none."""
    line = REPORTER.encode()
    found = HEAD.search(body)
    return body[:found.end()] + line + body[found.end():] if found else line + body


def outgoing(path: Path, kind: str, prototype: str) -> bytes:
    """What `/brief/files/…` sends for one file: a prototype's page with the reporter, anything else as it is."""
    body = path.read_bytes()
    return with_reporter(body) if kind.startswith("text/html") and prototype in path.parts else body


def clashes(text: str) -> list[dict[str, object]]:
    """Each top-level declaration in a page's scripts of a name the browser has taken, with its line."""
    return [{"message": f"Identifier '{found.group(2)}' has already been declared: a page may not declare "
                        f"`{found.group(1)} {found.group(2)}` at the top of a script",
             "line": text.count("\n", 0, found.start()) + 1} for found in CLASH.finditer(text)]


def fault(page: Path) -> dict[str, object] | None:
    """What is known to be wrong with a prototype page without opening it, or nothing."""
    try:
        found = clashes(page.read_text(encoding="utf-8", errors="replace")) if page.is_file() else []
    except OSError:
        return None
    return found[0] if found else None


HOLDER = ('<div class="fault" hidden role="alert"><p></p>'
          '<button type="button">Ask it to fix this</button></div>')


def under(played: str, drawn: bool) -> str:
    """What sits under the prototype's frame: a way to play it in a window of its own, and the fault's holder."""
    return (f'<p class="full"{"" if drawn else " hidden"}><button type="button" class="widen" '
            f'aria-pressed="false">Show it full width</button> · <a class="quiet-link" target="_blank" '
            f'rel="noopener" href="{played}">Open the prototype in a full window</a></p>{HOLDER}')

STYLE = """
#sketch .fault { margin: 10px 0 0; padding: 10px 12px; border: 1px solid #e3b4ad; border-radius: 8px;
  background: #fdf3f1; color: #7a271d; font-size: 14px; }
#sketch .fault p { margin: 0 0 8px; }
#sketch .full { margin: 8px 0 0; font-size: 13px; }
#sketch .full .widen { font: inherit; padding: 2px 8px; }
#sketch.wide { grid-template-columns: minmax(0, 1fr); }
#sketch.wide iframe { height: 85vh; }
"""

SCRIPT = """
{
  const page = document.getElementById('sketch');
  const box = page && page.querySelector('.fault');
  if (box) {
    const frame = page.querySelector('iframe'), words = box.querySelector('p'), fix = box.querySelector('button');
    const template = __FIX__;
    let seen = null, known = null, busy = false;
    const show = () => {
      const now = known || seen;  // the file's own line where it is known: a browser names the script's
      box.hidden = !now;
      if (!now) return;
      const where = now.line ? ' (prototype/index.html, line ' + now.line + ')' : '';
      words.textContent = 'The prototype does not run: ' + now.message + where + '.';
      fix.disabled = busy; fix.dataset.say = template.replace('{message}', now.message).replace('{where}', where);
    };
    // What the framed page itself reports: only from this board's own frame, and only as words.
    window.addEventListener('message', event => {
      const said = event.data && event.data.slipwaiFault;
      if (event.origin !== location.origin || event.source !== frame.contentWindow || !said) return;
      if (!seen) { seen = {message: String(said.message || '').slice(0, 300), line: Number(said.line) || 0}; show(); }
    });
    // A redrawn prototype is a new page: what the last one reported is forgotten as it is asked for.
    const full = page.querySelector('.full');
    new MutationObserver(changes => {
      if (changes.some(one => one.attributeName === 'src')) { seen = null; show(); }
      full.hidden = frame.hidden;  // the link appears with the first drawing
    }).observe(frame, {attributes: true, attributeFilter: ['src', 'hidden']});
    document.addEventListener('brief-polled', event => {
      known = event.detail.fault || null; busy = !!event.detail.busy; show();
    });
    const widen = full.querySelector('.widen');
    const wide = on => {
      page.classList.toggle('wide', on); widen.setAttribute('aria-pressed', String(on));
      widen.textContent = on ? 'Back to side by side' : 'Show it full width';
    };
    let kept = false;
    try { kept = localStorage.getItem('slipwai-prototype-wide') === '1'; } catch (refused) {}
    wide(kept);
    widen.addEventListener('click', () => {
      const on = !page.classList.contains('wide'); wide(on);
      try { localStorage.setItem('slipwai-prototype-wide', on ? '1' : '0'); } catch (refused) {}
      if (on) frame.scrollIntoView({block: 'start', behavior: 'smooth'});
    });
    fix.addEventListener('click', () => {
      document.dispatchEvent(new CustomEvent('brief-say', {detail: fix.dataset.say}));
    });
  }
}
""".replace("__FIX__", json.dumps(FIX))

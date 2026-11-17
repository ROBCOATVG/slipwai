"""What waits on the person, said where they will see it.

A page that waits on somebody says so in its own words — *Draw the storyboard*, a card with a question on it,
a slice parked on you — and a person who has gone to another window for the ten minutes a stage takes
comes back to find the words have been there for nine. This is the one place that says *it is waiting on
you* loudly enough to be seen from elsewhere: a strip under the page's title naming the first thing and
carrying the way to it, a count on the tab's title, a badge on the installed board, and — only once they
have asked for it — a notification from the browser, while the page is not the one they are looking at.

Nothing here decides what counts as waiting; the pages do, each from what it already knows. The Voyage's
poll carries `on_you.waiting`, the one list, folded on the server from the same flags that show its buttons
and in two groups — what holds work up, and what can wait until a person has time — which the strip opens
onto, each item a link to where it is acted on. The first page folds its own from the poll it already has:
a card not yet answered, and the brief being ready to hand over; it has no groups, and the strip is a line.

The notification is a permission, so it is a switch the person throws, in the corner beside the theme, and
it stays off until they do. It is never asked for on a page's behalf: a browser's prompt on a page that
was only being read is the pattern that got every site's prompt refused.
"""
from __future__ import annotations

#: What the person's switch is remembered under, in their browser.
KEY = "slipwai-tell-me"

STYLE = """
#waiting{display:flex;flex-wrap:wrap;align-items:center;gap:10px 16px;margin:14px 0 0;padding:10px 14px;
  border:1px solid var(--brass);border-left-width:5px;border-radius:8px;background:var(--brass-soft);color:var(--ink)}
#waiting[hidden]{display:none}
#waiting .what{flex:1 1 auto;font-weight:500}
#waiting a{font:inherit;font-size:.85rem;padding:6px 12px;border-radius:7px;border:1px solid var(--brass);
  color:var(--ink);text-decoration:none;background:var(--paper);white-space:nowrap}
#waiting a:hover{background:var(--brass-soft)}
#waiting .groups{font-size:.85rem;color:var(--ink-2)}
#waiting .more{font:inherit;font-size:.85rem;padding:6px 12px;border-radius:7px;border:1px solid var(--brass);
  background:transparent;color:var(--ink);cursor:pointer}
#waiting .all{flex:1 1 100%;display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px}
#waiting .all[hidden]{display:none}
#waiting .all b{display:block;font-size:.8rem;font-weight:500;margin-bottom:4px}
#waiting .all ul{list-style:none;margin:0;padding:0;display:grid;gap:6px}
#waiting .all a{display:block;white-space:normal}
"""

#: The strip, hidden until a page has something to put in it, and the switch, hidden until the script finds
#: a browser that can notify at all.
STRIP = ('<div id="waiting" hidden role="status" aria-live="polite"><span class="what"></span>'
         '<span class="groups"></span><a href="#" class="go">Go to it</a>'
         '<button type="button" class="more" aria-expanded="false" hidden>Show all</button>'
         '<div class="all" hidden><div class="hold"><b>Holding work up</b><ul></ul></div>'
         '<div class="later"><b>When you have time</b><ul></ul></div></div></div>')
TELL = '<button class="install" id="tell-me" hidden>Tell me when it waits on me</button>'

SCRIPT = """
(function(){
  const strip = document.getElementById('waiting');
  if (!strip) return;
  const KEY = 'slipwai-tell-me', BASE = document.title;
  const what = strip.querySelector('.what'), go = strip.querySelector('a.go');
  const tell = document.getElementById('tell-me');
  const groups = strip.querySelector('.groups'), more = strip.querySelector('.more'), all = strip.querySelector('.all');
  more.addEventListener('click', () => {
    all.hidden = !all.hidden;
    more.setAttribute('aria-expanded', String(!all.hidden));
    more.textContent = all.hidden ? 'Show all' : 'Hide';
    go.hidden = !all.hidden;
  });
  // Each item is its own words and a link to where it is acted on, written as text: what a stream or a
  // slice wrote is never markup here.
  const fill = (list, items) => {
    list.closest('div').hidden = !items.length;
    list.replaceChildren(...items.map(item => {
      const line = document.createElement('li'), link = document.createElement('a');
      link.href = item.href || '#'; link.textContent = item.text;
      line.append(link);
      // Something said to a stage and not said to it: the two things to do about it, here as on its card.
      if (item.say) {
        for (const [label, where, body] of [
            ['Say it now', '/stage/say', {command: item.say.command, message: item.say.text, resend: item.say.id}],
            ['Discard', '/stage/discard', {command: item.say.command, id: item.say.id}]]) {
          const button = document.createElement('button'); button.type = 'button'; button.className = 'install';
          button.textContent = label;
          button.addEventListener('click', async () => {
            button.disabled = true;
            const answer = await fetch(where, {method: 'POST', headers: {'Content-Type': 'application/json'},
                                               body: JSON.stringify(body)});
            if (!answer.ok) { button.disabled = false; alert(await answer.text()); }
          });
          line.append(' ', button);
        }
      }
      return line;
    }));
  };
  const total = items => items.reduce((sum, item) => sum + (item.n || 1), 0);
  const can = 'Notification' in window;
  const on = () => { try { return can && Notification.permission === 'granted' && !!localStorage.getItem(KEY); }
                     catch (fault) { return false; } };
  const keep = value => { try { localStorage.setItem(KEY, value); } catch (fault) { /* a private window */ } };
  const paintTell = () => {
    if (!tell) return;
    tell.hidden = !can;
    if (can && Notification.permission === 'denied') {
      tell.textContent = 'Notifications are blocked in this browser'; tell.disabled = true; return;
    }
    tell.textContent = on() ? 'Telling you when it waits on you \\u00b7 stop' : 'Tell me when it waits on me';
  };
  if (tell) tell.addEventListener('click', async () => {
    if (on()) { keep(''); paintTell(); return; }
    if ((await Notification.requestPermission()) === 'granted') keep('1');
    paintTell();
  });
  paintTell();
  // The way to it: a tab is opened by its button, anything else is a place on the page the tab script
  // already knows how to reach.
  strip.addEventListener('click', event => {
    const link = event.target.closest('a');
    if (!link) return;
    const name = (link.getAttribute('href').match(/^#tab-([a-z]+)$/) || [])[1];
    const tab = name && document.querySelector('.tabs [data-tab="' + name + '"]');
    if (tab) { event.preventDefault(); tab.click(); }
  });
  const away = () => document.visibilityState !== 'visible' || !document.hasFocus();
  const notify = said => {
    if (!on() || !away()) return;
    const note = new Notification(BASE, {body: said.text, tag: 'slipwai:' + location.pathname + location.search});
    note.onclick = () => { window.focus(); go.click(); note.close(); };
  };
  let last;   // what was last said; the first paint is what the page opened on, and is not news
  window.waiting = {set(said) {
    const count = said && said.count ? said.count : 0;
    strip.hidden = !count;
    if (count) { what.textContent = said.text; go.setAttribute('href', said.href || '#'); }
    // The one list, where the page has it: its count, its two groups in a line, and both of them a click away.
    const hold = (said && said.holding) || [], later = (said && said.later) || [];
    const listed = hold.length + later.length > 0;
    if (listed) {
      what.textContent = 'Waiting on you \u00b7 ' + count;
      groups.textContent = [hold.length ? total(hold) + ' holding work up' : '',
                            later.length ? total(later) + ' when you have time' : ''].filter(Boolean).join(' \u00b7 ');
      fill(all.querySelector('.hold ul'), hold);
      fill(all.querySelector('.later ul'), later);
    } else {
      groups.textContent = '';
      all.hidden = true;
    }
    more.hidden = !listed;
    go.hidden = listed && !all.hidden;
    document.title = (count ? '(' + count + ') ' : '') + BASE;
    if (navigator.setAppBadge) (count ? navigator.setAppBadge(count) : navigator.clearAppBadge()).catch(() => {});
    const key = count ? said.text : '';
    if (key && last !== undefined && key !== last) notify(said);
    last = key;
  }};
})();
"""

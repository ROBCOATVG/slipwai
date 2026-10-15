"""The chrome every page of the board shares: its tokens, its type, its three-state theme, its skeleton —
and what makes it something a browser will install.

The look is the mockup's (`docs/mockups/ledger-bridge.html`) and the rule that put it here is 14.4's: the
fleet, the bridge, generation and adoption are one page, so the stylesheet, the theme toggle and the
document around them are written once and the tabs are what differ. Before this they were the bridge's,
which was fine while the bridge was the only page there was.

**Rendered, not templated over the mockup.** The mockup is 44KB of hand-written markup with its example data
in the rows; replacing a "data section" in it would mean parsing somebody's HTML and hoping. What is carried
across is the design.

**And the board is installable, which is the other half of not being a terminal.** A manifest, an icon and a
worker with a fetch handler are what a browser asks for before it offers to install a page, and an installed
board opens in its own window from the dock — no address bar, no tab, and nothing typed to get there. They
are here rather than in a module of their own because they are the same thing the rest of this file is: what
the document says about itself, as against what any one tab puts inside it.
"""
from __future__ import annotations

import html
import json

from .assets import this_command
from .brand import MARK, favicon, inline, svg

# budget: 400 — one stylesheet, one document, the bar, and the four routes an installable page is made of,
# with the seat every page carries. Splitting the stylesheet out would put the look in one file and the
# document that is the only reason it exists in another, which is the seam 14.4 removed.


#: The method's word, and the word on the page. The page never shows the left-hand column.
PLAIN = {
    "boilers": "Captains at once",
    "fanout": "Delegates per captain",
    "bunker_per_slice": "Budget per slice (k tokens)",
    "bunker_per_day": "Budget per day (k tokens)",
    "stage_scale": "Stage budgets ×",
    "bar": "Stop a merge at or above",
    "decision_ceiling": "Unread decisions allowed",
    "wait_bound": "Longest wait (minutes)",
    "attempts": "Retries per piece of work",
    "browsers": "Browser test runs at once",
    "fairway": "Stream",
    "berth": "Workspace",
    "slice": "Piece of work",
    "capability": "Capability",
}

def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


STYLE = """
:root{--ground:#f1f3f4;--paper:#fcfcfb;--ink:#172129;--ink-2:#4a5862;--ink-3:#7a8891;--rule:#d9e0e4;
--rule-2:#e9eef1;--teal:#0f6b6b;--teal-soft:#dcecea;--brass:#8a6d24;--brass-soft:#f1e9d2;--good:#0ca30c;
--warn:#fab219;--serious:#ec835a;--critical:#d03b3b;
--mono:"IBM Plex Mono",ui-monospace,Menlo,monospace;
--sans:"IBM Plex Sans",system-ui,-apple-system,"Segoe UI",Arial,sans-serif}
/* Three states, not two: Auto follows the system, and Light and Dark say so. A two-state toggle can only
   mean "the system's, or the other one", which is the setting people cannot put back. Radios and `:has()`
   rather than a script, so the published copy — which has nothing to press — still has this. */
@media (prefers-color-scheme:dark){:root:has(#t-auto:checked){--ground:#10171c;--paper:#1a1a19;
--ink:#e6ecef;--ink-2:#b6c1c8;--ink-3:#808e97;--rule:#2c3840;--rule-2:#222c33;--teal:#5fc1bb;
--teal-soft:#15302f;--brass:#d2b465;--brass-soft:#2e2814}}
:root:has(#t-dark:checked){--ground:#10171c;--paper:#1a1a19;
--ink:#e6ecef;--ink-2:#b6c1c8;--ink-3:#808e97;--rule:#2c3840;--rule-2:#222c33;--teal:#5fc1bb;
--teal-soft:#15302f;--brass:#d2b465;--brass-soft:#2e2814}
:root:has(#t-light:checked){--ground:#f1f3f4;--paper:#fcfcfb;--ink:#172129;--ink-2:#4a5862;
--ink-3:#7a8891;--rule:#d9e0e4;--rule-2:#e9eef1;--teal:#0f6b6b;--teal-soft:#dcecea;--brass:#8a6d24;
--brass-soft:#f1e9d2}
.theme{display:flex;gap:0;border:1px solid var(--rule);border-radius:7px;padding:2px;margin:0;
background:var(--rule-2)}
.theme input{position:absolute;opacity:0;pointer-events:none}
.theme label{font-size:.78rem;color:var(--ink-2);padding:4px 10px;border-radius:5px;cursor:pointer;
user-select:none}
.theme input:checked+label{background:var(--paper);color:var(--ink);box-shadow:0 1px 2px rgba(0,0,0,.1)}
.theme input:focus-visible+label{outline:2px solid var(--teal);outline-offset:1px}
.corner{display:flex;align-items:center;gap:12px}
/* Quiet: the install is worth offering and is not what the page is for. The dial's own button, in the
   colours a control that has not been pressed yet wears. */
button.install{font:inherit;font-size:.8rem;padding:6px 12px;border-radius:7px;border:1px solid var(--rule);
background:var(--paper);color:var(--ink-2);cursor:pointer}
button.install:hover{color:var(--ink);border-color:var(--teal)}
*{box-sizing:border-box}
body{margin:0;background:var(--ground);color:var(--ink);font-family:var(--sans);font-size:14px;
line-height:1.45;padding-inline:20px;padding-block:0 60px}
.wrap{max-width:1200px;margin:0 auto}
code,.mono{font-family:var(--mono);font-size:.92em}
h1{font-size:1.35rem;font-weight:600;margin:0}
.sub{color:var(--ink-3);font-size:.85rem;margin-top:3px}
.top{padding-block:22px 14px;border-bottom:1px solid var(--rule);display:flex;align-items:flex-start;
justify-content:space-between;gap:16px}
/* The mark sits in the corner and stays out of the way. `currentColor` on the hull, the spark given the
   brass of its own, so the whole thing follows the theme rather than carrying two fixed colours into a
   dark page. */
.mark{width:44px;height:44px;flex:none;color:var(--teal)}
.mark .spark{color:var(--brass)}
@media (max-width:480px){.mark{width:34px;height:34px}}
.card{background:var(--paper);border:1px solid var(--rule);border-radius:10px;padding:16px;margin-top:18px}
.card h2{font-size:.95rem;font-weight:600;margin:0 0 10px}
table{width:100%;border-collapse:collapse;font-size:.9rem}
th{text-align:left;font-weight:500;color:var(--ink-3);font-size:.78rem;text-transform:uppercase;
letter-spacing:.05em;padding:0 10px 6px 0;border-bottom:1px solid var(--rule-2)}
td{padding:8px 10px 8px 0;border-bottom:1px solid var(--rule-2);vertical-align:top}
.chip{display:inline-block;font-size:.76rem;padding:2px 8px;border-radius:999px;background:var(--rule-2);
color:var(--ink-2)}
.chip.running{background:var(--teal-soft);color:var(--teal)}
.chip.stalled{background:#fbe1d7;color:var(--critical)}
.chip[data-state="waiting on you"]{background:var(--brass-soft);color:var(--brass)}
.dial{display:flex;gap:6px;flex-wrap:wrap;margin:8px 0}
.dial button,.dial span{font:inherit;font-size:.85rem;padding:7px 14px;border-radius:7px;cursor:pointer;
border:1px solid var(--rule);background:var(--paper);color:var(--ink-2)}
.dial .now{background:var(--teal);border-color:var(--teal);color:#fff;cursor:default}
.ask{display:flex;gap:8px;margin-top:8px}
.ask input{flex:1;font:inherit;padding:7px 10px;border:1px solid var(--rule);border-radius:7px;
background:var(--paper);color:var(--ink)}
button.go{font:inherit;padding:7px 14px;border-radius:7px;border:1px solid var(--teal);background:var(--teal);
color:#fff;cursor:pointer}
dl{display:grid;grid-template-columns:1fr auto;gap:6px 16px;margin:0;font-size:.88rem}
dt{color:var(--ink-2)}
dd{margin:0;text-align:right}
dd input{font:inherit;width:110px;padding:4px 8px;border:1px solid var(--rule);border-radius:6px;
background:var(--paper);color:var(--ink);text-align:right}
.empty{color:var(--ink-3);font-size:.9rem}
/* The one link rule. Said once here rather than per page, because a browser's own blue on a page whose
   every other colour is a token is the one thing that gives away that nobody chose it. */
a{color:var(--teal)}
/* Every log on the board is a tail: bounded, scrolled, and showing its newest line without being asked.
   A log that grew the page a screen at a time pushed everything under it off the bottom, and one that
   opened at its oldest line made a reader scroll to reach the part they came for. `[data-tail]` is the
   script's half of the same rule — it pins each of these to the bottom. */
[data-tail]{max-height:280px;overflow-y:auto;overscroll-behavior:contain}
.feed{font-family:var(--mono);font-size:.78rem;color:var(--ink-2);margin:0;padding:0;list-style:none}
.feed li{padding:2px 0}
tr.drawer td{padding:0 0 8px;border-bottom:1px solid var(--rule-2)}
details.log summary{cursor:pointer;font-size:.82rem;color:var(--teal);padding:4px 0;list-style:none}
details.log summary::-webkit-details-marker{display:none}
details.log summary::before{content:"\\25B8  ";color:var(--ink-3)}
details.log[open] summary::before{content:"\\25BE  "}
ol.lines{margin:4px 0 8px;padding:8px 12px;list-style:none;background:var(--ground);border-radius:7px;
font-family:var(--mono);font-size:.78rem}
ol.lines li{padding:1px 0;color:var(--ink-2)}
ol.lines .when{color:var(--ink-3);margin-right:8px}
@media (max-width:600px){dl{grid-template-columns:1fr}dd{text-align:left}}
"""

#: The toggle. Radios because three states need three, and because `:has()` makes them work with no
#: script at all — which is what the published copy has.
THEME = """<fieldset class="theme" aria-label="Theme">
  <input type="radio" name="theme" id="t-auto" checked><label for="t-auto">Auto</label>
  <input type="radio" name="theme" id="t-light"><label for="t-light">Light</label>
  <input type="radio" name="theme" id="t-dark"><label for="t-dark">Dark</label>
</fieldset>"""

#: What a form on this page is made of. Here rather than in the page that asks the questions, because the
#: adoption tab and the interview tab ask them the same way and a second stylesheet is a second look.
FORM = """
form.ask-page{display:grid;gap:14px;margin:0}
form.ask-page .q{display:grid;gap:4px}
form.ask-page label{font-size:.85rem;color:var(--ink-2);font-weight:500}
form.ask-page .why{color:var(--ink-3);font-size:.8rem;white-space:pre-line}
form.ask-page input,form.ask-page select{font:inherit;padding:7px 10px;border:1px solid var(--rule);
border-radius:7px;background:var(--paper);color:var(--ink);width:100%;max-width:460px}
form.ask-page .no{color:var(--brass);font-size:.8rem}
pre.said{background:var(--ground);border-radius:7px;padding:10px 12px;font-family:var(--mono);
font-size:.8rem;white-space:pre-wrap;overflow-x:auto;margin:10px 0 0}
pre.said.bad{color:var(--critical)}
@keyframes breathe{0%,100%{opacity:1}50%{opacity:.5}}
#fitting .chip.running{animation:breathe 1.7s ease-in-out infinite}
nav.tabs{display:flex;gap:4px;flex-wrap:wrap;margin-top:14px;border-bottom:1px solid var(--rule)}
nav.tabs a{font-size:.88rem;color:var(--ink-2);text-decoration:none;padding:8px 14px;border-radius:7px 7px 0 0;
border:1px solid transparent;border-bottom:none;margin-bottom:-1px}
nav.tabs a:hover{color:var(--ink)}
nav.tabs a[aria-current="page"]{background:var(--paper);border-color:var(--rule);color:var(--ink);
font-weight:600}
"""


#: The board's four places, in the order a person meets them: where they are looking, and the three things
#: they do from there. Written once and read by the bar, by the server's routes and by the suite, so a fifth
#: tab is a row here rather than an edit in three files.
#:
#: **The Voyage is not one of them, and that is the point.** These four are the harbour: pointing somewhere,
#: starting a project, adopting a repository, installing a language. A voyage is one product's run, which is
#: a thing a person leaves open on another screen for an afternoon — and a tab is a thing they lose the
#: moment they press Packages. So a voyage opens in a window of its own, and the board keeps its own.
TABS: tuple[tuple[str, str], ...] = (
    ("/", "Board"),
    ("/generate", "Start a project"),
    ("/adopt", "Adopt a repository"),
    ("/packages", "Packages"),
)

#: What a page that is not one of the board's tabs carries instead: the one way back, in its own window.
#: Its own window for the same reason it is not a tab — a run window that navigated itself to the board
#: would be a run nobody is watching, and the board it went to is probably already open behind it.
AWAY = ('<nav class="tabs" aria-label="Board">'
        '<a href="/" target="_blank" rel="noopener">The board \u2197</a></nav>')


def tabs(now: str) -> str:
    """The bar, with the tab being shown marked as the one it is — or, on a page that is not one of the
    board's, the one link back to it.

    Links, not a script: a tab is a place, and a place has a URL somebody can keep. That is also what makes
    `slipwai fleet` and `slipwai bridge` deep links into one page rather than three commands that each open
    something of their own.
    """
    if not any(where == now for where, _ in TABS):
        return AWAY
    here = ' aria-current="page"'
    rows = "".join(f'<a href="{esc(where)}"{here if where == now else ""}>{esc(name)}</a>'
                   for where, name in TABS)
    return f'<nav class="tabs" aria-label="Board">{rows}</nav>'


#: The routes a browser asks for before it will install a page, and the one it is given when the board is
#: not running. Routes rather than files beside the page: the board is a server, and a manifest in the
#: page's own directory is a file the bridge has no directory to put it in.
MANIFEST, WORKER, ICON, NOT_RUNNING = "/manifest.webmanifest", "/sw.js", "/mark.svg", "/not-running.html"
#: What the installed window is. `standalone` because the board is a tool and not a document: an address
#: bar on it would be a thing to type into, which is the whole of what this is for getting rid of. The two
#: colours are the palette's light ground and its teal, which is what the window is painted with before the
#: page's own CSS has said anything.
APP: dict[str, object] = {
    "id": "/",
    "name": "slipwai — the board",
    "short_name": "slipwai",
    "description": "The fleet, the bridge, and what can be started from here.",
    "start_url": "/",
    "scope": "/",
    "display": "standalone",
    "background_color": "#f1f3f4",
    "theme_color": "#0f6b6b",
    # One drawing, twice: `any` is the icon as drawn, and `maskable` is the same one for a platform that
    # crops it to its own shape. An SVG rather than the two PNGs a manifest usually carries, because the
    # mark is an SVG and a rasteriser is a build dependency this keel does not have and would not keep.
    "icons": [{"src": ICON, "sizes": "any", "type": "image/svg+xml", "purpose": "any"},
              {"src": ICON, "sizes": "any", "type": "image/svg+xml", "purpose": "maskable"}],
}
#: What the page says about itself, on the served board only. The published copy is one file on somebody's
#: Pages site: a manifest link there would be a route that 404s, and an install offer would install a copy
#: of a board that is not theirs.
HEAD = (f'<link rel="manifest" href="{MANIFEST}">'
        f'<meta name="theme-color" content="{APP["theme_color"]}">')
#: The button, beside the theme toggle and hidden until there is something to offer. A browser that will
#: install this page says so in its address bar, which is a place somebody who was handed a URL has never
#: had a reason to look — and this page's whole argument is that a person should not have to be told where
#: things are. Shown only when the browser has offered, never as a button that explains why it cannot.
#: "this board" and not "Install": the packages tab has an Install on every row, and two buttons a thumb
#: apart meaning different things is the kind of ambiguity a person only resolves by pressing one.
INSTALL = '<button class="install" id="install" hidden>Install this board</button>'
#: Registering the worker, and keeping the browser's own offer rather than letting it go by. The worker is
#: below; what it does is answer the one request a browser makes that nothing else can — the one made when
#: the board is not running.
REGISTER = f"""
if ('serviceWorker' in navigator) navigator.serviceWorker.register('{WORKER}');
let offered = null;
window.addEventListener('beforeinstallprompt', event => {{
  event.preventDefault();
  offered = event;
  const button = document.getElementById('install');
  if (!button) return;
  button.hidden = false;
  button.addEventListener('click', () => {{ button.hidden = true; offered.prompt(); offered = null; }});
}});
window.addEventListener('appinstalled', () => {{
  const button = document.getElementById('install');
  if (button) button.hidden = true;
}});
"""


#: The window's own seat, carried in its own URL and put on everything this page asks for or links to.
#:
#: One board serves many windows, and each is a person sitting in front of a directory of their own. The
#: seat is what says which: the server mints one when a window loads a page carrying none, and from then on
#: that window's address bar carries it — a reload keeps it, and a link opened in a new window has none and
#: is given a seat of its own, which is the whole of what this is for.
#:
#: Here rather than in each page's own script, for the reason the stylesheet is here: a page that forgot
#: would quietly answer about somebody else's directory, which is the one wrong answer this board can give.
#: Rewritten on the click rather than once at load, because a card the board repaints can carry a link that
#: was not in the document when this ran.
SEATED = """
const SEAT = new URLSearchParams(location.search).get('seat') || '';
function seated(where){
  if (!SEAT || typeof where !== 'string') return where;
  const url = new URL(where, location.href);
  if (url.origin !== location.origin || url.searchParams.has('seat')) return where;
  if (url.searchParams.has('look')) return where;   // names the project it opens: it wants a seat of its own
  url.searchParams.set('seat', SEAT);
  return url.pathname + url.search + url.hash;
}
if (SEAT) {
  const plain = window.fetch.bind(window);
  window.fetch = (where, how) => plain(seated(where), how);
  document.addEventListener('click', event => {
    const link = event.target.closest ? event.target.closest('a[href]') : null;
    if (link) link.setAttribute('href', seated(link.getAttribute('href')));
  }, true);
}
"""


def manifest() -> str:
    """The web app manifest, as the route serves it."""
    return json.dumps(APP, indent=2, ensure_ascii=False) + "\n"


def icon() -> str:
    """The mark in its own colours, for the dock, the Start menu and the installed window's title bar."""
    return svg(MARK)


#: Everything goes to the network. The one page kept is the one that says the board is not running, and it
#: is served only where the fetch failed outright — a 404 from the board is the board's own answer and this
#: has nothing to add to it. A dashboard is a fold of files that change under it, so a worker that served
#: yesterday's board out of a cache would be the one view that is a memory rather than a reading.
WORKER_SOURCE = f"""
const PAGE = '{NOT_RUNNING}';
const KEPT = 'slipwai-shell-1';
self.addEventListener('install', event => {{
  event.waitUntil(caches.open(KEPT).then(cache => cache.add(PAGE)).then(() => self.skipWaiting()));
}});
self.addEventListener('activate', event => {{
  event.waitUntil(caches.keys()
    .then(names => Promise.all(names.filter(name => name !== KEPT).map(name => caches.delete(name))))
    .then(() => self.clients.claim()));
}});
self.addEventListener('fetch', event => {{
  // A window's navigation, not a frame's: a mock-up shown small on the Voyage is a frame, and one that
  // fails to load should fail, not become the not-running page in a tile.
  if (event.request.mode !== 'navigate' || event.request.destination === 'iframe') return;
  event.respondWith(fetch(event.request).catch(() => caches.match(PAGE)));
}});
"""


def not_running() -> str:
    """The page the installed window gets when nothing is listening.

    The browser's own answer is a connection error, which tells somebody who does not open terminals
    nothing they can act on. This says what has happened and the one word that puts it right — and then the
    better answer, because installing a page cannot start a server and `bridge install` means nothing has to.
    """
    body = f"""<div class="card"><h2>Nothing is serving the board on this machine</h2>
<p class="empty">The board is a server on your own machine, and installing this window did not install
that. It is running whenever <code>{esc(this_command())}</code> is.</p>
<dl><dt>Start it</dt><dd><code>{esc(this_command())}</code></dd>
<dt>Or keep it running</dt><dd><code>{esc(this_command())} bridge install</code>
 — this machine starts the board with you, and this window stops needing anybody to type anything</dd>
<dt>Then come back</dt><dd><a href="/">reload the board</a></dd></dl></div>"""
    return document("slipwai", "the board is not running", body)


def document(title: str, sub: str, body: str, script: str = "", now: str = "") -> str:
    """One page, whatever started it: the mark in the corner, the theme toggle, and the cards it was given.

    `script` is left out of the published copy by its caller, not by this: a page with nothing to press is
    a decision about the controls, and this only knows how to put a document around them. `now` is which tab
    this is; unsaid, there is no bar at all, which is what the published copy has — one file, and a link to
    a route it does not carry would be the two copies disagreeing.

    A tab is also what says this page is being served by a board rather than published as a file, so it is
    what the manifest link and the worker hang on: the same rule as the bar, for the same reason.
    """
    served = bool(now)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<link rel="icon" href="{favicon()}">
{HEAD if served else ""}
<style>{STYLE}{FORM}</style></head>
<body><div class="wrap">
<div class="top"><div><h1>{esc(title)}</h1><div class="sub">{esc(sub)}</div></div>
<div class="corner">{INSTALL if served else ""}{THEME}{inline(
    title="slipwai — the little tug that moves the big one")}</div></div>
{tabs(now) if now else ""}
{body}
</div>{"<script>" + SEATED + script + REGISTER + "</script>" if served else
       "<script>" + script + "</script>" if script else ""}</body></html>
"""

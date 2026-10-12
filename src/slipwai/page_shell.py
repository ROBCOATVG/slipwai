"""The chrome every page of the board shares: its tokens, its type, its three-state theme and its skeleton.

The look is the mockup's (`docs/mockups/ledger-bridge.html`) and the rule that put it here is 14.4's: the
fleet, the bridge, generation and adoption are one page, so the stylesheet, the theme toggle and the
document around them are written once and the tabs are what differ. Before this they were the bridge's,
which was fine while the bridge was the only page there was.

**Rendered, not templated over the mockup.** The mockup is 44KB of hand-written markup with its example data
in the rows; replacing a "data section" in it would mean parsing somebody's HTML and hoping. What is carried
across is the design.
"""
from __future__ import annotations

import html

from .brand import favicon, inline


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
.feed{font-family:var(--mono);font-size:.78rem;color:var(--ink-2);margin:0;padding:0;list-style:none}
.feed li{padding:2px 0}
tr.drawer td{padding:0 0 8px;border-bottom:1px solid var(--rule-2)}
details.log summary{cursor:pointer;font-size:.82rem;color:var(--teal);padding:4px 0;list-style:none}
details.log summary::-webkit-details-marker{display:none}
details.log summary::before{content:"\\25B8  ";color:var(--ink-3)}
details.log[open] summary::before{content:"\\25BE  "}
ol.lines{margin:4px 0 8px;padding:8px 12px;list-style:none;background:var(--ground);border-radius:7px;
font-family:var(--mono);font-size:.78rem;max-height:280px;overflow-y:auto}
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
"""


def document(title: str, sub: str, body: str, script: str = "") -> str:
    """One page, whatever started it: the mark in the corner, the theme toggle, and the cards it was given.

    `script` is left out of the published copy by its caller, not by this: a page with nothing to press is
    a decision about the controls, and this only knows how to put a document around them.
    """
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<link rel="icon" href="{favicon()}">
<style>{STYLE}{FORM}</style></head>
<body><div class="wrap">
<div class="top"><div><h1>{esc(title)}</h1><div class="sub">{esc(sub)}</div></div>
<div class="corner">{THEME}{inline(title="slipwai — the little tug that moves the big one")}</div></div>
{body}
</div>{"<script>" + script + "</script>" if script else ""}</body></html>
"""

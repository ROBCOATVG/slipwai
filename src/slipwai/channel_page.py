"""A channel's own front page: what it serves, for a person who opened the URL.

A channel is a static site, and until now the only thing at its root was a 404. The machine's answer was
there — `slipwai-languages/index.json` — and the person's was not, which is the wrong way round for a page
somebody is sent to when they want to know what a chandlery *is*.

**Generated from the entries, like the index is.** `channel build` writes both, so a release that changes
one changes the other and neither is edited by hand. That is the same rule the index has and it is here
for the same reason: a page listing packages the channel does not serve is worse than no page.

**No script, no fetch, no build step.** The list is in the markup when it is written. A page that read its
own JSON at load would be blank wherever script is off and would break the moment the shape changed,
which is a lot of fragility for a list that is already known at render time.
"""
from __future__ import annotations

import html
from typing import Any

from .brand import favicon, inline
from .index_schema import EXTENSION, LANGUAGE

#: How wide a description may run before it is cut. A channel's page is a list to scan, not prose to read.
SAID = 220


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def newest(entries: list[dict]) -> list[dict]:
    """One row per package: its newest release, by the order the entries were built in."""
    found: dict[str, dict] = {}
    for entry in sorted(entries, key=lambda one: str(one.get("version", ""))):
        found[str(entry.get("name"))] = entry
    return [found[name] for name in sorted(found)]


def described(entry: dict) -> str:
    """What the page says about a package: the entry's own line, else its manifest's, else what it offers."""
    kind = str(entry.get("kind") or "language")
    held = entry.get(kind)
    manifest: dict[str, Any] = held if isinstance(held, dict) else {}
    said = str(entry.get("description") or manifest.get("description") or "")
    if said:
        return said[:SAID] + ("…" if len(said) > SAID else "")
    backends = ", ".join(manifest.get("backends") or {}) if kind != EXTENSION else ""
    return f"backends: {backends}" if backends else "no description"


#: The verb that installs each kind. A kind absent from this is one a channel may list and this keel has no
#: way to install — a target, until the clouds themselves are packages — and the page says so by offering no
#: command rather than by printing `slipwai install <name>`, which would go looking for a language.
INSTALLS = {LANGUAGE: "install", EXTENSION: "extension install"}


def row(entry: dict, base: str) -> str:
    kind = str(entry.get("kind") or LANGUAGE)
    name = str(entry.get("name"))
    verb = INSTALLS.get(kind)
    return f"""      <tr>
        <td><b>{esc(name)}</b></td>
        <td><span class="kind">{esc(kind)}</span></td>
        <td class="mono">{esc(entry.get("version"))}</td>
        <td>{esc(entry.get("publisher") or "—")}</td>
        <td>{esc(described(entry))}</td>
        <td class="mono cmd">{f"slipwai {esc(verb)} {esc(name)}" if verb else "—"}</td>
      </tr>"""


STYLE = """
:root{--ground:#f1f3f4;--paper:#fcfcfb;--ink:#172129;--ink-2:#4a5862;--ink-3:#7a8891;--rule:#d9e0e4;
--rule-2:#e9eef1;--teal:#0f6b6b;--brass:#8a6d24;
--mono:"IBM Plex Mono",ui-monospace,Menlo,monospace;
--sans:"IBM Plex Sans",system-ui,-apple-system,"Segoe UI",Arial,sans-serif}
@media (prefers-color-scheme:dark){:root{--ground:#10171c;--paper:#1a1a19;--ink:#e6ecef;--ink-2:#b6c1c8;
--ink-3:#808e97;--rule:#2c3840;--rule-2:#222c33;--teal:#5fc1bb;--brass:#d2b465}}
*{box-sizing:border-box}
body{margin:0;background:var(--ground);color:var(--ink);font-family:var(--sans);font-size:15px;
line-height:1.5;padding-inline:20px;padding-block:0 60px}
.wrap{max-width:1040px;margin:0 auto}
.top{display:flex;align-items:flex-start;justify-content:space-between;gap:16px;
padding-block:26px 16px;border-bottom:1px solid var(--rule)}
h1{font-size:1.4rem;font-weight:600;margin:0;letter-spacing:-.01em}
.sub{color:var(--ink-3);font-size:.9rem;margin-top:4px}
.mark{width:46px;height:46px;flex:none;color:var(--teal)}
.mark .spark{color:var(--brass)}
.card{background:var(--paper);border:1px solid var(--rule);border-radius:10px;padding:18px;margin-top:20px}
h2{font-size:.98rem;font-weight:600;margin:0 0 12px}
table{width:100%;border-collapse:collapse;font-size:.9rem}
th{text-align:left;font-weight:500;color:var(--ink-3);font-size:.76rem;text-transform:uppercase;
letter-spacing:.05em;padding:0 12px 7px 0;border-bottom:1px solid var(--rule-2)}
td{padding:10px 12px 10px 0;border-bottom:1px solid var(--rule-2);vertical-align:top}
.mono,code,pre{font-family:var(--mono)}
.cmd{color:var(--teal);white-space:nowrap;font-size:.84rem}
.kind{font-size:.76rem;padding:2px 8px;border-radius:999px;background:var(--rule-2);color:var(--ink-2)}
pre{background:var(--ground);border-radius:8px;padding:12px 14px;overflow-x:auto;font-size:.84rem;margin:0}
a{color:var(--teal)}
.empty{color:var(--ink-3)}
@media (max-width:640px){.cmd{white-space:normal}table{font-size:.84rem}}
"""


def page(name: str, entries: list[dict], base: str = "") -> str:
    """The channel's front page: what it serves, and the one command that installs each of them."""
    rows = newest(entries)
    listing = ("\n".join(row(entry, base) for entry in rows) if rows else "")
    table = (f"""<table>
      <tr><th>Package</th><th>Kind</th><th>Version</th><th>Publisher</th><th>What it is</th>
          <th>Install it</th></tr>
{listing}
    </table>""" if rows else '<p class="empty">This channel serves nothing yet.</p>')
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(name)}</title>
<meta name="description" content="A slipwai chandlery: the languages and extensions this channel serves.">
<link rel="icon" href="{favicon()}">
<style>{STYLE}</style></head>
<body><div class="wrap">
  <div class="top">
    <div>
      <h1>{esc(name)}</h1>
      <div class="sub">A slipwai chandlery — {len(rows)} package(s). Point slipwai at it and install one.</div>
    </div>
    {inline(title="slipwai")}
  </div>

  <div class="card"><h2>Using it</h2>
<pre>export SLIPWAI_CHANDLERY={esc(base) or "&lt;this page's URL&gt;"}
slipwai search
slipwai install &lt;a language&gt;
slipwai generate myapp --backend &lt;that language&gt;</pre>
  </div>

  <div class="card"><h2>What it serves</h2>
    {table}
  </div>

  <div class="card"><h2>Publishing to it</h2>
    <p>Four commands, and <a href="CONTRIBUTING.md">CONTRIBUTING.md</a> is the whole of it.</p>
<pre>slipwai package new &lt;name&gt;
slipwai package version .
slipwai package check .
slipwai package register . --channel &lt;a checkout of this repository&gt;</pre>
    <p class="empty">A name belongs to its first publisher, and a release is immutable. The machine's
    view of this channel is <a href="slipwai-languages/index.json">slipwai-languages/index.json</a>.</p>
  </div>
</div></body></html>
"""

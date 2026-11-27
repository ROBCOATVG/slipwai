"""Trunk on the board: a band on the Voyage while it is red, a card on the Fleet tab with what the mender did.

On the owner's first real fleet run trunk was red from the first commit, the trunk mender tried twice and
gave up — correctly, since the only fix was one its brief forbids — and the board showed none of it: no
band, no attempt, none of the mender's words, nothing waiting on anybody, while every slice that reached
its merge would have waited behind a red trunk. This draws `trunk_story`'s fold in three places:

- **the band**, above the Voyage's tabs where the passage and what to expect sit, whenever trunk is red: at
  which commit, since when, which jobs, that no merge is granted meanwhile, and what is being done — the
  attempt in flight, a fix landed and waiting on CI, or the mender spent and a person deciding. Briefly
  green once a mended trunk passes; empty otherwise. Its holder is always on the page and the poll swaps
  what is inside it, so turning red is never a change of the page's shape and never a reload;
- **the card** on the Fleet tab: each attempt, what the one in flight is doing, the mender's own last
  answer rendered as a document is (`spec_page.rendered`, which escapes before it marks anything up, with a
  link kept only where it is to the web), and the CI run's link where the run carries one;
- **the item** under *Waiting on you*, while a harbour park stands.

And the folder the board reads, against the forge's trunk (`checkout_level`, slipwai#166): a band at the top
while it is behind, with the count, so an old project is never drawn as the current one; and an item under
*Waiting on you* while the local trunk holds commits the forge's does not, naming them and how to land them.

Every word that came from the log or the agent is escaped here; none of it reaches the page as markup.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from .fleet_page import first_sentence, plural, when
from .page_shell import esc
from .spec_page import STYLE as DOC_STYLE
from .spec_page import rendered
from .stuck import minutes, now_stamp, stamp
from .trunk_story import BRIEFLY

STYLE = DOC_STYLE + """
#trunk{display:grid;gap:6px;border-left:5px solid var(--critical);background:var(--critical-soft)}
#trunk.green{border-left-color:var(--teal);background:var(--teal-soft)}
#trunk .head{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:baseline;gap:4px 12px}
#trunk h2{margin:0;color:var(--critical);font-size:1.05rem}#trunk.green h2{color:var(--teal)}
#trunk .head span{font-size:.84rem;color:var(--ink-2)}
#trunk p{margin:0;font-size:.9rem;line-height:1.45;overflow-wrap:anywhere}
#trunk .doing{font-weight:500}
#trunk a{font-size:.85rem;width:fit-content;padding:6px 12px;border-radius:7px;border:1px solid var(--critical);
  color:var(--ink);background:var(--paper);text-decoration:none}
#trunk-mend .mend-rows{display:grid;font-size:.86rem;margin:8px 0}
#trunk-mend .mend-row{display:grid;grid-template-columns:90px 110px minmax(0,1fr) minmax(0,2fr);gap:4px 10px;
  border-top:1px solid var(--rule-2);padding:6px 0;align-items:baseline}
#trunk-mend .mend-row code{font-family:var(--mono);font-size:.8rem;overflow-wrap:anywhere}
#trunk-mend .mended{color:var(--teal)}#trunk-mend .failed{color:var(--critical)}
#trunk-mend .why{color:var(--ink-2);overflow-wrap:anywhere}
#trunk-mend .mend-doing{font-family:var(--mono);font-size:.78rem;list-style:none;margin:6px 0;padding:8px 10px;
  display:grid;gap:3px;background:var(--rule-2);border-radius:6px;overflow-wrap:anywhere}
#trunk-mend details{margin-top:8px}#trunk-mend summary{cursor:pointer;font-weight:500}
#trunk-mend .doc{margin-top:8px;max-height:560px;overflow:auto;padding:4px 12px;border:1px solid var(--rule);
  border-radius:7px;background:var(--paper)}
#trunk-mend .runs{display:flex;flex-wrap:wrap;gap:8px;font-size:.85rem}
#checkout{display:grid;gap:6px;border-left:5px solid var(--brass);background:var(--brass-soft)}
#checkout h2{margin:0;font-size:1.05rem}
#checkout p{margin:0;font-size:.9rem;line-height:1.45;overflow-wrap:anywhere}
#checkout code{font-family:var(--mono);font-size:.82rem}
@media (max-width:640px){#trunk-mend .mend-row{grid-template-columns:1fr 1fr}#trunk-mend .mend-row .why{
  grid-column:1 / -1}}
"""

#: A link the agent's Markdown made, kept only where it goes to the web; any other address is dropped.
ADDRESS = re.compile(r'<a href="(?!https?://)[^"]*" rel="noopener">(.*?)</a>')


def document(text: str) -> str:
    """The mender's Markdown as the board renders a document: escaped first, then marked up."""
    return ADDRESS.sub(r"\1", rendered(text))


def ago(instant: str, now: float | None = None) -> str:
    seconds = stamp(instant)
    return minutes((now or now_stamp()) - seconds) if seconds else ""


def doing(trunk: dict[str, Any], now: datetime | None = None) -> str:
    """What is being done about a red trunk, in one or two sentences."""
    tried, of = trunk.get("attempts") or [], trunk.get("of") or 3
    parked = trunk.get("parked") or {}
    clears = ("Nothing on the board clears it but trunk going green: fix trunk on main, and merges resume once "
              "its CI passes.")
    if parked:
        if not parked.get("mend"):
            return f"Nobody is sent to fix it: a person decides. {clears}"
        spent = len(tried)
        last = next((one["why"] for one in reversed(tried) if one["why"]), "")
        return (f"The trunk mender could not clear it: {spent} attempt{'s' if spent != 1 else ''} spent. A person "
                f"decides what happens. {clears}" + (f" The last attempt: {last}." if last else ""))
    if not tried:
        return ("The mender is off for this project, so a person fixes trunk." if trunk.get("off")
                else "The trunk mender has not started yet: the harbour sends it on its next pass.")
    last = tried[-1]
    running = trunk.get("running") or {}
    if last["outcome"] == "running":
        took = minutes(now_stamp() - running["started"]) if running.get("started") else ""
        return (f"The trunk mender is on attempt {last['attempt']} of {of}, started {when(last['t'], now)}"
                + (f" · {took} in." if took else "."))
    if last["outcome"] == "mended":
        return (f"The mender's fix landed as {last['landed'][:8]} (attempt {last['attempt']} of {of}); trunk's CI "
                f"has not passed on it yet.")
    if last["outcome"] == "failed":
        return (f"Attempt {last['attempt']} of {of} ended without clearing it: {last['why']}. The next starts on "
                f"the harbour's next pass." if last["attempt"] < of else
                f"Attempt {last['attempt']} of {of} ended without clearing it: {last['why']}.")
    return f"Attempt {last['attempt']} of {of} started {when(last['t'], now)}; no word from it yet."


def band_html(trunk: dict[str, Any], now: datetime | None = None) -> str:
    """The Voyage's band: red with what is being done, green for a while after a mended trunk passes, or ""."""
    if trunk.get("state") == "green":
        landed = [one for one in trunk.get("attempts") or [] if one["outcome"] == "mended"]
        green = stamp(trunk.get("green_t") or "")
        if not landed or not green or now_stamp() - green > BRIEFLY:
            return ""
        return (f'<div class="card green" id="trunk" role="status"><div class="head"><h2>Trunk is green again'
                f'</h2><span>since {esc(when(trunk["green_t"], now))}</span></div><p>Mended at '
                f'<code>{esc(landed[-1]["landed"][:8])}</code> by the trunk mender\'s attempt '
                f'{esc(landed[-1]["attempt"])}. Merges are granted again.</p></div>')
    if trunk.get("state") != "red":
        return ""
    commit = str(trunk.get("commit") or "")[:8]
    since = trunk.get("red_t") or trunk.get("t") or ""
    jobs = trunk.get("job") or ""
    return (f'<div class="card red" id="trunk" role="status"><div class="head"><h2>Trunk is red'
            f'{" at " + esc(commit) if commit else ""}</h2><span>since {esc(when(since, now))} · '
            f"{esc(ago(since))}</span></div>"
            + (f"<p>Failed: <code>{esc(jobs)}</code></p>" if jobs else "")
            + "<p>No merge is granted until trunk is green: a slice that reaches its merge waits there.</p>"
            f'<p class="doing">{esc(doing(trunk, now))}</p>'
            '<a href="#trunk-mend">What the mender did and said</a></div>')


def held_item(trunk: dict[str, Any]) -> list[dict[str, Any]]:
    """The harbour's park as an item under *Waiting on you*, while trunk is red and it stands."""
    parked = trunk.get("parked") or {}
    if trunk.get("state") != "red" or not parked:
        return []
    why = first_sentence(str(parked.get("why") or "trunk is red and nobody is sent to fix it"), 170)
    return [{"n": 1, "href": "#trunk", "text": f"Trunk: {why}"}]


def checkout_band(trunk: dict[str, Any]) -> str:
    """Above the Voyage while the folder the board reads is behind the forge's trunk — by how much, and how to
    bring it level — or while its local trunk has commits of its own, which are landed first."""
    level = trunk.get("checkout") or {}
    behind, name = int(level.get("behind") or 0), str(level.get("trunk") or "main")
    stranded = [str(one) for one in level.get("stranded") or []]
    if behind <= 0 and not stranded:
        return ""
    own = (f"<p>Local <code>{esc(name)}</code> has {esc(plural(len(stranded), 'commit'))} the forge's does not, "
           f"and nothing pushes them: {esc('; '.join(one[:80] for one in stranded[:5]))}"
           f"{esc(f'; and {len(stranded) - 5} more') if len(stranded) > 5 else ''}. Put them on a branch and push "
           f"it — <code>git branch keep-local {esc(name)}</code>, <code>git push origin keep-local</code> — and "
           f"open a pull request. Never reset or rebase <code>{esc(name)}</code> over them.</p>" if stranded else "")
    if behind <= 0:
        return (f'<div class="card" id="checkout" role="status"><h2>This checkout has commits trunk does not'
                f"</h2>{own}</div>")
    then = (f"Once they are on the forge, <code>git switch -C {esc(name)} origin/{esc(name)}</code> here brings "
            f"it level; until then it stays behind." if stranded else
            "<code>git pull --ff-only</code> here brings it level.")
    return (f'<div class="card" id="checkout" role="status"><h2>This checkout is '
            f"{esc(plural(behind, 'commit'))} behind the forge's {esc(name)}</h2><p>The board reads the project "
            f"from this folder, so what it draws is that older project: slices merged since are not on it."
            f"</p>{own}<p>{then}</p></div>")


def unlanded_item(trunk: dict[str, Any]) -> list[dict[str, Any]]:
    """A stage branch the harbourmaster would not land, as one item under *Waiting on you* each: the work is on
    the forge only as that branch, and nothing tries it again by itself."""
    return [{"n": 1, "href": "#checkout",
             "text": f"{one['branch']} was not landed on trunk: {first_sentence(one['why'], 170)} Fix it on that "
                     f"branch and run `python3 scripts/agents/landing.py` again, or open a pull request from it"}
            for one in trunk.get("unlanded") or []]


def stranded_item(trunk: dict[str, Any]) -> list[dict[str, Any]]:
    """The local trunk's own commits, which nothing pushes, as one item under *Waiting on you*."""
    level = trunk.get("checkout") or {}
    stranded = [str(one) for one in level.get("stranded") or []]
    if not stranded:
        return []
    name = str(level.get("trunk") or "main")
    listed = "; ".join(one[:80] for one in stranded[:3]) + (f"; and {len(stranded) - 3} more"
                                                             if len(stranded) > 3 else "")
    return [{"n": 1, "href": "#checkout",
             "text": f"Local {name} has {plural(len(stranded), 'commit')} the forge's {name} does not, and nothing "
                     f"pushes them: {listed}. Put them on a branch and push it"}]


def attempt_row(one: dict[str, Any], now: datetime | None = None) -> str:
    word = {"mended": "mended", "failed": "did not clear it", "running": "running", "ending": "ended, being read",
            "no word": "no word yet"}.get(one["outcome"], one["outcome"])
    told = (f"landed as {one['landed'][:8]}" if one["outcome"] == "mended" else one["why"]) or ""
    branch = f" · <code>{esc(one['branch'])}</code>" if one["branch"] else ""
    return (f'<div class="mend-row"><b>Attempt {esc(one["attempt"])}</b><span>{esc(when(one["t"], now))}</span>'
            f'<span class="{esc(one["outcome"])}">{esc(word)} · <code>{esc(one["commit"][:8])}</code>{branch}'
            f'</span><span class="why">{esc(told)}</span></div>')


def mend_card(trunk: dict[str, Any], now: datetime | None = None) -> str:
    """The Fleet tab's Trunk card: the attempts, what the one in flight is doing, and the mender's own words.
    Nothing where trunk has never been red."""
    tried = trunk.get("attempts") or []
    if trunk.get("state") != "red" and not tried:
        return ""
    said = trunk.get("said") or {}
    if trunk.get("state") == "red":
        head = (f"Red at {str(trunk.get('commit') or '')[:8]} since {when(trunk.get('red_t') or '', now)}. "
                f"{doing(trunk, now)}")
    else:
        head = (f"Green since {when(trunk.get('green_t') or '', now)}. The last red was at "
                f"{str(trunk.get('commit') or '')[:8]}, from {when(trunk.get('red_t') or '', now)}.")
    rows = "".join(attempt_row(one, now) for one in tried)
    rows = (f'<div class="mend-rows">{rows}</div>' if rows else
            '<p class="empty">No attempt yet.</p>')
    live = ""
    if tried and tried[-1]["outcome"] == "running":
        lines = "".join(f"<li>{esc(line)}</li>" for line in said.get("doing") or [])
        live = (f"<h3>What attempt {esc(tried[-1]['attempt'])} is doing</h3>"
                + (f'<ul class="mend-doing">{lines}</ul>' if lines else '<p class="empty">Nothing said yet.</p>'))
    answer = ""
    if said.get("result"):
        opened = " open" if trunk.get("state") == "red" and not live else ""
        answer = (f'<details data-card="mender-said"{opened}><summary>The mender\'s last answer</summary>'
                  f'<div class="doc">{document(said["result"])}</div></details>')
    runs = "".join(f'<a href="{esc(url)}" target="_blank" rel="noopener">CI run {n}</a>'
                   for n, url in enumerate(trunk.get("urls") or [], 1))
    runs = f'<p class="runs">{runs}</p>' if runs else ""
    return (f'<div class="card" id="trunk-mend"><h2>Trunk</h2><p>{esc(head)}</p>{rows}{live}{answer}{runs}</div>')

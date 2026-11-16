"""The decision log drawn: a card per decision, the Decisions tab, and the tab in each slice's window.

A card leads with the entry's plain sentence — what the product now does, in words a product owner reads
without the specification open — and an entry written before that rule leads with its question instead.
Under it, the options with the one taken marked, who decided, how sure they were, what would change it and
its status; the entry as the agent wrote it is one click away. A card that awaits a person has Confirm.

**The tab opens on what awaits a person.** Every entry a stop meant for a person wrote with nobody there
stands as `awaiting human confirmation`; those come first, then the rest, each part grouped by capability
and then by slice. The count on the tab is that first part. The filters — stream, slice, who decided — are
kept in the address, and sit outside the band the page's one poll swaps, so a decision landing appears
without a reload, and a card a person has open stays open.

*Change this* opens the Feedback box with the decision quoted and its slice as the context. The conversation
windows a person will later say this to the slice in — its captain's once it has merged — are another
stream's (F, `docs/captain-agent-plan.md`); when they land, this button hands to them instead.
"""
from __future__ import annotations

import hashlib
import re
from collections.abc import Callable
from pathlib import Path

from .decision_entry import Option, chosen, options, plain
from .decision_log import Decision, decisions
from .feedback_card import opener
from .page_shell import esc

#: The parts of the entry shown as the agent wrote them, behind "Why, in full".
WRITTEN = ("Question", "Options", "Why", "Read against", "Written to")
#: A slice id the Feedback box accepts as its context; a stage's name is not one.
_SLICE = re.compile(r"[A-Za-z0-9_.-]{1,40}")

STYLE = """
.decs .head{display:flex;flex-wrap:wrap;gap:4px 14px;align-items:baseline;justify-content:space-between}
.decs .head h2{margin:0}.decs .says{font-size:.84rem;color:var(--ink-2)}
.decs .bar{display:flex;flex-wrap:wrap;gap:8px 14px;align-items:center;margin:10px 0}
.decs .bar label{font-size:.84rem;color:var(--ink-2);display:flex;gap:6px;align-items:center}
.decs .bar select{font:inherit;font-size:.84rem;min-height:32px;max-width:220px}
.decs .part{font-size:.9rem;margin:18px 0 6px;color:var(--ink);text-transform:none;letter-spacing:0}
.decs .group{display:grid;gap:8px;margin:8px 0 14px}
.decs .group>h4{margin:0;font-size:.84rem;font-weight:600;color:var(--ink-2);padding-bottom:4px;
  border-bottom:1px solid var(--rule)}
.decs .group h5{margin:4px 0 0;font-size:.78rem;font-weight:500;color:var(--ink-3)}
.decs article{border:1px solid var(--rule);border-radius:8px;padding:12px 14px;display:grid;gap:8px;
  background:var(--paper)}
.decs article.awaiting{border-color:var(--brass)}
.decs article.yours{border-left:3px solid var(--teal)}
.decs article[hidden],.decs .group[hidden],.decs .part[hidden]{display:none}
.decs .meta{display:flex;flex-wrap:wrap;gap:4px 10px;font-size:.76rem;color:var(--ink-2)}
.decs .num{font-family:var(--mono);color:var(--ink-3)}
.decs .status{font-weight:600;color:var(--teal)}.decs article.awaiting .status{color:var(--brass)}
.decs .lead{margin:0;font-size:.98rem;font-weight:600;line-height:1.4;color:var(--ink);text-transform:none;
  letter-spacing:0}
.decs .asked{font-size:.76rem;color:var(--ink-3)}
.decs .opts{list-style:none;margin:0;padding:0;display:grid;gap:4px}
.decs .opts li{display:flex;gap:8px;align-items:baseline;padding:6px 10px;border-radius:6px;
  border:1px solid var(--rule);font-size:.86rem;line-height:1.4;color:var(--ink-2)}
.decs .opts li.chosen{border-color:var(--teal);background:var(--teal-soft);color:var(--ink)}
.decs .opts .pick{flex:0 0 84px;font-size:.72rem;font-weight:600;color:var(--ink-3);white-space:nowrap}
.decs .opts li.chosen .pick{color:var(--teal)}
.decs .opts .rec{font-size:.72rem;color:var(--ink-3);white-space:nowrap}
.decs .said,.decs .rev{margin:0;font-size:.84rem;color:var(--ink-2);white-space:pre-wrap;overflow-wrap:anywhere}
.decs details summary{cursor:pointer;font-size:.84rem;color:var(--teal)}
.decs dl{display:grid;grid-template-columns:max-content minmax(0,1fr);gap:4px 12px;margin:8px 0 0;font-size:.82rem}
.decs dt{color:var(--ink-3)}.decs dd{margin:0;color:var(--ink-2);white-space:pre-wrap;overflow-wrap:anywhere}
.decs .acts{display:flex;flex-wrap:wrap;gap:6px}
.decs .acts a{font-size:.84rem;padding:6px 12px;border-radius:6px;border:1px solid var(--brass);color:var(--brass);
  text-decoration:none}
@media (max-width:620px){.decs dl{grid-template-columns:1fr}.decs .opts li{flex-direction:column;gap:2px}
  .decs .opts .pick{flex:none}}
"""

SCRIPT = """
// The decision cards: filtered in place with the choice kept in the address, and Mark read and Confirm
// written without a reload. The poll swaps the cards whole, so the filter is put back on what it brings.
(function(){
  const box = () => document.querySelector('.decs');
  if (!box()) return;
  const FILTERS = ['stream', 'slice', 'by'];
  const where = () => new URLSearchParams(location.search);
  const options = () => {
    const bar = document.querySelector('.decs .bar');
    if (!bar) return;
    FILTERS.forEach(name => {
      const pick = bar.querySelector('select[name=d-' + name + ']');
      const now = where().get('d-' + name) || pick.value;
      const seen = [...new Set([...document.querySelectorAll('.decs article')].map(one => one.dataset[name])
        .filter(Boolean))].sort();
      pick.replaceChildren(new Option(pick.dataset.every, ''), ...seen.map(one => new Option(one, one)));
      pick.value = seen.includes(now) ? now : '';
      pick.querySelectorAll('option').forEach(one => { one.defaultSelected = one.selected; });
    });
  };
  const filter = () => {
    const bar = document.querySelector('.decs .bar');
    const wanted = {};
    if (bar) FILTERS.forEach(name => { wanted[name] = bar.querySelector('select[name=d-' + name + ']').value; });
    document.querySelectorAll('.decs article').forEach(one => {
      one.hidden = FILTERS.some(name => wanted[name] && one.dataset[name] !== wanted[name]);
    });
    document.querySelectorAll('.decs .group, .decs .part').forEach(one => {
      const block = one.classList.contains('part') ? one.nextElementSibling : one;
      one.hidden = Boolean(block) && !block.querySelector('article:not([hidden])');
    });
    const left = document.querySelector('.decs .shown');
    if (left) left.textContent = document.querySelector('.decs article:not([hidden])') ? ''
      : 'Nothing here: no decision matches this filter.';
  };
  const keep = () => {
    const now = where();
    document.querySelectorAll('.decs .bar select').forEach(one => {
      if (one.value) now.set(one.name, one.value); else now.delete(one.name);
    });
    const query = now.toString();
    history.replaceState(null, '', location.pathname + (query ? '?' + query : '') + location.hash);
  };
  const post = async (path, body) => {
    const answer = await fetch(path, {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify(body)});
    if (!answer.ok) { alert(await answer.text()); return false; }
    return true;
  };
  document.addEventListener('change', event => {
    if (event.target.closest('.decs .bar')) { keep(); filter(); }
  });
  document.addEventListener('click', async event => {
    const read = event.target.closest('[data-decision-read]');
    const sure = event.target.closest('[data-decision-confirm]');
    const card = (read || sure) && (read || sure).closest('article');
    if (read && await post('/decisions/read', {keys: [read.dataset.decisionRead]})) {
      card.classList.add('read'); read.remove();
    }
    if (sure) {
      sure.disabled = true;
      if (await post('/decisions/confirm', {key: sure.dataset.decisionConfirm})) {
        card.classList.remove('awaiting'); card.classList.add('read'); sure.remove();
        const said = card.querySelector('.status'); if (said) said.textContent = 'Confirmed by you';
        const mark = card.querySelector('[data-decision-read]'); if (mark) mark.remove();
      } else sure.disabled = false;
    }
  });
  // A link from a slice's window to Change this here: the tab is opened by the page, and this presses it.
  if (location.hash.startsWith('#change-')) {
    const button = document.getElementById(location.hash.slice(1));
    if (button) setTimeout(() => button.click(), 0);
  }
  // Watched where the swap lands — the band's own children, or the slice panel's place — and nowhere the
  // filters are, since rebuilding their options is itself a change to the page.
  const panel = document.getElementById('slice-decisions');
  const host = document.querySelector('[data-band=decisions]') || (panel && panel.parentNode);
  if (host) new MutationObserver(() => { options(); filter(); }).observe(host, {childList: true});
  window.decisionSwap = found => {
    const now = document.getElementById('slice-decisions');
    if (!now || !found.decisions_html || now.dataset.said === found.decisions_said) return;
    const open = [...now.querySelectorAll('details[open]')].map(one => one.dataset.card);
    const held = document.createElement('div');
    held.innerHTML = found.decisions_html;
    held.querySelectorAll('details').forEach(one => { if (open.includes(one.dataset.card)) one.open = true; });
    now.replaceWith(held.firstElementChild);
  };
  options(); filter();
})();
"""


def who(by: str) -> str:
    """Who decided, in a person's words: the filter's value and the card's."""
    by = by.strip()
    if by in ("you", "human"):
        return "you"
    standing = re.match(r"host \(standing decision (D[-\w]+)\)", by)
    if standing:
        return f"the session, from {standing.group(1)}"
    if by.startswith("host"):
        return "the session, as the stage recommended"
    if by.startswith("sail-decide-skipper"):
        return "the skipper"
    if by.startswith("sail-unblock-bosun"):
        return "the bosun"
    return by or "nobody recorded"


# The filter's `Decided by` is who, not on what grounds: "the session, from D21" and "the session, as the
# stage recommended" are both the session, and forty standing decisions would be forty choices.


def status_said(one: Decision) -> str:
    said = plain(one.status)
    if one.awaiting:
        return "Awaiting your confirmation"
    if said.startswith("confirmed by human"):
        return "Confirmed by you" + (f" on {said.split()[-1]}" if said.split()[-1][:1].isdigit() else "")
    return said[:1].upper() + said[1:] if said else ""


def options_html(one: Decision) -> str:
    """The options with the one taken marked, or the field as written where it does not split."""
    listed = options(one.parts.get("Options", ""))
    letter, rest = chosen(one.decision, listed)
    if not listed or not letter:
        raw = one.parts.get("Options", "")
        return ((f'<p class="said"><b>Options:</b> {esc(plain(raw))}</p>' if raw else "")
                + f'<p class="said"><b>Decision:</b> {esc(plain(one.decision))}</p>')
    items = "".join(option_html(option, option.letter == letter) for option in listed)
    detail = f'<p class="said"><b>Made exact:</b> {esc(plain(rest))}</p>' if rest else ""
    return f'<ol class="opts">{items}</ol>{detail}'


def option_html(option: Option, taken: bool) -> str:
    rec = '<span class="rec">recommended</span>' if option.recommended else ""
    return (f'<li class="{"chosen" if taken else "other"}"><span class="pick">{"Chosen" if taken else "Not chosen"}'
            f"</span><span>{esc(option.text)}</span>{rec}</li>")


def card_id(one: Decision) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "-", one.key)


def change_button(one: Decision, here: bool) -> str:
    """Change this: the Feedback box with the decision quoted, on the Voyage window; a link to that from a
    slice's window, which has no box of its own."""
    if not here:
        return f'<a href="/voyage#change-{esc(card_id(one))}" target="_blank" rel="noopener">Change this</a>'
    lead = plain(one.sentence or one.title)
    context = {"from": f"decision {one.number}: {lead}", "fairway": one.stream,
               "slice": one.slice if _SLICE.fullmatch(one.slice) else ""}
    button = opener("Change this", context, ask=f"Change {one.number}: “{lead}” — what should it be instead?")
    return button.replace("<button ", f'<button id="change-{esc(card_id(one))}" ', 1)


def card_html(one: Decision, here: bool = True) -> str:
    kind = " ".join(word for word, on in (("awaiting", one.awaiting), ("read", one.read), ("yours", one.yours)) if on)
    meta = [f'<span class="num">{esc(one.number)}</span>', one.slice and f"<span>Slice {esc(one.slice)}</span>",
            f"<span>Decided by {esc(who(one.decided_by))}</span>",
            one.parts.get("Confidence") and f"<span>Confidence {esc(plain(one.parts['Confidence']))}</span>",
            status_said(one) and f'<span class="status">{esc(status_said(one))}</span>']
    lead = one.sentence or one.title
    asked = "" if one.sentence else ('<span class="asked">Its question, as the agent wrote it: this entry has no '
                                     "plain sentence</span>")
    reverse = one.parts.get("Would reverse if")
    rows = "".join(f"<dt>{esc(label)}</dt><dd>{esc(one.parts[label])}</dd>" for label in WRITTEN
                   if one.parts.get(label))
    rows += f"<dt>Decision</dt><dd>{esc(one.decision)}</dd>" if one.decision else ""
    acts = (f'<button type="button" class="go" data-decision-confirm="{esc(one.key)}">Confirm</button>'
            if one.awaiting else "") + change_button(one, here) + (
        "" if one.read else f'<button type="button" class="install" data-decision-read="{esc(one.key)}">Mark read'
                            "</button>")
    return (f'<article class="{kind}" id="decision-{esc(card_id(one))}" data-key="{esc(one.key)}" '
            f'data-stream="{esc(one.stream)}" data-slice="{esc(one.slice)}" '
            f'data-by="{esc(who(one.decided_by).split(",")[0])}">'
            f'<div class="meta">{"".join(part for part in meta if part)}</div>'
            f'<h3 class="lead">{esc(plain(lead))}</h3>{asked}{options_html(one)}'
            + (f'<p class="rev"><b>Would change if:</b> {esc(plain(reverse))}</p>' if reverse else "")
            + f'<details data-card="{esc(one.key)}"><summary>Why, in full</summary><dl>{rows}</dl></details>'
            f'<div class="acts">{acts}</div></article>')


def grouped(found: list[Decision]) -> str:
    """Capability, then slice, in the order the newest decision of each was taken."""
    by_cap: dict[str, dict[str, list[Decision]]] = {}
    for one in found:
        by_cap.setdefault(one.capability, {}).setdefault(one.slice, []).append(one)
    html = ""
    for capability, slices in by_cap.items():
        named = capability or "Before the slices, or in no capability the chart names"
        inner = "".join(f"<h5>{esc(f'Slice {piece}' if piece else 'No slice named')}</h5>"
                        + "".join(card_html(one) for one in ones) for piece, ones in slices.items())
        html += f'<div class="group"><h4>{esc(named)}</h4>{inner}</div>'
    return html


def listing(found: list[Decision]) -> str:
    """The band the poll swaps: what awaits a person first, then the rest."""
    first = [one for one in found if one.awaiting]
    rest = [one for one in found if not one.awaiting]
    says = (f"{len(found)} decision{'s' if len(found) != 1 else ''} · {len(first)} awaiting your confirmation · "
            "grouped by capability, then slice")
    html = f'<p class="says">{says}</p>'
    if first:
        html += f'<h3 class="part">Awaiting your confirmation · {len(first)}</h3><div>{grouped(first)}</div>'
    if rest:
        html += f'<h3 class="part">Everything else · {len(rest)}</h3><div>{grouped(rest)}</div>'
    return f'<div class="dec-list">{html}</div>'


def bar_html() -> str:
    names = (("stream", "Stream", "every stream"), ("slice", "Slice", "every slice"),
             ("by", "Decided by", "anyone"))
    picks = "".join(f'<label>{face} <select name="d-{name}" data-every="{every}"><option value="">{every}</option>'
                    f"</select></label>" for name, face, every in names)
    return f'<div class="bar">{picks}</div>'


def tab(root: Path, band: Callable[[str, str], str]) -> tuple[str, int]:
    """The Decisions tab, and how many decisions in it await a person. `band` wraps the cards as the page's
    poll keeps them current."""
    found = decisions(root)
    if not found:
        return "", 0
    return (f'<div class="card decs" id="decisions"><div class="head"><h2>Decisions</h2></div>{bar_html()}'
            f'{band("decisions", listing(found))}<p class="empty shown"></p></div>',
            sum(1 for one in found if one.awaiting))


def polled(root: Path) -> tuple[str, int]:
    """What the poll carries: the cards, and the count on the tab."""
    found = decisions(root)
    return (listing(found) if found else ""), sum(1 for one in found if one.awaiting)


def slice_panel(root: Path, slice_id: str) -> tuple[str, int]:
    """One slice's decisions, for the tab in its window, and how many there are."""
    found = [one for one in decisions(root) if one.slice == slice_id]
    first = sorted(found, key=lambda one: not one.awaiting)
    inner = "".join(card_html(one, here=False) for one in first) or (
        '<p class="empty">No decision names this slice yet.</p>')
    said = hashlib.sha1(inner.encode("utf-8")).hexdigest()[:16]
    return f'<div class="decs" id="slice-decisions" data-said="{said}">{inner}</div>', len(found)


def payload(root: Path, slice_id: str) -> dict[str, str]:
    """The slice window's poll: its decisions, with the signature it compares them by."""
    drawn, _ = slice_panel(root, slice_id)
    return {"decisions_said": drawn.split('data-said="', 1)[1].split('"', 1)[0], "decisions_html": drawn}

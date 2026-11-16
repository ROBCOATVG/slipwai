"""A slice's example map, drawn for its window: the story across the top, a column a rule, the questions last.

Four colours, as the method draws them on a table: yellow for the story, blue for a rule, green for an
example, red for a question — faded once its line says what answered it. They are this page's own tokens,
set for the light theme and again for the dark one, so the text on each card stays readable in both: the
dark set is the same four hues taken down to a ground light text reads on.

Read-only. The map is the slice's `examples.md`; it is changed by telling the slice, never here.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from urllib.parse import quote

from .example_map import Example, ExampleMap, Question, found_map, summary
from .page_shell import esc

DARK = ("--map-story:#4a3f12;--map-rule:#1d3a55;--map-example:#1f4027;--map-question:#5c2419;"
        "--map-answered:#2f2724;--map-ink:#eef2f3;--map-ink-2:#c3ccd1;--map-edge:#e6ecef")

STYLE = f"""
:root{{--map-story:#f2d76b;--map-rule:#8fbfe8;--map-example:#9fd6a3;--map-question:#f0806b;
--map-answered:#efd8d1;--map-ink:#172129;--map-ink-2:#3b4750;--map-edge:#172129}}
@media (prefers-color-scheme:dark){{:root:has(#t-auto:checked){{{DARK}}}}}
:root:has(#t-dark:checked){{{DARK}}}
#slice-map{{display:flex;flex-direction:column;gap:10px;margin-top:18px}}
#slice-map .story{{padding:10px 14px;border-radius:6px;background:var(--map-story);color:var(--map-ink);
  font-size:.95rem;line-height:1.45}}
#slice-map .says{{font-size:.86rem;color:var(--ink-2)}}
#slice-map .map-row{{overflow-x:auto;padding-bottom:10px}}
#slice-map .cols{{display:flex;gap:10px;align-items:flex-start;min-width:max-content}}
#slice-map .col{{flex:0 0 230px;width:230px;display:flex;flex-direction:column;gap:6px}}
#slice-map .rule,#slice-map .ex,#slice-map .q{{padding:8px 10px;border-radius:6px;color:var(--map-ink);
  font-size:.86rem;line-height:1.35}}
#slice-map .rule{{background:var(--map-rule)}}
#slice-map .ex{{display:flex;flex-direction:column;gap:4px;min-height:44px;border:0;background:var(--map-example);
  font:inherit;font-size:.86rem;text-align:left;cursor:pointer}}
#slice-map .ex:focus-visible{{outline:2px solid var(--teal);outline-offset:2px}}
#slice-map .proof{{font-size:.78rem;color:var(--map-ink-2)}}
#slice-map .ex .gwt{{display:none;flex-direction:column;gap:4px;padding-top:6px;border-top:1px solid var(--map-edge);
  font-size:.82rem;line-height:1.4;overflow-wrap:anywhere}}
#slice-map .ex[aria-expanded="true"] .gwt{{display:flex}}
#slice-map .none{{font-size:.8rem;color:var(--ink-3);margin:0;padding:4px 2px}}
#slice-map .q{{display:flex;flex-direction:column;gap:4px;background:var(--map-question)}}
#slice-map .q.answered{{background:var(--map-answered);color:var(--map-ink-2)}}
#slice-map .q .said{{font-size:.78rem;font-weight:600}}
#slice-map .key{{font-size:.8rem;color:var(--ink-3)}}
"""

#: How the window says what the colours are and how the map is changed.
KEY = ("Yellow is the story, blue a rule, green an example, red a question still open. Press an example for its "
       "Given, When and Then. Drawn from the slice's own examples file; to change it, tell the slice.")


#: Under a rule with no example yet: still shown, since a rule with nothing under it is what to ask about.
NONE = '<p class="none">No examples yet</p>'


def plain(text: str) -> str:
    """The words without the file's markdown marks: `**answered by D53**` reads as `answered by D53`."""
    return re.sub(r"\*+|`", "", text).strip()


def example_html(one: Example, key: str) -> str:
    proof = "Proven by a test" if one.proven else "Not proven yet"
    parts = [(word, getattr(one, word.lower())) for word in ("Given", "When", "Then")]
    told = "".join(f"<span><b>{word}</b> {esc(plain(said))}</span>" for word, said in parts if said)
    told = told or f"<span>{esc(plain(one.said)) or 'Nothing written under it yet.'}</span>"
    named = f"<b>{esc(one.id)} · </b>" if one.id else ""
    return (f'<button type="button" class="ex" aria-expanded="false" data-ex="{esc(key)}">'
            f"<span>{named}{esc(plain(one.title))}</span><span class=\"proof\">{proof}</span>"
            f'<span class="gwt">{told}</span></button>')


def question_html(one: Question) -> str:
    answer = plain(one.answer)
    if one.open:
        said = f"Open · {answer}" if answer else "Open"
    else:
        said = answer[:1].upper() + answer[1:] if answer.lower().startswith(("answered", "decided")) else \
            f"Answered: {answer}" if answer else "Answered"
    named = f"<b>{esc(one.id)} · </b>" if one.id else ""
    return (f'<div class="q {"open" if one.open else "answered"}"><span>{named}{esc(plain(one.text))}</span>'
            f'<span class="said">{esc(said)}</span></div>')


def map_html(found: ExampleMap | None) -> str:
    """The map, or what stands in for it where the slice has no `examples.md` yet."""
    if found is None:
        inner = ('<p class="empty">No example map yet: this slice has no <code>examples.md</code> on its branch '
                 "or on trunk. Its first stage writes one.</p>")
    else:
        story = esc(plain(found.story)) or "No story written yet."
        columns = ""
        for place, rule in enumerate(found.rules):
            cards = "".join(example_html(one, one.id or f"{rule.id or place}:{index}")
                            for index, one in enumerate(rule.examples))
            named = f"<b>{esc(rule.id)} · </b>" if rule.id else ""
            columns += (f'<div class="col"><div class="rule">{named}{esc(plain(rule.text)) or "Not under a rule"}'
                        f"</div>{cards or NONE}</div>")
        if found.questions:
            columns += f'<div class="col">{"".join(question_html(one) for one in found.questions)}</div>'
        inner = (f'<div class="story"><b>Story · </b>{story}</div><span class="says">{esc(summary(found))}</span>'
                 f'<div class="map-row"><div class="cols">{columns}</div></div><span class="key">{KEY}</span>')
    said = hashlib.sha1(inner.encode("utf-8")).hexdigest()[:16]
    return f'<div id="slice-map" data-said="{said}">{inner}</div>'


def card_html(row: dict[str, str]) -> str:
    """The counts a slice's card carries, and the way to its map: under the Examples step of a slice in
    flight, and at the foot of a done one, whose window is where its map is read once it has merged."""
    counts = row.get("examples", "")
    if not counts:
        return ""
    there = (f"/slice?fairway={quote(row['fairway'], safe='')}&slice={quote(row['slice'], safe='')}&tab=map"
             if row.get("fairway") else "")
    link = f' · <a href="{esc(there)}" target="_blank" rel="noopener">Open its example map</a>' if there else ""
    if row.get("state") == "done":
        return f'<p class="span">{esc(counts)}{link}</p>'
    return f"<small>{esc(counts)}{link}</small>"


def map_panel(root: Path, slice_id: str) -> str:
    try:
        found = found_map(root, slice_id)
    except OSError:
        found = None
    return map_html(found)

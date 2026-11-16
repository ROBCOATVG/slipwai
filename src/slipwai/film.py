"""A capability's film on the Voyage tab: one recording of the whole walk, with a chapter per slice.

A demo is of a capability, and the hand walks one as a single flow. Its recordings were still a file per
example — in game-club-manager, twenty-nine clips of half a second to four, named `ac1-3`, one of them the
sign-in page — so what the board offered under "Watch it work" was a list nobody could watch. The hand now
films the walk once (`try_it.py film`, which also keeps the marks: the instant each example begins, its
slice, and a sentence saying who is signed in and what they are about to do), and this draws it: the
recording, the sentence for the part that is playing, and a chapter per slice that plays from there. A
slice's own card links to its chapter (`slice_card.py`).

**Read from two files and nothing else**: `.slipwai/run/walks/<feature>/<capability>/film.webm` and the
`film.json` beside it. A film with no marks is still a film; marks with no recording are nothing.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import quote

from .logs import run_dir
from .page_shell import esc

FILM = "film.webm"
MARKS = "film.json"
ROUTE = "/walks/"

STYLE = """
.film{display:grid;grid-template-columns:minmax(0,1.6fr) minmax(0,1fr);gap:14px;align-items:start;margin-top:10px}
@media (max-width:760px){.film{grid-template-columns:1fr}}
.film video{width:100%;border-radius:6px;border:1px solid var(--rule);background:#000;display:block}
.film .says{margin:8px 0 0;font-size:.9rem;min-height:2.6em;color:var(--ink)}
.film .sub{font-size:.78rem;color:var(--ink-3)}
.film ol{list-style:none;margin:0;padding:0;display:grid;gap:4px}
.film ol button{font:inherit;font-size:.84rem;width:100%;min-height:40px;display:flex;justify-content:space-between;
  gap:8px;align-items:center;text-align:left;padding:4px 10px;border-radius:6px;border:1px solid transparent;
  background:transparent;color:var(--ink);cursor:pointer}
.film ol button:hover{border-color:var(--rule)}
.film ol button[aria-current="true"]{background:var(--teal-soft);font-weight:500}
.film ol .at{font-family:var(--mono);font-size:.76rem;color:var(--ink-3)}
.films h3{display:flex;gap:10px;align-items:center;margin:14px 0 0}
.films .due{font-size:.72rem;font-weight:400;padding:1px 8px;border-radius:999px;border:1px solid var(--critical);
  color:var(--critical)}
"""

SCRIPT = """
// A film: a chapter plays from its mark, a slice's card plays from its chapter, and while it plays the line
// under it says what is on the screen and the chapter it is in is the one marked.
(function(){
  const play = (film, at) => {
    const video = film && film.querySelector('video');
    if (!video) return;
    const go = () => { video.currentTime = at; video.play().catch(() => {}); };
    if (video.readyState >= 1) go(); else { video.addEventListener('loadedmetadata', go, {once: true}); video.load(); }
  };
  document.addEventListener('click', event => {
    const mark = event.target.closest('[data-film-at]');
    if (!mark) return;
    const named = (mark.getAttribute('href') || '').slice(1);
    const film = named ? document.getElementById(named) : mark.closest('.film');
    if (film) { play(film, Number(mark.dataset.filmAt) || 0); film.scrollIntoView({block: 'nearest'}); }
  });
  document.addEventListener('timeupdate', event => {
    const film = event.target.closest && event.target.closest('.film');
    if (!film) return;
    let marks = [];
    try { marks = JSON.parse(film.dataset.marks || '[]'); } catch (fault) {}
    const now = event.target.currentTime;
    const on = marks.filter(one => one.at <= now + 0.2).pop();
    const says = film.querySelector('.says');
    if (says && on) says.textContent = on.says;
    film.querySelectorAll('ol button').forEach(one => one.setAttribute('aria-current',
      String(Boolean(on) && one.dataset.slice === on.slice)));
  }, true);
})();
"""


def ranged(data: bytes, asked: str) -> tuple[int, bytes, tuple]:
    """The part of a recording a browser asked for, since a player seeks by asking for a range of bytes and
    one handed the whole file every time can only play from the start."""
    found = re.fullmatch(r"bytes=(\d*)-(\d*)", asked.strip())
    if not found or not (found[1] or found[2]) or not data:
        return 200, data, (("Accept-Ranges", "bytes"),)
    first = int(found[1]) if found[1] else max(0, len(data) - int(found[2]))
    last = min(int(found[2]), len(data) - 1) if found[1] and found[2] else len(data) - 1
    if first > last:
        return 416, b"", (("Content-Range", f"bytes */{len(data)}"),)
    return 206, data[first:last + 1], (("Accept-Ranges", "bytes"),
                                       ("Content-Range", f"bytes {first}-{last}/{len(data)}"))


def clock(seconds: float) -> str:
    return f"{int(seconds) // 60}:{int(seconds) % 60:02d}"


def films_of(root: Path, seat: str = "") -> list[dict]:
    """Every capability's film the hand has left, by feature and capability, with its marks in order."""
    home = run_dir(root) / "walks"
    found = []
    for path in sorted(home.glob(f"*/*/{FILM}")) if home.is_dir() else []:
        feature, capability = path.parent.parent.name, path.parent.name
        try:
            held = json.loads((path.parent / MARKS).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            held = {}
        marks = held.get("chapters") if isinstance(held, dict) else None
        chapters = sorted(({"at": float(one.get("at") or 0), "slice": str(one.get("slice", "")),
                            "example": str(one.get("example", "")), "says": str(one.get("says", ""))}
                           for one in marks or [] if isinstance(one, dict)), key=lambda one: float(str(one["at"])))
        where = "/".join(quote(part, safe="") for part in (feature, capability, FILM))
        query = "&".join(([f"seat={quote(seat, safe='')}"] if seat else []) + [f"v={path.stat().st_mtime_ns}"])
        length = held.get("length") if isinstance(held, dict) else 0
        found.append({"feature": feature, "capability": capability,
                      "id": "film-" + re.sub(r"[^A-Za-z0-9_-]", "-", capability),
                      "title": capability.replace("-", " ").capitalize(), "href": f"{ROUTE}{where}?{query}",
                      "chapters": chapters, "length": float(length or 0)})
    return found


def film_html(film: dict, titles: dict[str, str], due: bool) -> str:
    """One film: the recording, what is on screen, and a chapter per slice."""
    firsts: dict[str, dict] = {}
    for one in film["chapters"]:
        firsts.setdefault(one["slice"], one)
    rows = "".join(
        f'<li><button type="button" data-film-at="{one["at"]}" data-slice="{esc(name)}">'
        f'<span>{number} · {esc(titles.get(name) or name)}</span><span class="at">{clock(one["at"])}</span>'
        f"</button></li>" for number, (name, one) in enumerate(firsts.items(), 1))
    opening = film["chapters"][0]["says"] if film["chapters"] else ""
    length = f"{clock(film['length'])} · " if film["length"] else ""
    chapters = (f"<div><ol>{rows}</ol><p class=\"sub\">A chapter is a slice. Its card on the Work tab opens the "
                f"film there.</p></div>") if rows else '<p class="sub">Filmed without chapter marks.</p>'
    # Due is a person's verdict owed, where the project says a person accepts demos. Otherwise the hand's
    # verdict was the acceptance and the film is an opportunity: the Feedback card's own box, opened from
    # the capability with the film's context, which its script opens from any `data-feedback` button.
    context = {"from": "capability", "feature": film["feature"], "capability": film["capability"]}
    ready = ('<span class="due">Ready for you · accept it below</span>' if due else
             f' <button type="button" class="install" data-feedback="{esc(json.dumps(context))}" '
             f'data-ask="What did the {esc(film["title"].lower())} film show?">Say what it showed</button>')
    marks = json.dumps([{"at": one["at"], "slice": one["slice"], "says": one["says"]} for one in film["chapters"]])
    return (f"<h3>{esc(film['title'])}{ready}</h3>"
            f'<div class="film" id="{esc(film["id"])}" data-marks="{esc(marks)}"><div>'
            f'<video controls preload="metadata" src="{esc(film["href"])}"></video>'
            f'<p class="says">{esc(opening)}</p>'
            f'<p class="sub">{length}one take through the running app, as the hand walked it</p></div>'
            f"{chapters}</div>")


def films_card(films: list[dict], rows: list[dict[str, str]], due: dict | None = None) -> str:
    """The films, the ones waiting on a person's verdict first. Nothing where the hand has filmed nothing."""
    if not films:
        return ""
    titles = {row["slice"]: f'{row["slice"]} · {row["title"]}' for row in rows if row.get("title")}
    waiting = due or {}
    ordered = sorted(films, key=lambda one: (one["capability"] not in waiting, one["feature"], one["capability"]))
    body = "".join(film_html(one, titles, one["capability"] in waiting) for one in ordered)
    return (f'<div class="card films" id="films"><h2>On film · {len(films)} '
            f'capabilit{"y" if len(films) == 1 else "ies"} filmed</h2>{body}</div>')

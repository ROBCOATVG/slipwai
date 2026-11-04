"""The surfaces a storyboard shows, and the states on each page, read from the page and nothing else.

A surface is one HTML page; `<title>` names it and each `<article class="state">`'s first `<h2>` names a
state. That is the whole of what the board reads from a drawing, whether the stage drew it or a person
handed it over under `docs/design/`, and it is the contract `docs/reference/the-brief.md` states for a
folder at the front door. It is read here, in one place, so the Voyage window's approve button, the
upstream stop that approves without a person, and `slipwai brief check` cannot each read a page their own
way: two readings of "drawn" were once a storyboard the board offered to approve and then could not.
"""
from __future__ import annotations

import html
import re
from pathlib import Path

_FEATURE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,80}$")
_ARTICLE = re.compile(r'<article\b[^>]*\bclass="[^"]*\bstate\b[^"]*"[^>]*>(.*?)</article>',
                      re.IGNORECASE | re.DOTALL)
_HEADING = re.compile(r"<h2>(.*?)</h2>", re.IGNORECASE | re.DOTALL)
_TITLE = re.compile(r"<title>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_NOT_A_SURFACE = frozenset({"storyboard.html", "index.html"})
#: A page the storyboard embeds or links: where the surfaces are when they were handed over rather than drawn.
_EMBEDDED = re.compile(r"""(?:src|href)=["']([^"'#?]+\.html)["']""", re.IGNORECASE)
#: What a page with no state article is: one state, the page as shown.
SHOWN = "shown"


def _plain(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _surface_name(title: str, stem: str) -> str:
    title = re.sub(r"^\s*mock(-?up)?:\s*", "", _plain(title), flags=re.IGNORECASE)
    for mark in ("—", " - "):
        if mark in title:
            title = title.split(mark)[-1].strip()
    return title or stem


def page_states(page: Path) -> tuple[str, list[str]]:
    """One page as the board reads it: the surface its title names, and the states its articles name.

    A page with no article is one state, `shown` — a plain page is still a drawing somebody can approve.
    Two articles with the same heading are one state.
    """
    text = page.read_text(encoding="utf-8", errors="replace")
    title = _TITLE.search(text)
    name = _surface_name(title.group(1) if title else "", page.stem)
    states: list[str] = []
    for article in _ARTICLE.finditer(text):
        heading = _HEADING.search(article.group(1))
        label = _plain(heading.group(1)) if heading else ""
        if label and label not in states:
            states.append(label)
    return name, states or [SHOWN]


def surface_pages(home: Path) -> list[Path]:
    """The surfaces of one feature's mock-ups: the pages beside the storyboard, else the pages it embeds or links.

    Every page but the storyboard and the contents page, where the stage drew them. Where it drew none, because
    a person handed the mock-ups over (`docs/design/`) and the stage storyboarded those instead of redrawing
    them, the surfaces are the pages the storyboard shows — inside the project, and there. The one reading of
    "drawn" for every question that asks it: two readings were a storyboard the board offered to approve and
    then could not.
    """
    beside = sorted(page for page in home.glob("*.html") if page.name not in _NOT_A_SURFACE)
    board = home / "storyboard.html"
    if beside or not board.is_file():
        return beside
    project, shown = home.parents[2].resolve(), []
    for target in _EMBEDDED.findall(board.read_text(encoding="utf-8", errors="replace")):
        page = (home / target).resolve()
        if page.is_file() and page.is_relative_to(project) and page.name not in _NOT_A_SURFACE \
                and page not in shown:
            shown.append(page)
    return shown


def drawn_states(root: Path, feature: str) -> list[tuple[str, list[str]]]:
    """Each drawn surface and the states on its page. The storyboard and the contents page are not surfaces."""
    if not _FEATURE.fullmatch(feature):
        raise ValueError(f"no feature {feature}")
    home = (root / "specs" / feature / "mockups").resolve()
    if not home.is_dir() or not home.is_relative_to((root / "specs").resolve()):
        raise ValueError(f"nothing drawn under specs/{feature}/mockups")
    found = [page_states(page) for page in surface_pages(home)]
    if not found:
        raise ValueError(f"nothing drawn under specs/{feature}/mockups")
    return found


def record_verdict(root: Path, feature: str, verdict: str, reason: str = "", by: str = "") -> str:
    """Write `mock-states.md` from the drawings a person has just approved or disapproved.

    Approving marks every drawn state approved. Disapproving parks them, and a park with no reason is a
    blank, which is the one mark this file refuses. `by` is a first line saying who gave the verdict, where
    it was not a person.
    """
    if verdict not in ("approved", "parked"):
        raise ValueError("approve or disapprove the storyboard")
    why = re.sub(r"\s+", " ", reason).strip()
    if verdict == "parked" and not why:
        raise ValueError("say why you disapprove, so the next drawing knows what to change")
    lines: list[str] = [by, ""] if by else []
    for name, states in drawn_states(root, feature):
        lines.append(f"## Surface: {name}")
        mark = "approved" if verdict == "approved" else f"parked: {why}"
        lines.extend(f"- {state} — {mark}" for state in states)
        lines.append("")
    (root / "specs" / feature / "mockups" / "mock-states.md").write_text("\n".join(lines), encoding="utf-8")
    return "approved" if verdict == "approved" else "disapproved"

"""`slipwai brief check <dir>`: what the front door will read from a folder, said before anything is generated.

A brief is handed over once, and what it was worth is found out three stages later: at the draft, which
lists what the document left open under `## Assumptions`, and at the storyboard, which shows the states a
page carried. Both are late. This reads the folder the way `generate --brief` will — the same `briefed`,
the same page reader, the same limits — and prints five lines, so the person who filled the folder, or the
tool that wrote it, can see what is missing while it is still cheap to add.

**It calls the readers the stages call, not a copy of them.** A check that read a page its own way would
pass a page the board then could not, which is the one thing a check must never do. The two readings it
adds — people, and facts with where they came from — are the shape `docs/reference/the-brief.md` states
and nothing more; what the draft and the skipper do with them lands with their own slices.

The assumptions line is a heuristic over the document, not the draft: a heading or a bullet that is a
question, `TBD`, `open:`, and whatever sits under a `## Open` heading. It finds what the document says it
has not decided. It cannot find what the document does not know it has not decided; that is the draft's.
"""
from __future__ import annotations

import re
from pathlib import Path

from .design_docs import PRD_NAMES, PRD_WORDS, briefed, weighed
from .drawn import SHOWN, decided_states, page_states
from .errors import GenerationError

#: Where the pages are, and where the look is, in a folder that follows the reference page.
SURFACES = "surfaces"
LOOK = "look"
#: A `## ` heading: one person, one fact, or one section of the document.
HEADING = re.compile(r"^##\s+(?P<title>.+?)\s*$", re.MULTILINE)
#: What a person is, in their section.
ROLE = re.compile(r"^role:\s*(?P<role>\S.*?)\s*$", re.MULTILINE | re.IGNORECASE)
#: A fact saying where it came from, which is what makes it citable rather than a claim.
SOURCE = re.compile(r"^\s*(?:source|from|where it came from)\s*:", re.MULTILINE | re.IGNORECASE)
#: A bullet, or a line, the document has not settled.
BULLET = re.compile(r"^\s*[-*]\s+(?P<text>.+?)\s*$", re.MULTILINE)
UNSETTLED = re.compile(r"\?\s*$|\bTBD\b|^\s*open:", re.IGNORECASE)


def sections(path: Path) -> list[tuple[str, str]]:
    """The document as `## ` sections: each heading and the text under it. Text before the first is `""`."""
    text = path.read_text(encoding="utf-8", errors="replace")
    found = list(HEADING.finditer(text))
    if not found:
        return [("", text)]
    parts = [("", text[:found[0].start()])]
    for index, match in enumerate(found):
        end = found[index + 1].start() if index + 1 < len(found) else len(text)
        parts.append((match.group("title"), text[match.end():end]))
    return parts


def people(path: Path) -> list[dict[str, str]]:
    """One person per heading, with the role their section says, or `""` where it says none."""
    found = []
    for title, body in sections(path):
        if not title:
            continue
        role = ROLE.search(body)
        found.append({"name": title, "role": role.group("role") if role else ""})
    return found


def facts(path: Path) -> list[dict[str, object]]:
    """One fact per heading, and whether its section says where it came from."""
    return [{"heading": title, "cited": bool(SOURCE.search(body))}
            for title, body in sections(path) if title]


def assumptions(prd: Path) -> list[str]:
    """What the document says it has not decided, each naming the file and the heading it was found under.

    A heading that is itself a question is one assumption, whatever is under it; everything under `## Open`
    is one each; and anywhere else, a bullet that ends in a question mark, says `TBD` or starts `open:`.
    """
    found: list[str] = []

    def add(text: str, title: str) -> None:
        where = f"{prd.name}, ## {title}" if title else prd.name
        line = f"{text} ({where})"
        if line not in found:
            found.append(line)

    for title, body in sections(prd):
        if title.rstrip().endswith("?"):
            add(title, title)
            continue
        if title.strip().lower().rstrip(":") == "open":
            for bullet in BULLET.finditer(body):
                add(bullet.group("text"), title)
            continue
        for bullet in BULLET.finditer(body):
            if UNSETTLED.search(bullet.group("text")):
                add(bullet.group("text"), title)
    return found


def how_found(document: Path, home: Path) -> str:
    """Which of the three questions `briefed` asked found the document, in its own words."""
    if document.name.lower() in PRD_NAMES:
        return "by name"
    if any(word in document.stem.lower() for word in PRD_WORDS):
        return "by a name that says what it is"
    return "by its first heading"


def surfaces_line(home: Path, pages: list[Path]) -> str:
    if not pages:
        return f"surfaces: none; one page per surface goes under {SURFACES}/"
    read = [(page, *page_states(page)) for page in pages]
    plain = [page.relative_to(home).as_posix() for page, _, states in read if states == [SHOWN]]
    total = sum(len(states) for _, _, states in read)
    if not plain:
        return f"surfaces: {len(read)}, states: {total}, each with a heading{who_decided(pages)}"
    return (f"surfaces: {len(read)}, states: {total}; {', '.join(plain)} "
            f"{'has' if len(plain) == 1 else 'have'} no <article class=\"state\"> and "
            f"{'is' if len(plain) == 1 else 'are'} one state each, {SHOWN}")


def who_decided(pages: list[Path]) -> str:
    """`, 10 decided by a person, 6 proposed` where any page says who chose a state; nothing where none does."""
    said = [who for page in pages for _, who in decided_states(page)[1]]
    if not any(said):
        return ""
    proposed = sum(who.lower() == "proposed" for who in said)
    return f", {sum(bool(who) for who in said) - proposed} decided by a person, {proposed} proposed"


def report(home: Path) -> list[str]:
    """The five lines, or a refusal that ends with what to do."""
    if not home.is_dir():
        raise GenerationError(f"{home} is not a directory; it is the folder your brief is in — "
                              f"run `slipwai brief check <dir>` against that folder")
    document, rest = briefed(home)
    weighed({one.relative_to(home).as_posix(): one for one in rest}, f"the brief {home}")
    lines = [f"requirements document: {document.relative_to(home).as_posix()}, {how_found(document, home)}"
             if document else "requirements document: none; the specification is written in the agent"]
    lines.append(surfaces_line(home, sorted(one for one in rest if one.parent == home / SURFACES
                                             and one.suffix.lower() == ".html")))
    sheets = sorted(one for one in rest if one.parent == home / LOOK and one.suffix.lower() == ".css")
    lines.append(f"look: {sheets[0].relative_to(home).as_posix()}" if sheets
                 else f"look: none; a stylesheet under {LOOK}/ is the direction the drawing follows")
    who = people(home / "people.md") if (home / "people.md").is_file() else []
    known = facts(home / "domain.md") if (home / "domain.md").is_file() else []
    uncited = [str(fact["heading"]) for fact in known if not fact["cited"]]
    said_facts = ("none" if not known else f"{len(known)}, cited" if not uncited
                  else f"{len(known)}, {len(uncited)} with no source ({', '.join(uncited)})")
    lines.append(f"people: {len(who) or 'none'}   facts: {said_facts}")
    open_ = assumptions(document) if document else []
    if not open_:
        lines.append("the draft will have to assume: nothing the document says it left open")
    elif len(open_) == 1:
        lines.append(f"the draft will have to assume: 1 — {open_[0]}")
    else:
        lines.append(f"the draft will have to assume: {len(open_)}")
        lines.extend(f"  — {one}" for one in open_)
    return lines

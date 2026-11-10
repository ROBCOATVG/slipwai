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

from .catalog import CATALOG
from .design_docs import PRD_NAMES, PRD_WORDS, briefed, played, weighed
from .drawn import SHOWN, decided_states, page_states
from .errors import GenerationError
from .targets import managed

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
#: The two lines under `## Who runs it` that size the first build, in the person's words and no term of ours:
#: who uses it, and what an afternoon without it is. `shape_of` turns them into the target's shape.
USED_BY = re.compile(r"^\s*[-*]\s+used by:\s*(?P<said>.+?)\s*$", re.MULTILINE | re.IGNORECASE)
WHEN_DOWN = re.compile(r"^\s*[-*]\s+when it is down:\s*(?P<said>.+?)\s*$", re.MULTILINE | re.IGNORECASE)
STAFF = ("staff", "team", "colleague", "named people", "volunteer", "internal", "our own")
CUSTOMERS = ("customer", "public", "member", "client", "visitor", "resident", "patient", "anyone")
ANNOYANCE = ("annoyance", "inconvenience", "nuisance", "wait")
EMERGENCY = ("emergency", "incident", "outage", "lost")
#: The third line, where it runs, in the person's words: their own cloud, a platform another team runs, or
#: nowhere yet. The first place named is the one meant. Absent, or none of these, is a brief that has not said.
RUNS_ON = re.compile(r"^\s*[-*]\s+where it runs:\s*(?P<said>.+?)\s*$", re.MULTILINE | re.IGNORECASE)
#: The two places that are not a cloud. A cloud is a managed target's, and its words are the catalogue's.
ELSEWHERE = (("platform", ("platform", "another team", "other team", "kubernetes", "cluster", "existing")),
             ("nowhere", ("nowhere", "not yet", "try", "laptop", "this machine", "my machine", "locally")))
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


def service(prd: Path) -> dict[str, str | bool]:
    """Who runs it, read off the two lines under `## Who runs it`: `used_by` as `staff` or `customers`,
    `when_down` as `annoyance` or `emergency`, each `''` where the line is missing or says neither; and
    `proposed`, where either line is the drawing's guess rather than the person's word."""
    body = next((text for title, text in sections(prd) if title.strip().lower() == "who runs it"), "")
    used = USED_BY.search(body)
    down = WHEN_DOWN.search(body)
    runs = RUNS_ON.search(body)

    def one(found: re.Match[str] | None, first: tuple[str, ...], second: tuple[str, ...], a: str, b: str) -> str:
        if found is None:
            return ""
        said = found.group("said").lower()
        head = said.split("—")[0].split(" - ")[0]
        if any(word in head for word in first):
            return a
        return b if any(word in head for word in second) else ""
    return {"used_by": one(used, STAFF, CUSTOMERS, "staff", "customers"),
            "when_down": one(down, ANNOYANCE, EMERGENCY, "annoyance", "emergency"),
            "runs_on": place_of(runs.group("said")) if runs else "",
            "proposed": any("(proposed)" in found.group("said").lower() for found in (used, down, runs) if found)}


def clouds() -> dict[str, str]:
    """Every managed target by key, with what the catalogue calls it: its label up to the dash.

    Read off the catalogue rather than listed here, so the keel names no cloud and a target added to the
    catalogue is a place a brief can say with no edit to this module."""
    return {key: str(entry.get("label", key)).split(" — ")[0].strip()
            for key, entry in CATALOG["targets"].items() if managed(CATALOG, key)}


def place_of(said: str) -> str:
    """Where a `Where it runs:` line says: a managed target's key, `platform` or `nowhere`; `""` where it
    names none.

    The earliest mention wins, rather than the first place listed: a person who writes "one cloud, not the
    other" has said the first, and reading in the list's order could answer the opposite of what they wrote."""
    head = said.lower().split("—")[0].split(" - ")[0]
    places = [*((key, (key, name.lower())) for key, name in clouds().items()), *ELSEWHERE]
    found = [(hit.start(), place) for place, words in places for word in words
             if (hit := re.search(rf"\b{re.escape(word)}\b", head))]
    return min(found)[1] if found else ""


def shape_of(found: dict[str, str | bool]) -> str:
    """The target's shape the two lines give: a skiff for a staff tool whose outage is an annoyance, a liner
    for anything else — and `''` where either line is not there to read."""
    if not found.get("used_by") or not found.get("when_down"):
        return ""
    return "skiff" if found["used_by"] == "staff" and found["when_down"] == "annoyance" else "liner"


def runs_line(found: dict[str, str | bool]) -> str:
    """The report's line for it, in the person's words: never a skiff or a liner."""
    shape = shape_of(found)
    if not shape:
        return "runs for: not said yet — who uses it, and what an afternoon without it is"
    where = ("one environment, the smallest" if shape == "skiff"
             else "the full stack, with a staging environment")
    down = "an annoyance" if found["when_down"] == "annoyance" else "an emergency"
    runs_on = str(found.get("runs_on") or "")
    place = RUNS_IN.get(runs_on) or (f", in your {clouds()[runs_on]} account" if runs_on in clouds() else "")
    guessed = " (proposed)" if found["proposed"] else ""
    return f"runs for: {found['used_by']}, {down} when it is down — {where}{place}{guessed}"


#: Where it runs, as the check's line says it: in the person's own terms, after the size. A cloud says its
#: own name, from `clouds`.
RUNS_IN = {"platform": ", on a platform another team runs", "nowhere": ", on this machine for now"}


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
    play = "; the prototype goes with them" if played(home) else ""
    if not plain:
        return f"surfaces: {len(read)}, states: {total}, each with a heading{who_decided(pages)}{play}"
    return (f"surfaces: {len(read)}, states: {total}; {', '.join(plain)} "
            f"{'has' if len(plain) == 1 else 'have'} no <article class=\"state\"> and "
            f"{'is' if len(plain) == 1 else 'are'} one state each, {SHOWN}{play}")


def who_decided(pages: list[Path]) -> str:
    """`, 10 decided by a person, 6 proposed` where any page says who chose a state; nothing where none does."""
    said = [who for page in pages for _, who in decided_states(page)[1]]
    if not any(said):
        return ""
    proposed = sum(who.lower() == "proposed" for who in said)
    return f", {sum(bool(who) for who in said) - proposed} decided by a person, {proposed} proposed"


def report(home: Path) -> list[str]:
    """The six lines, or a refusal that ends with what to do."""
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
    lines.append(runs_line(service(document) if document else {}))
    open_ = assumptions(document) if document else []
    if not open_:
        lines.append("the draft will have to assume: nothing the document says it left open")
    elif len(open_) == 1:
        lines.append(f"the draft will have to assume: 1 — {open_[0]}")
    else:
        lines.append(f"the draft will have to assume: {len(open_)}")
        lines.extend(f"  — {one}" for one in open_)
    return lines

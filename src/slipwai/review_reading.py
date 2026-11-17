"""What the drawing stage found, read for a person to work through: the review's findings and the open questions.

The surfaces stage writes `specs/<feature>/mockups/research.md` — a `## Questions` list the specification
does not answer — and, where a person handed mock-ups over, a review of each in the `/gaps` shape:
findings triaged Blocker, Should-address, Nice-to-have. On the first real run it wrote 84 findings, 14 of
them Blockers, and the board's only two moves were to approve all of it or to redraw all of it.

**Read defensively, because an agent wrote it.** No line here is a format the method fixes: a finding may be
a list item tagged `[Blocker]`, a row of a table, or a line under a `### Blockers` heading; the counts may be
a summary sentence. What is read is what can be read with confidence, and where the shape is not found the
answer is *unreadable* — the page shows a link to the file and nothing else, and the board that advances
by itself stops, because unknown is not clean. A file that is not there is a different answer: nothing was
reviewed, or nothing was asked.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

REVIEW, RESEARCH = "review.md", "research.md"
#: The three severities of the `find-gaps` triage, each with the spellings an agent has been seen to use.
SEVERITY = re.compile(r"\b(blockers?|should[- ]address(?:es)?|should[- ]haves?|nice[- ]to[- ]haves?)\b",
                      re.IGNORECASE)
#: A severity said as a number of them — `14 Blockers`, `| Blocker | 14 |` — which is a count, not a finding.
COUNTED = re.compile(r"(\d+)\s*(?:\*\*)?\s*(blockers?|should[- ]address(?:es)?|nice[- ]to[- ]haves?)\b"
                     r"|\|\s*(blockers?|should[- ]address(?:es)?|nice[- ]to[- ]haves?)\s*\|\s*(\d+)\s*\|",
                     re.IGNORECASE)
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(?:\[[ xX]\]\s+)?(.*)$")
ROW = re.compile(r"^\s*\|(.*)\|\s*$")
QUESTIONS = re.compile(r"^(?:open\s+)?questions?\b", re.IGNORECASE)
#: How a question somebody has answered is marked: the word, a ticked box, or struck through.
ANSWERED = re.compile(r"\banswered\b|\bresolved\b|^\s*(?:[-*+]|\d+[.)])\s+\[[xX]\]|~~.+~~", re.IGNORECASE)
NONE = re.compile(r"^\s*(?:none|nothing|no (?:open )?questions)\b", re.IGNORECASE)


@dataclass
class Finding:
    severity: str  # `blocker`, `should` or `nice`
    text: str
    where: str = ""  # the heading it was under: the mock-up it is about, where the review says


@dataclass
class Reading:
    """One feature's review and research, as far as each could be read."""

    feature: str
    review: bool = False  # whether there is a review at all
    research: bool = False
    review_read: bool = True  # False where the file is there and its shape is not
    research_read: bool = True
    counts: dict[str, int] = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)
    questions: list[str] = field(default_factory=list)  # the open ones
    answered: int = 0

    @property
    def blockers(self) -> list[Finding]:
        return [one for one in self.findings if one.severity == "blocker"]

    @property
    def readable(self) -> bool:
        return self.review_read and self.research_read


def severity_of(word: str) -> str:
    word = word.lower()
    return "blocker" if word.startswith("blocker") else "should" if word.startswith("should") else "nice"


def plain(text: str) -> str:
    """A line without its markdown: emphasis, code ticks, links and the severity tag said beside it."""
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\[\s*(?:blockers?|should[- ]address(?:es)?|nice[- ]to[- ]haves?)[^\]]*\]", "", text,
                  flags=re.IGNORECASE)
    text = re.sub(r"\*\*\s*(?:blockers?|should[- ]address(?:es)?|nice[- ]to[- ]haves?)\s*:?\s*\*\*:?", "", text,
                  flags=re.IGNORECASE)
    text = re.sub(r"^\s*(?:blockers?|should[- ]address(?:es)?|nice[- ]to[- ]haves?)\s*[:—–-]\s*", "", text,
                  flags=re.IGNORECASE)
    text = text.replace("**", "").replace("`", "").replace("__", "")
    return re.sub(r"\s+", " ", text).strip(" -—–:|")[:300]


def read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def review_of(text: str) -> tuple[dict[str, int], list[Finding], bool]:
    """The counts, the findings, and whether the file's shape was found at all."""
    findings: list[Finding] = []
    stated: dict[str, int] = {}
    where, under, level = "", "", 0  # the last plain heading; the severity a heading put every item under
    for line in text.splitlines():
        for found in COUNTED.finditer(line):
            number, word = (found.group(1), found.group(2)) if found.group(1) else (found.group(4), found.group(3))
            key = severity_of(word)
            stated[key] = max(stated.get(key, 0), int(number))
        heading = HEADING.match(line)
        if heading:
            depth, title = len(heading.group(1)), heading.group(2)
            tagged = SEVERITY.search(title)
            if tagged and not COUNTED.search(title):
                under, level = severity_of(tagged.group(1)), depth
            else:
                if under and depth <= level:
                    under = ""
                where = plain(title)
            continue
        item, row = ITEM.match(line), ROW.match(line)
        body = item.group(1) if item else row.group(1) if row else ""
        if not body.strip() or (row and re.fullmatch(r"[\s|:-]*", row.group(1))):
            continue
        tagged = SEVERITY.search(body)
        if tagged and COUNTED.search(body):
            continue  # a count said in a list or a table, not a finding
        if row and tagged:  # a table: the severity is a cell of its own, and the rest is the finding
            cells = [cell.strip() for cell in body.split("|")]
            words = [cell for cell in cells if cell and not SEVERITY.fullmatch(cell.strip("*[]_ "))]
            findings.append(Finding(severity_of(tagged.group(1)), plain(" — ".join(words)), where))
        elif tagged:
            findings.append(Finding(severity_of(tagged.group(1)), plain(body), where))
        elif item and under:
            findings.append(Finding(under, plain(body), where))
    counted: dict[str, int] = {}
    for one in findings:
        counted[one.severity] = counted.get(one.severity, 0) + 1
    # The larger of what the file says and what was read off it: a summary over findings this cannot parse
    # still counts, and a summary that undercounts is not believed over the findings themselves.
    counts = {key: max(stated.get(key, 0), counted.get(key, 0)) for key in {*stated, *counted}}
    return counts, findings, bool(findings or stated)


def questions_of(text: str) -> tuple[list[str], int, bool]:
    """The open questions under every `Questions` heading, how many are marked answered, and whether the shape
    was found. A file with no such heading asks nothing."""
    open_, answered, shaped = [], 0, True
    level = 0
    held: list[str] = []  # the section's lines, read at its end
    sections: list[list[str]] = []
    for line in [*text.splitlines(), "# end"]:
        heading = HEADING.match(line)
        if heading and level and len(heading.group(1)) <= level:
            sections.append(held)
            held, level = [], 0
        if heading and QUESTIONS.match(heading.group(2).strip("*: ")):
            level = len(heading.group(1))
            continue
        if level:
            held.append(line)
    for section in sections:
        items: list[str] = []
        for line in section:
            item = ITEM.match(line)
            if item:
                items.append(line)
            elif items and line.startswith((" ", "\t")) and line.strip():
                items[-1] += " " + line.strip()
        words = [line for line in section if line.strip() and not HEADING.match(line)]
        if not items:
            if words and not NONE.match(words[0]):
                shaped = False
            continue
        for line in items:
            if ANSWERED.search(line):
                answered += 1
            else:
                body = ITEM.match(line)
                open_.append(plain(body.group(1) if body else line))
    return open_, answered, shaped


def reading(root: Path, feature: str) -> Reading:
    """The feature's review and research, read; an empty reading where neither was written."""
    home = root / "specs" / feature / "mockups"
    found = Reading(feature)
    review = home / REVIEW
    if review.exists():
        found.review = True
        text = read_text(review)
        counts, findings, shaped = review_of(text) if text is not None else ({}, [], False)
        found.counts, found.findings, found.review_read = counts, findings, shaped
    research = home / RESEARCH
    if research.exists():
        found.research = True
        text = read_text(research)
        questions, answered, shaped = questions_of(text) if text is not None else ([], 0, False)
        found.questions, found.answered, found.research_read = questions, answered, shaped
    return found


def gate(root: Path, feature: str) -> str:
    """Why the board, advancing by itself, must not approve this storyboard: a sentence, or nothing where the
    review is clean and nothing is asked. A review it cannot read stops it as surely as a Blocker does."""
    found = reading(root, feature)
    why = []
    if not found.review_read:
        why.append(f"specs/{feature}/mockups/{REVIEW} could not be read, and a review nobody can read is not a "
                   "clean one")
    elif found.counts.get("blocker"):
        number = found.counts["blocker"]
        why.append(f"the review has {number} Blocker finding{'' if number == 1 else 's'}")
    if not found.research_read:
        why.append(f"the questions in specs/{feature}/mockups/{RESEARCH} could not be read")
    elif found.questions:
        number = len(found.questions)
        why.append(f"{number} question{'' if number == 1 else 's'} in the research only you can answer "
                   f"{'is' if number == 1 else 'are'} open")
    return "; ".join(why)

"""What the drawing stage found: the counts it declares, which decide, and its findings, which are only shown.

The surfaces stage writes `specs/<feature>/mockups/research.md` — the questions the specification leaves
open — and, where it reviewed anything, findings in the `/gaps` triage: Blocker, Should-address,
Nice-to-have. On the first real run it wrote 84 findings, 14 of them Blockers, and a board set to advance
approved straight past them. The files on this machine's projects are every shape an agent cares to write:
`review.md`, a `review-<surface>.md` per page, `gaps.md`, a `review/` folder; findings as list items, table
rows, a heading each, bold paragraphs; counts in a summary sentence or a table, or not at all.

**So the gate does not read prose.** `/mockups` has the stage declare what is left in two lines of its own,
`Blockers open: N` and `Questions open: N`, each on a line by itself in `research.md`, kept current by the
stage and by every turn of conversation that settles one. The board advancing by itself reads those two
lines and nothing else (`declared`, `gate`): both there and both nought is clean; anything else stops it,
saying the numbers or saying which line is missing — a drawing from before the lines is stopped, not waved
through.

**The panel reads the findings leniently, for a person** (`reading`): across every review-like file, as far
as each can be read, and said beside the stage's own count where the two differ. Nothing it reads decides
anything. Every file is read once, as a plain file, capped (`talk.read_bytes`): a pipe, a link or a file of
one endless line put where a review goes is not what holds a request up.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .talk import read_bytes

RESEARCH = "research.md"
#: The two counts the stage declares — the only thing the gate reads — and what between the words and the number
#: is forgiven: a colon, a table's bar, bold, italic, backticks, spaces.
DECLARED = re.compile(r"(blockers|questions)[ \t]+open[ \t]*[:|=][ \t]*(.*)$", re.IGNORECASE)
#: What may come before the words on their line: a quote, a table's bar, a list marker, indentation.
LEAD = re.compile(r"^[\s>|+-]*(?:\d{1,3}[.)]\s+)?")
#: A count: a whole number, then nothing but a full stop or a remark in brackets.
COUNT = re.compile(r"(\d{1,5})[ \t]*[.!]?[ \t]*(?:\([^)]*\))?[ \t]*[.!]?")
#: What the drawing is told, in `/mockups` and in the board's own prompt to the drawing, word for word.
DECLARE = ("Begin research.md with these two lines, as plain text — no bold, no list marker:\n\n"
           "Blockers open: pending\nQuestions open: pending\n\n"
           "and only when the review is finished replace `pending` with the counts, in figures — `Blockers open` "
           "the Blocker findings nobody has settled, `Questions open` the questions under `## Questions` nobody "
           "has answered, 0 where there are none — and keep them true as findings and questions are settled. The "
           "board reads these two lines to tell whether anything is left to discuss; `pending` tells it the "
           "review is not finished.")
#: How much of a file is read, and how much of one line: a review is pages, not megabytes.
READ = 512 * 1024
LINE = 2000
#: The severities of the `find-gaps` triage, with the spellings an agent has been seen to use.
WORDS = r"blockers?|critical|should[- ]address(?:es)?|should[- ]haves?|nice[- ]to[- ]haves?"
SEVERITY = re.compile(rf"\b({WORDS})\b", re.IGNORECASE)
COUNTED = re.compile(rf"\b(\d{{1,4}})\s{{0,3}}(?:\*\*)?\s{{0,3}}({WORDS})\b"
                     rf"|\|\s{{0,3}}({WORDS})\s{{0,3}}\|\s{{0,3}}(\d{{1,4}})\s{{0,3}}\|", re.IGNORECASE)
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
BOLD_HEADING = re.compile(r"^\s*\*\*([^*]{1,80})\*\*:?\s*$")
ITEM = re.compile(r"^\s*(?:[-*+]|\d{1,4}[.)])\s+(?:\[[ xX]\]\s+)?(.*)$")
ROW = re.compile(r"^\s*\|(.*)\|\s*$")
QUESTIONS = re.compile(r"^(?:open\s+|unresolved\s+|unanswered\s+)?questions?\b", re.IGNORECASE)
#: How a settled finding or an answered question is marked: as `/mockups` says to, or ticked, or struck.
SETTLED = re.compile(r"—\s*answered\b|\banswered\s*\(D\d+\)|^\s*(?:[-*+]|\d+[.)])\s+\[[xX]\]|~~.+~~", re.IGNORECASE)
NONE = re.compile(r"^\s*(?:[-*+]\s+)?_?(?:none|nothing|no\s+(?:open\s+)?(?:blockers?|questions?|findings?))\b",
                  re.IGNORECASE)


@dataclass
class Finding:
    severity: str  # `blocker`, `should` or `nice`
    text: str
    where: str = ""  # the heading it was under, or the file


@dataclass
class Reading:
    """One feature's findings and questions, read leniently for the panel; and the stage's own count."""

    feature: str
    files: list[str] = field(default_factory=list)  # every review-like file, by its name under mockups/
    research: bool = False
    findings: list[Finding] = field(default_factory=list)
    questions: list[str] = field(default_factory=list)  # the open ones the panel could find
    blockers_open: int | None = None  # the stage's own `Blockers open:` line
    questions_open: int | None = None

    @property
    def blockers(self) -> list[Finding]:
        return [one for one in self.findings if one.severity == "blocker"]


def text_of(path: Path) -> str | None:
    """A file as text — once, a plain file, capped, each line cut short — or None where it is not one."""
    read = read_bytes(path, READ)
    if read is None:
        return None
    return "\n".join(line[:LINE] for line in read[0].decode("utf-8", "replace").splitlines())


def severity_of(word: str) -> str:
    word = word.lower()
    return "blocker" if word.startswith(("blocker", "critical")) else "should" if word.startswith("should") \
        else "nice"


def plain(text: str) -> str:
    """A line without its markdown and its severity tag."""
    text = re.sub(r"\[([^\]]{0,300})\]\([^)]{0,300}\)", r"\1", text)
    text = re.sub(rf"\[\s*(?:{WORDS})[^\]]{{0,40}}\]", "", text, flags=re.IGNORECASE)
    text = re.sub(rf"\*\*\s*(?:{WORDS})\s*:?\s*\*\*:?", "", text, flags=re.IGNORECASE)
    text = re.sub(rf"^\s*(?:{WORDS})\s*[:—–-]\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(rf"\s[—–-]\s(?:{WORDS})\s[—–-]\s", " — ", text, flags=re.IGNORECASE)
    text = text.replace("**", "").replace("`", "").replace("__", "")
    return re.sub(r"\s+", " ", text).strip(" -—–:|")[:300]


def section_title(title: str) -> str:
    """The severity a heading puts what is under it in — `Blockers`, `**Should-address**` — or nothing where the
    heading is a finding of its own (`G1 — Blocker — no held state`) or about something else."""
    words = SEVERITY.sub("", plain(title)).strip(" ()0123456789:—–-")
    found = SEVERITY.search(title)
    return severity_of(found.group(1)) if found and not words else ""


def findings_of(text: str, name: str) -> list[Finding]:
    """Every finding a person could be shown, from one review-like file. Lenient on purpose: it decides nothing."""
    found: list[Finding] = []
    where, under, level = name, "", 7
    detail = False  # inside a finding that is a heading of its own: its bullets are its detail, not findings
    for line in text.splitlines():
        heading, bold = HEADING.match(line), BOLD_HEADING.match(line)
        if heading or bold:
            depth = len(heading.group(1)) if heading else 6
            title = heading.group(2) if heading else bold.group(1) if bold else ""
            detail = False
            if (severity := section_title(title)):
                under, level = severity, depth
                continue
            if under and depth <= level:
                under = ""
            tagged = SEVERITY.search(title)
            if heading and under and depth > level:  # `## Blockers` over `### G1 — …`: a finding a heading
                if not SETTLED.search(title):
                    found.append(Finding(under, plain(title), where))
                detail = True
            elif heading and tagged and not COUNTED.search(title):  # `### G1 — Blocker — …`
                if not SETTLED.search(title):
                    found.append(Finding(severity_of(tagged.group(1)), plain(title), where))
                detail = True
            elif heading:
                where = plain(title) or where
            continue
        if detail:
            continue
        item, row = ITEM.match(line), ROW.match(line)
        body = item.group(1) if item else row.group(1) if row else line if line.lstrip().startswith("**") else ""
        if not body.strip() or (row and re.fullmatch(r"[\s|:-]*", row.group(1))) or NONE.match(body):
            continue
        if SETTLED.search(line) or COUNTED.search(body):
            continue  # settled, or a count said in a list or a table
        tagged = SEVERITY.search(body)
        # Led by its severity — `[Blocker] …`, `**Blocker:** …`, `Nice-to-have — …` — or tagged `[Critical]`.
        lead = (re.match(rf"\s*(?:\[|\*\*)?\s*({WORDS})\b", body, re.IGNORECASE)
                or re.search(rf"\[\s*({WORDS})\b", body, re.IGNORECASE))
        if row and len(SEVERITY.findall(body)) > 1:
            continue  # a table's head, naming the severities as its columns
        if row and tagged:
            cells = [cell.strip() for cell in body.split("|")]
            words = [cell for cell in cells if cell and not SEVERITY.fullmatch(cell.strip("*[]_ "))]
            found.append(Finding(severity_of(tagged.group(1)), plain(" — ".join(words)), where))
        elif lead and plain(body):
            found.append(Finding(severity_of(lead.group(1)), plain(body), where))
        elif item and under:
            found.append(Finding(under, plain(body), where))
    return found


def questions_of(text: str) -> list[str]:
    """The open questions under every `Questions` heading, bold or not, items or `### Q1` sub-headings."""
    open_: list[str] = []
    level, inside = 0, False
    for line in text.splitlines():
        heading, bold = HEADING.match(line), BOLD_HEADING.match(line)
        if heading or bold:
            depth = len(heading.group(1)) if heading else 6
            title = (heading.group(2) if heading else bold.group(1) if bold else "").strip("*: ")
            if QUESTIONS.match(title):
                level, inside = depth, True
                continue
            if inside and depth <= level:
                inside = False
            elif inside and heading and not SETTLED.search(line):  # `### Q1 — Who cancels?`
                open_.append(plain(title))
            continue
        item = ITEM.match(line)
        if inside and item and not NONE.match(item.group(1)) and not SETTLED.search(line):
            open_.append(plain(item.group(1)))
    return open_


def declared(text: str) -> tuple[int | None, int | None]:
    """The stage's own two counts, read forgivingly: whatever is around them — a list marker, bold, italic,
    backticks, a blockquote, a table's bars, indentation, case, a trailing full stop or a remark in brackets —
    and both on one line or the pair said twice where they agree. A count is `None`, unknown, where it is not
    said, is said in words or as `pending`, is not a whole number, or is said twice and disagrees. `N` alone
    is the instruction quoted, not a count. Only a line that begins with the words (after the markers), with a
    colon or a table's bar after them, is read: prose that happens to say "blockers open" is not a count."""
    found: dict[str, set[int]] = {"blockers": set(), "questions": set()}
    unknown: set[str] = set()
    for line in text.replace("\r", "").splitlines():
        line = re.sub(r"[*_`]", "", line)
        for part in re.split(r"[,;]\s+(?=(?:blockers|questions)\s+open\b)", line, flags=re.IGNORECASE):
            said = DECLARED.match(LEAD.sub("", part, count=1).strip())
            if not said:
                continue
            key, value = said.group(1).lower(), said.group(2).strip().rstrip("|").strip()
            whole = COUNT.fullmatch(value)
            if whole:
                found[key].add(int(whole.group(1)))
            elif value.lower() != "n":
                unknown.add(key)

    def one(key: str) -> int | None:
        return None if key in unknown or len(found[key]) != 1 else next(iter(found[key]))
    return one("blockers"), one("questions")


def review_files(home: Path) -> list[Path]:
    """Every file a drawing has written its findings in, by the names agents have used."""
    named = [home / "review.md", home / "gaps.md", *sorted(home.glob("review-*.md")),
             *sorted((home / "review").glob("*.md"))]
    return [path for path in named if path.is_file() and not path.is_symlink()]


def reading(root: Path, feature: str) -> Reading:
    """The feature's findings and questions for the panel, and the stage's own count."""
    home = root / "specs" / feature / "mockups"
    found = Reading(feature)
    for path in review_files(home):
        text = text_of(path)
        if text is not None:
            found.files.append(path.relative_to(home).as_posix())
            found.findings += findings_of(text, path.stem)
    research = text_of(home / RESEARCH) if (home / RESEARCH).is_file() else None
    if research is not None:
        found.research = True
        found.questions = questions_of(research)
        found.blockers_open, found.questions_open = declared(research)
    return found


def gate(root: Path, feature: str) -> str:
    """Why the board, advancing by itself, must not approve this storyboard — a sentence, or nothing where the
    stage has declared nought Blockers and nought questions open. Reads the declaration and nothing else, and
    only `advance` reads this: a drawing without the lines is a drawing like any other to a person."""
    research = root / "specs" / feature / "mockups" / RESEARCH
    text = text_of(research) if research.is_file() and not research.is_symlink() else None
    blockers, questions = declared(text) if text is not None else (None, None)
    missing = [line for line, value in (("Blockers open: N", blockers), ("Questions open: N", questions))
               if value is None]
    if missing:
        return (f"specs/{feature}/mockups/{RESEARCH} does not say {' and '.join(f'`{one}`' for one in missing)} "
                "with a number, so the board cannot tell whether anything is left to discuss — add the line, or "
                "judge the storyboard yourself; a project made before the drawing was asked for it gets the "
                "instruction with `slipwai migrate`")
    why = []
    if blockers:
        why.append(f"the drawing says {blockers} Blocker{' is' if blockers == 1 else 's are'} open")
    if questions:
        why.append(f"{questions} question{'' if questions == 1 else 's'} only you can answer "
                   f"{'is' if questions == 1 else 'are'} open")
    return "; ".join(why)

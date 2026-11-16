"""One `decisions.md` entry read the way a person reads it: its sentence, its options, which one was taken.

The entries are written by agents for agents. A question cites requirement and decision numbers; the
options are a paragraph each, run together on one line as `(a) … ; (b) … ; (c) …`, the one the stage
recommended in bold; the decision is often just `(a).`. A product owner reading that cannot tell what was
decided. So an entry written since the rule carries `**In short:**` — one sentence saying what the product
now does — and the board leads with it. An entry written before the rule leads with its question as it did.

**The options are split where they can be, and shown as written where they cannot.** Two shapes are in real
records: `(a) … ; (b) …` with lower-case letters in brackets, and `A — … · B — …`. The letters have to run
`a, b, c` from the first one for a split to be trusted: a stray `(c)` inside option (a)'s words, citing
another entry's option, would otherwise cut it in two. The last option ends at its first full stop followed
by a new sentence, because the field often goes on after the list — "The candidates are `make seams`'
groups…" — and that is the field's commentary, not part of the option. A list that does not split is shown
whole, which is what the board showed before, rather than guessed at.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_HEAD = re.compile(r"^## (D(?:-[A-Za-z0-9_-]+-)?\d+)\s*[—-]\s*(.*)$", re.MULTILINE)
#: One `**Label:** value`, several to a line where ` · ` joins them; across the lines a field continues on.
_FIELD = re.compile(r"\*\*([^*:\n]+):\*\*\s*(.*?)(?=\s+·\s+\*\*[^*:\n]+:\*\*|\Z)", re.DOTALL)
#: The status the gate allows for a stop meant for a person and answered with nobody there.
AWAITING = "awaiting human confirmation"
#: What the sentence field is called, in the entry and on the board.
SENTENCE = "In short"


@dataclass(frozen=True)
class Option:
    """One option as a person reads it: its letter, its words, and whether the stage recommended it."""

    letter: str
    text: str
    recommended: bool = False


def parse(text: str) -> dict[str, dict[str, str]]:
    """`decisions.md` as `D<n>` → its heading and each `**Label:** value`.

    A field goes on over the indented lines under it — the shape's own `Why` does, and real `Options` carry a
    table there — so a line that does not open a new `- **Label:**` belongs to the field above it. Only the
    first line of each was read before, which cut an Options list after its first line."""
    found: dict[str, dict[str, str]] = {}
    heads = list(_HEAD.finditer(text))
    for index, head in enumerate(heads):
        body = text[head.end():heads[index + 1].start() if index + 1 < len(heads) else len(text)]
        parts = {"title": head.group(2).strip()}
        bullets: list[str] = []
        for line in body.splitlines():
            if line.startswith("- **"):
                bullets.append(line[2:])
            elif bullets and (line.startswith((" ", "\t")) or not line.strip()):
                bullets[-1] += "\n" + line.strip()
            elif line.strip():
                bullets.append("")  # prose between entries' fields ends the field above it
        for bullet in bullets:
            for label, value in _FIELD.findall(bullet.strip()):
                parts.setdefault(label.strip(), re.sub(r"\n{3,}", "\n\n", value.strip()))
        found[head.group(1)] = parts
    return found


def plain(text: str) -> str:
    """The words without the file's marks: `**seven contexts**` reads as seven contexts, and a backticked
    name as the name."""
    return re.sub(r"\*\*|__|`", "", text).strip()


def _cut_last(text: str) -> str:
    """The last option, without whatever the field goes on to say after the list."""
    text = text.split("\n\n", 1)[0]
    ended = re.search(r"(?<=[.!?])\s+(?=[A-Z`])", text)
    return text[:ended.start()] if ended else text


def _option(letter: str, words: str, last: bool) -> Option:
    words = (_cut_last(words) if last else words).strip().rstrip(";·,").strip()
    if not last:
        words = re.sub(r"\s+(?:or|and)$", "", words)
    recommended = bool(re.search(r"\(recommended\)", words, re.IGNORECASE))
    words = re.sub(r"\s*\((?:recommended)\)", "", words, flags=re.IGNORECASE)
    words = " ".join(plain(words).split()).rstrip(".;").strip()
    return Option(letter, words, recommended)


def _split(text: str, marker: str, letters: str) -> list[Option] | None:
    """Split on `marker` (with `{}` for the letter), the letters running in order from the first."""
    starts: list[tuple[int, int, str]] = []
    at = 0
    for letter in letters:
        found = re.compile(marker.format(re.escape(letter))).search(text, at)
        if not found:
            break
        starts.append((found.start(1), found.end(), letter))
        at = found.end()
    if len(starts) < 2:
        return None
    return [_option(letter, text[end:starts[n + 1][0] if n + 1 < len(starts) else len(text)],
                    n + 1 == len(starts)) for n, (_, end, letter) in enumerate(starts)]


def options(text: str) -> list[Option] | None:
    """The options an entry's `Options` field lists, or None where it lists them in no shape this reads."""
    text = text.strip()
    if not text:
        return None
    first = text.split("\n\n", 1)[0]
    return (_split(first, r"(?:^|[;·,]\s*|\s)(\(\s*{}\s*\))\s*", "abcdefgh")
            or _split(first, r"(?:^|\s[·;]\s*)({})\s+[—–-]\s+", "ABCDEFGH"))


def chosen(decision: str, listed: list[Option] | None) -> tuple[str, str]:
    """The letter the `Decision` field took, and what it says beyond the letter — `(a).` alone says nothing
    beyond, `(a). (1) JoinWithCode matches only …` says the detail the option was made exact with."""
    if not listed:
        return "", decision.strip()
    letters = {one.letter for one in listed}
    said = decision.strip()
    took = re.match(r"^\s*(?:(?:a\s+)?variant\s+of\s+|option\s+)?\(\s*([a-h])\s*\)", said, re.IGNORECASE) \
        or re.match(r"^\s*(?:option\s+)?([A-H])(?=\s*[—–-]|\s*[.,;:]|\s*$)", said)
    if not took or took.group(1) not in letters:
        return "", said
    rest = said[took.end():].lstrip(" .,;:—–-").strip()
    return took.group(1), rest


def awaiting(status: str) -> bool:
    """Whether a person has yet to confirm this decision: the stop was meant for them and nobody was there."""
    return plain(status).lower().startswith(AWAITING)


def confirmed_status(status: str, day: str) -> str | None:
    """The `Status` a person's confirmation leaves, or None where the decision is not awaiting one."""
    return f"confirmed by human {day}" if awaiting(status) else None

"""A slice's example map, read from its `examples.md`: the story, the rules, their examples, the questions.

The example-map stage writes one shape (`assets/toolkit/commands/example-map.md`): `## Story`, then
`## R<n> — <rule>` each with its `### Scenario: <title> (<ID>)` blocks of **Given** · **When** · **Then**,
then `## Questions`. Real maps stray from it — a scenario stated as a list rather than Given/When/Then, a
heading marked `*(gaps pass)*`, a `## Questions answered` beside `## Questions`, questions written as a
paragraph — so this reads what it can and never raises: a file that does not follow the shape is a partial
map, and a slice with no file has none.

**A question is open until its line says it has been answered.** The questions are the list items under any
heading that starts `## Questions`, after any sentence that introduces them and up to the next paragraph
(what follows is a note or the stage's recommendations, not another question). A section that opens with
"None open" holds no questions, and its sentence is kept as the map's note. An item is answered when its
answer says so — `answered by`, `decided by`, or an arrow straight onto a decision (`→ D26`,
`→ standing D55`) — and nothing before that says it is still open: `→ not yet decided`,
`→ to be decided by the host` and `→ open; see D26` are open, and so is AC1's `Q4 … → the plan's to decide`.

**An example is proven when `tasks.md`'s `## Examples proven` names it beside a test**: in the first cell
of a table row, or at the head of a list item, with a test named after it (a path, a quoted test name, a
backtick) and no word that it is not proven, deferred or pending. `| AC1-3 What Discord shares | screen |
SignIn.test.tsx … |`, `| CL4-1, 3, 5 | route | … |` and `- TB1-1 Priya sets … — set-club-week.test.ts` are;
`| X-3 | not proven — deferred |` is not, and a slice whose list has no such section has nothing proven.

**A berth's uncommitted map is not seen**: in flight the map is read off the slice's branch, so what a
session has written and not yet committed shows once it is.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

RULE = re.compile(r"^##\s+(R\d+)\b\s*[—–:.-]?\s*(.*)$")
SCENARIO = re.compile(r"^###\s+(?:Scenario|Example)\b:?\s*(.*)$", re.I)
#: The id a scenario's heading ends on, before any `*(review)*` marks after it.
ENDS_ON = re.compile(r"\(([A-Za-z][A-Za-z0-9]*-\d+[a-z]?)\)\s*$")
MARKS = re.compile(r"(\s*\*\([^)]*\)\*)+\s*$")
GWT = re.compile(r"\*\*(Given|When|Then)\*\*", re.I)
ITEM = re.compile(r"^(?:[-*]|\d+[.)])\s+(.*)$")
#: A question's own id, where it carries one: `Q1.`, `**AC2-q1**`. One without is called by its place.
ASKED_ID = re.compile(r"^(?:\*\*)?([A-Za-z0-9]+-q\d+|Q\d+)(?:\*\*)?[.:]?\s*(?:—\s*)?")
#: Where an answer says it has been answered: the end of the match is how far the open words are looked for.
ANSWERED = re.compile(r"\b(?:answered|decided) by\b|^\W*(?:answered\b|(?:standing\s+)?D\d+\b)", re.I)
ANSWERED_BY = re.compile(r"\b(?:answered|decided) by\b", re.I)
#: The words that keep a question open whatever follows them.
STILL_OPEN = re.compile(r"\bnot yet\b|\bto be (?:decided|answered)\b|\bopen\b|\bundecided\b|\bunanswered\b|"
                        r"\bto decide\b|\bpending\b", re.I)
#: The sentence a Questions section opens with when it has none to list.
NONE_OPEN = re.compile(r"^\W*(?:none\b|no questions?\b|nothing open\b)", re.I)
#: A proof row's test cell names a test (a backtick, a quoted name, a file), and says nothing against it.
NAMES_A_TEST = re.compile(r'[`"“]|\b[\w-]+\.\w{1,4}\b|\btests?\b', re.I)
NOT_PROVEN = re.compile(r"\bnot (?:yet )?proven\b|\bunproven\b|\bdeferred\b|\bpending\b|\bnot yet\b", re.I)
#: A scenario id as a proof row names it, and what may follow it: a range, or more numbers of the same prefix.
FULL = re.compile(r"\b([A-Z][A-Za-z0-9]*)-(\d+)\b")
#: The proof's heading: at the start of a line, or ending one after an unclosed backtick. A task that says
#: "fill `## Examples proven` later" closes its backtick and is not the heading.
PROOF = re.compile(r"^##\s+Examples proven\b|`##\s+Examples proven\s*$", re.I)


@dataclass
class Example:
    id: str
    title: str
    given: str = ""
    when: str = ""
    then: str = ""
    #: The body as written, for a scenario that is not Given/When/Then.
    said: str = ""
    proven: bool = False


@dataclass
class Rule:
    id: str
    text: str
    examples: list[Example] = field(default_factory=list)


@dataclass
class Question:
    id: str
    text: str
    answer: str
    open: bool


@dataclass
class ExampleMap:
    story: str = ""
    rules: list[Rule] = field(default_factory=list)
    questions: list[Question] = field(default_factory=list)
    #: A Questions section written as a sentence ("None open — D72–D78 answered …"): asked and settled.
    notes: list[str] = field(default_factory=list)

    @property
    def examples(self) -> list[Example]:
        return [one for rule in self.rules for one in rule.examples]


def plural(count: int, word: str) -> str:
    return f"{count} {word}{'' if count == 1 else 's'}"


def summary(found: ExampleMap) -> str:
    """The window's line: `11 rules · 16 examples · 4 questions, 1 open · 14 of 16 proven`."""
    examples, opened = found.examples, sum(1 for one in found.questions if one.open)
    asked = (f"{plural(len(found.questions), 'question')}, {opened or 'none'} open" if found.questions
             else "no questions")
    proven = sum(1 for one in examples if one.proven)
    return " · ".join((plural(len(found.rules), "rule"), plural(len(examples), "example"), asked,
                       f"{proven} of {len(examples)} proven"))


def card_counts(found: ExampleMap | None) -> str:
    """The card's Examples step: `11 rules · 16 examples · 1 question open`."""
    if found is None:
        return ""
    opened = sum(1 for one in found.questions if one.open)
    return " · ".join((plural(len(found.rules), "rule"), plural(len(found.examples), "example"),
                       f"{opened} question{'' if opened == 1 else 's'} open" if opened else "no questions open"))


def sections(text: str) -> list[tuple[str, list[str]]]:
    """The file cut at its `##` headings: each heading with the lines under it, `###` included."""
    found: list[tuple[str, list[str]]] = [("", [])]
    for line in text.splitlines():
        if line.startswith("## "):
            found.append((line, []))
        else:
            found[-1][1].append(line)
    return found


def joined(lines: list[str]) -> str:
    return " ".join(" ".join(lines).split())


def scenario(heading: str, body: list[str]) -> Example:
    named = MARKS.sub("", heading).strip()
    found = ENDS_ON.search(named)
    title = named[:found.start()].strip() if found else named
    one = Example(id=found.group(1) if found else "", title=title)
    text = joined([line for line in body if line.strip()])
    parts = GWT.split(text)
    if len(parts) > 1:
        for word, words in zip(parts[1::2], parts[2::2], strict=False):
            setattr(one, word.lower(), words.strip().strip("·").strip())
    else:
        one.said = text
    return one


def rule_of(heading: str, lines: list[str]) -> Rule:
    found = RULE.match(heading)
    rule = Rule(id=found.group(1), text=found.group(2).strip()) if found else Rule(id="", text="")
    # Each `### Scenario` takes the lines under it; any other `###` (a "Found at review" note) ends it.
    titled, body = "", list[str]()
    for line in [*lines, "### "]:
        if line.startswith("### "):
            if titled:
                rule.examples.append(scenario(titled, body))
            matched = SCENARIO.match(line)
            titled, body = (matched.group(1) or "?") if matched else "", []
        elif titled:
            body.append(line)
    return rule


def questions_of(lines: list[str]) -> tuple[list[Question], str]:
    """The section's questions, and the sentence it opens with where it lists none."""
    items: list[list[str]] = []
    opening: list[str] = []
    for line in lines:
        if not line.strip():
            continue
        item = ITEM.match(line)
        if item and not line[0].isspace():
            if NONE_OPEN.match(joined(opening)):
                break  # "None open. Each reading taken here …": what is listed is not a question
            items.append([item.group(1)])
        elif line[0].isspace() and items:
            items[-1].append(line)
        elif items:
            break  # a paragraph: what follows is a note or a recommendation, not a question
        else:
            opening.append(line)  # "Open for the host:", or a section that is only this sentence
    found = [question(joined(item), f"Q{index}") for index, item in enumerate(items, 1)]
    return found, "" if found else joined(opening)


def answered(said: str, arrowed: bool) -> bool:
    plain = said.replace("*", "")
    mark = (ANSWERED if arrowed else ANSWERED_BY).search(plain)
    return mark is not None and not STILL_OPEN.search(plain[:mark.end()])


def question(text: str, fallback: str) -> Question:
    """One question; one with no id of its own is called by where it stands in the list."""
    named = ASKED_ID.match(text)
    ident, text = (named.group(1), text[named.end():]) if named else (fallback, text)
    asked, arrow, after = text.partition("→")
    return Question(id=ident, text=asked.strip().rstrip(".") if arrow else text, answer=after.strip(),
                    open=not answered(after if arrow else text, bool(arrow)))


def read(text: str, proof: str = "") -> ExampleMap:
    """One `examples.md`, and the `tasks.md` beside it for which examples a test proves."""
    found = ExampleMap()
    loose = Rule(id="", text="")
    for heading, lines in sections(text):
        title = heading[3:].strip()
        if title.lower() == "story":
            found.story = joined([line for line in lines if line.strip()])
        elif RULE.match(heading):
            found.rules.append(rule_of(heading, lines))
        elif title.lower().startswith("questions"):
            asked, note = questions_of(lines)
            found.questions += asked
            found.notes += [note] if note else []
        elif not found.rules:
            # Scenarios written before any rule is named: kept, under a rule with no name.
            loose.examples += rule_of("", lines).examples
    if loose.examples:
        found.rules.insert(0, loose)
    proven = proven_ids(proof)
    for one in found.examples:
        one.proven = bool(one.id) and one.id in proven
    return found


def named_ids(cell: str) -> set[str]:
    """Every scenario id a proof row's first cell names: `AC1-3`, `LB2-2, LB2-10`, `CL4-1, 3, 5`, `X-1–X-4`."""
    found: set[str] = set()
    for one in FULL.finditer(cell):
        prefix, first = one.group(1), int(one.group(2))
        found.add(f"{prefix}-{one.group(2)}")
        rest = cell[one.end():]
        span = re.match(rf"\s*(?:[–-]|to)\s*(?:{re.escape(prefix)}-)?(\d+)\b", rest)
        if span and first < int(span.group(1)) <= first + 500:
            found.update(f"{prefix}-{number}" for number in range(first, int(span.group(1)) + 1))
            continue
        more = re.match(r"(?:\s*,\s*(?:and\s+)?\d+\b)+", rest)
        found.update(f"{prefix}-{number}" for number in re.findall(r"\d+", more.group(0) if more else ""))
    return found


def proven_ids(text: str) -> set[str]:
    """The scenario ids `tasks.md`'s `## Examples proven` names beside a test.

    The heading is found where it is written, which is not always at the start of a line: AC5's session
    wrote the heading at the end of the line that ticked its closing task, T015, and the table under that.
    """
    found: set[str] = set()
    inside = False
    for line in text.splitlines():
        if PROOF.search(line):
            inside = True
        elif line.startswith("## "):
            inside = False
        elif not inside:
            continue
        elif line.startswith("|"):
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if len(cells) > 1 and beside_a_test(" | ".join(cells[1:])):
                found |= named_ids(cells[0])
        elif item := ITEM.match(line):
            head, dash, rest = item.group(1).partition(" — ")
            head, tick, after = head.partition("`")
            if beside_a_test(rest if dash else tick + after):
                found |= named_ids(head)
    return found


def beside_a_test(said: str) -> bool:
    return bool(NAMES_A_TEST.search(said)) and not NOT_PROVEN.search(said)

"""`docs/feedback/`: what a person said after using the built product, and what it turned into.

The board had a way into the work for a new feature (`docs/intake/`, from `/sail`) and a way to answer a
captain that had stopped (a `told`), and nothing for the commonest thing a person has after trying the app:
*this is wrong*, *I wanted something else*, *it would help if*. They said it in a terminal or not at all, and
nothing kept a trail from what was said to the change it caused.

**One file per item, and the file is the state.** Capture writes `NNNN-<slug>.md`: front matter for the
context the board knew (the slice, the capability, the signed-in user, trunk's commit) and the person's
words as the body. Triage — a headless session, `scripts/agents/triage.py` — adds `route`, `about`,
`becomes` and `proposed`, and a `## Proposed` section with its reasons. Nothing else moves until a person
confirms here, and confirming adds `confirmed` and `became`: what it was handed to. Dropping adds `dropped`.

**Confirming hands the item to what already exists**, never to anything new:

- *scope* is captured as an intake idea, the same `docs/intake/<slug>/brief.md` `/sail` writes;
- *note* goes under `## From feedback` in `docs/design.md`, which every slice with a screen reads first;
- *defect*, *change* and *planned* are a `told` to the slice's stream, addressed to its captain and
  written `by: feedback`. Addressed, so it is not a note under *Waiting on you*; not a person's, so it
  clears no park — a confirmed defect in L18 must not read as the answer to L10's question. A change to a
  slice in flight says which a person chose: park it now with the change as the reason, or leave it alone
  until it has merged.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

PLACE = "docs/feedback"
DESIGN = "docs/design.md"
DESIGN_HEADING = "## From feedback"
#: Where each item can go, as triage proposes and a person confirms. The order is the menu's.
ROUTES = {"defect": "Defect", "change": "Change", "scope": "New scope", "planned": "Already planned",
          "note": "Note"}
#: The context a capture may carry, in the order it is written. Anything else a page sends is ignored.
CONTEXT = ("from", "page", "feature", "fairway", "slice", "capability", "signed-in-as", "trunk")
#: How much a person may say in one item, and how long one line of context may be.
WORDS, LINE = 4000, 200
#: What a person chooses for a change that reaches a slice still being worked.
HOLDS = ("park", "after-merge")
_SLICE = re.compile(r"[A-Za-z0-9_.-]{1,40}")
_NAME = re.compile(r"^(\d{4})-[a-z0-9-]+\.md$")
_SLUG = re.compile(r"[^a-z0-9]+")


@dataclass
class Item:
    """One record: its number, its file, its front matter in order, and what the person said."""

    number: str
    path: Path
    fields: dict[str, str] = field(default_factory=dict)
    said: str = ""
    proposed: str = ""

    @property
    def state(self) -> str:
        if self.fields.get("dropped"):
            return "dropped"
        if self.fields.get("confirmed"):
            return "confirmed"
        if self.fields.get("proposed") and self.fields.get("route") in ROUTES:
            return "proposed"
        return "triaging"

    @property
    def route(self) -> str:
        return self.fields.get("routed") or self.fields.get("route", "")

    @property
    def title(self) -> str:
        first = next((line for line in self.said.splitlines() if line.strip()), "")
        return self.fields.get("about") or (first[:80] + ("…" if len(first) > 80 else ""))


def now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def one_line(value: object, limit: int = LINE) -> str:
    return " ".join(str(value or "").split())[:limit]


def parse(path: Path) -> Item | None:
    """A record read back, or None for a file that is not one: no number, or no front matter."""
    named = _NAME.match(path.name)
    if not named:
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    if not text.startswith("---\n"):
        return None
    head, marker, body = text[4:].partition("\n---\n")
    if not marker:
        return None
    fields: dict[str, str] = {}
    for line in head.splitlines():
        key, colon, value = line.partition(":")
        if colon and key.strip():
            fields[key.strip()] = value.strip()
    said, _, proposed = body.partition("\n## Proposed\n")
    return Item(named.group(1), path, fields, said.strip(), proposed.strip())


def write(item: Item) -> None:
    head = "".join(f"{key}: {one_line(value)}\n" for key, value in item.fields.items() if str(value).strip())
    tail = f"\n## Proposed\n\n{item.proposed.strip()}\n" if item.proposed.strip() else ""
    item.path.write_text(f"---\n{head}---\n{item.said.strip()}\n{tail}", encoding="utf-8")


def items(root: Path) -> list[Item]:
    """Every record, newest first."""
    home = root / PLACE
    if not home.is_dir():
        return []
    found = [one for one in (parse(path) for path in home.glob("*.md")) if one is not None]
    return sorted(found, key=lambda one: one.number, reverse=True)


def find(root: Path, number: str) -> Item:
    held = next((one for one in items(root) if one.number == str(number).zfill(4)), None)
    if held is None:
        raise ValueError(f"there is no feedback {number} under {PLACE}")
    return held


def slug_of(words: str) -> str:
    first = next((line for line in words.splitlines() if line.strip()), "feedback")
    return "-".join(_SLUG.sub(" ", first.lower()).split()[:7])[:48].strip("-") or "feedback"


def capture(root: Path, words: str, context: dict[str, object] | None = None) -> Item:
    """Write what a person said as the next record, with the context the board knew when they said it."""
    words = str(words or "").strip()
    if not words:
        raise ValueError("say what using it showed; the record is your words")
    if len(words) > WORDS:
        raise ValueError(f"that is more than {WORDS} characters; split it into two")
    given = {key: one_line(value) for key, value in (context or {}).items() if key in CONTEXT}
    if given.get("slice") and not _SLICE.fullmatch(given["slice"]):
        raise ValueError(f"{given['slice']!r} is not a slice id")
    home = root / PLACE
    home.mkdir(parents=True, exist_ok=True)
    taken = [int(one.number) for one in items(root)]
    number = f"{(max(taken) + 1) if taken else 1:04d}"
    item = Item(number, home / f"{number}-{slug_of(words)}.md",
                {"said": now(), "by": "person", **{key: given[key] for key in CONTEXT if given.get(key)}}, words)
    write(item)
    return item


def untriaged(root: Path) -> list[Item]:
    return [one for one in items(root) if one.state == "triaging"]


def drop(root: Path, number: str) -> str:
    item = find(root, number)
    if item.state == "confirmed":
        raise ValueError(f"feedback {item.number} was already handed on as {item.fields.get('became')}")
    item.fields["dropped"] = now()
    write(item)
    return f"dropped feedback {item.number}"


def chart_fairway(root: Path, feature: str, slice_id: str) -> str:
    """The stream a slice belongs to, from its chart, for a slice no captain has claimed yet."""
    charts = sorted((root / "specs").glob(f"{feature or '*'}/chart.yaml"))
    for chart in charts:
        lines = chart.read_text(encoding="utf-8", errors="replace").splitlines()
        inside = False
        for line in lines:
            if re.match(rf"^\s{{2}}{re.escape(slice_id)}:\s*$", line):
                inside = True
            elif inside and re.match(r"^\s{0,2}\S", line):
                inside = False
            elif inside and (held := re.match(r"^\s+fairway:\s*(\S+)", line)):
                return held.group(1)
    return ""


def told_message(item: Item, route: str, state: str, hold: str) -> str:
    """What the slice's captain is told, addressed to it so the board does not show it as a note for a person."""
    slice_id = item.fields.get("slice", "")
    record = item.path.name
    said = one_line(item.said, 600)
    why = one_line(item.fields.get("becomes", ""), 300)
    merged = state == "done"
    head = f"For the captain, from feedback {item.number} ({PLACE}/{record}), confirmed by a person"
    if route == "defect":
        act = (f"{slice_id} has merged: add a fix slice after it and carry it like any other" if merged
               else f"fix it in {slice_id} before it merges")
        return f"{head}: a defect in {slice_id}. {said} {why} So {act}."
    if route == "planned":
        return (f"{head}: something a person missed while trying the app, which is already planned in {slice_id}. "
                f"{said} Read it when {slice_id} is planned; it changes nothing that has been decided.")
    if merged or state == "todo":
        act = ("amend the specification and the example map first, then carry it as a new slice after "
               f"{slice_id}" if merged else f"amend the specification and the example map before {slice_id} "
               "is planned")
    elif hold == "park":
        act = (f"park {slice_id} at its next boundary with this change as the reason, then amend the "
               "specification and the example map, and carry the new rule instead of finishing the old one")
    else:
        act = (f"leave {slice_id} as it is while it is in flight; once it has merged, amend the specification "
               "and the example map, and carry this as a new slice after it")
    return f"{head}: a change to what {slice_id} was specified to do. {said} {why} So {act}."


def note_design(root: Path, item: Item) -> str:
    path = root / DESIGN
    text = path.read_text(encoding="utf-8") if path.is_file() else "# Design\n"
    if DESIGN_HEADING not in text:
        text = text.rstrip("\n") + (f"\n\n{DESIGN_HEADING}\n\nWhat people said after using the built app, "
                                    "confirmed on the board. A slice with a screen reads these too.\n")
    text = text.rstrip("\n") + f"\n- {one_line(item.said, 600)} (feedback {item.number}, {item.fields['said'][:10]})\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return DESIGN


def confirm(root: Path, number: str, rows: list[dict[str, str]], route: str = "", hold: str = "",
            slice_id: str = "") -> str:
    """Hand one item on, as triage proposed it or as the person routed it instead, and record which."""
    from .deck import tell
    from .project.intake import capture as intake

    item = find(root, number)
    if item.state == "confirmed":
        raise ValueError(f"feedback {item.number} was already handed on as {item.fields.get('became')}")
    if item.state == "dropped":
        raise ValueError(f"feedback {item.number} was dropped")
    chosen = route or item.fields.get("route", "")
    if chosen not in ROUTES:
        raise ValueError(f"route feedback {item.number} first: {', '.join(ROUTES)}")
    if hold and hold not in HOLDS:
        raise ValueError(f"a change in flight is held one of two ways: {', '.join(HOLDS)}")
    if slice_id:
        if not _SLICE.fullmatch(slice_id):
            raise ValueError(f"{slice_id!r} is not a slice id")
        item.fields["slice"] = slice_id
    if chosen == "scope":
        folder, _ = intake(root, item.said)
        became = folder.relative_to(root).as_posix()
    elif chosen == "note":
        became = note_design(root, item)
    else:
        named = item.fields.get("slice", "")
        if not named:
            raise ValueError(f"a {ROUTES[chosen].lower()} is about a slice; name the slice it is in")
        row = next((one for one in rows if one.get("slice") == named), {})
        fairway = row.get("fairway") or chart_fairway(root, item.fields.get("feature", ""), named)
        if not fairway:
            raise ValueError(f"{named} is on no stream's chart here, so no captain can be told")
        tell(root, fairway, told_message(item, chosen, row.get("state", ""), hold), named, by="feedback")
        became = f"told {fairway} about {named}" + (f" ({hold})" if hold else "")
    if route and route != item.fields.get("route"):
        item.fields["routed"] = route
    if hold:
        item.fields["hold"] = hold
    item.fields.update(confirmed=now(), became=became)
    write(item)
    return f"feedback {item.number}: {became}"

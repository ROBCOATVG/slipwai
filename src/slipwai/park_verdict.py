"""Approve and Reject on a card whose block waits on a person's verdict on a mock-up.

manda's S97 waited on a person approving a founder-facing mock-up state, and the only thing its card could do
was chat. The verdict has a record already: `specs/<feature>/mockups/mock-states.md`, which the storyboard's
Approve and Disapprove write through `drawn.record_verdict`. So the card writes that record, the same way, and
then answers the park as a person answers one from the card's own box — a signed message from the person in
the slice's inbox, carrying `park:<instant>` — which the captain turns into the person's `told` and the
harbourmaster clears the park on, by the same rule as any answer, ceiling and all (`logs.answer_held`).

**Only while a drawing waits.** The buttons are offered, and a verdict taken, only where a surface page under
`specs/<feature>/mockups/` has no standing verdict — no block for it in `mock-states.md`, or one on a page
that has changed since. A verdict with nothing new drawn would be a verdict on what a person approved
already, written again as though they had looked at the state the slice waits for.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from . import drawn, talk
from .block_actions import kind_of
from .fleet import fairways, harbour_log, park_row
from .stage_talk import release
from .talk_said import receipt_line, say

VERDICTS = {"approve": "approved", "reject": "parked"}


def awaiting(root: Path, feature: str) -> bool:
    """Whether a surface page drawn for this feature has no standing verdict, so a person's is wanted."""
    return bool(pending(root, feature))


def pending(root: Path, feature: str) -> list[str]:
    """Each surface page drawn for this feature with no standing verdict, by its path in the project — what a
    press of Approve or Reject is about, which the card names, since the record it writes covers the feature."""
    try:
        drawn.drawn_states(root, feature)
    except ValueError:
        return []
    home = root / "specs" / feature / "mockups"
    record = home / "mock-states.md"
    try:
        text = record.read_text(encoding="utf-8") if record.is_file() else ""
    except (OSError, UnicodeDecodeError):
        text = ""
    blocks = drawn.blocks(text)
    by_path = {block["path"]: block for block in blocks if block["path"]}
    # A verdict written before pages were recorded beside it names its surface and no page.
    by_name = {block["name"] for block in blocks if not block["path"]}
    found = []
    for page in drawn.surface_pages(home):
        block = by_path.get(drawn.where_in(root, page))
        if (block is None and drawn.decided_states(page)[0] not in by_name) or \
                (block is not None and drawn.stale(root, block)):
            found.append(drawn.where_in(root, page))
    return found


def mark(root: Path, found: dict[str, Any]) -> dict[str, Any]:
    """The board with `ready` on every mock-up action — whether its card may offer Approve and Reject now — and
    the `pages` a verdict would be given on.

    The actions are the rows' own dicts, which the groups hold too, so one mark reaches every card drawn."""
    asked: dict[str, list[str]] = {}
    for row in [*(found.get("inbox") or []), *(found.get("groups") or [])]:
        action = row.get("action") if isinstance(row, dict) else None
        if isinstance(action, dict) and "verdict" in action:
            feature = str(action["verdict"])
            if feature not in asked:
                asked[feature] = pending(root, feature) if feature else []
            action["ready"], action["pages"] = bool(asked[feature]), asked[feature]
    return found


def the_park(root: Path, fairway: str, of: str) -> dict[str, Any]:
    """The open park `of` names, as the board lists it, refused unless it waits on a mock-up verdict."""
    stamp = of.removeprefix("park:")
    one = next((stream for stream in fairways(root, harbour_log(root))[0] if stream.name == fairway), None)
    park = next((e for e in one.parks if e.t == stamp), None) if one is not None and of.startswith("park:") else None
    if one is None or park is None:
        raise ValueError(f"{fairway} has no open park at {stamp or '(none named)'}: it may have cleared already")
    row = park_row(one, park, False)
    if kind_of(row) != "mockup":
        raise ValueError(f"the park at {stamp} does not wait on a mock-up verdict; answer it from its box")
    return row


def give(root: Path, fairway: str, slice_id: str, of: str, feature: str, verdict: str, reason: str = "") -> str:
    """Write a person's verdict on the drawing a park waits on, then answer the park with it from the card.

    `verdict` is `approve` or `reject`; a reject carries one line on what to change, which `record_verdict`
    refuses to go without. Answers what the message's receipt says, as the card's own box does."""
    if verdict not in VERDICTS:
        raise ValueError("a verdict on a card is approve or reject")
    why = " ".join(reason.split())
    if verdict == "reject" and not why:
        raise ValueError("say in one line what to change, so the next drawing knows")
    the_park(root, fairway, of)
    if not awaiting(root, feature):
        raise ValueError(f"nothing under specs/{feature}/mockups waits on a verdict: run `/mockups {feature}` "
                         f"to draw the state first")
    drawn.record_verdict(root, feature, VERDICTS[verdict], why)
    release(root, "mockups")  # a verdict is the person's word to carry on from the drawing, as on the storyboard
    text = (f"Approved the drawn mock-up states of {feature}: specs/{feature}/mockups/mock-states.md records it"
            if verdict == "approve" else
            f"Rejected the drawn mock-up states of {feature}: {why} (specs/{feature}/mockups/mock-states.md "
            f"records it)")
    sent = say(root, fairway, slice_id, text, "wait", talk.PERSON, of)
    return receipt_line(root, fairway, slice_id, sent)

"""Feedback's *New scope*, as the second door into the hand-over: one conversation, started from an item's words.

Confirming an item as new scope used to write its words straight under `docs/intake/`: nobody asked whether
it was one feature or three, and a document could not ride along. On the board it now opens the hand-over's
conversation (`intake_talk.py`) with the item's words as the person's first, on the Next features tab, where a
document is attached as it is to any other turn. Nothing is copied: the conversation, its limits, its capture
and its card are the ones that tab already had.

**The link is the item's own record.** The conversation keeps the item's number beside its first words, and
`Capture this idea` confirms the item with `became: docs/intake/<slug>` (`feedback.py`), exactly what New scope
wrote before. Until then the item is still a proposal on the Feedback tab; *Start again* lets go of the
conversation and leaves it one.

The words are a stranger's twice over — typed on a page, then read by an agent — and are held to what any
first message is held to (`intake_document.py`).
"""
from __future__ import annotations

from pathlib import Path

from .feedback import ROUTES, find
from .intake_talk import for_root
from .passage import specifications

#: The tab the conversation is on, said in every answer so the page knows to show it.
WHERE = "the Next features tab"


def new_scope(root: Path, number: str) -> str:
    """Open the hand-over from one feedback item, or say why not. One conversation a project: an open one is
    finished or let go of first, rather than given a second item's words."""
    item = find(root, number)
    if item.state in ("confirmed", "dropped"):
        ended = "handed on" if item.state == "confirmed" else "dropped"
        raise ValueError(f"feedback {item.number} was already {ended}")
    if not specifications(root):
        raise ValueError("this project has no specification yet: its first feature is drafted from docs/prd.md, "
                         f"and {ROUTES['scope'].lower()} is a further one")
    talk = for_root(root)
    held = talk.said()
    if held["open"]:
        raise ValueError(f"feedback {item.number} is already in the hand-over on {WHERE}" if held["feedback"]
                         == item.number else f"a hand-over is already open on {WHERE}: capture it or press Start "
                         f"again there, then confirm feedback {item.number} as new scope")
    talk.ask(item.said, feedback=item.number)
    return (f"feedback {item.number} is in the hand-over on {WHERE}: say more or attach its document there, and "
            "capture it once the agent says the idea is ready")

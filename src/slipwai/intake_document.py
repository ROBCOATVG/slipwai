"""A document a person attaches to a further feature on the board: checked, then held until it is captured.

A page cannot hand over a path (`folder_choice.py` says why), so the Next features tab reads the chosen file
in the browser and posts its name and its text, as the first page's file input does. Everything posted is a
stranger's: the name is held to a plain file name, so it cannot climb out of the folder it is written to or
stand in for a file intake reads as an answer (`confirmed`, `specified.json`, `brief.md`); the text is held to
text, and to a size a conversation can carry.

A document that passes is written under the run's own folder, where the hand-over's session can read it and
nothing reads it as part of the project. `project/intake.py`'s `capture` copies it beside `brief.md` from
there, by path, exactly as it copies a document `/sail` was pointed at: one way in.
"""
from __future__ import annotations

import re
from pathlib import Path

from .project.intake import BRIEF, CONFIRMED, RECEIPT

#: Bytes one document, or one message, may be, as UTF-8: a long requirements document is a tenth of this, and
#: the whole of it rides in an agent's context when it is read.
LIMIT = 256 * 1024
#: Documents one idea may carry.
MOST = 5
#: The conversation as `capture` keeps it beside the brief, where a person answered something after the first
#: message. Not a name a document may take.
TRANSCRIPT = "conversation.md"
#: A plain file name: letters, digits, and the few marks a document's name has, starting with a letter or digit.
NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._()-]{0,79}$")
#: Names Windows keeps for devices, whatever follows the dot.
DEVICES = frozenset(("con", "prn", "aux", "nul", *(f"com{n}" for n in range(1, 10)),
                     *(f"lpt{n}" for n in range(1, 10))))
#: What intake itself writes in an idea's folder; a document called one of these would be read as it.
RESERVED = frozenset(one.lower() for one in (BRIEF, CONFIRMED, RECEIPT, TRANSCRIPT))
#: Control characters text does not carry: everything below a space but tab, line feed, form feed and return.
BINARY = re.compile(r"[\x00-\x08\x0b\x0e-\x1f]")


def named(name: str) -> str:
    """The name a posted document is kept under, or the refusal. Never a path: no separator, no leading dot."""
    name = name.strip()
    if not NAME.match(name) or name.endswith((".", " ")) or ".." in name:
        raise ValueError("a document's name is a plain file name: letters, digits, spaces, and . _ - ( ), "
                         "with no folder in it; rename the file and choose it again")
    if name.lower() in RESERVED or name.split(".", 1)[0].lower() in DEVICES:
        raise ValueError(f"{name} is a name intake keeps for itself; rename the file and choose it again")
    return name


def text_of(text: str, what: str = "the document") -> str:
    """Posted words held to text of a size a session can read, or the refusal."""
    if len(text.encode("utf-8", errors="replace")) > LIMIT:
        raise ValueError(f"{what} is more than {LIMIT // 1024} KB; hand over a shorter one, or hand the feature "
                         "to /sail in the agent, which reads a file of any size where it is")
    if BINARY.search(text) or "�" in text:
        raise ValueError(f"{what} does not read as text; a document here is Markdown or plain text")
    return text


def held(folder: Path) -> list[Path]:
    """The documents waiting in `folder`, by name."""
    return sorted(one for one in folder.iterdir() if one.is_file()) if folder.is_dir() else []


def staged(folder: Path, name: str, text: str) -> Path:
    """One posted document written under `folder`, checked first. A second by a name already held, in any
    case, is a refusal rather than an overwrite."""
    name, text = named(name), text_of(text)
    if not text.strip():
        raise ValueError(f"{name} is empty")
    waiting = held(folder)
    if any(one.name.lower() == name.lower() for one in waiting):
        raise ValueError(f"{name} is attached already; rename the file to attach another")
    if len(waiting) >= MOST:
        raise ValueError(f"an idea carries {MOST} documents at most; capture this one and hand over the rest "
                         "as another")
    path = (folder / name).resolve()
    if path.parent != folder.resolve():  # belt and braces: `named` has already refused anything that climbs
        raise ValueError(f"{name} is not a plain file name")
    folder.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="")
    return path

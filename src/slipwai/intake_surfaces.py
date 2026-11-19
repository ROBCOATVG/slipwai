"""The surfaces a handed-over idea seems to touch: named by the hand-over's agent, kept with the idea as a hint.

A further feature is drawn into the project's storyboard, and the first question that stage has is which of
the surfaces already there the feature changes. The hand-over's agent has just read the project and the idea,
so it is asked to say: one line, just before the line that says the idea is ready, naming them by the names
the project uses. The board keeps what that line named as `docs/intake/<slug>/surfaces.json`
(`project/intake.py` writes it, and says its shape).

**A suggestion and never an answer.** An agent that read a few files said what it thought; nobody checked it
against the app, and a name here need not be a surface that exists. The file says so in itself
(`"authoritative": false`), nothing in the keel acts on it, and the storyboard stage is free to start from it
and to end somewhere else.

What the agent said is a stranger's: only that one line of its last reply is read, each name is held to one
short line of text, and there are only so many. No name becomes a path or anything the board does.
"""
from __future__ import annotations

#: How the line begins, exactly: the role tells the agent, and nothing else in a reply is read for surfaces.
HEAD = "Surfaces it seems to touch:"
#: How many names are kept, and how long one may be.
MOST, LONG = 12, 80
#: What the hand-over's role says about it (`intake_talk.py`), kept here beside the line it asks for.
ASK = f"""Where the idea seems to change screens or other surfaces this project already has, name them on one
line just before that last line, exactly as `{HEAD} <name>; <name>`, by the names the project uses: a
`## Surface:` heading under `specs/*/mockups/`, a screen, a route. It is a suggestion the storyboard stage
starts from and may change. Leave the line out where it touches none or you cannot tell."""


def suggested(replies: list[str]) -> list[str]:
    """The names on that line of the agent's last reply, in the order it gave them, or none."""
    last = replies[-1] if replies else ""
    line = next((one.strip() for one in reversed(last.splitlines()) if one.strip().startswith(HEAD)), "")
    names: list[str] = []
    for part in line[len(HEAD):].split(";"):
        plain = "".join(" " if one == "`" or ord(one) < 32 else one for one in part)
        name = " ".join(plain.split()).rstrip(" .")[:LONG].strip()
        if name and name.lower() not in (one.lower() for one in names):
            names.append(name)
    return names[:MOST]

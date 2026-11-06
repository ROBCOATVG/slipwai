"""The one shape a refusal has: what is wrong, and the command that puts it right.

Version 1 wrote its refusals by hand, one f-string at a time, and the experiment then needed nine test
files to hold their wording — `test_refusals_verbs.py`, `test_refusals_loader.py`,
`test_refusals_name_the_fix.py` and six more — because nothing but a test could tell whether a given
refusal had remembered to name the fix. A type remembers for them.

A `Fault` is one thing that is wrong and, where a command would put it right, that command. A `Refusal`
carries every fault found rather than the first, says them in one line, and ends that line with the
command. `refuse` is how a verb reports one: `slipwai <verb>: error: <line>` on stderr and exit status 2,
with no `usage:` block — a refusal about the machine or the project is not about the command line, and a
usage block under it says it was. argparse's own errors keep theirs.

One line, always. A package's name, a path, or a backend key may hold a newline; `one_line` writes it out
as its escape rather than letting it break the shape a reader and a log parser both depend on.
"""
from __future__ import annotations

import sys
from collections.abc import Sequence
from dataclasses import dataclass
from typing import NoReturn


class GenerationError(RuntimeError):
    """Something the keel cannot do, said in one line. Every refusal the keel raises derives from this."""


@dataclass(frozen=True)
class Fault:
    """One thing that is wrong, and the command that puts it right where a command can.

    `wrong` is a fragment, not a sentence: no leading capital and no full stop, because it is joined with
    others. `fix` is a command a reader can paste. It is `None` only where no command exists — a value the
    person has to choose, a service that has to come back — and then the fault says what to do in `wrong`.
    """

    wrong: str
    fix: str | None = None

    def __str__(self) -> str:
        return one_line(self.wrong if self.fix is None else f"{self.wrong}. Run: {self.fix}")


class Refusal(GenerationError):
    """Every fault found, in one line. Never the first fault alone: a reader who fixes one and is handed
    the next has paid for the round trip the keel could have saved them.

    Faults that share a fix name it once, at the end, so the line ends with the command. Faults with
    different fixes carry their own, because there is no one command to end with.
    """

    def __init__(self, *faults: Fault | str) -> None:
        self.faults: Sequence[Fault] = tuple(f if isinstance(f, Fault) else Fault(f) for f in faults)
        super().__init__(str(self))

    def __str__(self) -> str:
        if not self.faults:
            return "refused, with no fault given"
        fixes = {fault.fix for fault in self.faults}
        if len(fixes) == 1 and (shared := self.faults[0].fix) is not None:
            return one_line("; ".join(fault.wrong for fault in self.faults) + f". Run: {shared}")
        return "; ".join(str(fault) for fault in self.faults)


def refuse(prog: str, message: object) -> NoReturn:
    """A verb's refusal: `<prog>: error: <message>` on stderr and exit status 2, with no `usage:` block.

    `message` is a `Refusal`, a `Fault`, or anything with a `__str__`; `one_line` is applied here too, so a
    caller that builds its own string cannot break the shape either.
    """
    print(f"{prog}: error: {one_line(str(message))}", file=sys.stderr)
    raise SystemExit(2)


def one_line(text: str) -> str:
    """`text` with every character a line splits on written out as its escape, so that it stays one line."""
    return "".join(ch.encode("unicode_escape").decode() if len(f"a{ch}b".splitlines()) > 1 else ch for ch in text)


def said(error: BaseException) -> str | None:
    """An exception's text, or None where the text cannot be made. `__str__` is the package's code too; whatever
    it raises (`SystemExit(0)` included) is not the verb's."""
    try:
        return str(error)
    except BaseException as unprintable:  # any of it; only the user's interrupt is let through
        if isinstance(unprintable, KeyboardInterrupt):
            raise
        return None


def failure(error: BaseException) -> str:
    """How an exception a package raised is said: its type and its text, or its type alone where the text cannot
    be made."""
    text = said(error)
    return type(error).__name__ if text is None else f"{type(error).__name__}: {text}"


def blame(error: BaseException) -> str:
    """`failure(error)` for anything a package's code raised, which is every exception but the user's own: a
    `KeyboardInterrupt` propagates. A package that calls `sys.exit`, or raises `GeneratorExit` or an exception
    of its own deriving from `BaseException`, has ended nothing but itself."""
    if isinstance(error, KeyboardInterrupt):
        raise error
    return failure(error)


class Busy(ValueError):
    """A conversation's turn is under way, so a second message cannot go in yet. Not a refusal of the
    message: the page waits and sends it when the turn ends, however many windows are open on the run."""

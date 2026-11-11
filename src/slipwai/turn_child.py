"""A turn's child heard to its end, and every way it can end said.

The sketch and the console each run one turn of the coding agent as a child and read its stream. A turn that
ended badly said so only where the child had said nothing at all, so a child stopped at the time limit after
it had spoken, one that crashed half way through an answer, and one whose reader failed in the board itself
each ended in silence: the page showed a conversation that had simply stopped, and the person asked it why.
This module is the one place a child is heard, so the two cannot differ in what they leave unsaid.
"""
from __future__ import annotations

import subprocess
import threading
from collections.abc import Callable, Sequence


def ending(status: int, answered: bool, late: bool, limit: int, aside: Sequence[str]) -> str | None:
    """Why a turn's child ended, in a sentence, or None where it ended well. Every other ending is said. A
    child stopped at the limit after it had spoken, one that crashed half way through an answer, and one that
    left with nothing at all each ended in silence: the page showed a conversation that had simply stopped.
    `aside` is the last of what it printed that was not its stream — where an agent says what went wrong."""
    printed = f" The last it printed: {' / '.join(aside)}" if aside else ""
    if late:
        return f"This answer was stopped after {limit // 60} minutes, before it was finished."
    if status:
        return (f"The session ended with status {status} "
                + ("before the answer was finished." if answered else "and said nothing.") + printed)
    return None if answered else "The session ended without an answer." + printed


def unheard(fault: BaseException) -> str:
    """What is said where the board itself failed while hearing a session, which it then stopped."""
    return ("The board stopped hearing the session, and stopped it rather than leave it running unseen: "
            f"{type(fault).__name__}: {fault}")


def to_its_end(child: subprocess.Popen[str], take: Callable[[str], bool], limit: int) -> tuple[bool, str | None]:
    """A turn's child heard to its end: whether it had words for the person, and why it ended where it did
    not end well (`ending`). A child the board can no longer hear is stopped before the failure is raised:
    the first one outlived its reader by ten minutes, editing files with nobody listening."""
    late = threading.Event()

    def stopped() -> None:
        late.set()
        child.kill()

    timer = threading.Timer(limit, stopped)
    timer.start()
    answered = False
    aside: list[str] = []
    try:
        for line in child.stdout or []:
            answered = take(line) or answered
            if line.strip() and not line.lstrip().startswith("{"):
                aside = [*aside, line.strip()[:200]][-3:]
        child.wait()
    except BaseException:
        child.kill()
        raise
    finally:
        timer.cancel()
    return answered, ending(child.returncode, answered, late.is_set(), limit, aside)

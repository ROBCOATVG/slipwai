"""What this machine has of each tool, asked off the request, once, and kept.

`prerequisites.found` asks a tool its version by running it, and a page that waited for that waited for the
slowest tool on the machine: twelve seconds on a Windows runner, for a page whose own content was ready at
once. So nothing a page is made of asks a tool any more. A page reads `MACHINE`, which answers at once with
what it knows — a tool it has not heard from yet is `checking` — and asks the tools on threads of their own,
one each, so a slow one holds neither the others nor the page. The page's own poll reads again until every
tool has said something (`machine_card`).

**One asking at a time.** A read while tools are still being asked starts nothing: it is given what has
answered so far. The count of threads still out is the single flight, held under the one lock.

**Kept, for two lengths of time.** A good copy is kept `KEEP` seconds — five minutes, which is how long the
login shell's own `PATH` is kept (`shell_environment.LOGIN_KEPT`): a tool's place is read off that `PATH`,
so an answer kept longer would outlive what it was read from. Anything else — missing, too old — is kept
only `RETRY` seconds, because the card tells a person to install it and reload: long enough that a page and
the poll that fills it in are one asking, short enough that the reload after an install is asked afresh.
The board's own install drops its tool's answer the moment it lands (`forget`).

**A bound per tool.** One that has not answered `BOUND` seconds after it was asked is `unanswered`, said in
words, and what it says later is not taken: `found` gives up on a tool at twenty seconds and reports that as
missing, and a tool that hung is not a tool the machine lacks. Fifteen is over the twelve the slowest honest
answer has been seen to take and under that twenty. It is asked again by the next read after its thread is
back.
"""
from __future__ import annotations

import threading
import time
from collections.abc import Callable
from functools import partial

from .prerequisites import TOOLS, Found, Tool, found

#: The two things a tool can be besides what `Found` already says: asked and not heard from yet, and not
#: heard from within the bound.
CHECKING, UNANSWERED = "checking", "unanswered"
KEEP, RETRY, BOUND = 300.0, 5.0, 15.0


def on_a_thread(work: Callable[[], None]) -> None:
    threading.Thread(target=work, daemon=True).start()


class Machine:
    """The tools' answers, behind one lock. `look`, `clock` and `start` are a test's to give: a stand-in for
    the tool, the time, and whether an asking runs on a thread at all."""

    def __init__(self, look: Callable[[Tool], Found] | None = None, clock: Callable[[], float] = time.monotonic,
                 start: Callable[[Callable[[], None]], None] = on_a_thread) -> None:
        self.look, self.clock, self.start = look, clock, start
        self.lock = threading.Lock()
        self.kept: dict[str, tuple[float, Found]] = {}
        self.began = 0.0
        self.out = 0

    def fresh(self, key: str, now: float) -> bool:
        held = self.kept.get(key)
        return held is not None and now - held[0] < (KEEP if held[1].state == "found" else RETRY)

    def read(self) -> list[Found]:
        """Every tool, in the table's order, as it stands now; and the ones with no answer worth keeping
        asked again, unless an asking is still out."""
        with self.lock:
            now = self.clock()
            stale = [] if self.out else [tool for tool in TOOLS if not self.fresh(tool.key, now)]
            for tool in stale:
                self.kept.pop(tool.key, None)
            if stale:
                self.began, self.out = now, len(stale)
            began = self.began
        for tool in stale:  # outside the lock: an asking that answers at once takes it to say so
            self.start(partial(self.ask, tool, began))
        with self.lock:
            now = self.clock()
            return [self.kept[tool.key][1] if tool.key in self.kept
                    else Found(tool, UNANSWERED if now - self.began >= BOUND else CHECKING) for tool in TOOLS]

    def ask(self, tool: Tool, began: float) -> None:
        one = None
        try:
            one = (self.look or found)(tool)
        finally:  # whatever became of it, it is no longer out: an asking that faulted must not be the last
            with self.lock:
                self.out -= 1
                now = self.clock()
                if one is not None and now - began < BOUND:
                    self.kept[tool.key] = (now, one)

    def forget(self, key: str) -> None:
        """Drop one tool's answer: the board has just installed it, and the next read asks it again."""
        with self.lock:
            self.kept.pop(key, None)


#: The one reading every page of this board shares.
MACHINE = Machine()

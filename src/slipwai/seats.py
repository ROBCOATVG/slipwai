"""Who is looking at what, on one board: a seat per window, and a record per project of what is under way.

The bridge served one directory for as long as it kept `root` on its handler class. A second window opened
on the same board looked wherever the first one had pointed it, and a generate in one tab moved every other
tab with it. This is the table that fixed that, and the reason it is a module is that it holds the one piece
of state the board has: every route in `bridge.py` is a fold of files on disk, and this is not.

**A seat is a window, and it owns one thing.** Where a person is looking is a property of the person, so it
is a seat's. Everything else the board shows — the streams, the logs, the telegraph, the fine tune — is read
off disk at that directory on every request, which is why two seats pointed at the same project are two
views of one run rather than two runs.

**An outfit is a project, and it is keyed by one.** `./init`, the draft, the launch, the cast-off and the
stop are things that happen to a tree. There is one of each per tree and not one per person watching it, so
a second window on the same project sees the child that is running rather than being offered a second — and
`launched` stays what it was there to be, which is the reason a fleet is never cast off twice.
"""
from __future__ import annotations

import threading
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path

from .init_run import Fitting

#: How many seats are kept. A seat is minted for every window that loads the board without one, and a board
#: a login service has kept running for a month would otherwise hold every window anybody had ever opened on
#: it. The least recently used is let go of first, and letting one go costs nothing a person can see: a
#: window whose seat has been forgotten is given a new one at the directory the board was started in, which
#: is where a window that has just been opened starts anyway.
SEATS = 64


@dataclass
class Seat:
    """One window on a board, and the one thing about it that is the window's own."""

    root: Path


@dataclass
class Outfit:
    """What a board has started in one project: the child running there, and whether that project's build
    has been continued from this board.

    `launched` is shown-once rather than a count: a fleet cast off twice is two harbourmasters, which
    `fleet.py` refuses, and the refusal reads as a fault rather than as an answer.
    """

    fitting: Fitting | None = None
    launched: bool = False


class Bench:
    """One board's windows, and what is under way in each project they have been pointed at.

    An object per server rather than attributes on the handler class, because a mutable default on a base
    class is one dictionary however many subclasses inherit it — and `bridge.serve` makes a subclass per
    server, so two boards in one process would otherwise be one board's windows seen through two ports.

    The lock is around the seat table because the board polls: a voyage window asks twice a second, several
    windows are in the server at once, and `move_to_end` on a key another thread has just let go of is a
    500 on a page that was only reloading.
    """

    def __init__(self, start: Path) -> None:
        #: Where a seat starts looking: the directory the board was started in. It is not where the board
        #: is looking, because the board is not looking anywhere — its windows are.
        self.start = start
        self.seats: OrderedDict[str, Seat] = OrderedDict()
        self.outfits: dict[Path, Outfit] = {}
        self.lock = threading.Lock()

    def seat(self, named: str) -> Seat:
        """The window carrying that id, minted where it is one this board has not seen.

        An unseen id is a new window rather than a fault: a board restarted under an open window, or a seat
        let go of to stay under `SEATS`, would otherwise answer a reload with a refusal, and a refusal is
        the one thing a person sitting in front of a page cannot act on. `''` is a seat too — the one a
        poller, a `curl` and the suite sit in, reading the board the way it was read before windows had
        names.
        """
        with self.lock:
            if named in self.seats:
                self.seats.move_to_end(named)
                return self.seats[named]
        return self.sit(named, self.start)

    def sit(self, named: str, root: Path) -> Seat:
        """A window added, the least recently used let go of where there are now too many."""
        with self.lock:
            self.seats[named] = Seat(root=root)
            self.seats.move_to_end(named)
            while len(self.seats) > SEATS:
                self.seats.popitem(last=False)
            return self.seats[named]

    def outfit(self, root: Path, starting: bool = False) -> Outfit:
        """What is under way in that project, by its resolved path — so two seats that spell the same
        directory differently are still looking at the one run.

        `starting` is the writers' and nobody else's. Reading is not a reason to remember a directory, and
        a board that recorded every tree it was ever pointed at would hold a record of nothing per window
        per harbour for as long as a login service kept it running. A reader gets an empty one of its own,
        which says what is true: nothing is under way there.
        """
        where = root.resolve()
        held = self.outfits.get(where)
        if held is None and starting:
            with self.lock:
                held = self.outfits.setdefault(where, Outfit())
        return held if held is not None else Outfit()


def parameter(query: str, name: str) -> str:
    """One named value out of a query string, or `''` where it is not there.

    Its own function rather than `urllib.parse`'s, for the reason the rest of this server is what it is:
    two names are read out of a query here and both are the board's own, so the whole of the parsing is
    the three lines it takes. A repeated name is the first one; a malformed pair is nothing.
    """
    for pair in query.split("&"):
        this, _, value = pair.partition("=")
        if this == name:
            return value
    return ""
